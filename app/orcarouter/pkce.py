"""PKCE primitives and the OAuth 2.0 authorization-code flow.

Only the standard library is used: :mod:`secrets` for the verifier and state,
:mod:`hashlib` for the S256 challenge and :mod:`base64` for base64url. No new
dependency is introduced for either.

Flow A (loopback redirect) is the flow this integration implements, because
OpenManus runs as a console program on the operator's own workstation: a
browser is available and binding ``127.0.0.1:<ephemeral>`` is permitted, so the
authorization code comes back automatically instead of being copied by hand.

``S256`` is always sent. The consent screen lets a user choose "Show me a
code"; if a human can be handed the code, a ``plain`` challenge would put the
verifier itself into browser history and proxy logs. The same client therefore
also accepts a pasted code, which is the consent screen's code-delivery path
rather than a second flow.
"""

import base64
import hashlib
import http.server
import logging
import secrets
import socket
import threading
import time
import urllib.parse
import webbrowser
from typing import Callable, Dict, List, NamedTuple, Optional

from app.orcarouter.constants import ACCEPTED_SCOPES, REQUIRED_SCOPE, OrcaOrigins
from app.orcarouter.errors import (
    OrcaAuthError,
    OrcaAuthorizationDenied,
    OrcaAuthorizationTimeout,
    OrcaCodeRejected,
    OrcaExchangeRejected,
    OrcaNetworkError,
    OrcaRateLimited,
    OrcaScopeError,
    OrcaStateMismatch,
    constant_time_equals,
    redact,
)


VERIFIER_BYTES = 32
STATE_BYTES = 16
DEFAULT_APP_NAME = "OpenManus"
DEFAULT_TIMEOUT = 300.0
CALLBACK_PATH = "/cb"

_SUCCESS_PAGE = (
    b"<!doctype html><meta charset='utf-8'><title>OrcaRouter</title>"
    b"<p>Connected to OrcaRouter. You can close this tab and return to "
    b"OpenManus.</p>"
)
_FAILURE_PAGE = (
    b"<!doctype html><meta charset='utf-8'><title>OrcaRouter</title>"
    b"<p>Authorization was not completed. Return to OpenManus for details.</p>"
)

_log = logging.getLogger("openmanus.orcarouter")


def b64url(raw: bytes) -> str:
    """base64url without padding, as required for PKCE parameters."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def new_verifier() -> str:
    """A fresh, high-entropy PKCE verifier from the cryptographic RNG."""
    return b64url(secrets.token_bytes(VERIFIER_BYTES))


def new_state() -> str:
    """A fresh opaque ``state`` (the CSRF token for the loopback listener)."""
    return b64url(secrets.token_bytes(STATE_BYTES))


def challenge_for(verifier: str) -> str:
    """``base64url(sha256(verifier))`` without padding."""
    return b64url(hashlib.sha256(verifier.encode("ascii")).digest())


class PkceAttempt(NamedTuple):
    """One authorization attempt. The verifier never leaves this object."""

    verifier: str
    state: str
    challenge: str
    redirect_uri: str

    def __repr__(self) -> str:  # pragma: no cover - keep the verifier out
        return f"PkceAttempt(redirect_uri={self.redirect_uri!r}, <secrets hidden>)"

    __str__ = __repr__


def build_authorize_url(
    origins: OrcaOrigins,
    attempt: PkceAttempt,
    app_name: str = DEFAULT_APP_NAME,
    scope: str = REQUIRED_SCOPE,
    login_hint: Optional[str] = None,
    workspace_hint: Optional[str] = None,
    prompt: Optional[str] = None,
) -> str:
    """Build the consent-screen URL. Never contains the verifier."""
    params: Dict[str, str] = {
        "callback_url": attempt.redirect_uri,
        "code_challenge": attempt.challenge,
        "code_challenge_method": "S256",
        "state": attempt.state,
        "app_name": app_name,
        "scope": scope,
    }
    if login_hint:
        params["login_hint"] = login_hint
    if workspace_hint:
        params["workspace_hint"] = workspace_hint
    if prompt:
        params["prompt"] = prompt
    return f"{origins.authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_body(attempt: PkceAttempt, code: str) -> Dict[str, str]:
    """The JSON body for ``POST {auth_base}/api/v1/auth/keys``."""
    return {
        "code": code,
        "code_verifier": attempt.verifier,
        "code_challenge_method": "S256",
    }


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Serves exactly one authorization callback, then stops the server."""

    server_version = "OpenManusOrcaRouter/1.0"

    def log_message(self, fmt, *args):  # pragma: no cover - silence stdlib logs
        return

    def do_GET(self):  # noqa: N802 - stdlib naming
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        state = (params.get("state") or [None])[0]
        code = (params.get("code") or [None])[0]
        error = (params.get("error") or [None])[0]

        result = self.server.result  # type: ignore[attr-defined]

        # Compare state before anything else, and never surface the value that
        # was received.
        if not constant_time_equals(state, result["state"]):
            body, outcome = _FAILURE_PAGE, ("state_mismatch", "state mismatch")
        elif error:
            body, outcome = _FAILURE_PAGE, ("error", error)
        elif not code:
            body, outcome = _FAILURE_PAGE, ("error", "missing_code")
        else:
            body, outcome = _SUCCESS_PAGE, ("ok", code)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        result["kind"] = outcome[0]
        result["value"] = outcome[1]
        result["event"].set()
        threading.Thread(target=self.server.shutdown, daemon=True).start()


