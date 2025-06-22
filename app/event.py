import asyncio
import re
from collections import deque
from datetime import datetime
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    List,
    NamedTuple,
    Optional,
    ParamSpec,
    Pattern,
    TypeVar,
    Dict,
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
    step: int
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

    def event_wrapper(
        before_event: str, after_event: str, error_event: Optional[str] = None
    ):
        """A generic decorator that wraps a method with before/after event notifications.

        Args:
            before_event: Event name to emit before method execution
            after_event: Event name to emit after successful method execution
            error_event: Optional event name to emit on error (defaults to f"{after_event}:error")

        Example:
            @event_wrapper("step:before", "step:after")
            async def step(self) -> str:
                return "Step result"

            @event_wrapper("tool:start", "tool:end", "tool:error")
            async def execute_tool(self) -> str:
                return "Tool result"
        """

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            async def wrapper(
                self: "BaseAgent", *args: P.args, **kwargs: P.kwargs
            ) -> R:
                # Get counter for this specific method
                method_name = func.__name__
                counter_name = f"_{method_name}_counter"
                current_count = getattr(self, counter_name, 0) + 1
                setattr(self, counter_name, current_count)

                # Prepare base event data
                event_data = {
                    "method": method_name,
                    "count": current_count,
                    "message": f"Executing {method_name} #{current_count}",
                }

                # Emit before event
                self.emit(before_event, event_data)

                try:
                    # Execute the method
                    result = await func(self, *args, **kwargs)

                    # Add result to event data
                    event_data.update(
                        {
                            "result": result,
                            "message": f"Completed {method_name} #{current_count}",
                        }
                    )

                    # Emit after event
                    self.emit(after_event, event_data)

                    return result
                except Exception as e:
                    # Prepare error event data
                    error_data = {
                        **event_data,
                        "error": str(e),
                        "message": f"Error in {method_name} #{current_count}: {str(e)}",
                    }

                    # Emit error event
                    actual_error_event = error_event or f"{after_event}:error"
                    self.emit(actual_error_event, error_data)
                    raise

            return wrapper

        return decorator

