import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from app.event.registry import event_handler
from app.event.events import TestEvent,TestAddEvent
from app.event import publish_event
from app.event.simple_bus import get_global_bus, publish_event
from app.event.middleware import create_default_middleware_chain

@event_handler("test.*", name="test_handler")
async def handle_test_events(event):
    """Handle test events."""
    print(f"Handled test event: {event.event_type} 11111111111")
    return True

@event_handler("test.testadd")
async def handle_test_add_events(event):
    """Handle test add events."""
    a = event.data.get("a", 0)
    b = event.data.get("b", 0)
    print(f"{a} + {b} = {int(a) + int(b)}")
    return True

async def run():
    bus = get_global_bus()
    bus.middleware_chain= create_default_middleware_chain(
        enable_logging=False,
        enable_retry=False,
        enable_error_isolation=False,
        enable_metrics=False,
        enable_Test=True
    )

    test_event = TestEvent("4","3",priority =-1)
    test_add_event = TestAddEvent("4","9",priority =0)

    await publish_event([test_event,test_add_event])

    stats = bus.get_event_stats()
    stats.update(bus.get_metrics())

    print(f"Total Events: {stats.get('total_events', 0)}")
    print(f"Active Events: {stats.get('active_events', 0)}")
    print(f"Registered Handlers: {stats.get('registered_handlers', 0)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
