"""System domain events.

This module contains all system-related events including error events,
logging events, metrics events, and streaming events.
"""

from .events import (
    SystemEvent,
    SystemErrorEvent,
    create_system_error_event
)

from .chainable import (
    ChainableSystemEvent,
    ChainableLogWriteEvent,
    ChainableMetricsUpdateEvent,
    ChainableStreamEvent,
    ChainableStreamStartEvent,
    ChainableStreamChunkEvent,
    ChainableStreamEndEvent,
    ChainableStreamInterruptEvent
)

__all__ = [
    # Basic system events
    "SystemEvent",
    "SystemErrorEvent",
    "create_system_error_event",
    
    # Chainable system events
    "ChainableSystemEvent",
    "ChainableLogWriteEvent",
    "ChainableMetricsUpdateEvent",
    "ChainableStreamEvent",
    "ChainableStreamStartEvent",
    "ChainableStreamChunkEvent",
    "ChainableStreamEndEvent",
    "ChainableStreamInterruptEvent"
]
