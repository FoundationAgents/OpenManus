"""Chainable event bus implementation with interrupt support.

This module provides an enhanced event bus that extends SimpleEventBus with:
1. Event chain management and context propagation
2. Cascading event interruption support
3. Conversation/agent-based event grouping
4. Context-aware event processing

This follows the layered architecture principle - ChainableEventBus builds upon
SimpleEventBus core functionality and adds advanced chain management features.
"""

import asyncio
from typing import Any, Dict, List, Optional, Set, Union

from app.logger import logger
from app.event.core.base import BaseEvent, ChainableEvent, EventContext
from app.event.infrastructure.bus.simple_bus import SimpleEventBus


class ChainableEventBus(SimpleEventBus):
    """Event bus with support for event chains and interruption.

    Extends SimpleEventBus with advanced features:
    - Event chain management and context propagation
    - Cascading event interruption
    - Conversation/agent-based event grouping
    - Context-aware event processing

    Design principle: Build upon SimpleEventBus core functionality,
    adding chain management without breaking the basic event processing.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Event chain management for interruption support
        self.conversation_contexts: Dict[str, EventContext] = {}
        self.active_event_chains: Dict[str, Set[str]] = {}  # root_event_id -> {child_event_ids}

    async def publish(self, event: Union[BaseEvent, ChainableEvent]) -> bool:
        """Publish an event with optional chain and interruption support.

        Args:
            event: The event to publish (BaseEvent or ChainableEvent)

        Returns:
            bool: True if at least one handler processed the event successfully
        """
        # If it's a ChainableEvent, use enhanced processing with context management
        if isinstance(event, ChainableEvent):
            return await self._publish_chainable_event(event)
        else:
            # For regular BaseEvent, use parent class logic
            return await super().publish(event)

    async def _publish_chainable_event(self, event: ChainableEvent) -> bool:
        """Publish a chainable event with context management and interruption support."""

        # 1. Check if event is already cancelled
        if event.is_cancelled():
            logger.info(f"ChainableEvent {event.event_id} was cancelled before processing")
            return False

        # 2. Initialize context if this is a root event
        if not event.context:
            self._initialize_event_context(event)

        # 3. Add event to execution chain
        self._add_to_execution_chain(event)

        # 4. Use parent class processing but with context awareness
        try:
            # Add to active events for tracking
            self.active_events[event.event_id] = event

            # Get matching handlers from registry
            independent_handlers, dependent_handlers = self.registry.get_handlers_for_event(event.event_type)
            all_handlers = independent_handlers + dependent_handlers

            if not all_handlers:
                logger.debug(f"No handlers found for event type: {event.event_type}")
                event.mark_completed()
                return False

            # Process handlers with context awareness and interruption checks
            success_count = 0
            async with self.processing_semaphore:
                for handler_info in all_handlers:
                    # Check for cancellation before each handler
                    if event.is_cancelled():
                        logger.info(f"Event {event.event_id} was cancelled during processing")
                        break

                    try:
                        # Create middleware context
                        from app.event.infrastructure.middleware import MiddlewareContext
                        context = MiddlewareContext(
                            event=event,
                            handler_name=handler_info.name
                        )

                        # Define context-aware handler wrapper
                        async def handler_wrapper(middleware_context):
                            # Final cancellation check before handler execution
                            if event.is_cancelled():
                                return False
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
                            logger.debug(f"Handler '{handler_info.name}' successfully processed chainable event {event.event_id}")
                        else:
                            logger.warning(f"Handler '{handler_info.name}' failed to process chainable event {event.event_id}")

                    except Exception as e:
                        logger.error(f"Error in handler '{handler_info.name}' for chainable event {event.event_id}: {str(e)}")

            # Update event status based on results
            if success_count > 0:
                event.mark_completed()
                return True
            else:
                event.mark_failed("No handlers processed the chainable event successfully")
                return False

        except Exception as e:
            logger.error(f"Error publishing chainable event {event.event_id}: {str(e)}")
            event.mark_failed(str(e))
            return False
        finally:
            # Cleanup: remove from active events and add to history
            if event.event_id in self.active_events:
                del self.active_events[event.event_id]
            self.add_to_history(event)
            self._cleanup_event_chain(event)

    def _initialize_event_context(self, event: ChainableEvent) -> None:
        """Initialize event context for a root event."""
        conversation_id = event.get_conversation_id() or 'default'
        agent_id = event.get_agent_id() or 'unknown'

        cancellation_token = asyncio.Event()
        event.context = EventContext(
            root_event_id=event.event_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            execution_chain=[],
            cancellation_token=cancellation_token
        )

        # Save context for conversation-level management
        self.conversation_contexts[conversation_id] = event.context
        self.active_event_chains[event.event_id] = {event.event_id}

        logger.debug(f"Created new event chain for conversation {conversation_id}, root event {event.event_id}")

    def _add_to_execution_chain(self, event: ChainableEvent) -> None:
        """Add event to the execution chain."""
        if event.context and event.context.root_event_id in self.active_event_chains:
            self.active_event_chains[event.context.root_event_id].add(event.event_id)
            event.context.execution_chain.append(event.event_id)

    def _cleanup_event_chain(self, event: ChainableEvent) -> None:
        """Clean up event chain tracking.

        Note: We keep the chain and context alive for potential interruption
        until explicitly cleaned up or after a timeout.
        """
        if event.context and event.context.root_event_id in self.active_event_chains:
            chain = self.active_event_chains[event.context.root_event_id]
            # Remove this specific event from the chain but keep the chain alive
            chain.discard(event.event_id)

            # Only clean up if this is explicitly a chain termination event
            # or if the chain has been marked for cleanup
            # For now, we keep chains alive to support interruption

    async def interrupt_conversation(self, conversation_id: str, reason: str = "user_interrupt") -> bool:
        """Interrupt all active events in a conversation.

        Args:
            conversation_id: The conversation to interrupt
            reason: Reason for interruption

        Returns:
            bool: True if interruption was successful
        """
        if conversation_id not in self.conversation_contexts:
            logger.warning(f"No active conversation found for ID: {conversation_id}")
            return False

        context = self.conversation_contexts[conversation_id]
        context.cancellation_token.set()

        logger.info(f"Interrupted conversation {conversation_id}, reason: {reason}")
        return True

    async def interrupt_event_chain(self, root_event_id: str, reason: str = "chain_interrupt") -> bool:
        """Interrupt a specific event chain.

        Args:
            root_event_id: The root event ID of the chain to interrupt
            reason: Reason for interruption

        Returns:
            bool: True if interruption was successful
        """
        if root_event_id not in self.active_event_chains:
            logger.warning(f"No active event chain found for root event: {root_event_id}")
            return False

        # Find the context and set cancellation token
        for context in self.conversation_contexts.values():
            if context.root_event_id == root_event_id:
                context.cancellation_token.set()
                logger.info(f"Interrupted event chain {root_event_id}, reason: {reason}")
                return True

        logger.warning(f"Could not find context for event chain: {root_event_id}")
        return False

    async def end_event_chain(self, root_event_id: str, reason: str = "chain_complete") -> bool:
        """Explicitly end an event chain and clean up resources.

        Args:
            root_event_id: The root event ID of the chain to end
            reason: Reason for ending the chain

        Returns:
            bool: True if chain was ended successfully
        """
        if root_event_id not in self.active_event_chains:
            logger.warning(f"No active event chain found for root event: {root_event_id}")
            return False

        # Clean up the chain
        del self.active_event_chains[root_event_id]

        # Clean up associated conversation context
        for conv_id, context in list(self.conversation_contexts.items()):
            if context.root_event_id == root_event_id:
                del self.conversation_contexts[conv_id]
                break

        logger.info(f"Ended event chain {root_event_id}, reason: {reason}")
        return True

    def get_active_chains(self) -> Dict[str, Any]:
        """Get information about active event chains.

        Returns:
            Dict containing active chain information
        """
        return {
            "active_conversations": list(self.conversation_contexts.keys()),
            "active_chains": {
                root_id: list(chain)
                for root_id, chain in self.active_event_chains.items()
            },
            "total_active_events": sum(len(chain) for chain in self.active_event_chains.values())
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get bus-specific metrics including chain information.

        Returns:
            Dict[str, Any]: Enhanced bus metrics with chain data
        """
        metrics = super().get_metrics()
        metrics.update({
            "active_conversations": len(self.conversation_contexts),
            "active_event_chains": len(self.active_event_chains),
            "total_chained_events": sum(len(chain) for chain in self.active_event_chains.values()),
            "supports_interruption": True,
        })
        return metrics
