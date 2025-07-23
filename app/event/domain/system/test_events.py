"""Test events for the event system."""

from app.event.core.base import BaseEvent


class TestEvent(BaseEvent):
    """Basic test event."""

    def __init__(self, a: str, b: str, priority: int = 0, **kwargs):
        super().__init__(
            event_type="test.basic",
            data={"a": a, "b": b},
            **kwargs
        )


class TestAddEvent(BaseEvent):
    """Test event for addition operations."""

    def __init__(self, a: str, b: str, priority: int = 0, **kwargs):
        super().__init__(
            event_type="test.testadd",
            data={"a": a, "b": b},
            **kwargs
        )

