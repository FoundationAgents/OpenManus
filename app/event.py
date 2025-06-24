import asyncio
import re
import uuid
from collections import deque
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    NamedTuple,
    Optional,
    ParamSpec,
    Pattern,
    TypeVar,
)

from app.logger import logger

if TYPE_CHECKING:
    from app.agent.base import BaseAgent


P = ParamSpec("P")
R = TypeVar("R")


class EventItem(NamedTuple):
    id: Optional[str]
    parent_id: Optional[str]
    name: str
    timestamp: datetime
    content: Any


EventHandler = Callable[[EventItem], Coroutine[Any, Any, None]]


class EventPattern:
    def __init__(self, pattern: str, handler: EventHandler):
        self.pattern: Pattern = re.compile(pattern)
        self.handler: EventHandler = handler


# Event constants
BASE_AGENT_EVENTS_PREFIX = "agent:lifecycle"


class BaseAgentEvents:
    # Lifecycle events
    LIFECYCLE_START = f"{BASE_AGENT_EVENTS_PREFIX}:start"
    LIFECYCLE_COMPLETE = f"{BASE_AGENT_EVENTS_PREFIX}:complete"
    LIFECYCLE_ERROR = f"{BASE_AGENT_EVENTS_PREFIX}:error"
    # State events
    STATE_CHANGE = f"{BASE_AGENT_EVENTS_PREFIX}:state:change"
    STATE_STUCK_DETECTED = f"{BASE_AGENT_EVENTS_PREFIX}:state:stuck_detected"
    STATE_STUCK_HANDLED = f"{BASE_AGENT_EVENTS_PREFIX}:state:stuck_handled"
    # Step events
    STEP_MAX_REACHED = f"{BASE_AGENT_EVENTS_PREFIX}:step_max_reached"
    # Memory events
    MEMORY_ADDED = f"{BASE_AGENT_EVENTS_PREFIX}:memory:added"


REACT_AGENT_EVENTS_PREFIX = "agent:lifecycle:step"
REACT_AGENT_EVENTS_THINK_PREFIX = "agent:lifecycle:step:think"
REACT_AGENT_EVENTS_ACT_PREFIX = "agent:lifecycle:step:act"


class ReActAgentEvents(BaseAgentEvents):
    STEP_START = f"{REACT_AGENT_EVENTS_PREFIX}:start"
    STEP_COMPLETE = f"{REACT_AGENT_EVENTS_PREFIX}:complete"
    STEP_ERROR = f"{REACT_AGENT_EVENTS_PREFIX}:error"

    THINK_START = f"{REACT_AGENT_EVENTS_THINK_PREFIX}:start"
    THINK_COMPLETE = f"{REACT_AGENT_EVENTS_THINK_PREFIX}:complete"
    THINK_ERROR = f"{REACT_AGENT_EVENTS_THINK_PREFIX}:error"
    THINK_TOKEN_COUNT = f"{REACT_AGENT_EVENTS_THINK_PREFIX}:token:count"

    ACT_START = f"{REACT_AGENT_EVENTS_ACT_PREFIX}:start"
    ACT_COMPLETE = f"{REACT_AGENT_EVENTS_ACT_PREFIX}:complete"
    ACT_ERROR = f"{REACT_AGENT_EVENTS_ACT_PREFIX}:error"
    ACT_TOKEN_COUNT = f"{REACT_AGENT_EVENTS_ACT_PREFIX}:token:count"


TOOL_CALL_THINK_AGENT_EVENTS_PREFIX = "agent:lifecycle:step:think:tool"
TOOL_CALL_ACT_AGENT_EVENTS_PREFIX = "agent:lifecycle:step:act:tool"


