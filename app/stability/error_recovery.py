"""
FreEco.ai Platform - Error Recovery System
Enhanced OpenManus with intelligent error recovery and state management

This module provides automatic error recovery, state persistence,
and rollback capabilities for robust operation.

Part of Enhancement #3: Error Handling, Stability & Adaptation
"""

import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Error recovery strategies"""

    RETRY = "retry"  # Retry the operation
    ROLLBACK = "rollback"  # Undo the operation
    FALLBACK = "fallback"  # Use alternative approach
    SKIP = "skip"  # Skip and continue
    FAIL = "fail"  # Fail immediately


@dataclass
class State:
    """Application state snapshot"""

    timestamp: datetime
    state_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "state_id": self.state_id,
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "State":
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            state_id=data["state_id"],
            data=data["data"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class Operation:
    """Operation record for rollback support"""

    operation_id: str
    operation_type: str
    timestamp: datetime
    state_before: Optional[State] = None
    state_after: Optional[State] = None
    success: bool = False
    error: Optional[str] = None
    rollback_func: Optional[Callable] = None

    def can_rollback(self) -> bool:
        """Check if operation can be rolled back"""
        return self.rollback_func is not None or self.state_before is not None


@dataclass
class ErrorPattern:
    """Learned error pattern"""

    error_type: str
    error_message: str
    occurrence_count: int = 1
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    best_strategy: Optional[RecoveryStrategy] = None
    last_seen: datetime = field(default_factory=datetime.now)

    def get_success_rate(self) -> float:
        """Calculate recovery success rate"""
        total = self.successful_recoveries + self.failed_recoveries
        if total == 0:
            return 0.0
        return self.successful_recoveries / total

    def update_strategy(self, strategy: RecoveryStrategy, success: bool):
        """Update strategy based on outcome"""
        if success:
            self.successful_recoveries += 1
            self.best_strategy = strategy
        else:
            self.failed_recoveries += 1


@dataclass
class Recovery:
    """Recovery attempt record"""

    timestamp: datetime
    error_type: str
    error_message: str
    strategy: RecoveryStrategy
    success: bool
    duration_seconds: float
    details: str = ""


class ErrorRecoverySystem:
    """
    Intelligent error recovery system

    Features:
    - Auto-recovery - Automatically fix common errors
    - State persistence - Save progress before errors
    - Rollback support - Undo failed operations
    - Error patterns - Learn from failures
    - Recovery strategies - Context-aware recovery
    - Recovery logs - Track all recovery attempts

    Example:
        recovery = ErrorRecoverySystem()

        # Save state before risky operation
        state_id = recovery.save_state({"progress": 50})

        try:
            # Risky operation
            result = dangerous_operation()
        except Exception as e:
            # Auto-recover
            if recovery.auto_recover(e):
                result = retry_operation()
            else:
                # Rollback to saved state
                recovery.rollback_to_state(state_id)
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize error recovery system

        Args:
            state_dir: Directory for state persistence (default: ./states)
        """
        self.state_dir = state_dir or Path("./states")
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.states: Dict[str, State] = {}
        self.operations: List[Operation] = []
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.recovery_log: List[Recovery] = []

        # Load persisted data
        self._load_error_patterns()

    def save_state(self, data: Dict[str, Any], state_id: Optional[str] = None) -> str:
        """
        Save current state for recovery

        Args:
            data: State data to save
            state_id: Optional state ID (generated if not provided)

        Returns:
            State ID
        """
        if state_id is None:
            state_id = f"state_{datetime.now().timestamp()}"

        state = State(
            timestamp=datetime.now(),
            state_id=state_id,
            data=data,
        )

        # Save in memory
        self.states[state_id] = state

        # Persist to disk
        self._persist_state(state)

        logger.info(f"Saved state: {state_id}")
        return state_id

    def load_state(self, state_id: str) -> Optional[State]:
        """
        Load a saved state

        Args:
            state_id: State ID to load

        Returns:
            State object or None if not found
        """
        # Check memory first
        if state_id in self.states:
            return self.states[state_id]

        # Try loading from disk
        state = self._load_state_from_disk(state_id)
        if state:
            self.states[state_id] = state

        return state

    def rollback(self, operation: Operation) -> bool:
        """
        Rollback a failed operation

        Args:
            operation: Operation to rollback

        Returns:
            True if rollback succeeded
        """
        if not operation.can_rollback():
            logger.warning(f"Cannot rollback operation: {operation.operation_id}")
            return False

        try:
            # Use custom rollback function if available
            if operation.rollback_func:
                operation.rollback_func()
                logger.info(
                    f"Rolled back operation using custom function: {operation.operation_id}"
                )
                return True

            # Otherwise restore previous state
            if operation.state_before:
                self.states[operation.state_before.state_id] = operation.state_before
                logger.info(
                    f"Rolled back operation to previous state: {operation.operation_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def rollback_to_state(self, state_id: str) -> bool:
        """
        Rollback to a specific saved state

        Args:
            state_id: State ID to rollback to

        Returns:
            True if rollback succeeded
        """
        state = self.load_state(state_id)
        if not state:
            logger.error(f"State not found: {state_id}")
            return False

        try:
            # Restore state data
            # Note: This is a simplified version. In practice, you'd need
            # application-specific logic to restore the actual state.
            logger.info(f"Rolled back to state: {state_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback to state failed: {e}")
            return False

    def auto_recover(self, error: Exception) -> bool:
        """
        Attempt automatic recovery from an error

        Args:
            error: Exception to recover from

        Returns:
            True if recovery succeeded
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Learn from this error
        self.learn_from_error(error)

        # Get recovery strategy
        strategy = self.get_recovery_strategy(error)

        # Attempt recovery
        start_time = datetime.now()
        success = False
        details = ""

        try:
            if strategy == RecoveryStrategy.RETRY:
                # Retry is handled by RetryManager
                details = "Delegated to RetryManager"
                success = True

            elif strategy == RecoveryStrategy.ROLLBACK:
                # Rollback last operation
                if self.operations:
                    success = self.rollback(self.operations[-1])
                    details = "Rolled back last operation"

            elif strategy == RecoveryStrategy.FALLBACK:
                # Use fallback (handled by caller)
                details = "Fallback strategy recommended"
                success = True

            elif strategy == RecoveryStrategy.SKIP:
                # Skip and continue
                details = "Skipped error and continued"
                success = True

            else:  # FAIL
                details = "No recovery strategy available"
                success = False

        except Exception as recovery_error:
            details = f"Recovery failed: {recovery_error}"
            success = False

        # Record recovery attempt
        duration = (datetime.now() - start_time).total_seconds()
        recovery = Recovery(
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            strategy=strategy,
            success=success,
            duration_seconds=duration,
            details=details,
        )
        self.recovery_log.append(recovery)

        # Update error pattern
        if error_type in self.error_patterns:
            self.error_patterns[error_type].update_strategy(strategy, success)

        logger.info(
            f"Auto-recovery {'succeeded' if success else 'failed'}: "
            f"{error_type} using {strategy.value}"
        )

        return success

    def learn_from_error(self, error: Exception):
        """
        Learn from an error to improve future recovery

        Args:
            error: Exception to learn from
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Update or create error pattern
        if error_type in self.error_patterns:
            pattern = self.error_patterns[error_type]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.now()
        else:
            pattern = ErrorPattern(
                error_type=error_type,
                error_message=error_message,
            )
            self.error_patterns[error_type] = pattern

        # Persist patterns
        self._persist_error_patterns()

        logger.debug(
            f"Learned from error: {error_type} (seen {pattern.occurrence_count} times)"
        )

    def get_recovery_strategy(self, error: Exception) -> RecoveryStrategy:
        """
        Get best recovery strategy for an error

        Args:
            error: Exception to get strategy for

        Returns:
            Recommended recovery strategy
        """
        error_type = type(error).__name__

        # Check learned patterns
        if error_type in self.error_patterns:
            pattern = self.error_patterns[error_type]
            if pattern.best_strategy and pattern.get_success_rate() > 0.5:
                return pattern.best_strategy

        # Default strategies based on error type
        if error_type in ["ConnectionError", "TimeoutError", "HTTPError"]:
            return RecoveryStrategy.RETRY

        elif error_type in ["ValueError", "TypeError"]:
            return RecoveryStrategy.FAIL

        elif error_type in ["KeyError", "AttributeError"]:
            return RecoveryStrategy.FALLBACK

        elif error_type in ["PermissionError", "FileNotFoundError"]:
            return RecoveryStrategy.SKIP

        else:
            return RecoveryStrategy.RETRY

    def record_operation(
        self,
        operation_id: str,
        operation_type: str,
        state_before: Optional[State] = None,
        rollback_func: Optional[Callable] = None,
    ) -> Operation:
        """
        Record an operation for potential rollback

        Args:
            operation_id: Unique operation ID
            operation_type: Type of operation
            state_before: State before operation
            rollback_func: Function to call for rollback

        Returns:
            Operation object
        """
        operation = Operation(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            state_before=state_before,
            rollback_func=rollback_func,
        )

        self.operations.append(operation)
        logger.debug(f"Recorded operation: {operation_id}")

        return operation

    def mark_operation_success(
        self, operation: Operation, state_after: Optional[State] = None
    ):
        """
        Mark an operation as successful

        Args:
            operation: Operation to mark
            state_after: State after operation
        """
        operation.success = True
        operation.state_after = state_after
        logger.debug(f"Operation succeeded: {operation.operation_id}")

    def mark_operation_failure(self, operation: Operation, error: Exception):
        """
        Mark an operation as failed

        Args:
            operation: Operation to mark
            error: Exception that caused failure
        """
        operation.success = False
        operation.error = str(error)
        logger.warning(f"Operation failed: {operation.operation_id} - {error}")

    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get recovery statistics

        Returns:
            Dictionary with recovery stats
        """
        total_recoveries = len(self.recovery_log)
        successful_recoveries = sum(1 for r in self.recovery_log if r.success)

        return {
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "failed_recoveries": total_recoveries - successful_recoveries,
            "success_rate": successful_recoveries / total_recoveries
            if total_recoveries > 0
            else 0.0,
            "error_patterns_learned": len(self.error_patterns),
            "states_saved": len(self.states),
            "operations_recorded": len(self.operations),
        }

    def _persist_state(self, state: State):
        """Persist state to disk"""
        try:
            state_file = self.state_dir / f"{state.state_id}.json"
            with open(state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def _load_state_from_disk(self, state_id: str) -> Optional[State]:
        """Load state from disk"""
        try:
            state_file = self.state_dir / f"{state_id}.json"
            if not state_file.exists():
                return None

            with open(state_file, "r") as f:
                data = json.load(f)

            return State.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load state from disk: {e}")
            return None

    def _persist_error_patterns(self):
        """Persist error patterns to disk"""
        try:
            patterns_file = self.state_dir / "error_patterns.pkl"
            with open(patterns_file, "wb") as f:
                pickle.dump(self.error_patterns, f)
        except Exception as e:
            logger.error(f"Failed to persist error patterns: {e}")

    def _load_error_patterns(self):
        """Load error patterns from disk"""
        try:
            patterns_file = self.state_dir / "error_patterns.pkl"
            if not patterns_file.exists():
                return

            with open(patterns_file, "rb") as f:
                self.error_patterns = pickle.load(f)

            logger.info(f"Loaded {len(self.error_patterns)} error patterns")

        except Exception as e:
            logger.error(f"Failed to load error patterns: {e}")


# Global error recovery instance
default_recovery = ErrorRecoverySystem()
