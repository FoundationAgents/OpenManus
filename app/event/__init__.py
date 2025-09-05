"""Event system package for OpenManus.

This is the main entry point for the event system, providing a clean API
that abstracts the internal layered architecture.
"""

# Core abstractions
from app.event.core import (
    BaseEvent,
    BaseEventHandler,
    BaseEventBus,
    ChainableEvent,
    EventContext,
    EventStatus,
    ToolExecutionStatus
)

# Infrastructure components
from app.event.infrastructure import (
    EventHandlerRegistry,
    HandlerInfo,
    event_handler,
    get_global_registry,
    BaseMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    LoggingMiddleware,
    RetryMiddleware,
    ErrorIsolationMiddleware,
    MetricsMiddleware,
    create_default_middleware_chain,
    SimpleEventBus,
    ChainableEventBus,
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats
)

# Domain events
from app.event.domain import (
    # Agent events
    AgentEvent,
    AgentStepStartEvent,
    AgentStepCompleteEvent,
    ChainableAgentEvent,
    ChainableAgentStepStartEvent,
    ChainableAgentStepCompleteEvent,

    # Conversation events
    ConversationEvent,
    ConversationCreatedEvent,
    ConversationClosedEvent,
    UserInputEvent,
    InterruptEvent,
    AgentResponseEvent,
    LLMStreamEvent,
    ToolResultDisplayEvent,

    # Tool events
    ToolEvent,
    ToolExecutionEvent,
    ToolResultEvent,
    ChainableToolEvent,
    ChainableToolExecutionRequestEvent,
    ChainableToolExecutionCompletedEvent,

    # System events
    SystemEvent,
    SystemErrorEvent,
    ChainableSystemEvent,
    ChainableLogWriteEvent,
    ChainableMetricsUpdateEvent,
    ChainableStreamEvent,
    ChainableStreamStartEvent,
    ChainableStreamChunkEvent,
    ChainableStreamEndEvent,
    ChainableStreamInterruptEvent
)

# Event factory functions
from app.event.interfaces import (
    create_agent_step_start_event,
    create_chainable_agent_step_start_event,
    create_conversation_created_event,
    create_user_input_event,
    create_interrupt_event,
    create_tool_execution_event,
    create_chainable_tool_execution_request_event,
    create_system_error_event
)

__all__ = [
    # Core abstractions
    "BaseEvent",
    "BaseEventHandler",
    "BaseEventBus",
    "ChainableEvent",
    "EventContext",
    "EventStatus",
    "ToolExecutionStatus",

    # Infrastructure components
    "EventHandlerRegistry",
    "HandlerInfo",
    "event_handler",
    "get_global_registry",
    "BaseMiddleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "LoggingMiddleware",
    "RetryMiddleware",
    "ErrorIsolationMiddleware",
    "MetricsMiddleware",
    "create_default_middleware_chain",
    "SimpleEventBus",
    "ChainableEventBus",
    "get_global_bus",
    "set_global_bus",
    "publish_event",
    "subscribe_handler",
    "unsubscribe_handler",
    "get_bus_stats",

    # Agent events
    "AgentEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
    "ChainableAgentEvent",
    "ChainableAgentStepStartEvent",
    "ChainableAgentStepCompleteEvent",

    # Conversation events
    "ConversationEvent",
    "ConversationCreatedEvent",
    "ConversationClosedEvent",
    "UserInputEvent",
    "InterruptEvent",
    "AgentResponseEvent",
    "LLMStreamEvent",
    "ToolResultDisplayEvent",

    # Tool events
    "ToolEvent",
    "ToolExecutionEvent",
    "ToolResultEvent",
    "ChainableToolEvent",
    "ChainableToolExecutionRequestEvent",
    "ChainableToolExecutionCompletedEvent",

    # System events
    "SystemEvent",
    "SystemErrorEvent",
    "ChainableSystemEvent",
    "ChainableLogWriteEvent",
    "ChainableMetricsUpdateEvent",
    "ChainableStreamEvent",
    "ChainableStreamStartEvent",
    "ChainableStreamChunkEvent",
    "ChainableStreamEndEvent",
    "ChainableStreamInterruptEvent",

    # Event factory functions
    "create_agent_step_start_event",
    "create_chainable_agent_step_start_event",
    "create_conversation_created_event",
    "create_user_input_event",
    "create_interrupt_event",
    "create_tool_execution_event",
    "create_chainable_tool_execution_request_event",
    "create_system_error_event",
]
