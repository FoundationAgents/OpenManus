"""Simple event bus implementation with registry and middleware support.

This module provides a complete event bus implementation that integrates
the handler registry system and middleware chain for robust event processing.
"""

import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from app.logger import logger
from app.event.base import BaseEvent, BaseEventBus, BaseEventHandler
from app.event.registry import EventHandlerRegistry, get_global_registry, HandlerInfo
from app.event.middleware import MiddlewareChain, MiddlewareContext, create_default_middleware_chain


class SimpleEventBus(BaseEventBus):
    """Simple event bus with registry and middleware support."""

    def __init__(
        self,
        name: str = "SimpleEventBus",
        max_concurrent_events: int = 10,
        registry: Optional[EventHandlerRegistry] = None,
        middleware_chain: Optional[MiddlewareChain] = None,
        use_thread_pool: bool = False,
        thread_pool_size: int = 4
    ):
        super().__init__(name=name, max_concurrent_events=max_concurrent_events)

        # Use provided registry or global registry
        self.registry = registry or get_global_registry()

        # Use provided middleware chain or create default
        self.middleware_chain = middleware_chain or create_default_middleware_chain()

        # Thread pool for sync handlers
        self.use_thread_pool = use_thread_pool
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size) if use_thread_pool else None

        # Processing semaphore to limit concurrent events
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_events)

    async def publish(self, event: BaseEvent) -> bool:
        """Publish an event to the bus for processing.

        Args:
            event: The event to publish

        Returns:
            bool: True if at least one handler processed the event successfully
        """
        if event.event_id in self.active_events:
            logger.warning(f"Event {event.event_id} is already being processed")
            return False

        # Add to active events
        self.active_events[event.event_id] = event

        try:
            # Get handlers for this event type, split by dependency
            independent_handlers, dependent_handlers = self.registry.get_handlers_for_event(event.event_type)

            total_handlers = len(independent_handlers) + len(dependent_handlers)
            if total_handlers == 0:
                logger.debug(f"No handlers found for event type: {event.event_type}")
                event.mark_completed()
                return False

            logger.debug(f"Processing event {event.event_id} with {total_handlers} handlers "
                        f"({len(independent_handlers)} independent, {len(dependent_handlers)} dependent)")

            # Use semaphore to limit concurrent processing
            async with self.processing_semaphore:
                success_count = await self._process_handlers_optimized(event, independent_handlers, dependent_handlers)

            # Mark event as completed if any handler succeeded
            if success_count > 0:
                event.mark_completed()
                logger.debug(f"Event {event.event_id} processed successfully by {success_count} handlers")
                return True
            else:
                event.mark_failed("No handlers processed the event successfully")
                logger.warning(f"Event {event.event_id} failed - no successful handlers")
                return False

        except Exception as e:
            error_msg = f"Error processing event {event.event_id}: {str(e)}"
            logger.error(error_msg)
            event.mark_failed(error_msg)
            return False

        finally:
            # Remove from active events and add to history
            if event.event_id in self.active_events:
                del self.active_events[event.event_id]
            self.add_to_history(event)

    async def subscribe(self, handler: BaseEventHandler) -> bool:
        """Subscribe a handler to the event bus.

        Args:
            handler: The event handler to register

        Returns:
            bool: True if handler was registered successfully
        """
        try:
            # Register with the registry
            self.registry.register_handler(
                name=handler.name,
                handler=handler.handle,
                patterns=handler.supported_events or ["*"],
                enabled=handler.enabled
            )

            # Also add to our handlers dict for compatibility
            self.handlers[handler.name] = handler

            logger.info(f"Subscribed handler '{handler.name}' to event bus")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe handler '{handler.name}': {str(e)}")
            return False

    async def unsubscribe(self, handler_name: str) -> bool:
        """Unsubscribe a handler from the event bus.

        Args:
            handler_name: Name of the handler to unregister

        Returns:
            bool: True if handler was unregistered successfully
        """
        try:
            # Remove from registry
            registry_success = self.registry.unregister_handler(handler_name)

            # Remove from handlers dict
            if handler_name in self.handlers:
                del self.handlers[handler_name]

            if registry_success:
                logger.info(f"Unsubscribed handler '{handler_name}' from event bus")
                return True
            else:
                logger.warning(f"Handler '{handler_name}' not found for unsubscription")
                return False

        except Exception as e:
            logger.error(f"Failed to unsubscribe handler '{handler_name}': {str(e)}")
            return False

    async def _process_handlers_optimized(
        self,
        event: BaseEvent,
        independent_handlers: List[HandlerInfo],
        dependent_handlers: List[HandlerInfo]
    ) -> int:
        """Process event with optimized parallel/sequential handling.

        Args:
            event: The event to process
            independent_handlers: Handlers with no dependencies (can run in parallel)
            dependent_handlers: Handlers with dependencies (run sequentially)

        Returns:
            int: Number of handlers that processed the event successfully
        """
        success_count = 0

        # Process independent handlers in parallel
        if independent_handlers:
            logger.debug(f"Processing {len(independent_handlers)} independent handlers in parallel")

            # Create tasks for all independent handlers
            independent_tasks = []
            for handler_info in independent_handlers:
                task = self._process_single_handler(event, handler_info)
                independent_tasks.append(task)

            # Wait for all independent handlers to complete
            independent_results = await asyncio.gather(*independent_tasks, return_exceptions=True)

            # Count successes
            for result in independent_results:
                if result is True:
                    success_count += 1

        # Process dependent handlers sequentially
        if dependent_handlers:
            logger.debug(f"Processing {len(dependent_handlers)} dependent handlers sequentially")

            for handler_info in dependent_handlers:
                try:
                    success = await self._process_single_handler(event, handler_info)
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Dependent handler '{handler_info.name}' error: {str(e)}")
                    # Continue with other handlers due to error isolation

        return success_count

    async def _process_single_handler(self, event: BaseEvent, handler_info: HandlerInfo) -> bool:
        """Process a single handler through the middleware chain.

        Args:
            event: The event to process
            handler_info: Handler information

        Returns:
            bool: True if handler processed successfully
        """
        try:
            # Create middleware context
            context = MiddlewareContext(
                event=event,
                handler_name=handler_info.name
            )

            # Process through middleware chain
            success = await self.middleware_chain.process(context, handler_info.handler)

            if success:
                logger.debug(f"Handler '{handler_info.name}' processed event {event.event_id} successfully")
            else:
                logger.debug(f"Handler '{handler_info.name}' failed to process event {event.event_id}")

            return success

        except Exception as e:
            logger.error(f"Handler '{handler_info.name}' error: {str(e)}")
            return False

    def get_registry(self) -> EventHandlerRegistry:
        """Get the event handler registry."""
        return self.registry

    def get_middleware_chain(self) -> MiddlewareChain:
        """Get the middleware chain."""
        return self.middleware_chain

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics from middleware."""
        for middleware in self.middleware_chain.middlewares:
            if hasattr(middleware, 'get_metrics'):
                return middleware.get_metrics()
        return {}

    def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about event processing (override to include registry handlers)."""
        total_events = len(self.event_history)
        active_count = len(self.active_events)

        status_counts = {}
        for event in self.event_history:
            status = event.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_events": total_events,
            "active_events": active_count,
            "registered_handlers": len(self.registry.list_handlers()),  # Use registry instead
            "status_distribution": status_counts,
        }



    def enable_handler(self, handler_name: str) -> bool:
        """Enable a handler."""
        return self.registry.enable_handler(handler_name)

    def disable_handler(self, handler_name: str) -> bool:
        """Disable a handler."""
        return self.registry.disable_handler(handler_name)

    def list_handlers(self) -> List[HandlerInfo]:
        """List all registered handlers."""
        return self.registry.list_handlers()

    async def shutdown(self) -> None:
        """Shutdown the event bus and cleanup resources."""
        logger.info(f"Shutting down event bus '{self.name}'")

        # Wait for active events to complete
        if self.active_events:
            logger.info(f"Waiting for {len(self.active_events)} active events to complete...")
            # Give events some time to complete
            await asyncio.sleep(1.0)

        # Shutdown thread pool if used
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)

        logger.info(f"Event bus '{self.name}' shutdown complete")


