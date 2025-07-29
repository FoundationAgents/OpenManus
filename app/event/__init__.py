"""Event system package for OpenManus.

This is the main entry point for the event system, providing a clean API
that abstracts the internal layered architecture.
"""

# Core abstractions
from app.event.core import BaseEvent, BaseEventBus, BaseEventHandler, EventContext

# Event factory functions
# Domain events
from app.event.domain import (  # Agent events; Conversation events; Tool events; System events
    AgentEvent,
    AgentResponseEvent,
    AgentStepCompleteEvent,
    AgentStepStartEvent,
    ConversationClosedEvent,
    ConversationCreatedEvent,
    ConversationEvent,
    InterruptEvent,
    LLMStreamEvent,
    SystemErrorEvent,
    SystemEvent,
    ToolEvent,
    ToolExecutionEvent,
    ToolResultDisplayEvent,
    ToolResultEvent,
    UserInputEvent,
    create_agent_step_start_event,
    create_conversation_created_event,
    create_interrupt_event,
    create_system_error_event,
    create_tool_execution_event,
    create_user_input_event,
)

# Infrastructure components
from app.event.infrastructure import (
    BaseMiddleware,
    ErrorIsolationMiddleware,
    EventBus,
    EventHandlerRegistry,
    HandlerInfo,
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    RetryMiddleware,
    WebSocketForwarderMiddleware,
    bus,
    create_default_middleware_chain,
    event_handler,
    get_global_registry,
)

__all__ = [
    # Core abstractions
    "BaseEvent",
    "BaseEventHandler",
    "BaseEventBus",
    "EventContext",
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
    "WebSocketForwarderMiddleware",
    "EventBus",
    "bus",
    # Agent events
    "AgentEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
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
    # System events
    "SystemEvent",
    "SystemErrorEvent",
    # Event factory functions
    "create_agent_step_start_event",
    "create_conversation_created_event",
    "create_user_input_event",
    "create_interrupt_event",
    "create_tool_execution_event",
    "create_system_error_event",
]
