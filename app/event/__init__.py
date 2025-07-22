"""Event system package for OpenManus."""

from app.event.base import BaseEvent, BaseEventHandler, BaseEventBus
from app.event.types import EventStatus
from app.event.registry import (
    EventHandlerRegistry,
    HandlerInfo,
    event_handler,
    get_global_registry
)
from app.event.middleware import (
    BaseMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    LoggingMiddleware,
    RetryMiddleware,
    ErrorIsolationMiddleware,
    MetricsMiddleware,
    create_default_middleware_chain
)
from app.event.simple_bus import (
    SimpleEventBus,
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats
)
from app.event.events import (
    SystemEvent,
    AgentEvent,
    ToolEvent,
    ConversationEvent,
    ConversationCreatedEvent,
    ConversationClosedEvent,
    UserInputEvent,
    InterruptEvent,
    AgentStepStartEvent,
    AgentStepCompleteEvent,
    AgentResponseEvent,
    LLMStreamEvent,
    ToolResultDisplayEvent,
    ToolExecutionEvent,
    ToolResultEvent,
    SystemErrorEvent,
    create_conversation_created_event,
    create_user_input_event,
    create_interrupt_event,
    create_agent_step_start_event,
    create_tool_execution_event,
    create_system_error_event
)
__all__ = [
    # Base classes
    "BaseEvent",
    "BaseEventHandler",
    "BaseEventBus",

    # Types
    "EventStatus",

    # Registry system
    "EventHandlerRegistry",
    "HandlerInfo",
    "event_handler",
    "get_global_registry",

    # Middleware system
    "BaseMiddleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "LoggingMiddleware",
    "RetryMiddleware",
    "ErrorIsolationMiddleware",
    "MetricsMiddleware",
    "create_default_middleware_chain",

    # Simple event bus
    "SimpleEventBus",
    "get_global_bus",
    "set_global_bus",
    "publish_event",
    "subscribe_handler",
    "unsubscribe_handler",
    "get_bus_stats",

    # Domain events
    "SystemEvent",
    "AgentEvent",
    "ToolEvent",
    "FlowEvent",
    "MCPEvent",
    "ConversationEvent",
    "ConversationCreatedEvent",
    "ConversationClosedEvent",
    "UserInputEvent",
    "InterruptEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
    "AgentResponseEvent",
    "LLMStreamEvent",
    "ToolResultDisplayEvent",
    "ToolExecutionEvent",
    "ToolResultEvent",
    "SystemErrorEvent",

    # Event factories
    "create_conversation_created_event",
    "create_user_input_event",
    "create_interrupt_event",
    "create_agent_step_start_event",
    "create_tool_execution_event",
    "create_system_error_event",
]
