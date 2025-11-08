"""Hardware level enforcement models OS sandbox guarantees."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.logger import logger
from app.safety.exceptions import PermissionDeniedError


class Platform(str, Enum):
    """Supported operating system platforms."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


class Operation(str, Enum):
    """Operations that must be hardware-enforced."""

    CREATE_CHILD_PROCESS = "create_child_process"
    REGISTRY_ACCESS = "registry_access"
    NETWORK_IO = "network_io"
    FILE_WRITE = "file_write"
    FILE_READ = "file_read"
    MEMORY_ALLOCATION = "memory_allocation"
    SANDBOX_ESCAPE = "sandbox_escape"


@dataclass(frozen=True)
class Constraint:
    """Static constraint describing what is allowed."""

    allowed_file_roots: List[Path] = field(default_factory=list)
    read_only_roots: List[Path] = field(default_factory=list)
    allowed_network_endpoints: List[str] = field(default_factory=list)
    max_memory_mb: Optional[int] = None
    allow_child_processes: bool = False
    sandbox_escape_allowed: bool = False
    registry_access_allowed: bool = False


DEFAULT_CONSTRAINTS: Dict[Platform, Constraint] = {
    Platform.WINDOWS: Constraint(
        allowed_file_roots=[Path("data"), Path("logs"), Path("cache")],
        read_only_roots=[Path("app")],
        allowed_network_endpoints=["monitor.ixlinx-agent.local"],
        max_memory_mb=1024,
        allow_child_processes=False,
        sandbox_escape_allowed=False,
        registry_access_allowed=False,
    ),
    Platform.LINUX: Constraint(
        allowed_file_roots=[Path("data"), Path("logs"), Path("cache")],
        read_only_roots=[Path("/"), Path("/ixlinx-agent/app"), Path("/ixlinx-agent/app/safety")],
        allowed_network_endpoints=["monitor.ixlinx-agent.local"],
        max_memory_mb=1024,
    ),
    Platform.MACOS: Constraint(
        allowed_file_roots=[Path("data"), Path("logs"), Path("cache")],
        read_only_roots=[Path("/Applications/iXlinx-Agent.app")],
        allowed_network_endpoints=["monitor.ixlinx-agent.local"],
        max_memory_mb=1024,
    ),
}


@dataclass
class EnforcementDecision:
    """Result of evaluating whether an operation is permitted."""

    platform: Platform
    operation: Operation
    allowed: bool
    reason: str
    details: Dict[str, str] = field(default_factory=dict)


class HardwareLevelEnforcer:
    """Evaluates hardware-level constraints before allowing operations."""

    def __init__(self, constraints: Optional[Dict[Platform, Constraint]] = None) -> None:
        self.constraints = constraints or DEFAULT_CONSTRAINTS

    def enforce(
        self,
        platform: Platform,
        operation: Operation,
        *,
        target: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> EnforcementDecision:
        details = details or {}
        constraint = self.constraints.get(platform)
        if constraint is None:
            reason = f"Unsupported platform: {platform}"
            logger.error(reason)
            return EnforcementDecision(platform, operation, False, reason, details)

        allowed = True
        reason = "allowed"

        if operation == Operation.CREATE_CHILD_PROCESS and not constraint.allow_child_processes:
            allowed = False
            reason = "Child process creation is disabled"
        elif operation == Operation.REGISTRY_ACCESS and not constraint.registry_access_allowed:
            allowed = False
            reason = "Registry access is prohibited"
        elif operation == Operation.SANDBOX_ESCAPE and not constraint.sandbox_escape_allowed:
            allowed = False
            reason = "Sandbox escape detected"
        elif operation == Operation.FILE_WRITE:
            allowed = self._is_within_allowed_roots(target, constraint.allowed_file_roots)
            if not allowed:
                reason = "Write outside of approved directories"
        elif operation == Operation.FILE_READ:
            allowed = not self._is_within_read_only_roots(target, constraint.read_only_roots)
            if not allowed:
                reason = "Attempted write access to read-only root"
        elif operation == Operation.NETWORK_IO:
            allowed = target in constraint.allowed_network_endpoints
            if not allowed:
                reason = "Unapproved network endpoint"
        elif operation == Operation.MEMORY_ALLOCATION and constraint.max_memory_mb is not None:
            requested = int(details.get("requested_mb", "0"))
            allowed = requested <= constraint.max_memory_mb
            if not allowed:
                reason = "Memory allocation exceeds enforced limit"

        if not allowed:
            logger.critical(
                "Hardware enforcement blocked operation",
                extra={
                    "platform": platform.value,
                    "operation": operation.value,
                    "target": target,
                    "reason": reason,
                },
            )

        return EnforcementDecision(platform, operation, allowed, reason, details)

    def ensure_allowed(
        self,
        platform: Platform,
        operation: Operation,
        *,
        target: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> None:
        decision = self.enforce(platform, operation, target=target, details=details)
        if not decision.allowed:
            raise PermissionDeniedError(decision.reason)

    @staticmethod
    def _is_within_allowed_roots(target: Optional[str], roots: Iterable[Path]) -> bool:
        if not target:
            return False
        path = Path(target).resolve()
        for root in roots:
            try:
                if path.is_relative_to(root.resolve()):
                    return True
            except AttributeError:  # pragma: no cover - Python <3.9 compatibility
                try:
                    path.relative_to(root.resolve())
                    return True
                except ValueError:
                    continue
            except ValueError:
                continue
        return False

    @staticmethod
    def _is_within_read_only_roots(target: Optional[str], roots: Iterable[Path]) -> bool:
        if not target:
            return False
        path = Path(target).resolve()
        for root in roots:
            try:
                if path.is_relative_to(root.resolve()):
                    return True
            except AttributeError:  # pragma: no cover - Python <3.9 compatibility
                try:
                    path.relative_to(root.resolve())
                    return True
                except ValueError:
                    continue
            except ValueError:
                continue
        return False
