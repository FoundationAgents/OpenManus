"""System domain events.

This module contains all system-related events including error events,
logging events, metrics events, and streaming events.
"""

from .events import SystemErrorEvent, SystemEvent, create_system_error_event

__all__ = [
    # Basic system events
    "SystemEvent",
    "SystemErrorEvent",
    "create_system_error_event",
]
