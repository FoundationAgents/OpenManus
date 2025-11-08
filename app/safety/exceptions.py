"""Safety-specific exception types for anti-replication enforcement."""

from __future__ import annotations

from dataclasses import dataclass


class SafetyViolationError(RuntimeError):
    """Base exception for safety violations."""


class CodeIntegrityViolation(SafetyViolationError):
    """Raised when immutable code integrity has been violated."""


class ReplicationAttemptDetected(SafetyViolationError):
    """Raised when a self-replication attempt is detected."""


class ImmutabilityError(SafetyViolationError):
    """Raised when attempting to mutate immutable resources."""


class PermissionDeniedError(SafetyViolationError):
    """Raised when an operation violates enforced permissions."""


class AuditLoggingError(SafetyViolationError):
    """Raised when an audit entry cannot be recorded securely."""


@dataclass(frozen=True)
class ShutdownSignal:
    """Immutable signal describing a forced shutdown action."""

    reason: str
    source: str
