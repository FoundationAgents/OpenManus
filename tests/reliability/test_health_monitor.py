"""
Tests for health monitoring system
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.reliability.health_monitor import (
    HealthMonitor,
    HealthStatus,
    ComponentHealth,
)


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.mark.asyncio
async def test_disk_health_check(temp_db):
    """Test disk health check"""
    monitor = HealthMonitor(str(temp_db))

    health = await monitor.check_disk_health()
    assert health.name == "disk"
    assert health.status in [HealthStatus.OK, HealthStatus.WARNING, HealthStatus.CRITICAL]
    assert "free_gb" in health.details
    assert "total_gb" in health.details


@pytest.mark.asyncio
async def test_memory_health_check(temp_db):
    """Test memory health check"""
    monitor = HealthMonitor(str(temp_db))

    health = await monitor.check_memory_health()
    assert health.name == "memory"
    assert health.status in [HealthStatus.OK, HealthStatus.WARNING, HealthStatus.CRITICAL]
    assert "used_gb" in health.details
    assert "percent" in health.details


@pytest.mark.asyncio
async def test_database_health_check(temp_db):
    """Test database health check"""
    monitor = HealthMonitor(str(temp_db))

    health = await monitor.check_database_health()
    assert health.name == "database"
    assert health.status in [HealthStatus.OK, HealthStatus.CRITICAL]


@pytest.mark.asyncio
async def test_health_summary(temp_db):
    """Test health summary generation"""
    monitor = HealthMonitor(str(temp_db))

    # Run some checks first
    await monitor.check_disk_health()
    await monitor.check_memory_health()
    await monitor.check_database_health()

    summary = monitor.get_health_summary()
    assert "overall_status" in summary
    assert "components" in summary
    assert summary["overall_status"] in ["✓", "⚠", "✗"]


@pytest.mark.asyncio
async def test_health_report_formatting(temp_db):
    """Test health report formatting"""
    monitor = HealthMonitor(str(temp_db))

    await monitor.check_disk_health()
    await monitor.check_memory_health()

    report = monitor.format_health_report()
    assert "System Health Report" in report
    assert "Overall Status" in report
    assert "disk:" in report or "memory:" in report


@pytest.mark.asyncio
async def test_all_health_checks(temp_db):
    """Test running all health checks concurrently"""
    monitor = HealthMonitor(str(temp_db))

    results = await monitor.check_all_health()
    assert len(results) > 0

    # Should have at least disk and memory checks
    assert "disk" in results or "memory" in results
    assert "database" in results


@pytest.mark.asyncio
async def test_health_thresholds(temp_db):
    """Test custom health thresholds"""
    monitor = HealthMonitor(str(temp_db))

    # Modify thresholds
    monitor._thresholds["memory_warning_percent"] = 50
    monitor._thresholds["memory_critical_percent"] = 80

    health = await monitor.check_memory_health()
    assert health.name == "memory"


@pytest.mark.asyncio
async def test_concurrent_health_checks(temp_db):
    """Test concurrent health checks"""
    monitor = HealthMonitor(str(temp_db))

    # Run multiple concurrent checks
    tasks = [
        monitor.check_disk_health(),
        monitor.check_memory_health(),
        monitor.check_database_health(),
        monitor.check_disk_health(),
        monitor.check_memory_health(),
    ]

    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    assert all(r.status in [HealthStatus.OK, HealthStatus.WARNING, HealthStatus.CRITICAL] for r in results)


@pytest.mark.asyncio
async def test_health_history_tracking(temp_db):
    """Test health history tracking"""
    monitor = HealthMonitor(str(temp_db))

    # Perform multiple checks
    await monitor.check_disk_health()
    await monitor.check_memory_health()
    await monitor.check_database_health()

    # All should be recorded
    assert len(monitor._health_history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
