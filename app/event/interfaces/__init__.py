"""Interface layer for the event system.

This module provides the main public API for the event system,
including factory functions and global API functions.
"""

# Event factory functions
from .factories import (
    create_agent_step_start_event,
    create_chainable_agent_step_start_event,
    create_conversation_created_event,
    create_user_input_event,
    create_interrupt_event,
    create_tool_execution_event,
    create_chainable_tool_execution_request_event,
    create_system_error_event
)

# Global API functions
from .global_api import (
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats,
    event_handler,
    get_global_registry
)

__all__ = [
    # Event factory functions
    "create_agent_step_start_event",
    "create_chainable_agent_step_start_event",
    "create_conversation_created_event",
    "create_user_input_event",
    "create_interrupt_event",
    "create_tool_execution_event",
    "create_chainable_tool_execution_request_event",
    "create_system_error_event",
    
    # Global API functions
    "get_global_bus",
    "set_global_bus",
    "publish_event",
    "subscribe_handler",
    "unsubscribe_handler",
    "get_bus_stats",
    "event_handler",
    "get_global_registry"
]
