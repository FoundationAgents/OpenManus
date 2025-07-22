"""Event system type definitions."""

from enum import Enum


class EventStatus(str, Enum):
    """Enumeration of possible event statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ToolExecutionStatus(str, Enum):
    """Tool execution status."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
