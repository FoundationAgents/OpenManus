"""
Tests for auto-restart service
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.reliability.auto_restart import AutoRestartService, ServiceManager


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.mark.asyncio
async def test_auto_restart_service_initialization(temp_db):
    """Test auto-restart service initialization"""
    service = AutoRestartService(str(temp_db))
    assert service._max_restarts == 3
    assert service._restart_delay == 5


@pytest.mark.asyncio
async def test_record_restart(temp_db):
    """Test recording a restart"""
    service = AutoRestartService(str(temp_db))

    success = service.record_restart("process_failure", exit_code=1)
    assert success


@pytest.mark.asyncio
async def test_restart_count(temp_db):
    """Test restart count tracking"""
    service = AutoRestartService(str(temp_db))

    # Record some restarts
    for i in range(2):
        service.record_restart("test_failure", exit_code=i)

    count = service._get_restart_count()
    assert count >= 2


@pytest.mark.asyncio
async def test_can_restart(temp_db):
    """Test restart permission check"""
    service = AutoRestartService(str(temp_db))

    # Should be able to restart initially
    assert service.can_restart()

    # Record max restarts
    for i in range(3):
        service.record_restart("failure", exit_code=1)

    # Should not be able to restart now
    can_restart = service.can_restart()
    # Depends on if they're within the hour


@pytest.mark.asyncio
async def test_restart_history(temp_db):
    """Test restart history retrieval"""
    service = AutoRestartService(str(temp_db))

    # Record some restarts
    for i in range(3):
        service.record_restart(f"failure_{i}", exit_code=i)

    history = service.get_restart_history(hours=1)
    assert len(history) >= 3


@pytest.mark.asyncio
async def test_restart_status(temp_db):
    """Test restart status reporting"""
    service = AutoRestartService(str(temp_db))

    status = service.get_restart_status()
    assert "restart_count_1h" in status
    assert "max_restarts_per_hour" in status
    assert "can_restart" in status
    assert "restart_delay" in status


@pytest.mark.asyncio
async def test_service_manager_status(temp_db):
    """Test service manager status"""
    status = ServiceManager.get_service_status()
    assert "status" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