class ToolCallAgentEvents(BaseAgentEvents):
    TOOL_SELECTED = f"{TOOL_CALL_THINK_AGENT_EVENTS_PREFIX}:selected"

    TOOL_START = f"{TOOL_CALL_ACT_AGENT_EVENTS_PREFIX}:start"
    TOOL_COMPLETE = f"{TOOL_CALL_ACT_AGENT_EVENTS_PREFIX}:complete"
    TOOL_ERROR = f"{TOOL_CALL_ACT_AGENT_EVENTS_PREFIX}:error"

    TOOL_EXECUTE_START = f"{TOOL_CALL_ACT_AGENT_EVENTS_PREFIX}:execute:start"
    TOOL_EXECUTE_COMPLETE = f"{TOOL_CALL_ACT_AGENT_EVENTS_PREFIX}:execute:complete"


class AgentEvent:
    def __init__(self):
        self.queue: deque[EventItem] = deque()
        self._processing = False
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._handlers: List[EventPattern] = []

    def put(self, event: EventItem) -> None:
        self.queue.append(event)
        self._event.set()
        pass

    def emit(
        self, name: str, data: Any, options: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit an event and add it to the processing queue.

        Args:
            name: The name of the event to emit
            data: Event data dictionary
            options: Optional event options

        Example:
            ```python
            # Simple event emission
            event.emit("agent:state:change", {
                "old_state": old_state.value,
                "new_state": new_state.value
            })

            # Subscribe to events with regex pattern
            async def on_state_events(event: EventItem):
                print(f"Event {event.name}: State changed from {event.old_state} to {event.new_state}")

            event.on("agent:state:.*", on_state_events)
            ```
        """
        if options is None:
            options = {}
        if "id" not in options or options["id"] is None or options["id"] == "":
            options["id"] = str(uuid.uuid4())
        event = EventItem(
            id=options.get("id"),
            parent_id=options.get("parent_id"),
            name=name,
            timestamp=datetime.now(),
            content=data,
        )
        self.put(event)

    def on(self, event_pattern: str, handler: EventHandler) -> None:
        """Register an event handler for events matching the specified pattern.

        Args:
            event_pattern: Regex pattern to match event names
            handler: The async function to be called when matching events occur.
                    The handler must accept event as its first parameter.

        Example:
            ```python
            # Subscribe to all lifecycle events
            async def on_lifecycle(event: EventItem):
                print(f"Lifecycle event {event.name} occurred with data: {event.content}")

            event.on("agent:lifecycle:.*", on_lifecycle)

            # Subscribe to specific state changes
            async def on_state_change(event: EventItem):
                print(f"State changed from {event.old_state} to {event.new_state}")

            event.on("agent:state:change", on_state_change)
            ```
        """
        if not callable(handler):
            raise ValueError("Event handler must be a callable")
        self.add_handler(event_pattern, handler)

    def add_handler(self, event_pattern: str, handler: EventHandler) -> None:
        """Add an event handler with regex pattern support.

        Args:
            event_pattern: Regex pattern string to match event names
            handler: Async function to handle matching events
        """
        if not callable(handler):
            raise ValueError("Event handler must be a callable")
        self._handlers.append(EventPattern(event_pattern, handler))

    async def process_events(self) -> None:
        logger.info("Event processing loop started")
        while True:
            try:
                logger.debug("Waiting for events...")
                await self._event.wait()
                logger.debug("Event received, processing...")

                async with self._lock:
                    while self.queue:
                        event = self.queue.popleft()
                        logger.debug(f"Processing event: {event.name}")

                        if not self._handlers:
                            logger.warning("No event handlers registered")
                            continue

                        handler_found = False
                        for pattern in self._handlers:
                            if pattern.pattern.match(event.name):
                                handler_found = True
                                try:
                                    await pattern.handler(event)
                                except Exception as e:
                                    logger.error(
                                        f"Error in event handler for {event.name}: {str(e)}"
                                    )
                                    logger.exception(e)

                        if not handler_found:
                            logger.warning(
                                f"No matching handler found for event: {event.name}"
                            )

                    if not self.queue:
                        logger.debug("Queue empty, clearing event")
                        self._event.clear()

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in event processing loop: {str(e)}")
                logger.exception(e)
                await asyncio.sleep(1)
                continue

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.process_events())

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
