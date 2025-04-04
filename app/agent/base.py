import asyncio
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from typing import (
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

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from app.llm import LLM
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import ROLE_TYPE, AgentState, Memory, Message

EventHandler = Callable[..., Coroutine[Any, Any, None]]

P = ParamSpec("P")
R = TypeVar("R")


class EventItem(NamedTuple):
    name: str
    kwargs: dict
    step: int
    timestamp: datetime


class EventPattern:
    def __init__(self, pattern: str, handler: EventHandler):
        self.pattern: Pattern = re.compile(pattern)
        self.handler: EventHandler = handler


class EventQueue:
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
                                    kwargs = {
                                        "event_name": event.name,
                                        "step": event.step,
                                        **event.kwargs,
                                    }
                                    logger.debug(
                                        f"Calling handler for {event.name} with kwargs: {kwargs}"
                                    )
                                    await pattern.handler(**kwargs)
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


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    enable_event_queue: bool = Field(default=True, description="Enable event queue")
    _private_event_queue: EventQueue = PrivateAttr(default_factory=EventQueue)

    # Event constants
    class Events:
        # Lifecycle events
        LIFECYCLE_START = "agent:lifecycle:start"
        LIFECYCLE_COMPLETE = "agent:lifecycle:complete"

        # State events
        STATE_CHANGE = "agent:state:change"
        STATE_STUCK_DETECTED = "agent:state:stuck:detected"
        STATE_STUCK_HANDLED = "agent:state:stuck:handled"

        # Step events
        STEP_START = "agent:step:start"
        STEP_COMPLETE = "agent:step:complete"
        STEP_ERROR = "agent:step:error"
        STEP_MAX_REACHED = "agent:step:max_reached"

        # Memory events
        MEMORY_ADDED = "agent:memory:added"

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    task_id: Optional[str] = Field(None, description="Task ID for the agent")

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()

        # Initialize private attributes
        if self.enable_event_queue:
            self._private_event_queue.start()
        return self

    def __del__(self):
        if hasattr(self, "_private_event_queue"):
            self._private_event_queue.stop()

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            self.emit(
                self.Events.STATE_CHANGE,
                {"old_state": previous_state.value, "new_state": self.state.value},
            )
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            self.emit(
                self.Events.STATE_CHANGE,
                {"old_state": self.state.value, "new_state": AgentState.ERROR.value},
            )
            raise e
        finally:
            self.state = previous_state  # Revert to previous state
            self.emit(
                self.Events.STATE_CHANGE,
                {"old_state": self.state.value, "new_state": previous_state.value},
            )

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        message = message_map[role](content, **kwargs)
        logger.info(f"Adding message to memory: {message}")
        self.memory.add_message(message)
        self.emit(
            self.Events.MEMORY_ADDED, {"role": role, "message": message.to_dict()}
        )

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        self.emit(self.Events.LIFECYCLE_START, {"request": request})

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")

                try:
                    step_result = await self.step()
                except Exception as e:
                    raise

                # Check for stuck state
                if self.is_stuck():
                    self.emit(self.Events.STATE_STUCK_DETECTED, {})
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                self.emit(self.Events.STEP_MAX_REACHED, {"max_steps": self.max_steps})
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        await SANDBOX_CLIENT.cleanup()
        self.emit(self.Events.LIFECYCLE_COMPLETE, {"results": results})
        return "\n".join(results) if results else "No steps executed"

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

    @abstractmethod
    @event_wrapper(Events.STEP_START, Events.STEP_COMPLETE, Events.STEP_ERROR)
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.

        Events emitted:
        - step:before: Before step execution
        - step:after: After successful step execution
        - step:error: On step execution error
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

        self.emit(
            self.Events.STATE_STUCK_HANDLED, {"new_prompt": self.next_step_prompt}
        )

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value

    def on(self, event_pattern: str, handler: EventHandler) -> None:
        """Register an event handler for events matching the specified pattern.

        Args:
            event_pattern: Regex pattern to match event names
            handler: The async function to be called when matching events occur.
                    The handler must accept event_name as its first parameter.

        Example:
            ```python
            # Subscribe to all lifecycle events
            async def on_lifecycle(event_name: str, **data):
                print(f"Lifecycle event {event_name} occurred with data: {data}")

            agent.on("agent:lifecycle:.*", on_lifecycle)

            # Subscribe to specific state changes
            async def on_state_change(event_name: str, old_state: AgentState, new_state: AgentState):
                print(f"State changed from {old_state} to {new_state}")

            agent.on("agent:state:change", on_state_change)
            ```
        """
        if not callable(handler):
            raise ValueError("Event handler must be a callable")
        self._private_event_queue.add_handler(event_pattern, handler)

    def emit(self, event_name: str, data: Dict[str, Any]) -> None:
        """Emit an event and add it to the processing queue.

        Args:
            event_name: The name of the event to emit
            data: Event data dictionary

        Example:
            ```python
            # Simple event emission
            agent.emit("agent:state:change", {
                "old_state": old_state.value,
                "new_state": new_state.value
            })

            # Subscribe to events with regex pattern
            async def on_state_events(event_name: str, old_state: AgentState, new_state: AgentState):
                print(f"Event {event_name}: State changed from {old_state} to {new_state}")

            agent.on("agent:state:.*", on_state_events)
            ```
        """
        if not self.enable_event_queue:
            return
        event = EventItem(
            name=event_name,
            kwargs=data,
            step=self.current_step,
            timestamp=datetime.now(),
        )
        self._private_event_queue.put(event)
