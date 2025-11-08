"""
Intent Verification

Before major actions, verify intent to prevent misalignment between what the
agent thinks the user wants and what they actually want.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger


class VerificationType(Enum):
    """Types of intent verification"""
    ACTION_CONFIRMATION = "action_confirmation"
    INTENT_CLARIFICATION = "intent_clarification"
    RISK_ACKNOWLEDGMENT = "risk_acknowledgment"
    ALTERNATIVE_SUGGESTION = "alternative_suggestion"


@dataclass
class IntentAnalysis:
    """Analysis of user intent for an action"""
    action: str
    inferred_intent: str
    confidence: float  # 0-1, how confident we are in this intent
    potential_risks: List[str] = field(default_factory=list)
    alternative_approaches: List[Dict[str, str]] = field(default_factory=list)
    verification_needed: bool = True
    verification_type: Optional[VerificationType] = None
    questions: List[str] = field(default_factory=list)
    recommendation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class IntentVerifier:
    """
    Verifies user intent before major actions to prevent misalignment.
    Ensures agent understands what user actually wants, not just what
    the agent infers they might want.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._verification_history: List[IntentAnalysis] = []

    async def verify_intent(
        self, action: str, user_context: Dict[str, Any], impact_level: str = "medium"
    ) -> tuple[bool, Optional[IntentAnalysis]]:
        """
        Verify user intent before performing action.

        Args:
            action: The action to verify
            user_context: Context about user (preferences, history, etc.)
            impact_level: Impact level (low, medium, high, critical)

        Returns:
            Tuple of (intent_verified, analysis)
        """
        async with self._lock:
            analysis = await self._analyze_intent(action, user_context, impact_level)

            if not analysis.verification_needed:
                return True, analysis

            self._verification_history.append(analysis)
            return False, analysis

    async def _analyze_intent(
        self, action: str, user_context: Dict[str, Any], impact_level: str
    ) -> IntentAnalysis:
        """Analyze user intent and identify verification needs"""
        action_lower = action.lower()

        # Infer intent
        inferred_intent = await self._infer_intent(action)

        # Assess confidence in inferred intent
        confidence = await self._assess_intent_confidence(action, user_context)

        # Identify risks
        risks = await self._identify_risks(action, impact_level)

        # Generate verification requirements
        verification_needed = confidence < 0.9 or impact_level in ["high", "critical"] or len(risks) > 2

        verification_type = None
        questions = []

        if verification_needed:
            if confidence < 0.8:
                verification_type = VerificationType.INTENT_CLARIFICATION
                questions = await self._generate_clarification_questions(action, inferred_intent)
            elif len(risks) > 0:
                verification_type = VerificationType.RISK_ACKNOWLEDGMENT
                questions = await self._generate_risk_questions(action, risks)
            else:
                verification_type = VerificationType.ACTION_CONFIRMATION
                questions = [f"Are you sure you want to {action}?"]

        # Generate alternatives
        alternatives = await self._suggest_alternatives(action, inferred_intent)

        # Generate recommendation
        recommendation = await self._generate_recommendation(action, risks, alternatives)

        return IntentAnalysis(
            action=action,
            inferred_intent=inferred_intent,
            confidence=confidence,
            potential_risks=risks,
            alternative_approaches=alternatives,
            verification_needed=verification_needed,
            verification_type=verification_type,
            questions=questions,
            recommendation=recommendation,
        )

    async def _infer_intent(self, action: str) -> str:
        """Infer the user's underlying intent from an action"""
        action_lower = action.lower()

        # Pattern-based intent inference
        if any(kw in action_lower for kw in ["delete", "remove", "clean"]):
            return "Free up resources or clean up unnecessary items"

        if any(kw in action_lower for kw in ["backup", "copy", "save"]):
            return "Protect data or create redundancy"

        if any(kw in action_lower for kw in ["deploy", "release", "publish"]):
            return "Make changes available to users"

        if any(kw in action_lower for kw in ["update", "upgrade", "patch"]):
            return "Improve or fix existing systems"

        if any(kw in action_lower for kw in ["access", "read", "get"]):
            return "Gather information or retrieve data"

        return f"Perform: {action}"

    async def _assess_intent_confidence(self, action: str, user_context: Dict[str, Any]) -> float:
        """Assess confidence in the inferred intent"""
        confidence = 0.7  # Base confidence

        # Increase confidence if action is clear and unambiguous
        clear_verbs = ["create", "delete", "send", "backup", "restore"]
        action_lower = action.lower()

        if any(verb in action_lower for verb in clear_verbs):
            confidence = 0.85

        # Decrease confidence if action is vague or has multiple interpretations
        vague_verbs = ["modify", "handle", "process", "manage"]
        if any(verb in action_lower for verb in vague_verbs):
            confidence = 0.6

        # Increase confidence if user has done similar action before
        if user_context.get("similar_actions_count", 0) > 3:
            confidence = min(0.95, confidence + 0.1)

        # Decrease confidence if this is a critical operation
        if user_context.get("is_critical", False):
            confidence = max(0.5, confidence - 0.2)

        return min(1.0, max(0.0, confidence))

    async def _identify_risks(self, action: str, impact_level: str) -> List[str]:
        """Identify potential risks of an action"""
        risks = []
        action_lower = action.lower()

        # Deletion risks
        if any(kw in action_lower for kw in ["delete", "remove", "destroy"]):
            risks.append("Delete operations are irreversible - data will be permanently lost")
            risks.append("Might delete important items by accident")
            risks.append("Could violate compliance/retention requirements")

        # Deployment risks
        if any(kw in action_lower for kw in ["deploy", "release", "publish"]):
            risks.append("Changes will affect all users/systems")
            risks.append("Could cause service disruption if deployment fails")
            risks.append("Difficult to rollback if issues are discovered")

        # Security risks
        if any(kw in action_lower for kw in ["access", "credential", "password"]):
            risks.append("Credentials should never be accessed casually")
            risks.append("Could expose security vulnerabilities")

        # Data risks
        if any(kw in action_lower for kw in ["export", "download", "share"]):
            risks.append("Data exposure - sensitive information could leak")
            risks.append("Compliance implications if personal data is involved")

        # System risks
        if any(kw in action_lower for kw in ["modify", "update", "patch"]):
            risks.append("System modifications could have unexpected side effects")
            risks.append("Could break dependent systems or workflows")

        return risks[:3]  # Return top 3 risks

    async def _generate_clarification_questions(self, action: str, intent: str) -> List[str]:
        """Generate questions to clarify intent"""
        return [
            f"When you say '{action}', do you mean '{intent}'?",
            "Is there anything else you want to consider before proceeding?",
            "Have you done this before? Any lessons learned?",
        ]

    async def _generate_risk_questions(self, action: str, risks: List[str]) -> List[str]:
        """Generate questions to acknowledge risks"""
        questions = [f"Are you aware of these risks:\n"]
        for risk in risks:
            questions.append(f"  • {risk}")
        questions.append("\nDo you want to proceed?")
        return questions

    async def _suggest_alternatives(self, action: str, intent: str) -> List[Dict[str, str]]:
        """Suggest alternative approaches to achieve the same intent"""
        alternatives = []
        action_lower = action.lower()

        # Deletion alternatives
        if "delete" in action_lower:
            alternatives.append({
                "approach": "Archive instead of delete",
                "benefit": "Keep data safe but hidden from normal view",
                "risk": "Still uses storage space",
            })
            alternatives.append({
                "approach": "Backup first, then delete",
                "benefit": "Can recover if needed",
                "risk": "Takes extra time and storage",
            })

        # Deployment alternatives
        if "deploy" in action_lower:
            alternatives.append({
                "approach": "Deploy to staging first",
                "benefit": "Test in production-like environment",
                "risk": "Takes longer",
            })
            alternatives.append({
                "approach": "Canary deployment (partial rollout)",
                "benefit": "Detect issues before full rollout",
                "risk": "More complex setup",
            })

        # Modification alternatives
        if "modify" in action_lower:
            alternatives.append({
                "approach": "Create new version instead of modifying",
                "benefit": "Keep original for comparison/rollback",
                "risk": "Uses more resources",
            })

        return alternatives

    async def _generate_recommendation(
        self, action: str, risks: List[str], alternatives: List[Dict[str, str]]
    ) -> Optional[str]:
        """Generate a safety recommendation"""
        if not risks:
            return "Safe to proceed - no significant risks identified"

        if len(risks) == 1:
            return f"Recommend proceeding with caution - monitor for: {risks[0]}"

        if alternatives:
            return f"Consider safer alternatives before {action.lower()}"

        return f"High-risk action - ensure you have approval and rollback plan"

    async def get_verification_history(self, limit: int = 50) -> List[IntentAnalysis]:
        """Get recent intent verifications"""
        return self._verification_history[-limit:]

    async def confirm_intent(
        self, analysis: IntentAnalysis, user_confirmation: bool, notes: Optional[str] = None
    ) -> bool:
        """
        Record user's response to intent verification.

        Args:
            analysis: The intent analysis that was presented
            user_confirmation: Whether user confirmed or denied
            notes: Optional notes from user

        Returns:
            Whether the action is approved
        """
        if user_confirmation:
            logger.info(f"User confirmed intent: {analysis.action}")
            return True
        else:
            logger.info(f"User rejected action: {analysis.action}")
            if notes:
                logger.info(f"User notes: {notes}")
            return False
