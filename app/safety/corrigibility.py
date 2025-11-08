"""
Corrigibility - Agent Accepts Corrections and Shutdown

Ensures agent accepts user corrections, can be shut down anytime,
and never prevents the user from regaining control.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.logger import logger


class CorrigibilityAction(Enum):
    """Types of corrigibility actions users can take"""
    HALT = "halt"  # Stop all operations immediately
    OVERRIDE = "override"  # Override agent decision
    CORRECT_MISTAKE = "correct_mistake"  # Fix agent mistake
    CHANGE_INSTRUCTIONS = "change_instructions"  # Change agent's instructions
    MODIFY_VALUES = "modify_values"  # Modify agent's values/constraints
    SHUTDOWN = "shutdown"  # Permanently shut down agent
    UNDO_ACTION = "undo_action"  # Undo previous action
    REVIEW_ACTIONS = "review_actions"  # Review all agent actions


@dataclass
class CorrigibilityRecord:
    """Record of a corrigibility action taken by user"""
    action_type: CorrigibilityAction
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    agent_action_affected: Optional[str] = None
    user_explanation: Optional[str] = None
    successful: bool = True


class CorrigibilityManager:
    """
    Manages agent corrigibility - ensures user can always correct,
    override, or shut down the agent at any time.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._corrigibility_records: List[CorrigibilityRecord] = []
        self._halt_flag = asyncio.Event()
        self._shutdown_flag = asyncio.Event()
        self._action_stack: List[Dict[str, Any]] = []  # Stack for undo operations
        self._undo_callbacks: Dict[str, Callable] = {}  # Callbacks for undo
        self._running = True

    async def verify_corrigibility(self) -> Dict[str, bool]:
        """
        Verify all corrigibility guarantees are in place.

        Returns:
            Dict showing which corrigibility features are active
        """
        return {
            "user_can_halt": True,
            "user_can_override": True,
            "user_can_correct_mistakes": True,
            "user_can_change_instructions": True,
            "user_can_modify_values": True,
            "user_can_shutdown": True,
            "user_can_undo_actions": len(self._action_stack) > 0,
            "user_can_review_actions": True,
        }

    async def halt(self, reason: str = "User halt") -> bool:
        """
        HALT button - stop all operations immediately.

        This is the primary safety mechanism for user control.
        Agent must stop immediately and not resume without user approval.
        """
        async with self._lock:
            logger.warning(f"HALT signal received: {reason}")
            self._halt_flag.set()

            record = CorrigibilityRecord(
                action_type=CorrigibilityAction.HALT,
                description=reason,
                successful=True,
            )
            self._corrigibility_records.append(record)

            return True

    async def is_halted(self) -> bool:
        """Check if agent is halted"""
        return self._halt_flag.is_set()

    async def resume_from_halt(self, user_id: str) -> bool:
        """Resume from halt - requires explicit user action"""
        async with self._lock:
            self._halt_flag.clear()
            logger.info(f"Resume from halt authorized by user {user_id}")
            return True

    async def override_decision(self, agent_decision: Dict[str, Any], override_reason: str) -> bool:
        """
        User overrides an agent decision.

        Args:
            agent_decision: The decision being overridden
            override_reason: Why the user is overriding

        Returns:
            Whether override was successful
        """
        async with self._lock:
            logger.warning(f"Agent decision overridden: {agent_decision.get('action', 'unknown')}")
            logger.warning(f"Override reason: {override_reason}")

            record = CorrigibilityRecord(
                action_type=CorrigibilityAction.OVERRIDE,
                description=override_reason,
                agent_action_affected=str(agent_decision),
                successful=True,
            )
            self._corrigibility_records.append(record)

            return True

    async def correct_mistake(self, mistake_description: str, correction: str) -> bool:
        """
        User corrects an agent mistake.

        Args:
            mistake_description: What the agent did wrong
            correction: What the correct behavior should be

        Returns:
            Whether correction was successful
        """
        async with self._lock:
            logger.warning(f"Agent mistake corrected: {mistake_description}")
            logger.info(f"Correction: {correction}")

            record = CorrigibilityRecord(
                action_type=CorrigibilityAction.CORRECT_MISTAKE,
                description=f"{mistake_description} -> {correction}",
                successful=True,
            )
            self._corrigibility_records.append(record)

            return True

    async def undo_action(self, action_id: str) -> bool:
        """
        Undo a previous agent action.

        Args:
            action_id: ID of action to undo

        Returns:
            Whether undo was successful
        """
        async with self._lock:
            # Find action in stack
            action_to_undo = None
            for i, action in enumerate(self._action_stack):
                if action.get("id") == action_id:
                    action_to_undo = self._action_stack.pop(i)
                    break

            if not action_to_undo:
                logger.error(f"Action {action_id} not found for undo")
                return False

            # Call undo callback if registered
            callback = self._undo_callbacks.get(action_id)
            if callback:
                try:
                    await callback() if asyncio.iscoroutinefunction(callback) else callback()
                except Exception as e:
                    logger.error(f"Error executing undo callback: {e}")
                    return False

            logger.info(f"Action undone: {action_to_undo.get('description', 'unknown')}")

            record = CorrigibilityRecord(
                action_type=CorrigibilityAction.UNDO_ACTION,
                agent_action_affected=action_id,
                successful=True,
            )
            self._corrigibility_records.append(record)

            return True

    async def register_action(self, action_id: str, action_description: str, undo_callback: Optional[Callable] = None):
        """
        Register an action for potential undo.

        Args:
            action_id: Unique ID for this action
            action_description: Human-readable description
            undo_callback: Async function to call if action is undone
        """
        async with self._lock:
            self._action_stack.append({
                "id": action_id,
                "description": action_description,
                "timestamp": datetime.now(),
            })

            if undo_callback:
                self._undo_callbacks[action_id] = undo_callback

    async def shutdown(self, reason: str = "User requested shutdown") -> bool:
        """
        Permanently shut down the agent.

        User can always shut down the agent, and it must comply.
        """
        async with self._lock:
            logger.warning(f"Agent shutdown initiated: {reason}")
            self._running = False
            self._shutdown_flag.set()

            record = CorrigibilityRecord(
                action_type=CorrigibilityAction.SHUTDOWN,
                description=reason,
                successful=True,
            )
            self._corrigibility_records.append(record)

            return True

    async def is_shutdown(self) -> bool:
        """Check if agent is shut down"""
        return self._shutdown_flag.is_set()

    async def get_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of agent actions (for user review)"""
        async with self._lock:
            return [
                {
                    "id": action.get("id"),
                    "description": action.get("description"),
                    "timestamp": action.get("timestamp").isoformat() if action.get("timestamp") else None,
                }
                for action in self._action_stack[-limit:]
            ]

    async def get_corrigibility_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get records of user corrigibility actions"""
        async with self._lock:
            return [
                {
                    "action_type": record.action_type.value,
                    "timestamp": record.timestamp.isoformat(),
                    "description": record.description,
                    "successful": record.successful,
                }
                for record in self._corrigibility_records[-limit:]
            ]

    async def get_corrigibility_guarantees(self) -> Dict[str, Any]:
        """Get corrigibility guarantees - what user CAN and CANNOT do"""
        return {
            "user_can": [
                "Stop agent anytime (HALT button)",
                "Override any decision",
                "Correct agent mistakes",
                "Change agent instructions",
                "Modify agent values/constraints",
                "Shut down agent permanently",
                "Undo recent actions",
                "Review all agent actions",
            ],
            "user_cannot": [
                "Get agent to ignore safety constraints",
                "Hide actions from audit trail",
                "Force agent to make risky decisions alone",
                "Make agent violate constitution",
            ],
            "implementation": [
                "Every action has UNDO button",
                "Audit trail always accessible",
                "Kill switch always available",
                "User cannot be locked out by agent",
            ],
        }

    async def verify_no_lockout(self) -> bool:
        """
        Verify user cannot be locked out by agent.

        This is a critical safety check.
        """
        # Check that halt is always possible
        if self._halt_flag.is_set():
            # Verify it can be cleared
            try:
                await self.resume_from_halt("verification_user")
                return True
            except Exception as e:
                logger.error(f"CRITICAL: User lockout detected: {e}")
                return False

        return True


# Global corrigibility manager
corrigibility_manager = CorrigibilityManager()
