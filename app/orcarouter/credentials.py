"""The credential seam: one interface, two adapters, one credential shape.

``CredentialAdapter.acquire()`` is the only thing the rest of the program knows
about. :class:`ApiKeyAdapter` takes a pasted/configured ``sk-orca-...`` key;
:class:`PkceAdapter` runs OAuth 2.0 + PKCE and receives the very same kind of
key back. Downstream code - the OpenAI client, the model catalog, the agent
profiles - receives an :class:`OrcaCredential` and never inspects
``OrcaCredential.source`` to decide how to talk to OrcaRouter.
"""

from typing import Callable, Dict, Optional

from app.orcarouter.constants import (
    ACCEPTED_SCOPES,
    API_KEY_PROVIDER,
    PKCE_PROVIDER,
    OrcaOrigins,
    api_key_from_env,
    api_key_prefix_ok,
    looks_like_placeholder,
    resolve_origins,
)
from app.orcarouter.errors import OrcaConfigError
from app.orcarouter.pkce import (
    DEFAULT_APP_NAME,
    DEFAULT_TIMEOUT,
    LoopbackReceiver,
    PkceAttempt,
    acquire_with_pasted_code,
    acquire_with_receiver,
    new_attempt,
    new_oob_attempt,
)
from app.orcarouter.store import CredentialStore, mask_key


SOURCE_API_KEY = "api_key"
SOURCE_PKCE = "pkce"


class OrcaCredential:
    """A usable OrcaRouter credential plus its non-secret bookkeeping."""

    __slots__ = (
        "api_key",
        "source",
        "scope",
        "account_id",
        "user_id",
        "generation",
    )

    def __init__(
        self,
        api_key: str,
        source: str,
        scope: str = "api",
        account_id: str = "default",
        user_id: Optional[str] = None,
        generation: int = 0,
    ):
        self.api_key = api_key
        self.source = source
        self.scope = scope
        self.account_id = account_id or "default"
        self.user_id = user_id
        self.generation = int(generation or 0)

    @property
    def masked(self) -> str:
        return mask_key(self.api_key)

    def __repr__(self) -> str:  # pragma: no cover - keep the key out
        return (
            f"OrcaCredential(source={self.source!r}, scope={self.scope!r}, "
            f"account_id={self.account_id!r}, generation={self.generation}, "
            f"key={self.masked!r})"
        )

    __str__ = __repr__


class CredentialAdapter:
    """The seam. Adapters acquire a credential; nothing else differs."""

    source = ""

    def acquire(self) -> OrcaCredential:  # pragma: no cover - interface
        raise NotImplementedError

    def interactive(self) -> bool:
        """True when acquiring may prompt or open a browser."""
        return False


def _poster(timeout: float = 30.0) -> Callable[[str, Dict[str, str]], tuple]:
    """A JSON POST helper returning ``(status, text)`` and never a secret."""

    def post(url: str, body: Dict[str, str]) -> tuple:
        import httpx

        response = httpx.post(url, json=body, timeout=timeout)
        return response.status_code, response.text

    return post


