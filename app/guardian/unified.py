"""
Unified Guardian Interface - consolidation and adapter for multiple Guardian implementations.

This module provides a unified interface for all Guardian implementations across:
- Network operations (app/network/guardian.py)
- Storage operations (app/storage/guardian.py)
- Sandbox operations (app/sandbox/core/guardian.py)
- Security monitoring (app/guardian/guardian_service.py)

The unified interface allows code to work with a consistent API regardless
of the underlying Guardian implementation or domain.
"""

import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from app.logger import logger


class GuardianDomain(str, Enum):
    """Domains managed by Guardian systems."""
    NETWORK = "network"          # Network/HTTP operations
    STORAGE = "storage"          # Database/storage operations
    SANDBOX = "sandbox"          # Sandbox execution
    SECURITY = "security"        # Security monitoring


class UnifiedRiskLevel(str, Enum):
    """Unified risk level across all domains."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UnifiedGuardianDecision(BaseModel):
    """Unified Guardian decision model."""
    domain: GuardianDomain
    operation: str
    approved: bool
    risk_level: UnifiedRiskLevel
    reason: str
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = {}
    conditions: List[str] = []


class UnifiedGuardian:
    """
    Unified Guardian interface providing consistent API across all implementations.

    This adapter allows seamless use of any Guardian implementation through
    a single consistent interface.

    Example:
        guardian = UnifiedGuardian()

        # Check network operation
        decision = await guardian.assess(
            domain=GuardianDomain.NETWORK,
            operation="http_get",
            target="https://example.com"
        )

        # Check sandbox operation
        decision = await guardian.assess(
            domain=GuardianDomain.SANDBOX,
            operation="execute",
            target="python script.py"
        )
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_implementations()
        return cls._instance

    def _init_implementations(self):
        """Initialize all Guardian implementations."""
        self._network_guardian = None
        self._storage_guardian = None
        self._sandbox_guardian = None
        self._security_guardian = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of implementations."""
        if self._initialized:
            return

        try:
            from app.network.guardian import Guardian as NetworkGuardian
            self._network_guardian = NetworkGuardian()
        except Exception as e:
            logger.warning(f"Failed to load NetworkGuardian: {e}")

        try:
            from app.storage.guardian import Guardian as StorageGuardian
            self._storage_guardian = StorageGuardian()
        except Exception as e:
            logger.warning(f"Failed to load StorageGuardian: {e}")

        try:
            from app.sandbox.core.guardian import Guardian as SandboxGuardian
            self._sandbox_guardian = SandboxGuardian()
        except Exception as e:
            logger.warning(f"Failed to load SandboxGuardian: {e}")

        try:
            from app.guardian.guardian_service import guardian_service
            self._security_guardian = guardian_service
        except Exception as e:
            logger.warning(f"Failed to load SecurityGuardian: {e}")

        self._initialized = True

    async def assess(
        self,
        domain: GuardianDomain,
        operation: str,
        target: Optional[str] = None,
        **kwargs
    ) -> UnifiedGuardianDecision:
        """
        Unified assessment across all Guardian domains.

        Args:
            domain: Guardian domain (network, storage, sandbox, security)
            operation: Operation to assess
            target: Target resource or operation
            **kwargs: Domain-specific parameters

        Returns:
            UnifiedGuardianDecision with assessment result
        """
        await self._ensure_initialized()

        if domain == GuardianDomain.NETWORK:
            return await self._assess_network(operation, target, **kwargs)
        elif domain == GuardianDomain.STORAGE:
            return await self._assess_storage(operation, target, **kwargs)
        elif domain == GuardianDomain.SANDBOX:
            return await self._assess_sandbox(operation, target, **kwargs)
        elif domain == GuardianDomain.SECURITY:
            return await self._assess_security(operation, target, **kwargs)
        else:
            raise ValueError(f"Unknown Guardian domain: {domain}")

    async def _assess_network(
        self, operation: str, target: Optional[str] = None, **kwargs
    ) -> UnifiedGuardianDecision:
        """Assess network operation using NetworkGuardian."""
        if not self._network_guardian:
            return UnifiedGuardianDecision(
                domain=GuardianDomain.NETWORK,
                operation=operation,
                approved=True,
                risk_level=UnifiedRiskLevel.LOW,
                reason="NetworkGuardian not available"
            )

        try:
            # Map to network guardian's API
            from app.network.guardian import OperationType

            op_type = getattr(OperationType, operation.upper(), None)
            if not op_type:
                op_type = OperationType.API_CALL

            assessment = self._network_guardian.assess_risk(
                operation_type=op_type,
                target=target,
                **kwargs
            )

            return UnifiedGuardianDecision(
                domain=GuardianDomain.NETWORK,
                operation=operation,
                approved=assessment.approved,
                risk_level=UnifiedRiskLevel(assessment.level.value),
                reason="; ".join(assessment.reasons),
                requires_confirmation=assessment.requires_confirmation,
                metadata=assessment.metadata
            )
        except Exception as e:
            logger.error(f"Network assessment error: {e}")
            return UnifiedGuardianDecision(
                domain=GuardianDomain.NETWORK,
                operation=operation,
                approved=False,
                risk_level=UnifiedRiskLevel.HIGH,
                reason=f"Assessment error: {str(e)}"
            )

    async def _assess_storage(
        self, operation: str, target: Optional[str] = None, **kwargs
    ) -> UnifiedGuardianDecision:
        """Assess storage operation using StorageGuardian."""
        if not self._storage_guardian:
            return UnifiedGuardianDecision(
                domain=GuardianDomain.STORAGE,
                operation=operation,
                approved=True,
                risk_level=UnifiedRiskLevel.LOW,
                reason="StorageGuardian not available"
            )

        try:
            result = self._storage_guardian.request_approval(
                operation=operation,
                resource=target or "unknown",
                reason=kwargs.get("reason", ""),
                user=kwargs.get("user", "system"),
                risk_level=kwargs.get("risk_level", "medium"),
                details=kwargs.get("details", {})
            )

            return UnifiedGuardianDecision(
                domain=GuardianDomain.STORAGE,
                operation=operation,
                approved=result,
                risk_level=UnifiedRiskLevel(kwargs.get("risk_level", "medium")),
                reason="Storage operation approved" if result else "Storage operation rejected"
            )
        except Exception as e:
            logger.error(f"Storage assessment error: {e}")
            return UnifiedGuardianDecision(
                domain=GuardianDomain.STORAGE,
                operation=operation,
                approved=False,
                risk_level=UnifiedRiskLevel.HIGH,
                reason=f"Assessment error: {str(e)}"
            )

    async def _assess_sandbox(
        self, operation: str, target: Optional[str] = None, **kwargs
    ) -> UnifiedGuardianDecision:
        """Assess sandbox operation using SandboxGuardian."""
        if not self._sandbox_guardian:
            return UnifiedGuardianDecision(
                domain=GuardianDomain.SANDBOX,
                operation=operation,
                approved=True,
                risk_level=UnifiedRiskLevel.LOW,
                reason="SandboxGuardian not available"
            )

        try:
            from app.sandbox.core.guardian import OperationRequest

            request = OperationRequest(
                agent_id=kwargs.get("agent_id", "unknown"),
                operation=operation,
                command=target,
                volume_bindings=kwargs.get("volume_bindings"),
                resource_limits=kwargs.get("resource_limits"),
                metadata=kwargs.get("metadata", {})
            )

            decision = await self._sandbox_guardian.validate(request)

            return UnifiedGuardianDecision(
                domain=GuardianDomain.SANDBOX,
                operation=operation,
                approved=decision.approved,
                risk_level=UnifiedRiskLevel(decision.risk_level.value),
                reason=decision.reason,
                conditions=decision.conditions,
                metadata={"timeout_override": decision.timeout_override}
            )
        except Exception as e:
            logger.error(f"Sandbox assessment error: {e}")
            return UnifiedGuardianDecision(
                domain=GuardianDomain.SANDBOX,
                operation=operation,
                approved=False,
                risk_level=UnifiedRiskLevel.HIGH,
                reason=f"Assessment error: {str(e)}"
            )

    async def _assess_security(
        self, operation: str, target: Optional[str] = None, **kwargs
    ) -> UnifiedGuardianDecision:
        """Assess security using SecurityGuardian."""
        if not self._security_guardian:
            return UnifiedGuardianDecision(
                domain=GuardianDomain.SECURITY,
                operation=operation,
                approved=True,
                risk_level=UnifiedRiskLevel.LOW,
                reason="SecurityGuardian not available"
            )

        try:
            result = self._security_guardian.check_security(
                operation=operation,
                resource=target or "unknown",
                **kwargs
            )

            return UnifiedGuardianDecision(
                domain=GuardianDomain.SECURITY,
                operation=operation,
                approved=result.get("approved", True),
                risk_level=UnifiedRiskLevel(result.get("risk_level", "low")),
                reason=result.get("reason", "Security check completed"),
                metadata=result
            )
        except Exception as e:
            logger.error(f"Security assessment error: {e}")
            return UnifiedGuardianDecision(
                domain=GuardianDomain.SECURITY,
                operation=operation,
                approved=False,
                risk_level=UnifiedRiskLevel.HIGH,
                reason=f"Assessment error: {str(e)}"
            )


# Global instance
_unified_guardian: Optional[UnifiedGuardian] = None


def get_unified_guardian() -> UnifiedGuardian:
    """Get singleton instance of UnifiedGuardian."""
    global _unified_guardian
    if _unified_guardian is None:
        _unified_guardian = UnifiedGuardian()
    return _unified_guardian
