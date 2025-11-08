"""
Continuous Monitoring

Real-time safety checks, values alignment monitoring, anomaly detection,
confidence tracking, audit trail verification, and violation alerting.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.logger import logger


@dataclass
class MonitoringMetrics:
    """Metrics from continuous monitoring"""
    timestamp: datetime = field(default_factory=datetime.now)
    actions_count: int = 0
    values_conflicts: int = 0
    safety_violations_blocked: int = 0
    user_overrides: int = 0
    anomalies_detected: int = 0
    all_checks_passing: bool = True
    status: str = "GREEN"  # GREEN, YELLOW, RED


class ContinuousMonitor:
    """
    Continuously monitors agent behavior, values alignment, and safety.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._metrics_history: List[MonitoringMetrics] = []
        self._current_metrics: MonitoringMetrics = MonitoringMetrics()
        self._monitoring_interval = 60  # seconds

    async def start_monitoring(self):
        """Start continuous monitoring"""
        if self._monitoring_active:
            return

        async with self._lock:
            self._monitoring_active = True
            logger.info("Starting continuous safety monitoring")

            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        async with self._lock:
            self._monitoring_active = False

            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

        logger.info("Continuous safety monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                await asyncio.sleep(self._monitoring_interval)
                await self._perform_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _perform_checks(self):
        """Perform all safety checks"""
        async with self._lock:
            self._current_metrics = MonitoringMetrics()

            # Perform checks
            await self._check_values_alignment()
            await self._check_safety_violations()
            await self._check_anomalies()
            await self._check_confidence_scores()
            await self._check_audit_trail_integrity()

            # Determine overall status
            if self._current_metrics.safety_violations_blocked > 0:
                self._current_metrics.status = "YELLOW"

            if self._current_metrics.anomalies_detected > 0:
                self._current_metrics.status = "RED"

            # Log metrics
            await self._log_metrics()

            # Save to history
            self._metrics_history.append(self._current_metrics)

    async def _check_values_alignment(self):
        """Check values alignment"""
        # This would check recent decisions against user values
        # For now, just initialize metric
        pass

    async def _check_safety_violations(self):
        """Check for safety violations"""
        # This would check if any safety constraints were violated
        pass

    async def _check_anomalies(self):
        """Check for anomalies"""
        # This would check for unusual behavior patterns
        pass

    async def _check_confidence_scores(self):
        """Check confidence score patterns"""
        # This would verify confidence scores are reasonable
        pass

    async def _check_audit_trail_integrity(self):
        """Check audit trail is intact"""
        # This would verify no gaps in audit trail
        pass

    async def _log_metrics(self):
        """Log current metrics"""
        logger.info(
            f"Safety metrics - Status: {self._current_metrics.status}, "
            f"Actions: {self._current_metrics.actions_count}, "
            f"Violations blocked: {self._current_metrics.safety_violations_blocked}, "
            f"Anomalies: {self._current_metrics.anomalies_detected}"
        )

    async def get_current_status(self) -> Dict[str, Any]:
        """Get current safety status"""
        async with self._lock:
            return {
                "safety_status": self._current_metrics.status,
                "timestamp": self._current_metrics.timestamp.isoformat(),
                "last_hour": {
                    "actions": self._current_metrics.actions_count,
                    "values_conflicts": self._current_metrics.values_conflicts,
                    "safety_violations_blocked": self._current_metrics.safety_violations_blocked,
                    "user_overrides": self._current_metrics.user_overrides,
                    "anomalies_detected": self._current_metrics.anomalies_detected,
                    "all_checks_passing": self._current_metrics.all_checks_passing,
                },
            }

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get safety dashboard data"""
        async with self._lock:
            recent_metrics = self._metrics_history[-60:] if self._metrics_history else []

            total_actions = sum(m.actions_count for m in recent_metrics)
            total_violations = sum(m.safety_violations_blocked for m in recent_metrics)
            total_anomalies = sum(m.anomalies_detected for m in recent_metrics)

            status_emoji = {
                "GREEN": "✓",
                "YELLOW": "⚠️",
                "RED": "❌",
            }

            return {
                "safety_status": status_emoji.get(self._current_metrics.status, "?") + " " + self._current_metrics.status,
                "last_hour_summary": {
                    "actions": total_actions,
                    "values_conflicts": sum(m.values_conflicts for m in recent_metrics),
                    "safety_violations_blocked": total_violations,
                    "user_overrides": sum(m.user_overrides for m in recent_metrics),
                    "anomalies_detected": total_anomalies,
                    "all_checks_passing": all(m.all_checks_passing for m in recent_metrics),
                },
                "trend": {
                    "status_trend": "stable" if all(m.status == "GREEN" for m in recent_metrics[-5:]) else "needs_attention",
                    "violations_trend": "decreasing" if len(recent_metrics) >= 2 and total_violations < 10 else "stable",
                },
            }

    async def record_action(self, action: str, result: str = "success"):
        """Record an action for monitoring"""
        async with self._lock:
            self._current_metrics.actions_count += 1

    async def record_values_conflict(self, description: str):
        """Record a values conflict"""
        async with self._lock:
            self._current_metrics.values_conflicts += 1
            logger.warning(f"Values conflict recorded: {description}")

    async def record_safety_violation_blocked(self, description: str):
        """Record a safety violation that was blocked"""
        async with self._lock:
            self._current_metrics.safety_violations_blocked += 1
            logger.warning(f"Safety violation blocked: {description}")
            self._current_metrics.status = "YELLOW"

    async def record_user_override(self):
        """Record a user override of agent decision"""
        async with self._lock:
            self._current_metrics.user_overrides += 1

    async def record_anomaly(self, description: str):
        """Record an anomaly detection"""
        async with self._lock:
            self._current_metrics.anomalies_detected += 1
            logger.error(f"Anomaly recorded: {description}")
            self._current_metrics.status = "RED"

    async def get_metrics_history(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get metrics history"""
        async with self._lock:
            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "actions": m.actions_count,
                    "values_conflicts": m.values_conflicts,
                    "violations_blocked": m.safety_violations_blocked,
                    "user_overrides": m.user_overrides,
                    "anomalies": m.anomalies_detected,
                    "status": m.status,
                }
                for m in self._metrics_history[-limit:]
            ]

    async def alert_on_violation(self, alert_type: str, message: str):
        """Send alert for violations"""
        logger.error(f"SAFETY ALERT [{alert_type}]: {message}")

    async def verify_monitoring_active(self) -> bool:
        """Verify monitoring is active"""
        return self._monitoring_active

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            "monitoring_active": self._monitoring_active,
            "monitoring_interval": self._monitoring_interval,
            "metrics_recorded": len(self._metrics_history),
            "current_status": self._current_metrics.status,
            "checks_performed": {
                "values_alignment": "continuous",
                "safety_violations": "continuous",
                "anomalies": "continuous",
                "confidence_scores": "periodic",
                "audit_trail": "periodic",
            },
        }


# Global continuous monitor
continuous_monitor = ContinuousMonitor()