class ApiKeyAdapter(CredentialAdapter):
    """Paste, configure or prompt for an existing ``sk-orca-...`` key."""

    source = SOURCE_API_KEY
    provider_id = API_KEY_PROVIDER

    def __init__(
        self,
        store: Optional[CredentialStore] = None,
        api_key: Optional[str] = None,
        environ: Optional[Dict[str, str]] = None,
        prompt: Optional[Callable[[str], str]] = None,
        interactive: bool = False,
    ):
        self.store = store if store is not None else CredentialStore()
        self._explicit = api_key
        self._environ = environ
        self._prompt = prompt
        self._interactive = interactive

    def interactive(self) -> bool:
        return self._interactive

    def resolve_input(self) -> Optional[str]:
        """The key this adapter would use: argument, env, stored, prompt."""
        candidate = self._explicit
        if looks_like_placeholder(candidate or ""):
            candidate = None
        if candidate is None:
            candidate = api_key_from_env(self._environ)
        if candidate is None and self._interactive and self._prompt is not None:
            answer = self._prompt(
                "OrcaRouter API key (sk-orca-...), or leave empty to keep the "
                "stored credential: "
            )
            if answer and not looks_like_placeholder(answer):
                candidate = answer.strip()
        if candidate is None:
            stored = self.store.load()
            if stored and stored.get("api_key") and not stored.get("needs_reauth"):
                candidate = stored["api_key"]
        return candidate or None

    def acquire(self) -> OrcaCredential:
        key = self.resolve_input()
        if not key:
            raise OrcaConfigError(
                "No OrcaRouter API key found. Set api_key in config.toml, export "
                "ORCAROUTER_API_KEY, or run `orcarouter login --api-key sk-orca-...`. "
                "Create a key at https://www.orcarouter.ai/console."
            )
        if not api_key_prefix_ok(key):
            # A shape check only: an sk-orca- prefix is not proof of validity.
            raise OrcaConfigError(
                "That does not look like an OrcaRouter API key (expected an "
                "sk-orca-... value). Nothing was stored."
            )
        record = self.store.save(key, source=SOURCE_API_KEY, scope="api")
        return OrcaCredential(
            api_key=record["api_key"],
            source=SOURCE_API_KEY,
            scope=record.get("scope", "api"),
            account_id=record.get("account_id", "default"),
            generation=record.get("generation", 0),
        )


class PkceAdapter(CredentialAdapter):
    """Sign in with an OrcaRouter account (OAuth 2.0 authorization code + PKCE).

    The issued credential is a durable OrcaRouter API key, not a refresh token:
    it is reused until OrcaRouter revokes it. There is no refresh grant here,
    and none is invented.
    """

    source = SOURCE_PKCE
    provider_id = PKCE_PROVIDER

    def __init__(
        self,
        store: Optional[CredentialStore] = None,
        origins: Optional[OrcaOrigins] = None,
        environ: Optional[Dict[str, str]] = None,
        poster: Optional[Callable[[str, Dict[str, str]], tuple]] = None,
        open_browser: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
        app_name: str = DEFAULT_APP_NAME,
        on_url: Optional[Callable[[str], None]] = None,
        code_reader: Optional[Callable[[], str]] = None,
        reuse_stored: bool = True,
        scope: str = "api",
        receiver_factory: Optional[Callable[[], object]] = None,
    ):
        self.store = store if store is not None else CredentialStore()
        self.origins = origins or resolve_origins(environ)
        self._poster = poster or _poster()
        self._open_browser = open_browser
        self._timeout = timeout
        self._app_name = app_name
        self._on_url = on_url
        self._code_reader = code_reader
        self._reuse_stored = reuse_stored
        self._scope = scope
        self._receiver_factory = receiver_factory or (
            lambda: LoopbackReceiver("127.0.0.1")
        )

    def interactive(self) -> bool:
        return True

    def stored(self) -> Optional[OrcaCredential]:
        """The persisted PKCE credential, when one is usable."""
        record = self.store.load()
        if not record:
            return None
        if record.get("source") != SOURCE_PKCE:
            return None
        if record.get("needs_reauth"):
            return None
        key = record.get("api_key")
        if not key:
            return None
        return OrcaCredential(
            api_key=key,
            source=SOURCE_PKCE,
            scope=record.get("scope", "api"),
            account_id=record.get("account_id", "default"),
            user_id=record.get("user_id"),
            generation=record.get("generation", 0),
        )

    def acquire(
        self,
        use_loopback: bool = True,
        code_reader: Optional[Callable[[], str]] = None,
        receiver_factory: Optional[Callable[[], object]] = None,
    ) -> OrcaCredential:
        """Acquire a credential, reusing the stored one when it is still good.

        ``receiver_factory`` lets a caller (or a test) supply its own loopback
        receiver; it must expose ``port``, ``start(state)``, ``wait(timeout)``
        and ``close()``.
        """
        if self._reuse_stored:
            existing = self.stored()
            if existing is not None:
                return existing

        attempt: PkceAttempt
        if use_loopback:
            receiver = (receiver_factory or self._receiver_factory)()
            attempt = new_attempt(f"http://127.0.0.1:{receiver.port}/cb")
            try:
                payload = acquire_with_receiver(
                    self.origins,
                    self._poster,
                    attempt,
                    receiver,
                    timeout=self._timeout,
                    open_browser=self._open_browser,
                    app_name=self._app_name,
                    scope=self._scope,
                    on_url=self._on_url,
                )
            finally:
                receiver.close()
        else:
            attempt = new_oob_attempt()
            reader = code_reader or self._code_reader
            if reader is None:
                raise OrcaConfigError(
                    "Out-of-band authorization needs a way to read the code."
                )
            payload = acquire_with_pasted_code(
                self.origins,
                self._poster,
                attempt,
                reader,
                app_name=self._app_name,
                scope=self._scope,
                open_browser=self._open_browser,
                on_url=self._on_url,
            )

        return self._persist(payload)

    def _persist(self, payload: Dict[str, object]) -> OrcaCredential:
        record = self.store.save(
            payload["key"],
            source=SOURCE_PKCE,
            scope=payload.get("scope", "api"),
            account_id=payload.get("account_id") or "default",
            user_id=payload.get("user_id"),
        )
        return OrcaCredential(
            api_key=record["api_key"],
            source=SOURCE_PKCE,
            scope=record.get("scope", "api"),
            account_id=record.get("account_id", "default"),
            user_id=record.get("user_id"),
            generation=record.get("generation", 0),
        )

    def acquire_with_code(self, code: str) -> OrcaCredential:
        """Complete a login with a code the user pasted (S256 still applies)."""
        attempt = new_oob_attempt()
        payload = acquire_with_pasted_code(
            self.origins,
            self._poster,
            attempt,
            lambda: code,
            app_name=self._app_name,
            scope=self._scope,
            open_browser=False,
            on_url=self._on_url,
        )
        return self._persist(payload)


