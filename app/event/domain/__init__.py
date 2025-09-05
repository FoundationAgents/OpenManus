"""Domain events package.

This module contains all domain-specific events organized by business domain.
"""

# Agent domain events
from .agent import (
    AgentEvent,
    AgentStepStartEvent,
    AgentStepCompleteEvent,
    create_agent_step_start_event,
    ChainableAgentEvent,
    ChainableAgentStepStartEvent,
    ChainableAgentStepCompleteEvent,
    create_chainable_agent_step_start_event
)

# Conversation domain events
from .conversation import (
    ConversationEvent,
    ConversationCreatedEvent,
    ConversationClosedEvent,
    UserInputEvent,
    InterruptEvent,
    AgentResponseEvent,
    LLMStreamEvent,
    ToolResultDisplayEvent,
    create_conversation_created_event,
    create_user_input_event,
    create_interrupt_event
)

# Tool domain events
from .tool import (
    ToolEvent,
    ToolExecutionEvent,
    ToolResultEvent,
    create_tool_execution_event,
    ChainableToolEvent,
    ChainableToolExecutionRequestEvent,
    ChainableToolExecutionCompletedEvent,
    create_chainable_tool_execution_request_event
)

# System domain events
from .system import (
    SystemEvent,
    SystemErrorEvent,
    create_system_error_event,
    ChainableSystemEvent,
    ChainableLogWriteEvent,
    ChainableMetricsUpdateEvent,
    ChainableStreamEvent,
    ChainableStreamStartEvent,
    ChainableStreamChunkEvent,
    ChainableStreamEndEvent,
    ChainableStreamInterruptEvent
)

__all__ = [
    # Agent events
    "AgentEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
    "create_agent_step_start_event",
    "ChainableAgentEvent",
    "ChainableAgentStepStartEvent",
    "ChainableAgentStepCompleteEvent",
    "create_chainable_agent_step_start_event",
    
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
    "ChainableToolEvent",
    "ChainableToolExecutionRequestEvent",
    "ChainableToolExecutionCompletedEvent",
    "create_chainable_tool_execution_request_event",
    
    # System events
    "SystemEvent",
    "SystemErrorEvent",
    "create_system_error_event",
    "ChainableSystemEvent",
    "ChainableLogWriteEvent",
    "ChainableMetricsUpdateEvent",
    "ChainableStreamEvent",
    "ChainableStreamStartEvent",
    "ChainableStreamChunkEvent",
    "ChainableStreamEndEvent",
    "ChainableStreamInterruptEvent"
]
