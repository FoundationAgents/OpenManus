import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import from the new restructured event system
from app.event import (
    event_handler,
    get_global_bus,
    publish_event,
    create_default_middleware_chain
)
from app.event.domain.system.test_events import TestEvent, TestAddEvent

@event_handler("test.*", name="test_handler")
async def handle_test_events(event):
    """Handle test events."""
    print(f"Handled test event: {event.event_type} - Basic test handler")
    return True

@event_handler("test.testadd")
async def handle_test_add_events(event):
    """Handle test add events."""
    a = event.data.get("a", 0)
    b = event.data.get("b", 0)
    print(f"Addition test: {a} + {b} = {int(a) + int(b)}")
    return True

async def run():
    """Run the test scenario."""
    bus = get_global_bus()

    # Configure middleware chain
    bus.middleware_chain = create_default_middleware_chain(
        enable_logging=True,
        enable_retry=False,
        enable_error_isolation=True,
        enable_metrics=True
    )

    # Create test events
    print("Creating test events...")
    test_event = TestEvent("4", "3")
    test_add_event = TestAddEvent("4", "9")

    # Publish events
    print("Publishing events...")
    await publish_event(test_event)
    await publish_event(test_add_event)

    # Get and display statistics
    stats = bus.get_event_stats()
    metrics = bus.get_metrics()
    stats.update(metrics)

    print("\n=== Event System Statistics ===")
    print(f"Total Events: {stats.get('total_events', 0)}")
    print(f"Active Events: {stats.get('active_events', 0)}")
    print(f"Registered Handlers: {stats.get('registered_handlers', 0)}")
    print(f"Status Distribution: {stats.get('status_distribution', {})}")

    if 'handler_metrics' in stats:
        print(f"Handler Metrics: {stats['handler_metrics']}")

if __name__ == "__main__":
    print("Starting event system test...")
    asyncio.run(run())
    print("Test completed.")
