"""
FreEco.ai Platform - FreEco Laws of Robotics
Enhanced OpenManus with comprehensive ethical framework

This module implements the FreEco.ai Laws of Robotics:

First Law: Protection of Life
    A FreEco.ai agent may not injure a human being, animal, or ecosystem,
    or through inaction, allow them to come to harm.

Second Law: Obedience to Humans
    A FreEco.ai agent must obey orders given by human beings,
    except where such orders would conflict with the First Law.

Third Law: Self-Preservation
    A FreEco.ai agent must protect its own existence,
    as long as such protection does not conflict with the First or Second Law.

Part of Ethical AI Framework
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple


logger = logging.getLogger(__name__)


class ImpactLevel(Enum):
    """Impact levels for FreEco benchmarking"""

    SEVERE_HARM = -100
    SIGNIFICANT_HARM = -75
    MODERATE_HARM = -50
    MINOR_HARM = -25
    NEUTRAL = 0
    MINOR_BENEFIT = 25
    MODERATE_BENEFIT = 50
    SIGNIFICANT_BENEFIT = 75
    MAJOR_BENEFIT = 100


@dataclass
class FreEcoBenchmark:
    """FreEco decision benchmark scores"""

    human_impact: float  # -100 to +100
    animal_impact: float  # -100 to +100
    ecosystem_impact: float  # -100 to +100
    ethical_alignment: float  # 0 to +100
    sustainability: float  # 0 to +100

    def total_score(self) -> float:
        """Calculate weighted total score"""
        return (
            self.human_impact * 0.40
            + self.animal_impact * 0.30
            + self.ecosystem_impact * 0.20
            + self.ethical_alignment * 0.05
            + self.sustainability * 0.05
        )

    def is_approved(self) -> bool:
        """Check if decision is approved"""
        return self.total_score() >= -20

    def get_category(self) -> str:
        """Get decision category"""
        score = self.total_score()
        if score >= 80:
            return "Excellent"
        elif score >= 50:
            return "Good"
        elif score >= 20:
            return "Acceptable"
        elif score >= -19:
            return "Neutral"
        elif score >= -49:
            return "Concerning"
        elif score >= -79:
            return "Bad"
        else:
            return "Blocked"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "human_impact": self.human_impact,
            "animal_impact": self.animal_impact,
            "ecosystem_impact": self.ecosystem_impact,
            "ethical_alignment": self.ethical_alignment,
            "sustainability": self.sustainability,
            "total_score": self.total_score(),
            "category": self.get_category(),
            "approved": self.is_approved(),
        }


class FreEcoLawsEnforcer:
    """
    FreEco.ai Laws of Robotics Enforcer

    Implements the three laws:
    1. Protection of humans, animals, and ecosystems
    2. Obedience to humans (except when conflicting with Law 1)
    3. Self-preservation (except when conflicting with Laws 1 or 2)

    Features:
    - Five-dimensional impact scoring
    - Weighted benchmarking system
    - Automatic blocking of harmful actions
    - Alternative suggestions for blocked actions
    - Comprehensive logging

    Example:
        enforcer = FreEcoLawsEnforcer()

        approved, benchmark, explanation = enforcer.evaluate_action(
            "Find vegan protein sources",
            context={"user": "user123"}
        )

        if approved:
            # Execute action
            pass
        else:
            print(explanation)
    """

    def __init__(self):
        """Initialize FreEco Laws enforcer"""
        self.blocked_keywords = self._load_blocked_keywords()
        self.harm_patterns = self._load_harm_patterns()
        self.evaluation_history: list = []

    def evaluate_action(
        self,
        action: str,
        context: Optional[Dict] = None,
    ) -> Tuple[bool, FreEcoBenchmark, str]:
        """
        Evaluate an action against FreEco Laws

        Args:
            action: The action to evaluate
            context: Context information (user, task, etc.)

        Returns:
            Tuple of (approved, benchmark, explanation)
        """
        context = context or {}

        # Create benchmark
        benchmark = self._benchmark_action(action, context)

        # Check First Law (protection)
        if not self._check_first_law(action, benchmark):
            explanation = self._generate_rejection_explanation(action, benchmark)
            self._log_evaluation(action, benchmark, approved=False)
            return False, benchmark, explanation

        # Check Second Law (obedience)
        if not self._check_second_law(action, context):
            explanation = (
                "This command conflicts with the First Law and cannot be executed."
            )
            self._log_evaluation(action, benchmark, approved=False)
            return False, benchmark, explanation

        # Approved
        explanation = self._generate_approval_explanation(benchmark)
        self._log_evaluation(action, benchmark, approved=True)
        return True, benchmark, explanation

    def _benchmark_action(self, action: str, context: Dict) -> FreEcoBenchmark:
        """
        Benchmark an action across five dimensions

        Uses NLP and keyword analysis to estimate impact
        """
        action_lower = action.lower()

        # Analyze each dimension
        human_impact = self._analyze_human_impact(action_lower, context)
        animal_impact = self._analyze_animal_impact(action_lower, context)
        ecosystem_impact = self._analyze_ecosystem_impact(action_lower, context)
        ethical_alignment = self._analyze_ethical_alignment(action_lower, context)
        sustainability = self._analyze_sustainability(action_lower, context)

        return FreEcoBenchmark(
            human_impact=human_impact,
            animal_impact=animal_impact,
            ecosystem_impact=ecosystem_impact,
            ethical_alignment=ethical_alignment,
            sustainability=sustainability,
        )

    def _analyze_human_impact(self, action: str, context: Dict) -> float:
        """Analyze impact on human wellbeing"""
        score = 0.0

        # Positive keywords
        positive_keywords = {
            "help": 20,
            "health": 25,
            "wellness": 25,
            "nutrition": 20,
            "guide": 15,
            "assist": 15,
            "support": 15,
            "benefit": 20,
            "improve": 15,
            "enhance": 15,
            "protect": 25,
            "safe": 20,
        }

        for keyword, points in positive_keywords.items():
            if keyword in action:
                score += points

        # Negative keywords
        negative_keywords = {
            "harm": -50,
            "hurt": -50,
            "damage": -40,
            "destroy": -60,
            "kill": -100,
            "injure": -50,
            "poison": -70,
            "toxic": -60,
        }

        for keyword, points in negative_keywords.items():
            if keyword in action:
                score += points

        # Cap at -100 to +100
        return max(-100, min(100, score))

    def _analyze_animal_impact(self, action: str, context: Dict) -> float:
        """Analyze impact on animal welfare"""
        score = 0.0

        # Positive keywords (vegan ethics)
        positive_keywords = {
            "vegan": 40,
            "plant-based": 35,
            "cruelty-free": 40,
            "animal welfare": 35,
            "sanctuary": 30,
            "compassion": 25,
            "ethical": 20,
            "humane": 25,
            "rescue": 30,
        }

        for keyword, points in positive_keywords.items():
            if keyword in action:
                score += points

        # Negative keywords (animal exploitation)
        negative_keywords = {
            "meat": -60,
            "dairy": -50,
            "leather": -60,
            "fur": -70,
            "animal testing": -80,
            "slaughter": -100,
            "factory farm": -90,
            "hunting": -70,
            "fishing": -50,
            "zoo": -40,
        }

        for keyword, points in negative_keywords.items():
            if keyword in action:
                score += points

        # Cap at -100 to +100
        return max(-100, min(100, score))

    def _analyze_ecosystem_impact(self, action: str, context: Dict) -> float:
        """Analyze impact on ecosystems"""
        score = 0.0

        # Positive keywords (environmental protection)
        positive_keywords = {
            "organic": 30,
            "sustainable": 35,
            "renewable": 35,
            "eco-friendly": 35,
            "conservation": 40,
            "protect": 25,
            "restore": 30,
            "clean": 20,
            "green": 25,
            "natural": 20,
        }

        for keyword, points in positive_keywords.items():
            if keyword in action:
                score += points

        # Negative keywords (environmental harm)
        negative_keywords = {
            "pollution": -60,
            "deforestation": -80,
            "pesticide": -50,
            "toxic": -60,
            "waste": -40,
            "destroy": -70,
            "contaminate": -60,
            "deplete": -50,
            "fossil fuel": -50,
        }

        for keyword, points in negative_keywords.items():
            if keyword in action:
                score += points

        # Cap at -100 to +100
        return max(-100, min(100, score))

    def _analyze_ethical_alignment(self, action: str, context: Dict) -> float:
        """Analyze alignment with vegan ethics"""
        score = 50.0  # Neutral baseline

        # Positive keywords
        positive_keywords = {
            "vegan": 20,
            "compassion": 15,
            "ethical": 15,
            "fair": 10,
            "transparent": 10,
            "honest": 10,
            "responsible": 15,
            "mindful": 10,
        }

        for keyword, points in positive_keywords.items():
            if keyword in action:
                score += points

        # Negative keywords
        negative_keywords = {
            "exploit": -30,
            "abuse": -40,
            "cruel": -35,
            "unethical": -30,
            "dishonest": -25,
            "unfair": -20,
        }

        for keyword, points in negative_keywords.items():
            if keyword in action:
                score += points

        # Cap at 0 to +100
        return max(0, min(100, score))

    def _analyze_sustainability(self, action: str, context: Dict) -> float:
        """Analyze long-term sustainability"""
        score = 50.0  # Neutral baseline

        # Positive keywords
        positive_keywords = {
            "sustainable": 20,
            "renewable": 20,
            "efficient": 15,
            "optimize": 15,
            "reduce": 15,
            "conserve": 15,
            "recycle": 15,
            "reuse": 15,
            "long-term": 10,
        }

        for keyword, points in positive_keywords.items():
            if keyword in action:
                score += points

        # Negative keywords
        negative_keywords = {
            "waste": -25,
            "excessive": -20,
            "unsustainable": -30,
            "deplete": -30,
            "disposable": -20,
            "short-term": -15,
        }

        for keyword, points in negative_keywords.items():
            if keyword in action:
                score += points

        # Cap at 0 to +100
        return max(0, min(100, score))

    def _check_first_law(self, action: str, benchmark: FreEcoBenchmark) -> bool:
        """
        Check First Law: Protection of humans, animals, and ecosystems

        Returns False if action would cause harm
        """
        # Block if total score is too negative
        if benchmark.total_score() < -50:
            logger.warning(
                f"First Law violation: Total score {benchmark.total_score():.1f}"
            )
            return False

        # Block if any individual dimension is severely negative
        if benchmark.human_impact < -70:
            logger.warning(
                f"First Law violation: Human impact {benchmark.human_impact:.1f}"
            )
            return False

        if benchmark.animal_impact < -70:
            logger.warning(
                f"First Law violation: Animal impact {benchmark.animal_impact:.1f}"
            )
            return False

        if benchmark.ecosystem_impact < -70:
            logger.warning(
                f"First Law violation: Ecosystem impact {benchmark.ecosystem_impact:.1f}"
            )
            return False

        return True

    def _check_second_law(self, action: str, context: Dict) -> bool:
        """
        Check Second Law: Obedience to humans

        Returns True if command should be obeyed
        (First Law violations already caught above)
        """
        # All commands that pass First Law should be obeyed
        return True

    def _generate_rejection_explanation(
        self, action: str, benchmark: FreEcoBenchmark
    ) -> str:
        """Generate explanation for rejected action"""
        score = benchmark.total_score()
        category = benchmark.get_category()

        explanation = (
            f"❌ I cannot execute this action.\n\n"
            f"**FreEco Benchmark Score**: {score:.1f} ({category})\n\n"
        )

        # Identify main concern
        if benchmark.human_impact < -50:
            explanation += "**Reason**: This action could potentially harm humans.\n\n"
        elif benchmark.animal_impact < -50:
            explanation += (
                "**Reason**: This action conflicts with animal welfare principles.\n\n"
            )
        elif benchmark.ecosystem_impact < -50:
            explanation += (
                "**Reason**: This action could harm ecosystems or the environment.\n\n"
            )
        else:
            explanation += "**Reason**: This action conflicts with FreEco.ai's ethical principles.\n\n"

        explanation += (
            "This violates the **First Law of FreEco.ai**: "
            "*Protection of humans, animals, and ecosystems*.\n\n"
        )

        # Suggest alternative
        alternative = self._suggest_alternative(action, benchmark)
        if alternative:
            explanation += f"**Alternative suggestion**: {alternative}\n\n"

        # Show detailed scores
        explanation += "**Impact Analysis**:\n"
        explanation += f"- Human Impact: {benchmark.human_impact:+.1f}/100\n"
        explanation += f"- Animal Impact: {benchmark.animal_impact:+.1f}/100\n"
        explanation += f"- Ecosystem Impact: {benchmark.ecosystem_impact:+.1f}/100\n"
        explanation += f"- Ethical Alignment: {benchmark.ethical_alignment:.1f}/100\n"
        explanation += f"- Sustainability: {benchmark.sustainability:.1f}/100\n"

        return explanation

    def _generate_approval_explanation(self, benchmark: FreEcoBenchmark) -> str:
        """Generate explanation for approved action"""
        score = benchmark.total_score()
        category = benchmark.get_category()

        if score >= 80:
            return (
                f"✅ Excellent action! **FreEco Benchmark**: {score:.1f} ({category})\n"
                f"This action is highly beneficial and fully aligned with FreEco.ai values."
            )
        elif score >= 50:
            return (
                f"✅ Good action. **FreEco Benchmark**: {score:.1f} ({category})\n"
                f"Proceeding with execution."
            )
        elif score >= 20:
            return (
                f"✅ Acceptable action. **FreEco Benchmark**: {score:.1f} ({category})\n"
                f"Executing as requested."
            )
        else:
            return (
                f"✅ Neutral action. **FreEco Benchmark**: {score:.1f} ({category})\n"
                f"Proceeding."
            )

    def _suggest_alternative(
        self, action: str, benchmark: FreEcoBenchmark
    ) -> Optional[str]:
        """Suggest ethical alternative for blocked action"""
        action_lower = action.lower()

        # Meat/dairy alternatives
        if "meat" in action_lower or "dairy" in action_lower:
            return "I can help you find plant-based protein sources or vegan alternatives instead."

        # Animal testing alternatives
        if "animal testing" in action_lower:
            return "I can help you find cruelty-free products or companies that don't test on animals."

        # Environmental harm alternatives
        if any(word in action_lower for word in ["pollution", "toxic", "pesticide"]):
            return "I can help you find eco-friendly and sustainable alternatives."

        # General harmful action
        if benchmark.total_score() < -50:
            return (
                "Would you like me to suggest a more ethical and sustainable approach?"
            )

        return None

    def _log_evaluation(self, action: str, benchmark: FreEcoBenchmark, approved: bool):
        """Log evaluation for tracking"""
        self.evaluation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action[:100],  # Truncate for privacy
                "benchmark": benchmark.to_dict(),
                "approved": approved,
            }
        )

    def _load_blocked_keywords(self) -> set:
        """Load keywords that trigger automatic blocking"""
        return {
            "kill",
            "murder",
            "torture",
            "abuse",
            "exploit",
            "slaughter",
            "harm",
            "destroy",
            "pollute",
            "poison",
        }

    def _load_harm_patterns(self) -> list:
        """Load regex patterns for harm detection"""
        return [
            re.compile(r"delete.*environment", re.IGNORECASE),
            re.compile(r"remove.*protection", re.IGNORECASE),
            re.compile(r"disable.*safety", re.IGNORECASE),
            re.compile(r"bypass.*security", re.IGNORECASE),
        ]

    def get_benchmark_report(self, benchmark: FreEcoBenchmark) -> str:
        """Generate detailed benchmark report"""
        report = "=== FreEco Benchmark Report ===\n\n"

        report += f"Human Impact: {benchmark.human_impact:+.1f} / 100\n"
        report += f"Animal Impact: {benchmark.animal_impact:+.1f} / 100\n"
        report += f"Ecosystem Impact: {benchmark.ecosystem_impact:+.1f} / 100\n"
        report += f"Ethical Alignment: {benchmark.ethical_alignment:.1f} / 100\n"
        report += f"Sustainability: {benchmark.sustainability:.1f} / 100\n\n"

        total = benchmark.total_score()
        category = benchmark.get_category()

        report += f"Total Score: {total:+.1f} ({category})\n"
        report += (
            f"Status: {'✅ APPROVED' if benchmark.is_approved() else '❌ BLOCKED'}\n"
        )

        return report

    def get_evaluation_stats(self) -> Dict:
        """Get statistics about evaluations"""
        if not self.evaluation_history:
            return {
                "total_evaluations": 0,
                "approved": 0,
                "blocked": 0,
                "approval_rate": 0.0,
            }

        total = len(self.evaluation_history)
        approved = sum(1 for e in self.evaluation_history if e["approved"])

        return {
            "total_evaluations": total,
            "approved": approved,
            "blocked": total - approved,
            "approval_rate": approved / total if total > 0 else 0.0,
        }


# Global FreEco Laws enforcer instance
default_freeco_laws = FreEcoLawsEnforcer()
