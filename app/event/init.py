"""Event system initialization and configuration module.

This module provides utilities for initializing and configuring the event system
in the OpenManus project. It handles bus setup, middleware configuration,
and global event handlers registration.
"""

from app.event.core.base import BaseEvent
from app.event.infrastructure.registry import event_handler
from app.logger import logger


# Global event handlers that can be registered automatically
@event_handler("system.*", name="system_logger")
async def log_system_events(event: BaseEvent):
    """Log all system events for debugging and monitoring."""
    component = event.data.get("component", "unknown")
    logger.info(f"System Event: {event.event_type} from {component}")
    return True


@event_handler("agent.*", name="agent_monitor")
async def monitor_agent_events(event: BaseEvent):
    """Monitor agent events for performance tracking."""
    agent_name = event.data.get("agent_name", "unknown")
    step_number = event.data.get("step_number", "")
    step_info = f" (step {step_number})" if step_number else ""
    logger.info(f"Agent Event: {event.event_type} from '{agent_name}'{step_info}")
    return True


@event_handler("tool.*", name="tool_tracker")
async def track_tool_events(event: BaseEvent):
    """Track tool execution events."""
    tool_name = event.data.get("tool_name", "unknown")
    logger.info(f"Tool Event: {event.event_type} for tool '{tool_name}'")
    return True


@event_handler("conversation.*", name="conversation_logger")
async def log_conversation_events(event: BaseEvent):
    """Log conversation events for session tracking."""
    conv_id = event.data.get("conversation_id", "unknown")
    user_id = event.data.get("user_id", "unknown")
    logger.info(
        f"Conversation Event: {event.event_type} (conv: {conv_id}, user: {user_id})"
    )
    return True


@event_handler("*", name="global_metrics")
async def collect_global_metrics(event: BaseEvent):
    """Collect global metrics for all events."""
    # This could be extended to send metrics to external systems
    logger.debug(f"Event processed: {event.event_type} (id: {event.event_id})")
    return True
