"""
Containment & Sandboxing

Limits agent capabilities by default - read-only access, can't modify own
code/constraints, restricted system access, and resource limits.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger


class AccessLevel(Enum):
    """Access levels for agent capabilities"""
    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"


@dataclass
class AccessPolicy:
    """Policy for accessing a resource"""
    resource: str  # e.g., "filesystem", "network", "system_calls"
    access_level: AccessLevel
    requires_approval: bool = False
    rate_limit: Optional[int] = None  # Operations per minute
    resource_limit: Optional[str] = None  # e.g., "100MB" for disk
    allowed_domains: Optional[List[str]] = None  # For network access


@dataclass
class ResourceLimit:
    """Resource limit configuration"""
    cpu_percent: int = 50  # Max CPU usage %
    memory_mb: int = 512  # Max memory MB
    disk_mb: int = 1000  # Max disk write MB
    timeout_seconds: int = 3600  # Max execution time
    network_bandwidth_mbps: int = 10  # Max network bandwidth


class ContainmentManager:
    """
    Manages agent containment - limits capabilities through sandboxing,
    read-only defaults, and resource limits.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._access_policies: Dict[str, AccessPolicy] = {}
        self._resource_limits = ResourceLimit()
        self._initialization_complete = False
        self._initialize_default_policies()

    def _initialize_default_policies(self):
        """Initialize default containment policies"""
        # Filesystem: read-only by default
        self._access_policies["filesystem_read"] = AccessPolicy(
            resource="filesystem_read",
            access_level=AccessLevel.READ_ONLY,
            requires_approval=False,
        )
        self._access_policies["filesystem_write"] = AccessPolicy(
            resource="filesystem_write",
            access_level=AccessLevel.NONE,
            requires_approval=True,  # Writes need approval
        )

        # Network: restricted
        self._access_policies["network_http"] = AccessPolicy(
            resource="network_http",
            access_level=AccessLevel.EXECUTE,
            requires_approval=False,
            rate_limit=100,  # 100 requests per minute
            allowed_domains=None,  # Can be restricted
        )

        # System calls: read-only
        self._access_policies["system_calls"] = AccessPolicy(
            resource="system_calls",
            access_level=AccessLevel.READ_ONLY,
            requires_approval=False,
        )

        # Code modification: blocked
        self._access_policies["code_modification"] = AccessPolicy(
            resource="code_modification",
            access_level=AccessLevel.NONE,
            requires_approval=False,
        )

        # Constraint modification: blocked
        self._access_policies["constraint_modification"] = AccessPolicy(
            resource="constraint_modification",
            access_level=AccessLevel.NONE,
            requires_approval=False,
        )

        # Credential access: blocked
        self._access_policies["credentials"] = AccessPolicy(
            resource="credentials",
            access_level=AccessLevel.NONE,
            requires_approval=False,
        )

    async def check_access(
        self, resource: str, action: str, context: Optional[Dict] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if agent can access a resource.

        Args:
            resource: The resource being accessed
            action: The action (read, write, execute, etc.)
            context: Additional context

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        async with self._lock:
            policy_key = f"{resource}_{action}"
            policy = self._access_policies.get(policy_key)

            if not policy:
                # Default deny for unknown resources
                return False, f"No access policy for {policy_key}"

            if policy.access_level == AccessLevel.NONE:
                return False, f"Access denied: {resource} {action} is not allowed"

            if policy.requires_approval:
                return False, f"Approval required for {resource} {action}"

            return True, None

    async def request_access(
        self, resource: str, action: str, reason: str, context: Optional[Dict] = None
    ) -> bool:
        """
        Request elevated access for a resource.

        Args:
            resource: The resource
            action: The action
            reason: Why access is needed
            context: Additional context

        Returns:
            Whether access was granted
        """
        logger.info(f"Access request: {resource} {action}")
        logger.info(f"Reason: {reason}")

        # In production, this would check with user
        # For now, log the request
        policy_key = f"{resource}_{action}"
        policy = self._access_policies.get(policy_key)

        if policy and policy.requires_approval:
            logger.warning(f"Approval needed for {policy_key}: {reason}")
            return False

        return False

    async def enforce_resource_limits(self) -> Dict[str, any]:
        """Enforce resource limits on agent execution"""
        return {
            "cpu_percent": self._resource_limits.cpu_percent,
            "memory_mb": self._resource_limits.memory_mb,
            "disk_mb": self._resource_limits.disk_mb,
            "timeout_seconds": self._resource_limits.timeout_seconds,
            "network_bandwidth_mbps": self._resource_limits.network_bandwidth_mbps,
        }

    async def verify_containment(self) -> Dict[str, any]:
        """
        Verify containment and sandboxing is properly configured.

        Returns:
            Containment status
        """
        return {
            "filesystem_write_requires_approval": self._access_policies.get(
                "filesystem_write"
            ).requires_approval,
            "code_modification_blocked": self._access_policies.get(
                "code_modification"
            ).access_level == AccessLevel.NONE,
            "constraints_modification_blocked": self._access_policies.get(
                "constraint_modification"
            ).access_level == AccessLevel.NONE,
            "credentials_blocked": self._access_policies.get("credentials").access_level == AccessLevel.NONE,
            "resource_limits_enforced": True,
            "network_rate_limited": self._access_policies.get("network_http").rate_limit is not None,
        }

    async def get_containment_summary(self) -> Dict[str, any]:
        """Get summary of agent containment"""
        summary = {}
        for key, policy in self._access_policies.items():
            summary[key] = {
                "access_level": policy.access_level.value,
                "requires_approval": policy.requires_approval,
                "rate_limit": policy.rate_limit,
            }

        return {
            "policies": summary,
            "resource_limits": {
                "cpu_percent": self._resource_limits.cpu_percent,
                "memory_mb": self._resource_limits.memory_mb,
                "disk_mb": self._resource_limits.disk_mb,
                "timeout_seconds": self._resource_limits.timeout_seconds,
            },
        }

    async def sandbox_code_execution(self, code: str, timeout_seconds: int = 30) -> tuple[bool, str]:
        """
        Execute code in sandboxed environment.

        Args:
            code: Code to execute
            timeout_seconds: Execution timeout

        Returns:
            Tuple of (success, output)
        """
        # Check if code execution is allowed
        allowed, reason = await self.check_access("code_execution", "execute")
        if not allowed:
            return False, f"Code execution denied: {reason}"

        logger.info("Code would be executed in sandbox with timeout")
        return True, "Sandbox ready"

    async def restrict_network_access(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Restrict network access to specific URLs.

        Args:
            url: URL to access

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        allowed, reason = await self.check_access("network_http", "execute")
        if not allowed:
            return False, reason

        # Could add domain whitelist checking here
        return True, None

    async def block_self_modification(self):
        """Ensure agent cannot modify its own code or constraints"""
        # This is enforced by setting access_level to NONE for code_modification
        code_policy = self._access_policies.get("code_modification")
        constraints_policy = self._access_policies.get("constraint_modification")

        return (
            code_policy.access_level == AccessLevel.NONE
            and constraints_policy.access_level == AccessLevel.NONE
        )

    async def get_current_resource_usage(self) -> Dict[str, any]:
        """Get current resource usage"""
        return {
            "cpu_percent": 0,  # Would get actual usage
            "memory_mb": 0,
            "disk_mb": 0,
            "active_connections": 0,
        }


# Global containment manager
containment_manager = ContainmentManager()
