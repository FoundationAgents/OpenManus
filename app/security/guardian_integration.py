"""
Guardian Integration for UI Dialog and Event Bus.

Bridges Guardian validation decisions to UI components for user approval/denial.
"""

import asyncio
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

from app.logger import logger
from app.security.guardian_agent import GuardianAgent, get_guardian_agent


@dataclass
class ApprovalRequest:
    """Request for user approval."""
    approval_id: str
    command: str
    risk_level: str
    risk_score: float
    reason: str
    required_permissions: list
    blocking_factors: list
    source: str
    timestamp: str


class GuardianEventBus:
    """
    Event bus for Guardian validation events.

    Manages communication between Guardian Agent and UI dialogs.
    """

    def __init__(self):
        """Initialize the event bus."""
        self._approval_handlers: Dict[str, Callable] = {}
        self._response_handlers: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def register_approval_handler(self, handler: Callable[[ApprovalRequest], None]):
        """
        Register handler for approval requests.

        Args:
            handler: Async function that handles approval requests
        """
        handler_id = id(handler)
        with self._lock:
            self._approval_handlers[str(handler_id)] = handler
        logger.info(f"Registered approval handler: {handler_id}")

    def unregister_approval_handler(self, handler: Callable):
        """
        Unregister approval handler.

        Args:
            handler: Handler to unregister
        """
        handler_id = str(id(handler))
        with self._lock:
            self._approval_handlers.pop(handler_id, None)
        logger.info(f"Unregistered approval handler: {handler_id}")

    async def emit_approval_request(self, request: ApprovalRequest):
        """
        Emit approval request to all registered handlers.

        Args:
            request: The approval request
        """
        with self._lock:
            handlers = list(self._approval_handlers.values())

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(request)
                else:
                    # Run blocking handler in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler, request)
            except Exception as e:
                logger.error(f"Error in approval handler: {e}")

    def register_response_handler(self, handler: Callable[[str, bool], None]):
        """
        Register handler for user responses.

        Args:
            handler: Function that handles user responses (approval_id, approved)
        """
        handler_id = id(handler)
        with self._lock:
            self._response_handlers[str(handler_id)] = handler
        logger.info(f"Registered response handler: {handler_id}")

    def unregister_response_handler(self, handler: Callable):
        """
        Unregister response handler.

        Args:
            handler: Handler to unregister
        """
        handler_id = str(id(handler))
        with self._lock:
            self._response_handlers.pop(handler_id, None)
        logger.info(f"Unregistered response handler: {handler_id}")

    async def emit_user_response(self, approval_id: str, approved: bool):
        """
        Emit user response to all registered handlers.

        Args:
            approval_id: The approval ID
            approved: Whether user approved
        """
        with self._lock:
            handlers = list(self._response_handlers.values())

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(approval_id, approved)
                else:
                    # Run blocking handler in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler, approval_id, approved)
            except Exception as e:
                logger.error(f"Error in response handler: {e}")


class GuardianUIBridge:
    """
    Bridge between Guardian Agent and UI dialogs.

    Manages the approval workflow with UI components.
    """

    def __init__(self, event_bus: Optional[GuardianEventBus] = None):
        """
        Initialize Guardian UI Bridge.

        Args:
            event_bus: Optional event bus for communication
        """
        self.event_bus = event_bus or GuardianEventBus()
        self._approval_loop_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the approval request handler loop."""
        if self._approval_loop_task is None:
            self._approval_loop_task = asyncio.create_task(self._approval_request_loop())
            logger.info("Guardian UI Bridge started")

    async def stop(self):
        """Stop the approval request handler loop."""
        if self._approval_loop_task:
            self._approval_loop_task.cancel()
            try:
                await self._approval_loop_task
            except asyncio.CancelledError:
                pass
            self._approval_loop_task = None
            logger.info("Guardian UI Bridge stopped")

    async def _approval_request_loop(self):
        """Process approval requests from Guardian Agent."""
        try:
            guardian = await get_guardian_agent()
            approval_queue = await guardian.get_approval_queue()

            while True:
                try:
                    # Get approval request from Guardian queue
                    approval_event = await asyncio.wait_for(approval_queue.get(), timeout=1.0)

                    # Create approval request
                    request = ApprovalRequest(
                        approval_id=approval_event.get("approval_id"),
                        command=approval_event.get("command"),
                        risk_level=approval_event.get("risk_level"),
                        risk_score=approval_event.get("risk_score"),
                        reason=approval_event.get("reason"),
                        required_permissions=approval_event.get("required_permissions", []),
                        blocking_factors=approval_event.get("blocking_factors", []),
                        source=approval_event.get("source"),
                        timestamp=approval_event.get("timestamp")
                    )

                    # Emit to UI
                    await self.event_bus.emit_approval_request(request)

                    # Register response handler
                    async def handle_response(approval_id: str, approved: bool):
                        guardian.handle_user_response(approval_id, approved)
                        await self.event_bus.emit_user_response(approval_id, approved)

                    # Wait for response via event bus
                    # Note: Actual response handling done via register_response_handler

                except asyncio.TimeoutError:
                    # No pending approvals
                    pass
                except Exception as e:
                    logger.error(f"Error in approval request loop: {e}")
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.debug("Approval request loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in approval request loop: {e}")

    async def handle_ui_response(self, approval_id: str, approved: bool):
        """
        Handle user response from UI dialog.

        Args:
            approval_id: The approval ID
            approved: Whether user approved the command
        """
        try:
            guardian = await get_guardian_agent()
            guardian.handle_user_response(approval_id, approved)
            
            await self.event_bus.emit_user_response(approval_id, approved)
            
            logger.info(f"User response recorded: approval_id={approval_id}, approved={approved}")
        except Exception as e:
            logger.error(f"Error handling UI response: {e}")

    def register_approval_handler(self, handler: Callable[[ApprovalRequest], None]):
        """
        Register handler for approval requests.

        Args:
            handler: Function/coroutine that handles approval requests
        """
        self.event_bus.register_approval_handler(handler)

    def unregister_approval_handler(self, handler: Callable):
        """
        Unregister approval handler.

        Args:
            handler: Handler to unregister
        """
        self.event_bus.unregister_approval_handler(handler)


# Global event bus and UI bridge instances
_event_bus: Optional[GuardianEventBus] = None
_ui_bridge: Optional[GuardianUIBridge] = None


def get_event_bus() -> GuardianEventBus:
    """Get or create the global Guardian event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = GuardianEventBus()
    return _event_bus


def get_ui_bridge() -> GuardianUIBridge:
    """Get or create the global Guardian UI bridge."""
    global _ui_bridge
    if _ui_bridge is None:
        _ui_bridge = GuardianUIBridge(get_event_bus())
    return _ui_bridge


async def start_ui_bridge():
    """Start the global Guardian UI bridge."""
    bridge = get_ui_bridge()
    await bridge.start()


async def stop_ui_bridge():
    """Stop the global Guardian UI bridge."""
    bridge = get_ui_bridge()
    await bridge.stop()
