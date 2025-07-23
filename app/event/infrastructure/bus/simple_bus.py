"""Simple event bus implementation.

This module provides a clean, simple event bus focused on core functionality:
- Event publishing and handler dispatch
- Middleware processing
- Basic statistics and metrics

This follows the single responsibility principle - SimpleEventBus only handles
basic event processing. For advanced features like event chains and interruption,
use ChainableEventBus which extends this class.
"""

import asyncio
from typing import Any, Dict, Optional

from app.logger import logger
from app.event.core.base import BaseEvent, BaseEventBus
from app.event.infrastructure.registry import EventHandlerRegistry, get_global_registry
from app.event.infrastructure.middleware import MiddlewareChain, MiddlewareContext, create_default_middleware_chain


class SimpleEventBus(BaseEventBus):
    """Simple event bus with basic async dispatch and registry support.

    This implementation focuses on core functionality:
    - Event publishing and handler dispatch
    - Middleware processing
    - Basic statistics and metrics

    Design principle: Keep it simple and focused. Advanced features like
    event chains, interruption, and context management are handled by
    ChainableEventBus which extends this class.
    """

    def __init__(
        self,
        name: str = "SimpleEventBus",
        max_concurrent_events: int = 10,
        registry: Optional[EventHandlerRegistry] = None,
        middleware_chain: Optional[MiddlewareChain] = None
    ):
        super().__init__(name=name, max_concurrent_events=max_concurrent_events)

        # Use provided registry or global registry
        self.registry = registry or get_global_registry()

        # Use provided middleware chain or create default
        self.middleware_chain = middleware_chain or create_default_middleware_chain()

        # Processing semaphore to limit concurrent events
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_events)

    async def publish(self, event: BaseEvent) -> bool:
        """Publish an event to the bus for processing.

        This is the core method that:
        1. Finds matching handlers for the event
        2. Processes each handler through the middleware chain
        3. Tracks success/failure and updates event status

        Args:
            event: The event to publish

        Returns:
            bool: True if at least one handler processed the event successfully
        """
        # Add to active events for tracking
        self.active_events[event.event_id] = event

        try:
            # Get matching handlers from registry
            independent_handlers, dependent_handlers = self.registry.get_handlers_for_event(event.event_type)
            all_handlers = independent_handlers + dependent_handlers

            if not all_handlers:
                logger.debug(f"No handlers found for event type: {event.event_type}")
                event.mark_completed()
                return False

            # Process handlers with concurrency control
            success_count = 0
            async with self.processing_semaphore:
                for handler_info in all_handlers:
                    try:
                        # Create middleware context
                        context = MiddlewareContext(
                            event=event,
                            handler_name=handler_info.name
                        )

                        # Define handler wrapper for middleware
                        async def handler_wrapper(middleware_context):
                            # Check if handler is async or sync
                            import inspect
                            if inspect.iscoroutinefunction(handler_info.handler):
                                return await handler_info.handler(event)
                            else:
                                return handler_info.handler(event)

                        # Process through middleware chain
                        success = await self.middleware_chain.process(context, handler_wrapper)

                        if success:
                            success_count += 1
                            logger.debug(f"Handler '{handler_info.name}' successfully processed event {event.event_id}")
                        else:
                            logger.warning(f"Handler '{handler_info.name}' failed to process event {event.event_id}")

                    except Exception as e:
                        logger.error(f"Error in handler '{handler_info.name}' for event {event.event_id}: {str(e)}")

            # Update event status based on results
            if success_count > 0:
                event.mark_completed()
                return True
            else:
                event.mark_failed("No handlers processed the event successfully")
                return False

        except Exception as e:
            logger.error(f"Error publishing event {event.event_id}: {str(e)}")
            event.mark_failed(str(e))
            return False
        finally:
            # Cleanup: remove from active events and add to history
            if event.event_id in self.active_events:
                del self.active_events[event.event_id]
            self.add_to_history(event)

    async def subscribe(self, handler) -> bool:
        """Subscribe a handler to the event bus.

        Note: Handler registration is managed by the registry system.
        Use the @event_handler decorator or registry.register_handler() instead.

        Args:
            handler: The event handler to register

        Returns:
            bool: True (registration is handled by registry)
        """
        logger.info("Handler subscription should be done through the registry system using @event_handler decorator")
        return True

    async def unsubscribe(self, handler_name: str) -> bool:
        """Unsubscribe a handler from the event bus.

        Args:
            handler_name: Name of the handler to unregister

        Returns:
            bool: True if handler was unregistered successfully
        """
        return self.registry.unregister_handler(handler_name)

    def get_metrics(self) -> Dict[str, Any]:
        """Get bus-specific metrics.

        Returns:
            Dict[str, Any]: Bus metrics including registry and middleware info
        """
        return {
            "bus_name": self.name,
            "max_concurrent_events": self.max_concurrent_events,
            "registry_handlers": len(self.registry._handlers),
            "middleware_enabled": self.middleware_chain is not None,
        }


# Global bus instance management
_global_bus: Optional[SimpleEventBus] = None


def get_global_bus() -> SimpleEventBus:
    """Get the global event bus instance.

    Returns:
        SimpleEventBus: The global bus instance
    """
    global _global_bus
    if _global_bus is None:
        _global_bus = SimpleEventBus()
    return _global_bus


def set_global_bus(bus: SimpleEventBus) -> None:
    """Set the global event bus instance.

    Args:
        bus: The bus instance to set as global
    """
    global _global_bus
    _global_bus = bus


# Convenience functions for global bus operations
async def publish_event(event: BaseEvent) -> bool:
    """Publish an event using the global bus.

    Args:
        event: The event to publish

    Returns:
        bool: True if event was processed successfully
    """
    return await get_global_bus().publish(event)


async def subscribe_handler(handler) -> bool:
    """Subscribe a handler using the global bus.

    Args:
        handler: The handler to subscribe

    Returns:
        bool: True if subscription was successful
    """
    return await get_global_bus().subscribe(handler)


async def unsubscribe_handler(handler_name: str) -> bool:
    """Unsubscribe a handler using the global bus.

    Args:
        handler_name: Name of the handler to unsubscribe

    Returns:
        bool: True if unsubscription was successful
    """
    return await get_global_bus().unsubscribe(handler_name)


def get_bus_stats() -> Dict[str, Any]:
    """Get statistics from the global bus.

    Returns:
        Dict[str, Any]: Combined event stats and bus metrics
    """
    bus = get_global_bus()
    stats = bus.get_event_stats()
    stats.update(bus.get_metrics())
    return stats
