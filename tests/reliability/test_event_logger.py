"""
Tests for event logging system
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.reliability.event_logger import EventLogger, LogEvent


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_event_logger_initialization(temp_dir):
    """Test event logger initialization"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    assert logger._session_id is not None
    assert logger.logs_dir.exists()


@pytest.mark.asyncio
async def test_log_event(temp_dir):
    """Test logging an event"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    success = await logger.log_event(
        level="INFO",
        component="test_component",
        event_type="test_event",
        message="Test event message",
        details={"key": "value"},
    )

    assert success


@pytest.mark.asyncio
async def test_get_events(temp_dir):
    """Test retrieving events"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    # Log some events
    for i in range(3):
        await logger.log_event(
            level="INFO",
            component="test",
            event_type=f"event_{i}",
            message=f"Test message {i}",
        )

    # Retrieve events
    events = await logger.get_events(component="test")
    assert len(events) >= 3


@pytest.mark.asyncio
async def test_search_logs(temp_dir):
    """Test log searching"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    # Log some events
    await logger.log_event(
        level="ERROR",
        component="test",
        event_type="error_event",
        message="Something went wrong",
    )

    await logger.log_event(
        level="INFO",
        component="test",
        event_type="info_event",
        message="All is well",
    )

    # Search for error logs
    results = await logger.search_logs("wrong")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_session_id_persistence(temp_dir):
    """Test session ID persistence"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    session_id_1 = logger.get_session_id()

    await logger.log_event(
        level="INFO",
        component="test",
        event_type="test",
        message="Test",
    )

    session_id_2 = logger.get_session_id()
    assert session_id_1 == session_id_2


@pytest.mark.asyncio
async def test_get_system_info(temp_dir):
    """Test system information retrieval"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    info = logger._get_system_info()
    assert "platform" in info
    assert "python_version" in info
    assert "memory" in info
    assert "disk" in info


@pytest.mark.asyncio
async def test_event_filtering(temp_dir):
    """Test event filtering by level"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    # Log different levels
    await logger.log_event("INFO", "test", "info", "Info message")
    await logger.log_event("WARNING", "test", "warn", "Warning message")
    await logger.log_event("ERROR", "test", "error", "Error message")

    # Filter by level
    errors = await logger.get_events(level="ERROR")
    assert len(errors) > 0


@pytest.mark.asyncio
async def test_concurrent_logging(temp_dir):
    """Test concurrent event logging"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    # Log events concurrently
    tasks = [
        logger.log_event(
            level="INFO",
            component="test",
            event_type=f"event_{i}",
            message=f"Message {i}",
        )
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)
    assert all(results)


@pytest.mark.asyncio
async def test_cleanup_old_logs(temp_dir):
    """Test cleanup of old logs"""
    db_path = temp_dir / "test.db"
    logger = EventLogger(str(db_path))

    # Log some events
    await logger.log_event("INFO", "test", "test", "Test message")

    # Cleanup
    deleted = await logger.cleanup_old_logs(keep_days=0)
    assert deleted >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
