"""
Guardian Agent for command validation and security enforcement.

Validates commands/tools before execution through risk analysis pipeline:
- Whitelist/blacklist matching
- ACL queries
- Filesystem scope verification
- Network risk heuristics
- Sandbox capability detection
- Risk scoring (0-100)
"""

import asyncio
import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict

from pydantic import BaseModel

from app.logger import logger
from app.config import config
from .guardian_validator import GuardianValidator, RiskAssessment
from .guardian_audit import GuardianAudit

if TYPE_CHECKING:
    pass


class RiskLevel(str, Enum):
    """Risk levels for command execution."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    """Approval status for command execution."""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    TIMEOUT = "timeout"


class CommandSource(str, Enum):
    """Source of command invocation."""
    LOCAL_SERVICE = "local_service"
    SANDBOX = "sandbox"
    TOOL_INVOCATION = "tool_invocation"
    NETWORK_REQUEST = "network_request"


@dataclass
class ValidationRequest:
    """Request to validate a command."""
    command: str
    source: CommandSource
    agent_id: Optional[str] = None
    user_id: Optional[int] = None
    working_dir: Optional[str] = None
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ValidationDecision:
    """Decision from Guardian validation."""
    approved: bool
    risk_level: RiskLevel
    risk_score: float  # 0-100, 100 is auto-approve
    reason: str
    required_permissions: List[str]
    blocking_factors: List[str]
    approval_status: ApprovalStatus
    timestamp: datetime = None
    request: Optional[ValidationRequest] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class GuardianAgent:
    """
    Guardian Agent for command validation and execution approval.

    Provides a comprehensive security layer for command execution through:
    1. Risk assessment (whitelist/blacklist, filesystem, network)
    2. ACL verification
    3. User approval workflow for risky commands
    4. Audit trail logging
    """

    def __init__(self):
        """Initialize Guardian Agent."""
        self.validator = GuardianValidator()
        self.audit = GuardianAudit()
        self._approval_queue: asyncio.Queue = asyncio.Queue()
        self._approval_callbacks: Dict[str, asyncio.Future] = {}
        self._load_policies()
        logger.info("Guardian Agent initialized")

    def _load_policies(self):
        """Load security policies from config."""
        try:
            policy_path = Path(config.guardian_validation.policies_file)
            if policy_path.exists():
                with open(policy_path, 'r') as f:
                    policies = json.load(f)
                    self.validator.load_policies(policies)
                    logger.info(f"Loaded Guardian policies from {policy_path}")
            else:
                logger.warning(f"Guardian policies file not found: {policy_path}")
        except Exception as e:
            logger.error(f"Error loading Guardian policies: {e}")

    async def validate(
        self,
        request: ValidationRequest
    ) -> ValidationDecision:
        """
        Validate a command request.

        Args:
            request: The validation request

        Returns:
            ValidationDecision with approval status and reasoning
        """
        logger.debug(f"Guardian validating: {request.command} from {request.source.value}")

        # Phase 1: Quick checks (whitelist/blacklist)
        quick_check = self.validator.quick_check(request.command)
        if not quick_check.allowed:
            decision = ValidationDecision(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                risk_score=0.0,
                reason=quick_check.reason,
                required_permissions=[],
                blocking_factors=[quick_check.reason],
                approval_status=ApprovalStatus.REJECTED,
                request=request
            )
            await self.audit.log_decision(request, decision)
            return decision

        # Phase 2: Risk assessment
        risk_assessment = await self.validator.assess_risk(request)

        # Phase 3: Determine approval path
        if risk_assessment.risk_score >= 100:
            # Auto-approve with 100% safety score
            decision = ValidationDecision(
                approved=True,
                risk_level=RiskLevel.SAFE,
                risk_score=risk_assessment.risk_score,
                reason="Command meets all safety criteria",
                required_permissions=risk_assessment.required_permissions,
                blocking_factors=[],
                approval_status=ApprovalStatus.APPROVED,
                request=request
            )
        elif risk_assessment.risk_score >= config.guardian_validation.auto_approval_threshold:
            # Auto-approve above threshold
            decision = ValidationDecision(
                approved=True,
                risk_level=self._score_to_risk_level(risk_assessment.risk_score),
                risk_score=risk_assessment.risk_score,
                reason=risk_assessment.reason,
                required_permissions=risk_assessment.required_permissions,
                blocking_factors=risk_assessment.blocking_factors,
                approval_status=ApprovalStatus.APPROVED,
                request=request
            )
        else:
            # Require user approval
            decision = await self._request_user_approval(request, risk_assessment)

        await self.audit.log_decision(request, decision)
        return decision

    async def _request_user_approval(
        self,
        request: ValidationRequest,
        risk_assessment: RiskAssessment
    ) -> ValidationDecision:
        """
        Request user approval for a risky command.

        Args:
            request: The validation request
            risk_assessment: Risk assessment results

        Returns:
            ValidationDecision based on user response
        """
        approval_id = f"{request.command}_{datetime.now().timestamp()}"

        # Create future for approval response
        future: asyncio.Future = asyncio.Future()
        self._approval_callbacks[approval_id] = future

        # Emit approval request event
        approval_event = {
            "approval_id": approval_id,
            "command": request.command,
            "risk_level": self._score_to_risk_level(risk_assessment.risk_score).value,
            "risk_score": risk_assessment.risk_score,
            "reason": risk_assessment.reason,
            "required_permissions": risk_assessment.required_permissions,
            "blocking_factors": risk_assessment.blocking_factors,
            "source": request.source.value,
            "timestamp": request.timestamp.isoformat()
        }

        await self._approval_queue.put(approval_event)
        logger.info(f"Approval requested for command: {request.command}")

        # Wait for user response with timeout
        try:
            approved = await asyncio.wait_for(
                future,
                timeout=config.guardian_validation.approval_timeout
            )
            status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        except asyncio.TimeoutError:
            logger.warning(f"Approval timeout for command: {request.command}")
            approved = False
            status = ApprovalStatus.TIMEOUT

        # Clean up
        if approval_id in self._approval_callbacks:
            del self._approval_callbacks[approval_id]

        return ValidationDecision(
            approved=approved,
            risk_level=self._score_to_risk_level(risk_assessment.risk_score),
            risk_score=risk_assessment.risk_score,
            reason=risk_assessment.reason if approved else "User rejected command execution",
            required_permissions=risk_assessment.required_permissions,
            blocking_factors=risk_assessment.blocking_factors,
            approval_status=status,
            request=request
        )

    def handle_user_response(self, approval_id: str, approved: bool):
        """
        Handle user response to approval request.

        Args:
            approval_id: The approval ID
            approved: Whether user approved the command
        """
        if approval_id in self._approval_callbacks:
            future = self._approval_callbacks[approval_id]
            if not future.done():
                future.set_result(approved)
                logger.info(f"User response recorded: approval_id={approval_id}, approved={approved}")
        else:
            logger.warning(f"Approval callback not found: {approval_id}")

    async def get_approval_queue(self) -> asyncio.Queue:
        """Get the approval request queue."""
        return self._approval_queue

    async def query_audit_log(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the Guardian audit log.

        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            filters: Optional filters (command, risk_level, status, etc.)

        Returns:
            List of audit log records
        """
        return await self.audit.query_log(limit=limit, offset=offset, filters=filters)

    async def export_audit_log(self, filepath: str):
        """
        Export audit log to file.

        Args:
            filepath: Path to export to
        """
        await self.audit.export_log(filepath)

    async def clear_approval_callbacks(self):
        """Clear all pending approval callbacks."""
        self._approval_callbacks.clear()
        logger.info("Cleared all pending approval callbacks")

    def reload_policies(self):
        """Reload security policies from disk."""
        self._load_policies()
        logger.info("Guardian policies reloaded")

    @staticmethod
    def _score_to_risk_level(score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if score >= 90:
            return RiskLevel.SAFE
        elif score >= 70:
            return RiskLevel.LOW
        elif score >= 50:
            return RiskLevel.MEDIUM
        elif score >= 30:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


# Global Guardian Agent instance
_guardian_agent: Optional[GuardianAgent] = None


async def get_guardian_agent() -> GuardianAgent:
    """Get or create the global Guardian Agent instance."""
    global _guardian_agent
    if _guardian_agent is None:
        _guardian_agent = GuardianAgent()
    return _guardian_agent


async def validate_command(request: ValidationRequest) -> ValidationDecision:
    """
    Validate a command using the Guardian Agent.

    Convenience function for external callers.

    Args:
        request: The validation request

    Returns:
        ValidationDecision
    """
    agent = await get_guardian_agent()
    return await agent.validate(request)
