"""Origins, endpoints and provider identifiers for OrcaRouter.

OrcaRouter serves authentication and inference from two different public
origins:

* ``https://www.orcarouter.ai``  - consent screen and code exchange;
* ``https://api.orcarouter.ai/v1`` - inference and model discovery.

The two are configured independently. Neither is ever derived from the other by
rewriting a hostname or by appending ``/v1``: a self-hosted deployment may use
one shared origin or two unrelated ones, so the resolution order is
"explicit override, then shared fallback, then public default".
"""

import os
from typing import Dict, Optional
from urllib.parse import urlsplit


DEFAULT_AUTH_BASE_URL = "https://www.orcarouter.ai"
DEFAULT_API_BASE_URL = "https://api.orcarouter.ai/v1"

# Fixed paths on the auth origin. The exchange endpoint lives under
# ``/api/v1/auth``; ``https://api.orcarouter.ai/v1/auth/keys`` is a 404 and is
# never constructed anywhere in this package.
AUTHORIZE_PATH = "/auth"
EXCHANGE_PATH = "/api/v1/auth/keys"

# Provider identifiers, as they appear in ``config.toml`` ``api_type``.
API_KEY_PROVIDER = "orcarouter"
PKCE_PROVIDER = "orcarouter-oauth"
PROVIDER_IDS = (API_KEY_PROVIDER, PKCE_PROVIDER)

# ``sk-orca-`` keys are the only credential this integration ever transports.
API_KEY_PREFIX = "sk-orca-"

# Scope this integration needs, and the scope values it accepts back.
REQUIRED_SCOPE = "api"
ACCEPTED_SCOPES = ("api",)

# Environment variables, in resolution order.
AUTH_BASE_ENV = "ORCA_AUTH_BASE_URL"
API_BASE_ENV = "ORCA_API_BASE_URL"
SHARED_BASE_ENV = "ORCA_BASE_URL"
API_KEY_ENVS = ("ORCAROUTER_API_KEY", "ORCA_KEY")

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})


class OrcaOrigins:
    """The resolved auth and inference origins."""

    __slots__ = ("auth_base", "api_base")

    def __init__(self, auth_base: str, api_base: str):
        self.auth_base = auth_base.rstrip("/")
        self.api_base = api_base.rstrip("/")

    @property
    def authorize_url(self) -> str:
        return f"{self.auth_base}{AUTHORIZE_PATH}"

    @property
    def exchange_url(self) -> str:
        return f"{self.auth_base}{EXCHANGE_PATH}"

    @property
    def models_url(self) -> str:
        return f"{self.api_base}/models"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, OrcaOrigins)
            and self.auth_base == other.auth_base
            and self.api_base == other.api_base
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"OrcaOrigins(auth_base={self.auth_base!r}, api_base={self.api_base!r})"


def _env(source: Dict[str, str], name: str) -> Optional[str]:
    value = source.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _split_shared_base(shared: str) -> tuple:
    """Split a single self-hosted base into (auth_base, api_base).

    ``https://orca.example.com`` becomes auth ``https://orca.example.com`` and
    api ``https://orca.example.com/v1``. A shared base that already ends in
    ``/v1`` keeps its auth sibling instead of doubling the suffix.
    """
    stripped = shared.rstrip("/")
    if stripped.endswith("/v1"):
        return stripped[: -len("/v1")], stripped
    return stripped, f"{stripped}/v1"


def resolve_origins(
    environ: Optional[Dict[str, str]] = None,
    auth_base: Optional[str] = None,
    api_base: Optional[str] = None,
) -> OrcaOrigins:
    """Resolve the auth and inference origins.

    Precedence for each origin is: explicit argument, its own environment
    variable, the shared ``ORCA_BASE_URL`` fallback, then the public default.
    """
    env = os.environ if environ is None else environ
    shared = _env(env, SHARED_BASE_ENV)

    explicit_auth = auth_base or _env(env, AUTH_BASE_ENV)
    explicit_api = api_base or _env(env, API_BASE_ENV)

    shared_auth = shared_api = None
    if shared:
        shared_auth, shared_api = _split_shared_base(shared)

    resolved_auth = (explicit_auth or shared_auth or DEFAULT_AUTH_BASE_URL).rstrip("/")
    resolved_api = (explicit_api or shared_api or DEFAULT_API_BASE_URL).rstrip("/")

    _require_secure(resolved_auth, "auth")
    _require_secure(resolved_api, "api")
    return OrcaOrigins(resolved_auth, resolved_api)


def _require_secure(url: str, label: str) -> None:
    """Reject plaintext HTTP unless it points at loopback."""
    from app.orcarouter.errors import OrcaConfigError

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise OrcaConfigError(f"OrcaRouter {label} base URL must be http(s): {url}")
    if parts.scheme == "https":
        return
    host = (parts.hostname or "").lower()
    if host not in _LOOPBACK_HOSTS:
        raise OrcaConfigError(
            f"OrcaRouter {label} base URL must use HTTPS; plain HTTP is only "
            f"allowed for loopback development (got host {host!r})"
        )


def is_loopback_url(url: str) -> bool:
    """True when ``url`` points at the local machine over plain HTTP."""
    parts = urlsplit(url)
    return parts.scheme == "http" and (parts.hostname or "").lower() in _LOOPBACK_HOSTS


def api_key_from_env(environ: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Return a configured ``sk-orca-...`` key, if the environment has one."""
    env = os.environ if environ is None else environ
    for name in API_KEY_ENVS:
        value = _env(env, name)
        if value:
            return value
    return None


def api_key_prefix_ok(value: str) -> bool:
    """Lightweight shape check. Not proof that a credential is valid."""
    return bool(value) and value.strip().startswith(API_KEY_PREFIX)


def looks_like_placeholder(value: str) -> bool:
    """True for the shipped ``your ... api key`` style placeholders."""
    if not value:
        return True
    lowered = value.strip().lower()
    if lowered in ("", "your_api_key", "sk-...", "none", "null"):
        return True
    return "your " in lowered and "key" in lowered