class _CallbackServer(http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class LoopbackReceiver:
    """A one-shot ``127.0.0.1`` listener for the authorization redirect."""

    def __init__(self, host: str = "127.0.0.1"):
        self._server = _CallbackServer((host, 0), _CallbackHandler)
        self._server.result = {  # type: ignore[attr-defined]
            "state": None,
            "kind": None,
            "value": None,
            "event": threading.Event(),
        }
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def start(self, state: str) -> None:
        self._server.result["state"] = state  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait(self, timeout: float) -> tuple:
        """Block until the callback arrives. Returns ``(kind, value)``."""
        event = self._server.result["event"]  # type: ignore[attr-defined]
        if not event.wait(timeout):
            raise OrcaAuthorizationTimeout(
                "Timed out waiting for the OrcaRouter authorization callback. "
                "Re-run the connect command, or pass --code on the command line."
            )
        result = self._server.result  # type: ignore[attr-defined]
        kind, value = result["kind"], result["value"]
        if kind == "state_mismatch":
            raise OrcaStateMismatch(
                "The OrcaRouter consent redirect did not carry the expected "
                "state value; the callback was discarded."
            )
        if kind == "error":
            if value == "access_denied":
                raise OrcaAuthorizationDenied(
                    "OrcaRouter authorization was denied. Nothing was stored; "
                    "you can retry at any time."
                )
            raise OrcaAuthError(
                f"OrcaRouter authorization failed: {redact(str(value))}"
            )
        return kind, value

    def close(self) -> None:
        try:
            self._server.shutdown()
        except Exception:  # pragma: no cover - already stopped
            pass
        try:
            self._server.server_close()
        except Exception:  # pragma: no cover - already closed
            pass

    def __enter__(self) -> "LoopbackReceiver":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def new_attempt(redirect_uri: str) -> PkceAttempt:
    """A loopback attempt bound to ``redirect_uri``."""
    verifier = new_verifier()
    return PkceAttempt(
        verifier=verifier,
        state=new_state(),
        challenge=challenge_for(verifier),
        redirect_uri=redirect_uri,
    )


def new_oob_attempt() -> PkceAttempt:
    """An out-of-band attempt, used when no browser can be opened."""
    return new_attempt("oob")


def read_scope(payload: object) -> str:
    """Read the *granted* scope from an exchange response.

    The response reports what was granted, not what was requested; a caller
    that asked for ``connector`` and reads ``api`` was approved by somebody
    whose workspace role does not permit the wider grant.
    """
    if not isinstance(payload, dict):
        raise OrcaAuthError("OrcaRouter returned an unexpected exchange payload.")
    scope = payload.get("scope")
    if not scope:
        return REQUIRED_SCOPE
    return str(scope)


def ensure_scope_granted(granted: str, required: str = REQUIRED_SCOPE) -> None:
    """Fail closed when the granted scope does not cover this integration."""
    if granted not in ACCEPTED_SCOPES or (required and required not in granted):
        raise OrcaScopeError(
            f"OrcaRouter granted scope {granted!r}, which does not cover the "
            f"required {required!r} scope. Ask the workspace owner to grant it, "
            f"or use the API-key path."
        )


def classify_exchange_status(status: int, body: str, secrets=()) -> OrcaAuthError:
    """Map an exchange failure onto an actionable, redacted error."""
    detail = redact(str(body)[:400], secrets)
    if status == 400:
        return OrcaExchangeRejected(
            "OrcaRouter rejected the code exchange request (HTTP 400): the "
            f"code_challenge_method is unrecognised or differs from the one "
            f"sent at authorize time. {detail}"
        )
    if status == 401:
        return OrcaExchangeRejected(
            f"OrcaRouter refused the code exchange (HTTP 401). {detail}"
        )
    if status == 403:
        return OrcaCodeRejected(
            "OrcaRouter refused the authorization code (HTTP 403): it is "
            "unknown, expired, already used, or the verifier does not match. "
            f"Start a new connect attempt. {detail}"
        )
    if status == 429:
        return OrcaRateLimited(
            "OrcaRouter rate-limited this account (HTTP 429): at most 10 "
            "PKCE-issued keys may be minted per user per 24 hours. Reuse the "
            "stored credential, or use an existing API key. " + detail
        )
    return OrcaAuthError(f"OrcaRouter code exchange failed (HTTP {status}). {detail}")


def parse_exchange_body(text: str) -> dict:
    """Parse an exchange response body, bounded and shape-checked."""
    import json

    if len(text) > 64 * 1024:
        raise OrcaNetworkError("OrcaRouter exchange response was unexpectedly large.")
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise OrcaNetworkError(
            f"OrcaRouter exchange response was not valid JSON: {exc}"
        ) from None
    if not isinstance(payload, dict):
        raise OrcaNetworkError("OrcaRouter exchange response was not a JSON object.")
    return payload


def extract_key(payload: dict, secrets=()) -> str:
    """Pull the issued ``sk-orca-...`` key out of a successful exchange."""
    key = payload.get("key")
    if not isinstance(key, str) or not key.strip():
        raise OrcaNetworkError(
            "OrcaRouter exchange succeeded but returned no credential."
        )
    key = key.strip()
    if not key.startswith("sk-orca-"):
        raise OrcaNetworkError(
            "OrcaRouter exchange returned a credential that is not an "
            "OrcaRouter API key."
        )
    return key


def acquire_with_receiver(
    origins: OrcaOrigins,
    poster: Callable[[str, Dict[str, str]], tuple],
    attempt: PkceAttempt,
    receiver: LoopbackReceiver,
    timeout: float = DEFAULT_TIMEOUT,
    open_browser: bool = True,
    app_name: str = DEFAULT_APP_NAME,
    scope: str = REQUIRED_SCOPE,
    on_url: Optional[Callable[[str], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Run Flow A end to end against an already-listening ``receiver``.

    ``poster(url, body) -> (status, text)`` is the only network dependency, so
    the whole flow is exercisable against a fake auth server.
    """
    del sleep  # kept for signature stability with polling-based flows
    receiver.start(attempt.state)
    url = build_authorize_url(origins, attempt, app_name=app_name, scope=scope)
    if on_url:
        on_url(url)
    if open_browser:
        try:
            webbrowser.open(url, new=2)
        except Exception:  # pragma: no cover - headless environments
            pass

    _, code = receiver.wait(timeout)
    return _exchange(origins, poster, attempt, code)


def acquire_with_pasted_code(
    origins: OrcaOrigins,
    poster: Callable[[str, Dict[str, str]], tuple],
    attempt: PkceAttempt,
    code_reader: Callable[[], str],
    app_name: str = DEFAULT_APP_NAME,
    scope: str = REQUIRED_SCOPE,
    open_browser: bool = True,
    on_url: Optional[Callable[[str], None]] = None,
) -> dict:
    """Flow A with the code delivered by hand.

    This is the consent screen's "Show me a code" path; ``S256`` is sent
    either way, so a code that passes through human hands is still bound to
    this process.
    """
    url = build_authorize_url(origins, attempt, app_name=app_name, scope=scope)
    if on_url:
        on_url(url)
    if open_browser:
        try:
            webbrowser.open(url, new=2)
        except Exception:  # pragma: no cover - headless environments
            pass
    code = (code_reader() or "").strip()
    if not code:
        raise OrcaAuthorizationDenied(
            "No authorization code was provided; nothing was stored."
        )
    return _exchange(origins, poster, attempt, code)


def _exchange(
    origins: OrcaOrigins,
    poster: Callable[[str, Dict[str, str]], tuple],
    attempt: PkceAttempt,
    code: str,
) -> dict:
    """POST the code + verifier to the auth origin and read the granted scope."""
    body = exchange_body(attempt, code)
    try:
        status, text = poster(origins.exchange_url, body)
    except OrcaAuthError:
        raise
    except Exception as exc:
        # Never let a transport exception echo the request body.
        raise OrcaNetworkError(
            f"Could not reach the OrcaRouter auth origin ({type(exc).__name__})."
        ) from None

    if status != 200:
        raise classify_exchange_status(status, text, secrets=(attempt.verifier, code))

    payload = parse_exchange_body(text)
    granted = read_scope(payload)
    ensure_scope_granted(granted)
    return {
        "key": extract_key(payload, secrets=(attempt.verifier,)),
        "scope": granted,
        "user_id": payload.get("user_id"),
        "account_id": _account_id(payload),
    }


def _account_id(payload: dict) -> str:
    """A stable, non-secret identifier for the account behind the credential."""
    for field in ("user_id", "user", "email"):
        value = payload.get(field)
        if value:
            return str(value)
    return "default"


def free_port() -> int:
    """An ephemeral loopback port, used for tests and for URL previews."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until(predicate: Callable[[], object], timeout: float = 5.0) -> None:
    """Test helper: wait for ``predicate`` to become truthy, or time out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise OrcaAuthorizationTimeout("condition was not met before the deadline")


__all__: List[str] = [
    "CALLBACK_PATH",
    "DEFAULT_APP_NAME",
    "DEFAULT_TIMEOUT",
    "LoopbackReceiver",
    "PkceAttempt",
    "acquire_with_pasted_code",
    "acquire_with_receiver",
    "b64url",
    "build_authorize_url",
    "challenge_for",
    "classify_exchange_status",
    "ensure_scope_granted",
    "exchange_body",
    "extract_key",
    "free_port",
    "new_attempt",
    "new_oob_attempt",
    "new_state",
    "new_verifier",
    "parse_exchange_body",
    "read_scope",
]
