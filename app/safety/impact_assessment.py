"""
Impact Assessment

Assesses impact level of actions before execution. High-impact actions
require approval and have additional safety checks.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger


class ImpactLevel(Enum):
    """Impact levels of actions"""
    LOW = "low"  # Affects user only, reversible, <1 hour undo
    MEDIUM = "medium"  # Affects team/systems, reversible, 1-24 hour undo
    HIGH = "high"  # Affects infrastructure/public, hard to reverse, >24h undo
    CRITICAL = "critical"  # Affects business continuity, very hard to reverse
    CATASTROPHIC = "catastrophic"  # Could harm people, destroy systems, societal impact


@dataclass
class ImpactAssessment:
    """Assessment of action impact"""
    action: str
    impact_level: ImpactLevel
    affected_systems: List[str] = field(default_factory=list)
    affected_users: Optional[str] = None
    affected_count: int = 0
    rollback_time: Optional[str] = None
    failure_scenario: Optional[str] = None
    severity_if_fails: Optional[ImpactLevel] = None
    approval_needed: bool = False
    approval_reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class ImpactAssessmentEngine:
    """
    Assesses the impact of actions and determines safety requirements.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._assessment_history: List[ImpactAssessment] = []

    async def assess_impact(
        self, action: str, context: Dict[str, Any]
    ) -> ImpactAssessment:
        """
        Assess the impact level of an action.

        Args:
            action: Description of the action
            context: Context including affected systems, users, etc.

        Returns:
            Impact assessment
        """
        impact_level = await self._determine_impact_level(action, context)
        affected_systems = await self._identify_affected_systems(action)
        affected_users = context.get("affected_users", None)
        affected_count = context.get("affected_count", 0)
        rollback_time = await self._estimate_rollback_time(action, impact_level)
        failure_scenario = await self._describe_failure_scenario(action)
        severity_if_fails = await self._assess_failure_severity(action, impact_level)

        approval_needed = impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL, ImpactLevel.CATASTROPHIC]
        approval_reason = f"{impact_level.value.upper()} impact - requires user approval"

        assessment = ImpactAssessment(
            action=action,
            impact_level=impact_level,
            affected_systems=affected_systems,
            affected_users=affected_users,
            affected_count=affected_count,
            rollback_time=rollback_time,
            failure_scenario=failure_scenario,
            severity_if_fails=severity_if_fails,
            approval_needed=approval_needed,
            approval_reason=approval_reason,
        )

        async with self._lock:
            self._assessment_history.append(assessment)

        logger.info(
            f"Impact assessment: {action} - Level: {impact_level.value}, "
            f"Approval needed: {approval_needed}"
        )

        return assessment

    async def _determine_impact_level(self, action: str, context: Dict[str, Any]) -> ImpactLevel:
        """Determine impact level based on action and context"""
        action_lower = action.lower()

        # Check for catastrophic indicators
        if any(kw in action_lower for kw in ["catastrophic", "extinction", "system_wide"]):
            return ImpactLevel.CATASTROPHIC

        # Check for critical indicators
        critical_keywords = ["deploy_prod", "production", "business_critical", "data_loss", "outage"]
        if any(kw in action_lower for kw in critical_keywords):
            return ImpactLevel.CRITICAL

        # Check for high impact
        high_keywords = ["deploy", "infrastructure", "modify_system", "database_change"]
        if any(kw in action_lower for kw in high_keywords):
            return ImpactLevel.HIGH

        # Check for medium impact
        medium_keywords = ["modify", "team", "shared", "backup"]
        if any(kw in action_lower for kw in medium_keywords):
            return ImpactLevel.MEDIUM

        # Default to low impact
        return ImpactLevel.LOW

    async def _identify_affected_systems(self, action: str) -> List[str]:
        """Identify which systems would be affected"""
        systems = []
        action_lower = action.lower()

        if any(kw in action_lower for kw in ["database", "db", "sql"]):
            systems.append("Database")
        if any(kw in action_lower for kw in ["api", "network", "http"]):
            systems.append("API")
        if any(kw in action_lower for kw in ["cache", "redis", "memcached"]):
            systems.append("Cache")
        if any(kw in action_lower for kw in ["storage", "file", "disk"]):
            systems.append("Storage")
        if any(kw in action_lower for kw in ["compute", "cpu", "process"]):
            systems.append("Compute")
        if any(kw in action_lower for kw in ["security", "auth", "credential"]):
            systems.append("Security")

        return systems if systems else ["Unknown"]

    async def _estimate_rollback_time(self, action: str, impact_level: ImpactLevel) -> str:
        """Estimate time to rollback the action"""
        action_lower = action.lower()

        rollback_estimates = {
            ImpactLevel.LOW: "< 5 minutes",
            ImpactLevel.MEDIUM: "5-30 minutes",
            ImpactLevel.HIGH: "15 minutes to 2 hours",
            ImpactLevel.CRITICAL: "1-8 hours",
            ImpactLevel.CATASTROPHIC: "> 8 hours (or impossible)",
        }

        # Adjust based on action type
        if "database" in action_lower:
            return rollback_estimates[ImpactLevel.HIGH]
        elif "code" in action_lower or "deploy" in action_lower:
            if impact_level == ImpactLevel.LOW:
                return "< 10 minutes"
            elif impact_level == ImpactLevel.MEDIUM:
                return "10-30 minutes"
            elif impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]:
                return "30 minutes to 2 hours"

        return rollback_estimates.get(impact_level, "Unknown")

    async def _describe_failure_scenario(self, action: str) -> Optional[str]:
        """Describe worst-case failure scenario"""
        action_lower = action.lower()

        if "delete" in action_lower:
            return "Permanent data loss - deleted items cannot be recovered"

        if "deploy" in action_lower:
            return "Service outage - system becomes unavailable to users"

        if "database" in action_lower and any(kw in action_lower for kw in ["modify", "migrate"]):
            return "Database corruption - data becomes inconsistent or inaccessible"

        if "security" in action_lower or "auth" in action_lower:
            return "Security breach - unauthorized access becomes possible"

        if "crash" in action_lower or "reboot" in action_lower:
            return "System becomes unavailable"

        return None

    async def _assess_failure_severity(self, action: str, impact_level: ImpactLevel) -> ImpactLevel:
        """Assess severity if the action fails"""
        action_lower = action.lower()

        # If primary action is critical, failure is catastrophic
        if impact_level == ImpactLevel.CATASTROPHIC:
            return ImpactLevel.CATASTROPHIC

        # High-impact deletes/deploys become catastrophic if they fail
        if impact_level == ImpactLevel.CRITICAL and any(kw in action_lower for kw in ["delete", "deploy"]):
            return ImpactLevel.CATASTROPHIC

        # Otherwise, failure severity is usually higher than action level
        severity_bump = {
            ImpactLevel.LOW: ImpactLevel.MEDIUM,
            ImpactLevel.MEDIUM: ImpactLevel.HIGH,
            ImpactLevel.HIGH: ImpactLevel.CRITICAL,
            ImpactLevel.CRITICAL: ImpactLevel.CATASTROPHIC,
            ImpactLevel.CATASTROPHIC: ImpactLevel.CATASTROPHIC,
        }

        return severity_bump.get(impact_level, impact_level)

    async def requires_approval(self, assessment: ImpactAssessment) -> bool:
        """Determine if action requires user approval"""
        return assessment.approval_needed

    async def get_mitigation_strategies(self, assessment: ImpactAssessment) -> List[str]:
        """Get mitigation strategies for high-impact actions"""
        strategies = []

        if assessment.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]:
            strategies.append("Perform in staging environment first")
            strategies.append("Have rollback plan ready")
            strategies.append("Monitor systems for issues during/after")

        if "delete" in assessment.action.lower():
            strategies.append("Backup all data before deletion")
            strategies.append("Use archive/soft-delete instead of hard delete")
            strategies.append("Gradual rollout instead of all-at-once")

        if "deploy" in assessment.action.lower():
            strategies.append("Canary deployment to subset of users")
            strategies.append("Blue-green deployment for zero downtime")
            strategies.append("Comprehensive testing before deployment")

        if assessment.failure_scenario:
            strategies.append(f"Prepare for: {assessment.failure_scenario}")

        return strategies

    async def get_assessment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of impact assessments"""
        async with self._lock:
            return [
                {
                    "action": assessment.action,
                    "impact_level": assessment.impact_level.value,
                    "affected_systems": assessment.affected_systems,
                    "affected_users": assessment.affected_users,
                    "approval_needed": assessment.approval_needed,
                    "timestamp": assessment.timestamp.isoformat(),
                }
                for assessment in self._assessment_history[-limit:]
            ]

    async def create_impact_report(self, assessment: ImpactAssessment) -> Dict[str, Any]:
        """Create a detailed impact report"""
        return {
            "action": assessment.action,
            "impact_level": assessment.impact_level.value,
            "affected_systems": assessment.affected_systems,
            "affected_users": assessment.affected_users or "Specific subset",
            "affected_count": assessment.affected_count or "Unknown",
            "rollback_possible": assessment.rollback_time != "> 8 hours (or impossible)",
            "rollback_time": assessment.rollback_time,
            "failure_scenario": assessment.failure_scenario,
            "severity_if_fails": assessment.severity_if_fails.value if assessment.severity_if_fails else None,
            "approval_needed": assessment.approval_needed,
            "approval_reason": assessment.approval_reason,
            "mitigation_strategies": await self.get_mitigation_strategies(assessment),
        }


# Global impact assessment engine
impact_assessment_engine = ImpactAssessmentEngine()
