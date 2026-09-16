"""Where OrcaRouter appears in OpenManus's provider surface.

OpenManus has no provider-registry object: the provider *is* the ``api_type``
string on ``LLMSettings``, which selects the SDK client in ``LLM.__init__``.
This module is the single named place that lists the OrcaRouter provider ids,
their default base URL, their credential provider and their client
construction, so ``app/llm.py`` holds no OrcaRouter-specific constants.
"""

from typing import Callable, Dict, NamedTuple, Optional

from app.orcarouter.constants import (
    API_KEY_ENVS,
    API_KEY_PROVIDER,
    DEFAULT_API_BASE_URL,
    PKCE_PROVIDER,
    PROVIDER_IDS,
    OrcaOrigins,
    resolve_origins,
)
from app.orcarouter.credentials import (
    SOURCE_API_KEY,
    SOURCE_PKCE,
    OrcaCredential,
    stored_credential,
)
from app.orcarouter.store import CredentialStore


class ProviderSpec(NamedTuple):
    """One selectable OrcaRouter provider entry."""

    id: str
    label: str
    description: str
    base_url: str
    credential_source: str
    env_key: str
    console_url: str

    @property
    def is_oauth(self) -> bool:
        return self.credential_source == SOURCE_PKCE


CONSOLE_URL = "https://www.orcarouter.ai/console"
AUTHORIZED_APPS_URL = "https://www.orcarouter.ai/console/authorized-apps"

PROVIDERS: Dict[str, ProviderSpec] = {
    API_KEY_PROVIDER: ProviderSpec(
        id=API_KEY_PROVIDER,
        label="OrcaRouter - API",
        description="Paste an existing OrcaRouter API key (sk-orca-...).",
        base_url=DEFAULT_API_BASE_URL,
        credential_source=SOURCE_API_KEY,
        env_key="ORCAROUTER_API_KEY",
        console_url=CONSOLE_URL,
    ),
    PKCE_PROVIDER: ProviderSpec(
        id=PKCE_PROVIDER,
        label="OrcaRouter - Auth",
        description="Sign in with an OrcaRouter account (OAuth 2.0 + PKCE).",
        base_url=DEFAULT_API_BASE_URL,
        credential_source=SOURCE_PKCE,
        env_key="ORCAROUTER_API_KEY",
        console_url=AUTHORIZED_APPS_URL,
    ),
}


class ClientConfig(NamedTuple):
    """Everything ``LLM.__init__`` needs to build the OpenAI client."""

    api_key: str
    base_url: str
    provider_id: str
    credential: Optional[OrcaCredential]


def is_orcarouter(api_type: Optional[str]) -> bool:
    """True for either OrcaRouter provider id (case-insensitive)."""
    if not api_type:
        return False
    return api_type.strip().lower() in PROVIDER_IDS


def provider_spec(api_type: Optional[str]) -> Optional[ProviderSpec]:
    if not api_type:
        return None
    return PROVIDERS.get(api_type.strip().lower())


def client_config_for(
    api_type: str,
    configured_api_key: Optional[str] = None,
    configured_base_url: Optional[str] = None,
    store: Optional[CredentialStore] = None,
    environ: Optional[Dict[str, str]] = None,
    resolver: Optional[Callable[[], Optional[OrcaCredential]]] = None,
) -> ClientConfig:
    """Resolve the credential and base URL for an OrcaRouter profile.

    Both provider ids reach the same inference origin and transport the same
    kind of key; only the acquisition path differs, and it has already
    happened by the time this returns.
    """
    origins: OrcaOrigins = resolve_origins(environ)
    spec = provider_spec(api_type)
    provider_id = spec.id if spec else API_KEY_PROVIDER

    credential: Optional[OrcaCredential] = None
    api_key = (configured_api_key or "").strip()
    if not api_key:
        if resolver is not None:
            credential = resolver()
        else:
            # The stored credential first, then the environment, so a machine
            # with only ORCAROUTER_API_KEY exported still works with no login.
            credential = stored_credential(store=store, environ=environ)
            if credential is None:
                from app.orcarouter.constants import api_key_from_env

                env_key = api_key_from_env(environ)
                if env_key:
                    credential = OrcaCredential(
                        api_key=env_key,
                        source=SOURCE_API_KEY,
                        scope="api",
                        account_id="default",
                    )
        if credential is not None:
            api_key = credential.api_key
        else:
            from app.orcarouter.constants import api_key_from_env

            api_key = api_key_from_env(environ) or ""

    if not api_key:
        raise_orca_missing_key(provider_id)

    base_url = (configured_base_url or "").strip() or origins.api_base
    return ClientConfig(
        api_key=api_key,
        base_url=base_url,
        provider_id=provider_id,
        credential=credential,
    )


def raise_orca_missing_key(provider_id: str) -> None:
    from app.orcarouter.errors import OrcaConfigError

    spec = PROVIDERS.get(provider_id) or PROVIDERS[API_KEY_PROVIDER]
    hint = (
        f"Run `orcarouter login` to authorize this machine"
        if spec.is_oauth
        else f"Set api_key in config.toml or export {API_KEY_ENVS[0]}"
    )
    raise OrcaConfigError(
        f"No OrcaRouter credential is available for api_type={provider_id!r}. "
        f"{hint}. Keys are managed at {spec.console_url}."
    )


def mark_terminal_reauth(
    credential: Optional[OrcaCredential],
    store: Optional[CredentialStore] = None,
) -> bool:
    """Flag the exact rejected credential generation for reauthentication.

    Called when the relay answers ``401``. There is no refresh grant to attempt,
    so this never tries to mint a new key; it only records that this precise
    account and generation need a new login. A later request made with a
    superseded credential cannot mark a fresh one.
    """
    if credential is None:
        return False
    store = store if store is not None else CredentialStore()
    return store.mark_needs_reauth(
        account_id=credential.account_id, generation=credential.generation
    )


__all__ = [
    "AUTHORIZED_APPS_URL",
    "CONSOLE_URL",
    "ClientConfig",
    "PROVIDERS",
    "ProviderSpec",
    "client_config_for",
    "is_orcarouter",
    "mark_terminal_reauth",
    "provider_spec",
]
