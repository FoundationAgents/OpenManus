"""Domain events package.

This module contains all domain-specific events organized by business domain.
"""

# Agent domain events
from .agent_events import AgentEvent, AgentStepCompleteEvent, AgentStepStartEvent

# Conversation domain events
from .conversation_events import (
    AgentResponseEvent,
    ConversationClosedEvent,
    ConversationCreatedEvent,
    ConversationEvent,
    UserInputEvent,
    UserInterruptEvent,
)

# FileSystem domain events
from .filesystem_events import (
    DirectoryCreatedEvent,
    DirectoryDeletedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)

# System domain events
from .system_events import SystemErrorEvent, SystemEvent

# Tool domain events
from .tool_events import ToolEvent, ToolExecutionEvent, ToolResultEvent

__all__ = [
    # Agent events
    "AgentEvent",
    "AgentStepStartEvent",
    "AgentStepCompleteEvent",
    # Conversation events
    "ConversationEvent",
    "ConversationCreatedEvent",
    "ConversationClosedEvent",
    "UserInputEvent",
    "UserInterruptEvent",
    "AgentResponseEvent",
    # Tool events
    "ToolEvent",
    "ToolExecutionEvent",
    "ToolResultEvent",
    # System events
    "SystemEvent",
    "SystemErrorEvent",
    # FileSystem events
    "FileSystemEvent",
    "FileCreatedEvent",
    "FileModifiedEvent",
    "FileDeletedEvent",
    "FileMovedEvent",
    "DirectoryCreatedEvent",
    "DirectoryDeletedEvent",
]
