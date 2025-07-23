"""Event bus implementations.

This module contains concrete implementations of event buses including
simple bus and chainable bus with interrupt support.
"""

from .simple_bus import (
    SimpleEventBus,
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats
)

from .chainable_bus import ChainableEventBus

__all__ = [
    # Simple event bus
    "SimpleEventBus",
    "get_global_bus",
    "set_global_bus", 
    "publish_event",
    "subscribe_handler",
    "unsubscribe_handler",
    "get_bus_stats",
    
    # Chainable event bus
    "ChainableEventBus"
]
