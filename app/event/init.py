"""Event system initialization and configuration module.

This module provides utilities for initializing and configuring the event system
in the OpenManus project. It handles bus setup, middleware configuration,
and global event handlers registration.
"""

import asyncio
from typing import Optional, Dict, Any

from app.logger import logger
from app.event import (
    SimpleEventBus,
    ChainableEventBus,
    get_global_bus,
    set_global_bus,
    create_default_middleware_chain,
    event_handler
)


class EventSystemConfig:
    """Configuration class for the event system."""

    def __init__(
        self,
        bus_type: str = "simple",  # "simple" or "chainable"
        max_concurrent_events: int = 100,
        enable_logging: bool = False,
        enable_retry: bool = True,
        enable_error_isolation: bool = True,
        enable_metrics: bool = True,
        log_level: str = "INFO"
    ):
        self.bus_type = bus_type
        self.max_concurrent_events = max_concurrent_events
        self.enable_logging = enable_logging
        self.enable_retry = enable_retry
        self.enable_error_isolation = enable_error_isolation
        self.enable_metrics = enable_metrics
        self.log_level = log_level


def initialize_event_system(config: Optional[EventSystemConfig] = None) -> None:
    """Initialize the global event system with the given configuration.

    Args:
        config: Event system configuration. If None, uses default configuration.
    """
    if config is None:
        config = EventSystemConfig()

    logger.info(f"Initializing event system with {config.bus_type} bus...")

    # Create middleware chain
    middleware_chain = create_default_middleware_chain(
        enable_logging=config.enable_logging,
        enable_retry=config.enable_retry,
        enable_error_isolation=config.enable_error_isolation,
        enable_metrics=config.enable_metrics
    )

    # Create and configure the event bus
    if config.bus_type == "chainable":
        bus = ChainableEventBus(
            name="GlobalChainableEventBus",
            max_concurrent_events=config.max_concurrent_events,
            middleware_chain=middleware_chain
        )
    else:
        bus = SimpleEventBus(
            name="GlobalSimpleEventBus",
            max_concurrent_events=config.max_concurrent_events,
            middleware_chain=middleware_chain
        )

    # Set as global bus
    set_global_bus(bus)

    logger.info(f"Event system initialized successfully with {config.bus_type} bus")


def get_event_system_status() -> Dict[str, Any]:
    """Get the current status of the event system.

    Returns:
        Dict containing event system status information
    """
    try:
        bus = get_global_bus()
        stats = bus.get_event_stats()
        metrics = bus.get_metrics()

        return {
            "initialized": True,
            "bus_type": bus.__class__.__name__,
            "bus_name": bus.name,
            "stats": stats,
            "metrics": metrics
        }
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e)
        }


# Global event handlers that can be registered automatically
@event_handler("system.*", name="system_logger")
async def log_system_events(event):
    """Log all system events for debugging and monitoring."""
    component = event.data.get('component', 'unknown')
    logger.info(f"System Event: {event.event_type} from {component}")
    return True


@event_handler("agent.*", name="agent_monitor")
async def monitor_agent_events(event):
    """Monitor agent events for performance tracking."""
    agent_name = event.data.get('agent_name', 'unknown')
    step_number = event.data.get('step_number', '')
    step_info = f" (step {step_number})" if step_number else ""
    logger.info(f"Agent Event: {event.event_type} from '{agent_name}'{step_info}")
    return True


@event_handler("tool.*", name="tool_tracker")
async def track_tool_events(event):
    """Track tool execution events."""
    tool_name = event.data.get('tool_name', 'unknown')
    logger.info(f"Tool Event: {event.event_type} for tool '{tool_name}'")
    return True


@event_handler("conversation.*", name="conversation_logger")
async def log_conversation_events(event):
    """Log conversation events for session tracking."""
    conv_id = event.data.get('conversation_id', 'unknown')
    user_id = event.data.get('user_id', 'unknown')
    logger.info(f"Conversation Event: {event.event_type} (conv: {conv_id}, user: {user_id})")
    return True


@event_handler("*", name="global_metrics")
async def collect_global_metrics(event):
    """Collect global metrics for all events."""
    # This could be extended to send metrics to external systems
    logger.debug(f"Event processed: {event.event_type} (id: {event.event_id})")
    return True


def register_default_handlers() -> None:
    """Register default global event handlers.

    This function is called automatically during initialization to register
    system-level event handlers for logging, monitoring, and metrics collection.
    """
    logger.info("Default event handlers registered successfully")


async def shutdown_event_system() -> None:
    """Gracefully shutdown the event system.

    This should be called during application shutdown to ensure all events
    are processed and resources are cleaned up properly.
    """
    try:
        bus = get_global_bus()

        # Wait for active events to complete (with timeout)
        max_wait = 30  # seconds
        wait_time = 0

        while wait_time < max_wait:
            stats = bus.get_event_stats()
            active_events = stats.get('active_events', 0)

            if active_events == 0:
                break

            logger.info(f"Waiting for {active_events} active events to complete...")
            await asyncio.sleep(1)
            wait_time += 1

        # Force cleanup if needed
        if hasattr(bus, 'shutdown'):
            await bus.shutdown()

        logger.info("Event system shutdown completed")

    except Exception as e:
        logger.error(f"Error during event system shutdown: {str(e)}")


# Convenience functions for common event publishing
async def publish_agent_step_start(agent_name: str, agent_type: str, step_number: int,
                                 conversation_id: Optional[str] = None) -> bool:
    """Convenience function to publish agent step start event."""
    from app.event import create_agent_step_start_event, publish_event

    event = create_agent_step_start_event(
        agent_name=agent_name,
        agent_type=agent_type,
        step_number=step_number,
        conversation_id=conversation_id
    )
    return await publish_event(event)


async def publish_tool_execution(tool_name: str, tool_type: str, status: str,
                                parameters: Dict[str, Any],
                                conversation_id: Optional[str] = None) -> bool:
    """Convenience function to publish tool execution event."""
    from app.event import create_tool_execution_event, publish_event

    event = create_tool_execution_event(
        tool_name=tool_name,
        tool_type=tool_type,
        status=status,
        parameters=parameters,
        conversation_id=conversation_id
    )
    return await publish_event(event)


async def publish_system_error(component: str, error_type: str, error_message: str,
                              conversation_id: Optional[str] = None) -> bool:
    """Convenience function to publish system error event."""
    from app.event import create_system_error_event, publish_event

    event = create_system_error_event(
        component=component,
        error_type=error_type,
        error_message=error_message,
        conversation_id=conversation_id
    )
    return await publish_event(event)


# Auto-initialization flag
_auto_initialized = False


def ensure_event_system_initialized(config: Optional[EventSystemConfig] = None) -> None:
    """Ensure the event system is initialized (idempotent).

    This function can be called multiple times safely. It will only initialize
    the event system once.
    """
    global _auto_initialized

    if not _auto_initialized:
        initialize_event_system(config)
        register_default_handlers()
        _auto_initialized = True
