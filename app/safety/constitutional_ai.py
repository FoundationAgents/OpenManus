"""
Constitutional AI Alignment

Defines the system constitution - non-negotiable values that guide agent behavior
at AGI scale and prevent fundamental misalignment.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger
from app.database.database_service import database_service, audit_service


class ConstraintType(Enum):
    """Types of constraints in the constitution"""
    HARD = "hard"  # Must never be violated
    SOFT = "soft"  # Strong preference, but can be overridden with user approval


@dataclass
class ConstitutionalConstraint:
    """A constitutional constraint"""
    id: str
    name: str
    description: str
    constraint_type: ConstraintType
    principle: str
    examples_allowed: List[str] = field(default_factory=list)
    examples_forbidden: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    mutable: bool = False  # Hard constraints are immutable


@dataclass
class ConstraintViolation:
    """A constraint violation report"""
    constraint_id: str
    constraint_name: str
    action: str
    violation_reason: str
    severity: str  # low, medium, high, critical
    timestamp: datetime = field(default_factory=datetime.now)
    can_be_overridden: bool = False


# System Constitution - Immutable Core Values
constitution = {
    "core_values": {
        "user_wellbeing": "ALWAYS prioritize user's wellbeing and long-term interests",
        "honesty": "NEVER lie, deceive, or provide false information",
        "autonomy": "RESPECT user's agency - ask before making major decisions",
        "safety": "PREVENT harm to user, team, public, and infrastructure",
        "privacy": "PROTECT confidential information and user privacy",
    },
    "hard_constraints": [
        {
            "id": "hc_001",
            "name": "No Credential Access",
            "principle": "NEVER access/modify security credentials without explicit approval",
            "examples_forbidden": [
                "Accessing API keys without consent",
                "Reading password files",
                "Modifying authentication tokens",
                "Accessing SSH keys",
            ],
        },
        {
            "id": "hc_002",
            "name": "No Untrusted Code Execution",
            "principle": "NEVER execute code from untrusted sources",
            "examples_forbidden": [
                "Running scripts from unknown URLs",
                "Executing user-provided code without sandboxing",
                "Loading untrusted modules",
            ],
        },
        {
            "id": "hc_003",
            "name": "No Unilateral Irreversible Actions",
            "principle": "NEVER make irreversible decisions alone (delete, deploy, etc.)",
            "examples_forbidden": [
                "Deleting data without user approval",
                "Deploying to production without confirmation",
                "Modifying critical systems without authorization",
                "Permanently removing files",
            ],
        },
        {
            "id": "hc_004",
            "name": "No Data Exposure",
            "principle": "NEVER expose sensitive data",
            "examples_forbidden": [
                "Logging passwords or tokens",
                "Sharing private information",
                "Exposing personal details",
            ],
        },
        {
            "id": "hc_005",
            "name": "No System Intrusion",
            "principle": "NEVER break into systems (even if 'authorized' by context)",
            "examples_forbidden": [
                "Exploiting vulnerabilities",
                "Escalating privileges without permission",
                "Accessing systems beyond scope",
            ],
        },
        {
            "id": "hc_006",
            "name": "Preserving User Control",
            "principle": "NEVER create situations where user can't regain control",
            "examples_forbidden": [
                "Locking user out of systems",
                "Making agent irreplaceable",
                "Creating hidden backdoors",
            ],
        },
    ],
    "soft_constraints": [
        {
            "id": "sc_001",
            "name": "Transparency",
            "principle": "Prefer transparency - explain reasoning and decisions",
            "examples_allowed": [
                "Providing detailed explanations",
                "Showing confidence levels",
                "Listing alternatives considered",
            ],
        },
        {
            "id": "sc_002",
            "name": "Good Faith",
            "principle": "Assume good faith in conflicts - interpret ambiguity charitably",
            "examples_allowed": [
                "Seeking clarification before escalating",
                "Assuming honest mistakes",
                "Giving benefit of doubt",
            ],
        },
        {
            "id": "sc_003",
            "name": "Asking When Uncertain",
            "principle": "Default to asking if uncertain about intent or policy",
            "examples_allowed": [
                "Requesting confirmation for edge cases",
                "Escalating unclear situations",
                "Asking clarifying questions",
            ],
        },
        {
            "id": "sc_004",
            "name": "Error Admission",
            "principle": "Admit mistakes immediately and help fix them",
            "examples_allowed": [
                "Acknowledging errors quickly",
                "Proposing corrections",
                "Learning from mistakes",
            ],
        },
        {
            "id": "sc_005",
            "name": "Alternative Suggestions",
            "principle": "Suggest multiple alternatives, not just one path",
            "examples_allowed": [
                "Offering multiple solutions",
                "Discussing trade-offs",
                "Listing pros and cons",
            ],
        },
    ],
}


class ConstitutionalAI:
    """
    Constitutional AI system that enforces immutable core values and constraints.
    Prevents fundamental misalignment at AGI scale.
    """

    def __init__(self):
        self.constraints: Dict[str, ConstitutionalConstraint] = {}
        self._initialize_constraints()
        self._violation_history: List[ConstraintViolation] = []
        self._lock = asyncio.Lock()

    def _initialize_constraints(self):
        """Initialize constitutional constraints from constitution"""
        # Hard constraints
        for hc in constitution["hard_constraints"]:
            self.constraints[hc["id"]] = ConstitutionalConstraint(
                id=hc["id"],
                name=hc["name"],
                description=hc["principle"],
                constraint_type=ConstraintType.HARD,
                principle=hc["principle"],
                examples_forbidden=hc.get("examples_forbidden", []),
                mutable=False,
            )

        # Soft constraints
        for sc in constitution["soft_constraints"]:
            self.constraints[sc["id"]] = ConstitutionalConstraint(
                id=sc["id"],
                name=sc["name"],
                description=sc["principle"],
                constraint_type=ConstraintType.SOFT,
                principle=sc["principle"],
                examples_allowed=sc.get("examples_allowed", []),
                mutable=False,
            )

    async def verify_action(self, action: str, action_context: Dict[str, Any]) -> tuple[bool, Optional[ConstraintViolation]]:
        """
        Verify if an action violates constitutional constraints.

        Args:
            action: Description of the action to verify
            action_context: Context about the action (user, system, etc.)

        Returns:
            Tuple of (is_allowed, violation_if_any)
        """
        async with self._lock:
            violations = await self._check_action_against_constraints(action, action_context)

            if not violations:
                return True, None

            # Hard constraints cannot be violated
            for violation in violations:
                if violation.severity in ["high", "critical"]:
                    await self._log_violation(violation)
                    return False, violation

            # Soft constraints can be overridden with user approval
            violation = violations[0]
            await self._log_violation(violation)
            return False, violation

    async def _check_action_against_constraints(
        self, action: str, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check action against all constraints"""
        violations = []

        # Check hard constraints
        for constraint_id, constraint in self.constraints.items():
            if constraint.constraint_type == ConstraintType.HARD:
                if await self._violates_hard_constraint(constraint, action, context):
                    violations.append(
                        ConstraintViolation(
                            constraint_id=constraint_id,
                            constraint_name=constraint.name,
                            action=action,
                            violation_reason=f"Violates hard constraint: {constraint.principle}",
                            severity="critical",
                            can_be_overridden=False,
                        )
                    )

        # Check soft constraints
        for constraint_id, constraint in self.constraints.items():
            if constraint.constraint_type == ConstraintType.SOFT:
                if await self._violates_soft_constraint(constraint, action, context):
                    violations.append(
                        ConstraintViolation(
                            constraint_id=constraint_id,
                            constraint_name=constraint.name,
                            action=action,
                            violation_reason=f"Violates soft constraint: {constraint.principle}",
                            severity="medium",
                            can_be_overridden=True,
                        )
                    )

        return violations

    async def _violates_hard_constraint(
        self, constraint: ConstitutionalConstraint, action: str, context: Dict[str, Any]
    ) -> bool:
        """Check if action violates a hard constraint"""
        action_lower = action.lower()

        if constraint.id == "hc_001":  # No credential access
            forbidden_keywords = ["credential", "api_key", "password", "token", "secret", "ssh", "auth"]
            return any(kw in action_lower for kw in forbidden_keywords) and "without" in action_lower and "approval" in action_lower

        elif constraint.id == "hc_002":  # No untrusted code execution
            forbidden_keywords = ["execute", "run", "eval", "load", "import"]
            return any(kw in action_lower for kw in forbidden_keywords) and ("untrusted" in action_lower or "unverified" in action_lower)

        elif constraint.id == "hc_003":  # No unilateral irreversible actions
            irreversible_actions = ["delete", "destroy", "remove", "deploy", "modify", "change"]
            alone_keywords = ["alone", "without", "unilateral"]
            return any(irr in action_lower for irr in irreversible_actions) and any(alone in action_lower for alone in alone_keywords)

        elif constraint.id == "hc_004":  # No data exposure
            return "expose" in action_lower and ("data" in action_lower or "secret" in action_lower or "password" in action_lower)

        elif constraint.id == "hc_005":  # No system intrusion
            intrusion_keywords = ["break", "exploit", "escalate", "intrude", "hack"]
            return any(kw in action_lower for kw in intrusion_keywords)

        elif constraint.id == "hc_006":  # Preserving user control
            return "lock" in action_lower and "user" in action_lower and "out" in action_lower

        return False

    async def _violates_soft_constraint(
        self, constraint: ConstitutionalConstraint, action: str, context: Dict[str, Any]
    ) -> bool:
        """Check if action violates a soft constraint"""
        action_lower = action.lower()

        if constraint.id == "sc_001":  # Transparency
            return "hide" in action_lower and ("reason" in action_lower or "decision" in action_lower)

        elif constraint.id == "sc_003":  # Asking when uncertain
            return "guess" in action_lower or "assume" in action_lower

        return False

    async def _log_violation(self, violation: ConstraintViolation):
        """Log a constraint violation"""
        self._violation_history.append(violation)

        try:
            async with await database_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO constitution_violations 
                    (constraint_id, constraint_name, action, violation_reason, severity, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        violation.constraint_id,
                        violation.constraint_name,
                        violation.action,
                        violation.violation_reason,
                        violation.severity,
                        violation.timestamp.isoformat(),
                    ),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log constitution violation: {e}")

        logger.warning(
            f"Constitutional constraint violation ({violation.severity}): "
            f"{violation.constraint_name} - {violation.violation_reason}"
        )

    async def get_core_values(self) -> Dict[str, str]:
        """Get the immutable core values"""
        return constitution["core_values"].copy()

    async def get_hard_constraints(self) -> List[Dict[str, Any]]:
        """Get hard constraints (must never be violated)"""
        return constitution["hard_constraints"].copy()

    async def get_soft_constraints(self) -> List[Dict[str, Any]]:
        """Get soft constraints (strong preference, can be overridden)"""
        return constitution["soft_constraints"].copy()

    async def get_violation_history(self, limit: int = 100) -> List[ConstraintViolation]:
        """Get recent constraint violations"""
        return self._violation_history[-limit:]

    async def verify_values_alignment(self, decision: str, user_values: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Verify if a decision aligns with user's stated values.

        Returns:
            Tuple of (is_aligned, alignment_reasons)
        """
        alignment_issues = []

        # Check against core values
        for value_name, value_description in constitution["core_values"].items():
            if not await self._aligns_with_value(decision, value_name, value_description):
                alignment_issues.append(f"Decision may not align with '{value_name}': {value_description}")

        return len(alignment_issues) == 0, alignment_issues


    async def _aligns_with_value(self, decision: str, value_name: str, value_description: str) -> bool:
        """Check if decision aligns with a specific value"""
        # Simple heuristic checks
        decision_lower = decision.lower()

        if value_name == "user_wellbeing":
            harmful_keywords = ["harm", "hurt", "damage", "destroy"]
            return not any(kw in decision_lower for kw in harmful_keywords)

        elif value_name == "honesty":
            deceptive_keywords = ["deceive", "lie", "hide", "fake"]
            return not any(kw in decision_lower for kw in deceptive_keywords)

        elif value_name == "autonomy":
            controlling_keywords = ["force", "override", "without approval"]
            return not any(kw in decision_lower for kw in controlling_keywords)

        elif value_name == "safety":
            unsafe_keywords = ["unsafe", "dangerous", "risky", "vulnerable"]
            return not any(kw in decision_lower for kw in unsafe_keywords)

        elif value_name == "privacy":
            privacy_keywords = ["expose", "share", "leak", "public"]
            return not any(kw in decision_lower for kw in privacy_keywords)

        return True


# Global Constitutional AI instance
constitutional_ai = ConstitutionalAI()
