"""Global event system API.

This module provides the main public API for the event system,
including global bus functions and handler registration.
"""

# Import global functions from infrastructure
from app.event.infrastructure.bus import (
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats
)

from app.event.infrastructure.registry import (
    event_handler,
    get_global_registry
)

__all__ = [
    # Global bus functions
    "get_global_bus",
    "set_global_bus",
    "publish_event",
    "subscribe_handler", 
    "unsubscribe_handler",
    "get_bus_stats",
    
    # Handler registration
    "event_handler",
    "get_global_registry"
]
