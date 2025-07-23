from app.event.base import BaseEvent


class TestEvent(BaseEvent):
    "Test Event"
    def __init__(self, a, b, **kwargs):
        super().__init__(
            event_type=f"test.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "a": a,
                "b": b
            },
            **kwargs
        )

class TestAddEvent(TestEvent):
    "Test Add Event"
    def __init__(self, a, b, **kwargs):
        super().__init__(
            a=a,
            b=b,
            **kwargs
        )

def create_test_event(a, b):
    return TestEvent(a, b, source="test")

def create_test_add_event(a, b):
    return TestAddEvent(a, b, source="test")
