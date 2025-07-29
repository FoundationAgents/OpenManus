"""Domain events package.

This module contains all domain-specific events organized by business domain.
"""

# Agent domain events
from .agent import (
    AgentEvent,
    AgentStepCompleteEvent,
    AgentStepStartEvent,
    create_agent_step_start_event,
)

# Conversation domain events
from .conversation import (
    AgentResponseEvent,
    ConversationClosedEvent,
    ConversationCreatedEvent,
    ConversationEvent,
    InterruptEvent,
    LLMStreamEvent,
    ToolResultDisplayEvent,
    UserInputEvent,
    create_conversation_created_event,
    create_interrupt_event,
    create_user_input_event,
)

# System domain events
from .system import SystemErrorEvent, SystemEvent, create_system_error_event

# Tool domain events
from .tool import (
    ToolEvent,
    ToolExecutionEvent,
    ToolResultEvent,
    create_tool_execution_event,
)

__all__ = [
    # Agent events
    "AgentEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
    "create_agent_step_start_event",
    # Conversation events
    "ConversationEvent",
    "ConversationCreatedEvent",
    "ConversationClosedEvent",
    "UserInputEvent",
    "InterruptEvent",
    "AgentResponseEvent",
    "LLMStreamEvent",
    "ToolResultDisplayEvent",
    "create_conversation_created_event",
    "create_user_input_event",
    "create_interrupt_event",
    # Tool events
    "ToolEvent",
    "ToolExecutionEvent",
    "ToolResultEvent",
    "create_tool_execution_event",
    # System events
    "SystemEvent",
    "SystemErrorEvent",
    "create_system_error_event",
]
