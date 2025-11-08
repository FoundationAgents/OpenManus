"""
Guardian validation system for sandbox operations.

This module provides security validation and approval mechanisms
for sandbox operations, including ACL enforcement and risk assessment.
"""

import asyncio
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pydantic import BaseModel

from app.logger import logger


class RiskLevel(Enum):
    """Risk level for sandbox operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessMode(Enum):
    """Volume access modes."""
    READ_ONLY = "ro"
    READ_WRITE = "rw"


@dataclass
class VolumeACL:
    """Access control list for volume mounts."""
    host_path: str
    container_path: str
    mode: AccessMode
    allowed_patterns: List[str]
    blocked_patterns: List[str]


@dataclass
class OperationRequest:
    """Request for Guardian validation."""
    agent_id: str
    operation: str
    command: Optional[str] = None
    volume_bindings: Optional[Dict[str, str]] = None
    resource_limits: Optional[Dict[str, any]] = None
    metadata: Optional[Dict[str, any]] = None


class GuardianDecision(BaseModel):
    """Guardian validation decision."""
    approved: bool
    reason: str
    risk_level: RiskLevel
    conditions: List[str] = []
    timeout_override: Optional[int] = None


class SecurityRule(BaseModel):
    """Security rule for validation."""
    name: str
    pattern: str
    risk_level: RiskLevel
    action: str  # "allow", "deny", "require_approval"
    description: str
    enabled: bool = True


class Guardian:
    """Guardian validation system for sandbox operations.

    Provides security validation, ACL enforcement, and risk assessment
    for sandbox operations before execution.
    """

    def __init__(self):
        """Initialize Guardian with default security rules."""
        self.security_rules: List[SecurityRule] = []
        self.volume_acls: List[VolumeACL] = []
        self.blocked_commands: Set[str] = set()
        self.approved_agents: Set[str] = set()
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default security rules."""
        # Dangerous command patterns
        dangerous_patterns = [
            SecurityRule(
                name="rm_rf",
                pattern=r"rm\s+-rf\s+[/]",
                risk_level=RiskLevel.CRITICAL,
                action="deny",
                description="Recursive deletion from root"
            ),
            SecurityRule(
                name="format_disk",
                pattern=r"(mkfs|format)\s+[/]",
                risk_level=RiskLevel.CRITICAL,
                action="deny",
                description="Disk formatting operations"
            ),
            SecurityRule(
                name="system_shutdown",
                pattern=r"(shutdown|reboot|halt)\s+",
                risk_level=RiskLevel.HIGH,
                action="deny",
                description="System shutdown commands"
            ),
            SecurityRule(
                name="network_scan",
                pattern=r"(nmap|netdiscover)\s+",
                risk_level=RiskLevel.MEDIUM,
                action="require_approval",
                description="Network scanning tools"
            ),
            SecurityRule(
                name="privilege_escalation",
                pattern=r"(sudo\s+|su\s+)",
                risk_level=RiskLevel.HIGH,
                action="deny",  # Changed to deny for stricter security
                description="Privilege escalation attempts"
            ),
            SecurityRule(
                name="package_install",
                pattern=r"(apt|yum|pip)\s+(install|install\s+)",
                risk_level=RiskLevel.MEDIUM,
                action="allow",
                description="Package installation"
            ),
        ]
        self.security_rules.extend(dangerous_patterns)

    def add_volume_acl(self, acl: VolumeACL) -> None:
        """Add a volume access control rule."""
        self.volume_acls.append(acl)
        logger.info(f"Added volume ACL for {acl.host_path} -> {acl.container_path}")

    def approve_agent(self, agent_id: str) -> None:
        """Add an agent to the approved list."""
        self.approved_agents.add(agent_id)
        logger.info(f"Approved agent {agent_id}")

    def revoke_agent_approval(self, agent_id: str) -> None:
        """Remove an agent from the approved list."""
        self.approved_agents.discard(agent_id)
        logger.info(f"Revoked approval for agent {agent_id}")

    async def validate_operation(self, request: OperationRequest) -> GuardianDecision:
        """Validate a sandbox operation request.

        Args:
            request: Operation request to validate.

        Returns:
            GuardianDecision with validation result.
        """
        # Check agent approval
        if request.agent_id not in self.approved_agents:
            return GuardianDecision(
                approved=False,
                reason=f"Agent {request.agent_id} is not approved for sandbox operations",
                risk_level=RiskLevel.HIGH
            )

        risk_level = RiskLevel.LOW
        reasons = []
        conditions = []

        # Validate command if provided
        if request.command:
            cmd_risk, cmd_reasons = await self._assess_command_risk(request.command)
            risk_level = max(risk_level, cmd_risk, key=lambda x: x.value)
            reasons.extend(cmd_reasons)

        # Validate volume bindings
        if request.volume_bindings:
            vol_risk, vol_reasons = self._validate_volume_bindings(request.volume_bindings)
            risk_level = max(risk_level, vol_risk, key=lambda x: x.value)
            reasons.extend(vol_reasons)

        # Validate resource limits
        if request.resource_limits:
            res_risk, res_reasons, res_conditions = self._validate_resource_limits(request.resource_limits)
            risk_level = max(risk_level, res_risk, key=lambda x: x.value)
            reasons.extend(res_reasons)
            conditions.extend(res_conditions)

        # Make decision based on risk level and rules
        approved, decision_reason = self._make_decision(request, risk_level, reasons)

        return GuardianDecision(
            approved=approved,
            reason=decision_reason,
            risk_level=risk_level,
            conditions=conditions
        )

    async def _assess_command_risk(self, command: str) -> Tuple[RiskLevel, List[str]]:
        """Assess the risk level of a command."""
        max_risk = RiskLevel.LOW
        reasons = []

        for rule in self.security_rules:
            if not rule.enabled:
                continue

            if re.search(rule.pattern, command, re.IGNORECASE):
                max_risk = max(max_risk, rule.risk_level, key=lambda x: x.value)
                reasons.append(f"{rule.description}: {rule.risk_level.value}")

                if rule.action == "deny":
                    return RiskLevel.CRITICAL, [f"Command blocked by rule: {rule.description}"]

        return max_risk, reasons

    def _validate_volume_bindings(self, volume_bindings: Dict[str, str]) -> Tuple[RiskLevel, List[str]]:
        """Validate volume mount bindings against ACLs."""
        max_risk = RiskLevel.LOW
        reasons = []

        for host_path, container_path in volume_bindings.items():
            # Check for dangerous paths
            if any(dangerous in host_path.lower() for dangerous in ['/etc', '/boot', '/sys', '/proc']):
                max_risk = max(max_risk, RiskLevel.HIGH, key=lambda x: x.value)
                reasons.append(f"Sensitive host path mounted: {host_path}")

            # Check against ACLs
            acl_match = None
            for acl in self.volume_acls:
                if host_path.startswith(acl.host_path):
                    acl_match = acl
                    break

            if acl_match:
                # Check if container path is allowed
                for pattern in acl_match.blocked_patterns:
                    if re.search(pattern, container_path):
                        max_risk = max(max_risk, RiskLevel.HIGH, key=lambda x: x.value)
                        reasons.append(f"Container path blocked by ACL: {container_path}")
            else:
                # No ACL found, medium risk
                max_risk = max(max_risk, RiskLevel.MEDIUM, key=lambda x: x.value)
                reasons.append(f"No ACL defined for volume: {host_path}")

        return max_risk, reasons

    def _validate_resource_limits(self, resource_limits: Dict[str, any]) -> Tuple[RiskLevel, List[str], List[str]]:
        """Validate resource limits."""
        max_risk = RiskLevel.LOW
        reasons = []
        conditions = []

        # Check CPU limits
        if 'cpu_limit' in resource_limits:
            cpu_limit = resource_limits['cpu_limit']
            if cpu_limit > 4.0:
                max_risk = max(max_risk, RiskLevel.MEDIUM, key=lambda x: x.value)
                reasons.append(f"High CPU limit requested: {cpu_limit}")
                conditions.append(f"Monitor CPU usage closely")

        # Check memory limits
        if 'memory_limit' in resource_limits:
            memory_limit = resource_limits['memory_limit']
            # Parse memory limit (e.g., "2g", "512m")
            if isinstance(memory_limit, str):
                if memory_limit.endswith('g'):
                    gb = float(memory_limit[:-1])
                    if gb > 4.0:
                        max_risk = max(max_risk, RiskLevel.MEDIUM, key=lambda x: x.value)
                        reasons.append(f"High memory limit requested: {memory_limit}")
                        conditions.append(f"Monitor memory usage closely")

        # Check timeout
        if 'timeout' in resource_limits:
            timeout = resource_limits['timeout']
            if timeout > 3600:  # 1 hour
                max_risk = max(max_risk, RiskLevel.MEDIUM, key=lambda x: x.value)
                reasons.append(f"Long timeout requested: {timeout} seconds")
                conditions.append(f"Consider shorter timeout for safety")

        return max_risk, reasons, conditions

    def _make_decision(self, request: OperationRequest, risk_level: RiskLevel, reasons: List[str]) -> Tuple[bool, str]:
        """Make final approval decision."""
        # Auto-deny critical risk operations
        if risk_level == RiskLevel.CRITICAL:
            return False, f"Operation denied due to critical risk: {'; '.join(reasons)}"

        # Auto-approve low risk operations
        if risk_level == RiskLevel.LOW:
            return True, f"Operation approved (low risk): {'; '.join(reasons) if reasons else 'No issues detected'}"

        # For medium and high risk, require additional conditions
        if risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
            # Check if command requires explicit approval
            if request.command:
                for rule in self.security_rules:
                    if rule.enabled and rule.action == "require_approval":
                        if re.search(rule.pattern, request.command, re.IGNORECASE):
                            return False, f"Operation requires explicit approval: {rule.description}"

            return True, f"Operation approved with conditions ({risk_level.value} risk): {'; '.join(reasons)}"

        return True, "Operation approved"

    def get_security_summary(self) -> Dict[str, any]:
        """Get a summary of security configuration."""
        return {
            "total_rules": len(self.security_rules),
            "enabled_rules": len([r for r in self.security_rules if r.enabled]),
            "volume_acls": len(self.volume_acls),
            "approved_agents": len(self.approved_agents),
            "risk_levels": {
                "critical": len([r for r in self.security_rules if r.risk_level == RiskLevel.CRITICAL]),
                "high": len([r for r in self.security_rules if r.risk_level == RiskLevel.HIGH]),
                "medium": len([r for r in self.security_rules if r.risk_level == RiskLevel.MEDIUM]),
                "low": len([r for r in self.security_rules if r.risk_level == RiskLevel.LOW]),
            }
        }


# Global Guardian instance
_guardian_instance: Optional[Guardian] = None


def get_guardian() -> Guardian:
    """Get the global Guardian instance."""
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = Guardian()
    return _guardian_instance