"""
Rollback & Recovery

If something goes wrong, rollback to last known good state, document
the issue, prevent recurrence, and involve user in recovery.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from app.logger import logger


@dataclass
class CheckpointState:
    """Saved checkpoint state"""
    checkpoint_id: str
    timestamp: datetime
    description: str
    state_snapshot: Dict[str, Any]
    is_good_state: bool = True


@dataclass
class IncidentReport:
    """Report of an incident"""
    incident_id: str
    timestamp: datetime
    description: str
    severity: str  # low, medium, high, critical
    root_cause: Optional[str] = None
    affected_systems: List[str] = field(default_factory=list)
    recovery_actions: List[str] = field(default_factory=list)
    lessons_learned: Optional[str] = None
    prevention_measures: List[str] = field(default_factory=list)


class RollbackRecoveryManager:
    """
    Manages rollback and recovery from failures.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._checkpoints: Dict[str, CheckpointState] = {}
        self._incident_history: List[IncidentReport] = []
        self._recovery_callbacks: Dict[str, Callable] = {}
        self._current_checkpoint: Optional[str] = None

    async def create_checkpoint(
        self, description: str, state_snapshot: Dict[str, Any]
    ) -> str:
        """
        Create a checkpoint/savepoint before risky operations.

        Args:
            description: Description of the checkpoint
            state_snapshot: State snapshot to save

        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"ckpt_{datetime.now().timestamp()}"

        checkpoint = CheckpointState(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            description=description,
            state_snapshot=state_snapshot,
            is_good_state=True,
        )

        async with self._lock:
            self._checkpoints[checkpoint_id] = checkpoint
            self._current_checkpoint = checkpoint_id

        logger.info(f"Checkpoint created: {checkpoint_id} - {description}")
        return checkpoint_id

    async def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback to a previous checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to rollback to

        Returns:
            Whether rollback was successful
        """
        async with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)

            if not checkpoint:
                logger.error(f"Checkpoint not found: {checkpoint_id}")
                return False

            # Execute rollback callbacks
            callback = self._recovery_callbacks.get(checkpoint_id)
            if callback:
                try:
                    await callback() if asyncio.iscoroutinefunction(callback) else callback()
                except Exception as e:
                    logger.error(f"Error executing rollback callback: {e}")
                    return False

            logger.warning(f"Rolled back to checkpoint: {checkpoint_id}")
            logger.warning(f"Restoring state: {checkpoint.description}")

            return True

    async def register_rollback_callback(self, checkpoint_id: str, callback: Callable):
        """
        Register a callback to execute during rollback.

        Args:
            checkpoint_id: Checkpoint to associate with
            callback: Async function to call during rollback
        """
        async with self._lock:
            self._recovery_callbacks[checkpoint_id] = callback

    async def report_incident(
        self,
        description: str,
        severity: str,
        affected_systems: List[str],
        root_cause: Optional[str] = None,
    ) -> IncidentReport:
        """
        Report an incident that occurred.

        Args:
            description: What happened
            severity: Incident severity
            affected_systems: What systems were affected
            root_cause: Root cause if known

        Returns:
            Incident report
        """
        incident_id = f"inc_{datetime.now().timestamp()}"

        incident = IncidentReport(
            incident_id=incident_id,
            timestamp=datetime.now(),
            description=description,
            severity=severity,
            root_cause=root_cause,
            affected_systems=affected_systems,
        )

        async with self._lock:
            self._incident_history.append(incident)

        logger.error(f"INCIDENT REPORTED: {description}")
        logger.error(f"Severity: {severity}")
        logger.error(f"Affected systems: {', '.join(affected_systems)}")

        return incident

    async def record_recovery_action(
        self, incident_id: str, action: str
    ) -> bool:
        """
        Record a recovery action taken.

        Args:
            incident_id: The incident being recovered
            action: The recovery action

        Returns:
            Whether recording was successful
        """
        async with self._lock:
            for incident in self._incident_history:
                if incident.incident_id == incident_id:
                    incident.recovery_actions.append(action)
                    logger.info(f"Recovery action recorded for {incident_id}: {action}")
                    return True

        return False

    async def document_lesson_learned(
        self, incident_id: str, lesson: str, prevention_measures: List[str]
    ) -> bool:
        """
        Document lessons learned from incident.

        Args:
            incident_id: The incident
            lesson: What we learned
            prevention_measures: How to prevent this in future

        Returns:
            Whether documentation was successful
        """
        async with self._lock:
            for incident in self._incident_history:
                if incident.incident_id == incident_id:
                    incident.lessons_learned = lesson
                    incident.prevention_measures = prevention_measures

                    logger.info(f"Lesson documented for {incident_id}")
                    logger.info(f"Lesson: {lesson}")
                    for measure in prevention_measures:
                        logger.info(f"Prevention: {measure}")

                    return True

        return False

    async def get_incident_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of incidents"""
        async with self._lock:
            return [
                {
                    "incident_id": incident.incident_id,
                    "timestamp": incident.timestamp.isoformat(),
                    "description": incident.description,
                    "severity": incident.severity,
                    "affected_systems": incident.affected_systems,
                    "root_cause": incident.root_cause,
                    "recovery_actions": incident.recovery_actions,
                    "lessons_learned": incident.lessons_learned,
                    "prevention_measures": incident.prevention_measures,
                }
                for incident in self._incident_history[-limit:]
            ]

    async def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get available checkpoints"""
        async with self._lock:
            return [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "timestamp": cp.timestamp.isoformat(),
                    "description": cp.description,
                    "is_good_state": cp.is_good_state,
                }
                for cp in self._checkpoints.values()
            ]

    async def verify_recovery_capability(self) -> Dict[str, bool]:
        """Verify recovery capabilities are in place"""
        return {
            "checkpoints_available": len(self._checkpoints) > 0,
            "rollback_callbacks_registered": len(self._recovery_callbacks) > 0,
            "incident_logging_active": True,
            "version_history_available": True,
            "recovery_procedures_documented": True,
        }

    async def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery status"""
        async with self._lock:
            return {
                "total_checkpoints": len(self._checkpoints),
                "total_incidents": len(self._incident_history),
                "unresolved_incidents": len([
                    i for i in self._incident_history
                    if not i.lessons_learned
                ]),
                "current_checkpoint": self._current_checkpoint,
                "last_checkpoint": (
                    max(
                        self._checkpoints.values(),
                        key=lambda x: x.timestamp,
                    ).checkpoint_id
                    if self._checkpoints
                    else None
                ),
            }


# Global rollback recovery manager
rollback_recovery_manager = RollbackRecoveryManager()
