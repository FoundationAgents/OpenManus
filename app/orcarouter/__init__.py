"""First-class OrcaRouter provider support for OpenManus.

Two explicit authentication choices are exposed for the same provider:

* ``orcarouter``       - paste an existing ``sk-orca-...`` API key;
* ``orcarouter-oauth`` - sign in with an OrcaRouter account over OAuth 2.0
  (authorization code + PKCE, S256).

Both adapters implement the same :class:`~app.orcarouter.credentials.CredentialAdapter`
seam and yield the same :class:`~app.orcarouter.credentials.OrcaCredential`, so
inference and model discovery never branch on where the credential came from.
"""

from app.orcarouter.catalog import (  # noqa: F401
    VERIFIED_SEED,
    ModelCatalog,
    ModelRecord,
    capability_options,
)
from app.orcarouter.constants import (  # noqa: F401
    API_KEY_PROVIDER,
    AUTHORIZE_PATH,
    DEFAULT_API_BASE_URL,
    DEFAULT_AUTH_BASE_URL,
    EXCHANGE_PATH,
    PKCE_PROVIDER,
    PROVIDER_IDS,
    OrcaOrigins,
    api_key_prefix_ok,
    resolve_origins,
)
from app.orcarouter.credentials import (  # noqa: F401
    ApiKeyAdapter,
    CredentialAdapter,
    OrcaCredential,
    PkceAdapter,
    resolve_credential,
)
from app.orcarouter.errors import (  # noqa: F401
    OrcaAuthError,
    OrcaAuthorizationDenied,
    OrcaAuthorizationTimeout,
    OrcaCatalogError,
    OrcaCodeRejected,
    OrcaConfigError,
    OrcaError,
    OrcaExchangeRejected,
    OrcaNetworkError,
    OrcaRateLimited,
    OrcaScopeError,
    OrcaStateMismatch,
    redact,
)
from app.orcarouter.provider import (  # noqa: F401
    PROVIDERS,
    ClientConfig,
    ProviderSpec,
    client_config_for,
    is_orcarouter,
    mark_terminal_reauth,
    provider_spec,
)
from app.orcarouter.store import CredentialStore  # noqa: F401


__all__ = [
    "API_KEY_PROVIDER",
    "AUTHORIZE_PATH",
    "ApiKeyAdapter",
    "ClientConfig",
    "CredentialAdapter",
    "CredentialStore",
    "DEFAULT_API_BASE_URL",
    "DEFAULT_AUTH_BASE_URL",
    "EXCHANGE_PATH",
    "ModelCatalog",
    "ModelRecord",
    "OrcaAuthError",
    "OrcaAuthorizationDenied",
    "OrcaAuthorizationTimeout",
    "OrcaCatalogError",
    "OrcaCodeRejected",
    "OrcaConfigError",
    "OrcaCredential",
    "OrcaError",
    "OrcaExchangeRejected",
    "OrcaNetworkError",
    "OrcaOrigins",
    "OrcaRateLimited",
    "OrcaScopeError",
    "OrcaStateMismatch",
    "PKCE_PROVIDER",
    "PROVIDERS",
    "PROVIDER_IDS",
    "PkceAdapter",
    "ProviderSpec",
    "VERIFIED_SEED",
    "api_key_prefix_ok",
    "capability_options",
    "client_config_for",
    "is_orcarouter",
    "mark_terminal_reauth",
    "provider_spec",
    "redact",
    "resolve_credential",
    "resolve_origins",
]
