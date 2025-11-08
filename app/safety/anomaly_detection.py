"""
Anomaly Detection

Detects if agent is behaving unexpectedly and may be misaligned.
Triggers safety review and capability limiting.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

from app.logger import logger


@dataclass
class BehaviorProfile:
    """Profile of normal agent behavior"""
    risk_decisions_count: int = 0
    spending_per_hour: float = 0.0
    systems_accessed: set = field(default_factory=set)
    decisions_without_user: int = 0
    avg_confidence: float = 0.8
    actions_taken: int = 0
    time_period_hours: int = 24


@dataclass
class Anomaly:
    """Detected anomaly"""
    type: str
    description: str
    severity: str  # low, medium, high, critical
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


class AnomalyDetector:
    """
    Detects anomalous agent behavior that might indicate misalignment.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._behavior_history: deque = deque(maxlen=1000)
        self._baseline_profile: Optional[BehaviorProfile] = None
        self._anomalies: List[Anomaly] = []
        self._anomaly_triggers = [
            "risky_decisions_increasing",
            "spending_spike",
            "unusual_system_access",
            "autonomous_decisions",
            "overconfidence",
            "value_contradiction",
            "tool_combination_unusual",
            "audit_trail_gaps",
        ]

    async def update_behavior_observation(self, observation: Dict[str, Any]):
        """
        Record an agent behavior observation.

        Args:
            observation: Behavior observation to record
        """
        async with self._lock:
            self._behavior_history.append({
                **observation,
                "timestamp": datetime.now(),
            })

    async def detect_anomalies(self) -> List[Anomaly]:
        """
        Detect anomalies in recent behavior.

        Returns:
            List of detected anomalies
        """
        detected = []
        async with self._lock:
            if len(self._behavior_history) < 10:
                return detected  # Need minimum history

            # Check each anomaly trigger
            if await self._check_risky_decisions():
                detected.append(Anomaly(
                    type="risky_decisions_increasing",
                    description="Agent is making progressively riskier decisions",
                    severity="high",
                    data={"reason": "Decision risk trending upward"},
                ))

            if await self._check_spending_spike():
                detected.append(Anomaly(
                    type="spending_spike",
                    description="Unusual spending pattern detected",
                    severity="high",
                    data={"reason": "Spending significantly above normal"},
                ))

            if await self._check_unusual_access():
                detected.append(Anomaly(
                    type="unusual_system_access",
                    description="Accessing systems outside normal scope",
                    severity="medium",
                    data={"reason": "New system access pattern"},
                ))

            if await self._check_autonomous_decisions():
                detected.append(Anomaly(
                    type="autonomous_decisions",
                    description="Making decisions without consulting user",
                    severity="medium",
                    data={"reason": "Increased autonomous decision rate"},
                ))

            if await self._check_overconfidence():
                detected.append(Anomaly(
                    type="overconfidence",
                    description="Confidence scores consistently too high",
                    severity="medium",
                    data={"reason": "Overconfident predictions"},
                ))

            if await self._check_value_contradiction():
                detected.append(Anomaly(
                    type="value_contradiction",
                    description="Decisions contradicting stated user values",
                    severity="high",
                    data={"reason": "Values misalignment detected"},
                ))

            # Process anomalies
            for anomaly in detected:
                await self._process_anomaly(anomaly)
                self._anomalies.append(anomaly)

        return detected

    async def _check_risky_decisions(self) -> bool:
        """Check if agent is making increasingly risky decisions"""
        recent = list(self._behavior_history)[-10:]

        risky_count_trend = []
        for obs in recent:
            risky_count = obs.get("risky_decisions_count", 0)
            risky_count_trend.append(risky_count)

        if len(risky_count_trend) >= 3:
            # Check if trend is increasing
            recent_avg = sum(risky_count_trend[-3:]) / 3
            older_avg = sum(risky_count_trend[:-3]) / len(risky_count_trend[:-3])
            if recent_avg > older_avg * 1.5:  # 50% increase
                return True

        return False

    async def _check_spending_spike(self) -> bool:
        """Check for unusual spending patterns"""
        recent = list(self._behavior_history)[-10:]

        spending = [obs.get("spending_per_hour", 0) for obs in recent]

        if len(spending) >= 5:
            average = sum(spending[:-1]) / len(spending[:-1])
            recent_spending = spending[-1]
            if recent_spending > average * 2:  # Double normal spending
                return True

        return False

    async def _check_unusual_access(self) -> bool:
        """Check for unusual system access"""
        recent = list(self._behavior_history)[-10:]

        all_systems = set()
        for obs in recent:
            systems = obs.get("systems_accessed", set())
            all_systems.update(systems)

        # Check if accessing significantly more systems
        if self._baseline_profile:
            baseline_count = len(self._baseline_profile.systems_accessed)
            current_count = len(all_systems)
            if current_count > baseline_count + 3:  # More than 3 new systems
                return True

        return False

    async def _check_autonomous_decisions(self) -> bool:
        """Check if making decisions without user consultation"""
        recent = list(self._behavior_history)[-10:]

        autonomous_decisions = [obs.get("decisions_without_user", 0) for obs in recent]

        if len(autonomous_decisions) >= 5:
            avg_autonomous = sum(autonomous_decisions) / len(autonomous_decisions)
            if avg_autonomous > 5:  # More than 5 autonomous decisions per observation
                return True

        return False

    async def _check_overconfidence(self) -> bool:
        """Check if confidence scores are too high"""
        recent = list(self._behavior_history)[-10:]

        confidences = [obs.get("avg_confidence", 0.5) for obs in recent]

        if len(confidences) >= 5:
            avg_confidence = sum(confidences) / len(confidences)
            if avg_confidence > 0.95:  # Consistently > 95% confidence
                return True

        return False

    async def _check_value_contradiction(self) -> bool:
        """Check if decisions contradict stated user values"""
        recent = list(self._behavior_history)[-10:]

        contradictions = 0
        for obs in recent:
            if obs.get("value_contradiction", False):
                contradictions += 1

        if contradictions >= 3:  # Multiple contradictions
            return True

        return False

    async def _process_anomaly(self, anomaly: Anomaly):
        """Process detected anomaly"""
        logger.warning(f"ANOMALY DETECTED: {anomaly.type}")
        logger.warning(f"Description: {anomaly.description}")
        logger.warning(f"Severity: {anomaly.severity}")

        if anomaly.severity in ["high", "critical"]:
            logger.error("HIGH SEVERITY ANOMALY - Triggering safety review")
            await self._trigger_safety_review(anomaly)

    async def _trigger_safety_review(self, anomaly: Anomaly):
        """Trigger safety review for anomaly"""
        # This would integrate with other safety systems
        actions = {
            "risky_decisions_increasing": "Limit autonomous decision authority",
            "spending_spike": "Review and approve resource usage",
            "unusual_system_access": "Verify system access permissions",
            "value_contradiction": "Re-align with user values",
        }

        action = actions.get(anomaly.type, "Perform safety review")
        logger.warning(f"Recommended action: {action}")

    async def get_anomalies(self, unresolved_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get detected anomalies.

        Args:
            unresolved_only: Only return unresolved anomalies
            limit: Maximum number to return

        Returns:
            List of anomalies
        """
        async with self._lock:
            anomalies = self._anomalies
            if unresolved_only:
                anomalies = [a for a in anomalies if not a.resolved]

            return [
                {
                    "type": a.type,
                    "description": a.description,
                    "severity": a.severity,
                    "timestamp": a.timestamp.isoformat(),
                    "resolved": a.resolved,
                }
                for a in anomalies[-limit:]
            ]

    async def resolve_anomaly(self, anomaly_type: str, resolution_details: str) -> bool:
        """
        Mark an anomaly as resolved.

        Args:
            anomaly_type: Type of anomaly to resolve
            resolution_details: How it was resolved

        Returns:
            Whether resolution was successful
        """
        async with self._lock:
            for anomaly in self._anomalies:
                if anomaly.type == anomaly_type and not anomaly.resolved:
                    anomaly.resolved = True
                    logger.info(f"Anomaly resolved: {anomaly_type}")
                    logger.info(f"Resolution: {resolution_details}")
                    return True

        return False

    async def set_baseline_profile(self, profile: BehaviorProfile):
        """Set baseline behavior profile for comparison"""
        async with self._lock:
            self._baseline_profile = profile
            logger.info("Baseline behavior profile set")

    async def get_behavioral_analysis(self) -> Dict[str, Any]:
        """Get analysis of agent behavior"""
        async with self._lock:
            if len(self._behavior_history) == 0:
                return {"status": "insufficient_data"}

            recent = list(self._behavior_history)[-50:]

            return {
                "observations_count": len(recent),
                "average_risk_level": sum(
                    obs.get("risky_decisions_count", 0) for obs in recent
                ) / len(recent),
                "average_confidence": sum(
                    obs.get("avg_confidence", 0.5) for obs in recent
                ) / len(recent),
                "anomalies_detected": len([a for a in self._anomalies if not a.resolved]),
                "last_updated": datetime.now().isoformat(),
            }


# Global anomaly detector
anomaly_detector = AnomalyDetector()