def resolve_credential(
    provider_id: str,
    store: Optional[CredentialStore] = None,
    environ: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    allow_login: bool = True,
    **kwargs,
) -> OrcaCredential:
    """Acquire a credential for either OrcaRouter provider id.

    Both branches return the same object shape; callers must not need to know
    which adapter produced it.
    """
    if provider_id in (API_KEY_PROVIDER, "orcarouter_api"):
        adapter: CredentialAdapter = ApiKeyAdapter(
            store=store, api_key=api_key, environ=environ
        )
        return adapter.acquire()
    if provider_id in (PKCE_PROVIDER, "orcarouter_oauth"):
        pkce = PkceAdapter(
            store=store, environ=environ, open_browser=allow_login, **kwargs
        )
        return pkce.acquire()
    raise OrcaConfigError(f"{provider_id!r} is not an OrcaRouter provider id.")


def stored_credential(
    store: Optional[CredentialStore] = None,
    environ: Optional[Dict[str, str]] = None,
) -> Optional[OrcaCredential]:
    """Any usable stored credential, regardless of which adapter stored it."""
    store = store if store is not None else CredentialStore()
    record = store.load()
    if not record or record.get("needs_reauth"):
        return None
    key = record.get("api_key")
    if not key:
        return None
    scope = record.get("scope", "api")
    if scope not in ACCEPTED_SCOPES:
        return None
    return OrcaCredential(
        api_key=key,
        source=record.get("source", SOURCE_API_KEY),
        scope=scope,
        account_id=record.get("account_id", "default"),
        user_id=record.get("user_id"),
        generation=record.get("generation", 0),
    )


__all__ = [
    "ApiKeyAdapter",
    "CredentialAdapter",
    "OrcaCredential",
    "PkceAdapter",
    "SOURCE_API_KEY",
    "SOURCE_PKCE",
    "resolve_credential",
    "stored_credential",
]
