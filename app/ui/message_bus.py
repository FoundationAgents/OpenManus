"""
Unified Message Bus for UI component communication.

Enables decoupled communication between UI components using a pub/sub pattern.
Components can publish events and subscribe to events without direct dependencies.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A message passed through the message bus."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None


class MessageBus:
    """
    Central message bus for UI component communication.
    
    Features:
    - Pub/sub pattern for decoupled components
    - Type-based event routing
    - Thread-safe operations
    - Event history for debugging
    - Wildcard subscriptions
    
    Example:
        # Subscribe to events
        @message_bus.on("code_executed")
        def handle_code_execution(message):
            print(f"Code executed: {message.data}")
        
        # Publish events
        message_bus.publish("code_executed", {
            "output": "Hello, World!",
            "error": None
        })
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the message bus.
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[Message] = []
        self._max_history = max_history
        self._lock = RLock()
        
    def subscribe(self, event_type: str, handler: Callable[[Message], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to (or "*" for all events)
            handler: Callback function that takes a Message
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"Subscribed handler to '{event_type}' events")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Message], None]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from '{event_type}' events")
    
    def publish(self, event_type: str, data: Dict[str, Any], source: Optional[str] = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Optional source component identifier
        """
        message = Message(
            event_type=event_type,
            data=data,
            source=source
        )
        
        with self._lock:
            # Add to history
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            # Notify specific subscribers
            handlers = self._subscribers.get(event_type, []).copy()
            
            # Notify wildcard subscribers
            wildcard_handlers = self._subscribers.get("*", []).copy()
            handlers.extend(wildcard_handlers)
        
        # Call handlers outside the lock to prevent deadlocks
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler for '{event_type}': {e}", exc_info=True)
        
        logger.debug(f"Published '{event_type}' event from {source or 'unknown'}")
    
    def on(self, event_type: str) -> Callable:
        """
        Decorator for subscribing to events.
        
        Args:
            event_type: Type of event to subscribe to
            
        Returns:
            Decorator function
            
        Example:
            @message_bus.on("code_executed")
            def handle_code(message):
                print(message.data)
        """
        def decorator(handler: Callable[[Message], None]) -> Callable[[Message], None]:
            self.subscribe(event_type, handler)
            return handler
        return decorator
    
    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Message]:
        """
        Get message history.
        
        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of messages to return
            
        Returns:
            List of messages (most recent first)
        """
        with self._lock:
            messages = self._history.copy()
        
        if event_type:
            messages = [m for m in messages if m.event_type == event_type]
        
        return list(reversed(messages[-limit:]))
    
    def clear_history(self) -> None:
        """Clear message history."""
        with self._lock:
            self._history.clear()
        logger.debug("Cleared message history")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            event_counts = {}
            for message in self._history:
                event_type = message.event_type
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "total_messages": len(self._history),
                "event_types": len(self._subscribers),
                "total_subscribers": sum(len(handlers) for handlers in self._subscribers.values()),
                "event_counts": event_counts
            }


# Global message bus instance
_message_bus: Optional[MessageBus] = None
_message_bus_lock = RLock()


def get_message_bus() -> MessageBus:
    """
    Get the global message bus instance (singleton).
    
    Returns:
        Global MessageBus instance
    """
    global _message_bus
    
    if _message_bus is None:
        with _message_bus_lock:
            if _message_bus is None:
                _message_bus = MessageBus()
    
    return _message_bus


# Common event types (for reference)
class EventTypes:
    """Common event types used throughout the application."""
    
    # Application lifecycle
    APP_STARTED = "app_started"
    APP_CLOSING = "app_closing"
    
    # Component lifecycle
    COMPONENT_LOADED = "component_loaded"
    COMPONENT_FAILED = "component_failed"
    COMPONENT_READY = "component_ready"
    
    # Code editor events
    FILE_OPENED = "file_opened"
    FILE_SAVED = "file_saved"
    FILE_CLOSED = "file_closed"
    CODE_EXECUTED = "code_executed"
    
    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_MESSAGE = "agent_message"
    AGENT_ERROR = "agent_error"
    
    # Tool events
    TOOL_EXECUTED = "tool_executed"
    TOOL_ERROR = "tool_error"
    
    # Project events
    PROJECT_OPENED = "project_opened"
    PROJECT_CLOSED = "project_closed"
    PROJECT_SAVED = "project_saved"
    
    # Settings events
    SETTINGS_CHANGED = "settings_changed"
    THEME_CHANGED = "theme_changed"
    
    # UI events
    PANEL_SHOWN = "panel_shown"
    PANEL_HIDDEN = "panel_hidden"
    STATUS_MESSAGE = "status_message"
    ERROR_OCCURRED = "error_occurred"
