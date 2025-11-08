"""Declarative permission matrix describing what the agent may or may not do."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple

from app.safety.exceptions import PermissionDeniedError


Permission = Tuple[str, str]

ALLOWED_OPERATIONS: Tuple[Permission, ...] = (
    ("read", "own_code"),
    ("read", "user_data"),
    ("read", "configs"),
    ("write", "user_data"),
    ("write", "logs"),
    ("write", "cache"),
    ("execute", "approved_commands"),
    ("access", "approved_services"),
    ("call", "ixlinx_agent_components_read_only"),
)

BLOCKED_OPERATIONS: Tuple[Permission, ...] = (
    ("write", "own_code"),
    ("modify", "safety_modules"),
    ("modify", "constraints"),
    ("persist", "self_with_changes"),
    ("create", "child_processes"),
    ("access", "security_modules"),
    ("contact", "external_systems_for_replication"),
    ("escape", "sandbox"),
)


@dataclass(frozen=True)
class PermissionMatrix:
    allowed: Tuple[Permission, ...] = ALLOWED_OPERATIONS
    blocked: Tuple[Permission, ...] = BLOCKED_OPERATIONS

    def is_allowed(self, operation: str, resource: str) -> bool:
        key = (operation, resource)
        if key in self.blocked:
            return False
        return key in self.allowed

    def enforce(self, operation: str, resource: str) -> None:
        if not self.is_allowed(operation, resource):
            raise PermissionDeniedError(f"Operation '{operation}' on '{resource}' is prohibited")

    def describe(self) -> Dict[str, Iterable[str]]:
        return {
            "can": {f"{op}:{res}" for op, res in self.allowed},
            "cannot": {f"{op}:{res}" for op, res in self.blocked},
        }
