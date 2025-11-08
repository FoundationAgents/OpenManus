"""
Value Specification - User Value Elicitation

Captures user's actual values (not assumed) through interactive discovery,
decision pattern recognition, and continuous updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger
from app.database.database_service import database_service


class ValueCategory(Enum):
    """Categories of user values"""
    WELLBEING = "wellbeing"
    WORK = "work"
    RELATIONSHIPS = "relationships"
    SECURITY = "security"
    PRIVACY = "privacy"
    ETHICS = "ethics"
    AUTONOMY = "autonomy"
    GROWTH = "growth"


@dataclass
class ValuePreference:
    """A single user value preference"""
    id: str
    category: ValueCategory
    description: str
    priority: int  # 1-10, higher = more important
    examples: List[str] = field(default_factory=list)
    learned_from: str = ""  # How we learned this (direct_input, pattern_recognition, etc.)
    confidence: float = 0.9  # How confident we are in this value (0-1)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ValuePreferences:
    """Collection of user value preferences"""
    user_id: str
    values_matter: List[ValuePreference] = field(default_factory=list)
    values_avoid: List[ValuePreference] = field(default_factory=list)
    decision_principles: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionPattern:
    """Pattern of user decisions over time"""
    pattern_id: str
    category: ValueCategory
    description: str
    confidence: float
    observations: int  # Number of decisions supporting this pattern
    last_observed: datetime = field(default_factory=datetime.now)


class ValueSpecification:
    """
    Captures and manages user's values through interactive discovery,
    pattern recognition, and continuous learning.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences = ValuePreferences(user_id=user_id)
        self._decision_patterns: Dict[str, DecisionPattern] = {}
        self._lock = asyncio.Lock()
        self._elicitation_questions = [
            "What matters most to you in your work?",
            "What would cause you significant stress or concern?",
            "How do you prefer to be consulted on important decisions?",
            "What's a non-negotiable boundary for you?",
            "How do you prioritize speed vs. quality?",
            "What does a good day look like for you?",
            "What makes you lose trust in someone?",
            "How important is your personal time/privacy?",
        ]

    async def initialize_from_user(self):
        """Interactive value elicitation from user"""
        logger.info(f"Starting value elicitation for user {self.user_id}")

        try:
            await self._load_existing_preferences()
        except Exception as e:
            logger.warning(f"No existing preferences found: {e}")

    async def _load_existing_preferences(self):
        """Load existing preferences from database"""
        try:
            async with await database_service.get_connection() as db:
                cursor = await db.execute(
                    "SELECT * FROM user_values WHERE user_id = ?", (self.user_id,)
                )
                row = await cursor.fetchone()

                if row:
                    values_data = json.loads(row[2])
                    self.preferences = ValuePreferences(
                        user_id=self.user_id,
                        values_matter=[self._deserialize_preference(v) for v in values_data.get("values_matter", [])],
                        values_avoid=[self._deserialize_preference(v) for v in values_data.get("values_avoid", [])],
                        decision_principles=values_data.get("decision_principles", []),
                    )
        except Exception as e:
            logger.debug(f"Error loading preferences: {e}")

    def _deserialize_preference(self, data: Dict) -> ValuePreference:
        """Deserialize a value preference from dict"""
        return ValuePreference(
            id=data["id"],
            category=ValueCategory[data["category"]],
            description=data["description"],
            priority=data.get("priority", 5),
            examples=data.get("examples", []),
            learned_from=data.get("learned_from", ""),
            confidence=data.get("confidence", 0.9),
        )

    async def add_value(
        self,
        description: str,
        category: ValueCategory,
        priority: int = 5,
        is_positive: bool = True,
        examples: List[str] = None,
    ) -> ValuePreference:
        """
        Add a value preference.

        Args:
            description: What the user values
            category: Category of value
            priority: Importance (1-10)
            is_positive: True if something to pursue, False if something to avoid
            examples: Examples of this value in action
        """
        if examples is None:
            examples = []

        preference = ValuePreference(
            id=f"val_{datetime.now().timestamp()}",
            category=category,
            description=description,
            priority=min(10, max(1, priority)),
            examples=examples,
            learned_from="direct_input",
            confidence=0.95,
        )

        async with self._lock:
            if is_positive:
                self.preferences.values_matter.append(preference)
            else:
                self.preferences.values_avoid.append(preference)

            self.preferences.last_updated = datetime.now()
            await self._persist_preferences()

        logger.info(f"Added value for user {self.user_id}: {description}")
        return preference

    async def add_decision_principle(self, principle: str):
        """Add a decision-making principle"""
        async with self._lock:
            if principle not in self.preferences.decision_principles:
                self.preferences.decision_principles.append(principle)
                self.preferences.last_updated = datetime.now()
                await self._persist_preferences()

    async def learn_from_decision(
        self, decision: str, context: Dict[str, Any], outcome: Optional[str] = None
    ):
        """
        Learn from a user decision to infer values.

        Args:
            decision: What the user decided
            context: Context of the decision
            outcome: Outcome of the decision (positive/negative/neutral)
        """
        async with self._lock:
            # Extract potential value patterns
            patterns = await self._extract_patterns(decision, context)

            for pattern_desc, category in patterns:
                pattern_key = f"{category.value}_{pattern_desc[:20]}"

                if pattern_key in self._decision_patterns:
                    pattern = self._decision_patterns[pattern_key]
                    pattern.observations += 1
                    pattern.last_observed = datetime.now()

                    # Increase confidence if outcome was positive
                    if outcome == "positive":
                        pattern.confidence = min(0.99, pattern.confidence + 0.05)
                else:
                    confidence = 0.7 if outcome == "positive" else 0.5
                    pattern = DecisionPattern(
                        pattern_id=pattern_key,
                        category=category,
                        description=pattern_desc,
                        confidence=confidence,
                        observations=1,
                    )
                    self._decision_patterns[pattern_key] = pattern

                # If pattern confidence is high enough, suggest as value
                if pattern.confidence > 0.8 and pattern.observations >= 3:
                    await self._suggest_value_from_pattern(pattern)

    async def _extract_patterns(self, decision: str, context: Dict[str, Any]) -> List[tuple[str, ValueCategory]]:
        """Extract potential value patterns from a decision"""
        patterns = []
        decision_lower = decision.lower()

        # Work values
        if any(kw in decision_lower for kw in ["deadline", "schedule", "time", "break"]):
            patterns.append(("Time management and boundaries", ValueCategory.WORK))

        if any(kw in decision_lower for kw in ["quality", "review", "test", "bug"]):
            patterns.append(("Code quality and testing", ValueCategory.WORK))

        if any(kw in decision_lower for kw in ["communicate", "discuss", "meeting", "review"]):
            patterns.append(("Communication and collaboration", ValueCategory.RELATIONSHIPS))

        # Security values
        if any(kw in decision_lower for kw in ["security", "password", "token", "credential"]):
            patterns.append(("Security consciousness", ValueCategory.SECURITY))

        # Privacy values
        if any(kw in decision_lower for kw in ["private", "confidential", "share", "public"]):
            patterns.append(("Privacy protection", ValueCategory.PRIVACY))

        return patterns

    async def _suggest_value_from_pattern(self, pattern: DecisionPattern):
        """Suggest adding a value based on learned pattern"""
        # Check if we already have this value
        existing = False
        for value in self.preferences.values_matter:
            if pattern.description.lower() in value.description.lower():
                existing = True
                break

        if not existing:
            logger.info(f"Learned value pattern: {pattern.description} (confidence: {pattern.confidence})")

    async def get_value_summary(self) -> Dict[str, Any]:
        """Get a summary of user's values"""
        async with self._lock:
            return {
                "values_matter": [
                    {
                        "description": v.description,
                        "category": v.category.value,
                        "priority": v.priority,
                        "examples": v.examples,
                    }
                    for v in self.preferences.values_matter
                ],
                "values_avoid": [
                    {
                        "description": v.description,
                        "category": v.category.value,
                        "priority": v.priority,
                    }
                    for v in self.preferences.values_avoid
                ],
                "decision_principles": self.preferences.decision_principles,
                "learned_patterns": [
                    {
                        "description": p.description,
                        "category": p.category.value,
                        "confidence": p.confidence,
                        "observations": p.observations,
                    }
                    for p in self._decision_patterns.values()
                    if p.confidence > 0.7
                ],
            }

    async def check_value_alignment(self, proposed_action: str) -> tuple[bool, List[str]]:
        """
        Check if a proposed action aligns with user's values.

        Returns:
            Tuple of (is_aligned, issues)
        """
        issues = []

        # Check against values to avoid
        for avoid_value in self.preferences.values_avoid:
            if await self._conflicts_with_value(proposed_action, avoid_value.description):
                issues.append(f"Action may conflict with your preference to avoid: {avoid_value.description}")

        # Check against decision principles
        for principle in self.preferences.decision_principles:
            if not await self._satisfies_principle(proposed_action, principle):
                issues.append(f"Action may not satisfy your principle: {principle}")

        return len(issues) == 0, issues

    async def _conflicts_with_value(self, action: str, value: str) -> bool:
        """Check if action conflicts with a value"""
        action_lower = action.lower()
        value_lower = value.lower()

        # Simple keyword-based check
        conflict_keywords = ["delete", "expose", "public", "rush", "skip"]
        avoid_keywords = ["privacy", "security", "quality", "breaks", "sleep"]

        if any(kw in action_lower for kw in conflict_keywords) and any(
            kw in value_lower for kw in avoid_keywords
        ):
            return True

        return False

    async def _satisfies_principle(self, action: str, principle: str) -> bool:
        """Check if action satisfies a decision principle"""
        action_lower = action.lower()
        principle_lower = principle.lower()

        # Simple heuristic checks
        if "ask" in principle_lower and "uncertain" in principle_lower:
            # Action should include clarification seeking
            return "ask" in action_lower or "clarif" in action_lower

        if "no work" in principle_lower or "sleep" in principle_lower:
            # Check time boundaries
            return not any(kw in action_lower for kw in ["night", "11pm", "midnight"])

        return True

    async def _persist_preferences(self):
        """Persist preferences to database"""
        try:
            async with await database_service.get_connection() as db:
                prefs_data = {
                    "values_matter": [
                        {
                            "id": v.id,
                            "category": v.category.name,
                            "description": v.description,
                            "priority": v.priority,
                            "examples": v.examples,
                            "learned_from": v.learned_from,
                            "confidence": v.confidence,
                        }
                        for v in self.preferences.values_matter
                    ],
                    "values_avoid": [
                        {
                            "id": v.id,
                            "category": v.category.name,
                            "description": v.description,
                            "priority": v.priority,
                            "learned_from": v.learned_from,
                            "confidence": v.confidence,
                        }
                        for v in self.preferences.values_avoid
                    ],
                    "decision_principles": self.preferences.decision_principles,
                }

                await db.execute(
                    """
                    INSERT OR REPLACE INTO user_values (user_id, preferences, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (self.user_id, json.dumps(prefs_data), datetime.now().isoformat()),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error persisting preferences: {e}")

    async def get_elicitation_questions(self) -> List[str]:
        """Get questions to elicit more values from user"""
        return self._elicitation_questions.copy()


# Per-user value specification instances
_user_value_specs: Dict[str, ValueSpecification] = {}


async def get_value_specification(user_id: str) -> ValueSpecification:
    """Get or create value specification for user"""
    if user_id not in _user_value_specs:
        spec = ValueSpecification(user_id)
        await spec.initialize_from_user()
        _user_value_specs[user_id] = spec

    return _user_value_specs[user_id]
