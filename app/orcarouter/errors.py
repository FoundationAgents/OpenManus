"""OrcaRouter error types.

Every message produced here is passed through :func:`redact` before it is
raised, so a credential, an authorization code or a PKCE verifier can never
reach a log line, a traceback or a crash report.
"""

import hmac
import re
from typing import Iterable, Optional


_PLACEHOLDER = "<redacted>"

# Anything that looks like a credential or a one-time code, even when the
# caller forgot to hand us the exact value.
_PATTERNS = (
    re.compile(r"sk-orca-[A-Za-z0-9_\-]+"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)\b(code|code_verifier|api_key|key)=([^&\s\"']+)"),
)


def redact(text: str, secrets: Optional[Iterable[str]] = None) -> str:
    """Return ``text`` with known and recognisable secrets removed."""
    if text is None:
        return ""
    out = str(text)
    for secret in secrets or ():
        if secret and len(str(secret)) >= 6:
            out = out.replace(str(secret), _PLACEHOLDER)
    out = _PATTERNS[0].sub(_PLACEHOLDER, out)
    out = _PATTERNS[1].sub(lambda m: f"{m.group(1)} {_PLACEHOLDER}", out)
    out = _PATTERNS[2].sub(lambda m: f"{m.group(1)}={_PLACEHOLDER}", out)
    return out


def constant_time_equals(left: Optional[str], right: Optional[str]) -> bool:
    """Compare two opaque values without leaking their contents by timing."""
    if not left or not right:
        return False
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


class OrcaError(Exception):
    """Base class for every OrcaRouter failure raised by this package."""

    def __init__(self, message: str, secrets: Optional[Iterable[str]] = None):
        self.raw_message = str(message)
        super().__init__(redact(self.raw_message, secrets))


class OrcaConfigError(OrcaError):
    """Origins, environment or configuration are unusable."""


class OrcaAuthError(OrcaError):
    """Base class for credential-acquisition failures."""


class OrcaAuthorizationDenied(OrcaAuthError):
    """The user declined the authorization request (``access_denied``)."""


class OrcaStateMismatch(OrcaAuthError):
    """The ``state`` returned on the loopback callback did not match ours."""


class OrcaAuthorizationTimeout(OrcaAuthError):
    """No authorization callback arrived before the deadline."""


class OrcaCodeRejected(OrcaAuthError):
    """HTTP 403 - code unknown, expired, already used, or verifier mismatch."""


class OrcaExchangeRejected(OrcaAuthError):
    """HTTP 400 - the exchange request itself was refused (downgrade defence)."""


class OrcaRateLimited(OrcaAuthError):
    """HTTP 429 - too many PKCE keys issued for this account in 24 hours."""


class OrcaNetworkError(OrcaAuthError):
    """The auth origin was unreachable or answered with a malformed body."""


class OrcaScopeError(OrcaAuthError):
    """The granted scope does not cover what this integration needs."""


class OrcaCatalogError(OrcaError):
    """The model catalog could not be parsed within its bounds."""


class OrcaNeedsReauth(OrcaError):
    """A stored credential was rejected with 401 and needs a new login."""
