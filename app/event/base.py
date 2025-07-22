"""Base classes for the event bus system."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from app.logger import logger
from app.event.types import EventStatus


class BaseEvent(BaseModel):
    """Base class for all events in the system.

    Provides common event properties and serialization capabilities.
    All custom events should inherit from this class.
    """

    # Core event properties
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event identifier")
    event_type: str = Field(..., description="Type/name of the event")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event creation timestamp")

    # Event metadata
    source: Optional[str] = Field(None, description="Source component that generated the event")
    status: EventStatus = Field(default=EventStatus.PENDING, description="Current event status")
    priority: int = Field(default=0, description="execution priority (higher = earlier)")

    # Event data
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")

    # Processing tracking
    processed_by: List[str] = Field(default_factory=list, description="List of handlers that processed this event")
    error_message: Optional[str] = Field(None, description="Error message if event processing failed")

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility

    def mark_processing(self, handler_name: str) -> None:
        """Mark event as being processed by a handler."""
        self.status = EventStatus.PROCESSING
        if handler_name not in self.processed_by:
            self.processed_by.append(handler_name)

    def mark_completed(self) -> None:
        """Mark event as successfully completed."""
        self.status = EventStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark event as failed with error message."""
        self.status = EventStatus.FAILED
        self.error_message = error

    def mark_cancelled(self) -> None:
        """Mark event as cancelled."""
        self.status = EventStatus.CANCELLED


class BaseEventHandler(ABC, BaseModel):
    """Abstract base class for event handlers.

    Event handlers process specific types of events. Each handler should
    implement the handle method to define its processing logic.
    """

    # Handler identification
    name: str = Field(..., description="Unique name of the event handler")
    description: Optional[str] = Field(None, description="Optional handler description")

    # Handler configuration
    enabled: bool = Field(default=True, description="Whether the handler is enabled")

    # Event filtering
    supported_events: List[str] = Field(default_factory=list, description="List of event types this handler supports")

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    @abstractmethod
    async def handle(self, event: BaseEvent) -> bool:
        """Handle an event.

        Args:
            event: The event to process

        Returns:
            bool: True if event was handled successfully, False otherwise

        Raises:
            Exception: If event processing fails
        """
        pass

    def can_handle(self, event: BaseEvent) -> bool:
        """Check if this handler can process the given event.

        Args:
            event: The event to check

        Returns:
            bool: True if handler can process the event
        """
        if not self.enabled:
            return False

        # If no specific events are configured, handle all events
        if not self.supported_events:
            return True

        return event.event_type in self.supported_events

    async def safe_handle(self, event: BaseEvent) -> bool:
        """Safely handle an event with error handling and logging.

        Args:
            event: The event to process

        Returns:
            bool: True if event was handled successfully, False otherwise
        """
        if not self.can_handle(event):
            return False

        try:
            event.mark_processing(self.name)
            logger.debug(f"Handler '{self.name}' processing event {event.event_id} ({event.event_type})")

            result = await self.handle(event)

            if result:
                logger.debug(f"Handler '{self.name}' successfully processed event {event.event_id}")
            else:
                logger.warning(f"Handler '{self.name}' failed to process event {event.event_id}")

            return result

        except Exception as e:
            error_msg = f"Handler '{self.name}' error processing event {event.event_id}: {str(e)}"
            logger.error(error_msg)
            event.mark_failed(error_msg)
            return False


class BaseEventBus(ABC, BaseModel):
    """Abstract base class for event bus implementations.

    The event bus is responsible for routing events to appropriate handlers
    and managing the overall event processing lifecycle.
    """

    # Bus configuration
    name: str = Field(default="EventBus", description="Name of the event bus")
    max_concurrent_events: int = Field(default=10, description="Maximum concurrent event processing")

    # Handler management
    handlers: Dict[str, BaseEventHandler] = Field(default_factory=dict, description="Registered event handlers")

    # Processing state
    active_events: Dict[str, BaseEvent] = Field(default_factory=dict, description="Currently processing events")
    event_history: List[BaseEvent] = Field(default_factory=list, description="Event processing history")
    max_history_size: int = Field(default=1000, description="Maximum number of events to keep in history")

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    @abstractmethod
    async def publish(self, event: BaseEvent) -> bool:
        """Publish an event to the bus for processing.

        Args:
            event: The event to publish

        Returns:
            bool: True if event was published successfully
        """
        pass

    @abstractmethod
    async def subscribe(self, handler: BaseEventHandler) -> bool:
        """Subscribe a handler to the event bus.

        Args:
            handler: The event handler to register

        Returns:
            bool: True if handler was registered successfully
        """
        pass

    @abstractmethod
    async def unsubscribe(self, handler_name: str) -> bool:
        """Unsubscribe a handler from the event bus.

        Args:
            handler_name: Name of the handler to unregister

        Returns:
            bool: True if handler was unregistered successfully
        """
        pass

    def get_handler(self, name: str) -> Optional[BaseEventHandler]:
        """Get a registered handler by name.

        Args:
            name: Name of the handler

        Returns:
            Optional[BaseEventHandler]: The handler if found, None otherwise
        """
        return self.handlers.get(name)

    def add_to_history(self, event: BaseEvent) -> None:
        """Add an event to the processing history.

        Args:
            event: The event to add to history
        """
        self.event_history.append(event)

        # Maintain history size limit
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]

    def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about event processing.

        Returns:
            Dict[str, Any]: Event processing statistics
        """
        total_events = len(self.event_history)
        active_count = len(self.active_events)

        status_counts = {}
        for event in self.event_history:
            status = event.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_events": total_events,
            "active_events": active_count,
            "registered_handlers": len(self.handlers),
            "status_distribution": status_counts,
        }