# Global event bus instance
_global_bus: Optional[SimpleEventBus] = None


def get_global_bus() -> SimpleEventBus:
    """Get or create the global event bus instance."""
    global _global_bus
    if _global_bus is None:
        _global_bus = SimpleEventBus(name="GlobalEventBus")
    return _global_bus


def set_global_bus(bus: SimpleEventBus) -> None:
    """Set the global event bus instance."""
    global _global_bus
    _global_bus = bus


async def publish_event(event: BaseEvent | list) -> bool:
    """Publish an event or list of events to the global event bus.

    If a list is provided, events are sorted by priority (lower number = higher priority)
    and processed in order.
    """
    if isinstance(event, BaseEvent):
        return await get_global_bus().publish(event)
    else:
        # Sort events by priority (lower number = higher priority)
        sorted_events = sorted(event, key=lambda e: e.priority)

        results = []
        for e in sorted_events:
            result = await get_global_bus().publish(e)
            results.append(result)

        # Return True if any event was processed successfully
        return any(results)


async def subscribe_handler(handler: BaseEventHandler) -> bool:
    """Subscribe a handler to the global event bus."""
    return await get_global_bus().subscribe(handler)


async def unsubscribe_handler(handler_name: str) -> bool:
    """Unsubscribe a handler from the global event bus."""
    return await get_global_bus().unsubscribe(handler_name)


def get_bus_stats() -> Dict[str, Any]:
    """Get statistics from the global event bus."""
    bus = get_global_bus()
    stats = bus.get_event_stats()
    stats.update(bus.get_metrics())
    return stats
