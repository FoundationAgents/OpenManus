"""
Tests for Resource Monitor.
"""

import pytest
import time
from app.core.resource_monitor import ResourceMonitor, get_resource_monitor


def test_resource_monitor_initialization():
    """Test resource monitor initialization."""
    monitor = ResourceMonitor()
    
    assert monitor.min_available_memory_mb == 512
    assert monitor.max_cpu_percent == 80.0


def test_get_current_snapshot():
    """Test getting current resource snapshot."""
    monitor = ResourceMonitor()
    
    snapshot = monitor.get_current_snapshot()
    
    assert snapshot.timestamp > 0
    assert snapshot.cpu_percent >= 0
    assert snapshot.memory_available_mb > 0
    assert snapshot.memory_total_mb > 0
    assert 0 <= snapshot.memory_percent <= 100


def test_get_available_memory():
    """Test getting available memory."""
    monitor = ResourceMonitor()
    
    memory = monitor.get_available_memory_mb()
    assert memory > 0


def test_get_cpu_usage():
    """Test getting CPU usage."""
    monitor = ResourceMonitor()
    
    cpu = monitor.get_cpu_usage()
    assert 0 <= cpu <= 100


def test_is_resource_available():
    """Test checking if resources are available."""
    monitor = ResourceMonitor()
    
    # Should have resources for small requirement
    assert monitor.is_resource_available(10)
    
    # Should not have resources for huge requirement
    assert not monitor.is_resource_available(1000000)


def test_get_recommendation():
    """Test getting loading recommendation."""
    monitor = ResourceMonitor()
    
    components = ["comp1", "comp2", "comp3"]
    requirements = {
        "comp1": 100,
        "comp2": 200,
        "comp3": 50
    }
    
    recommendation = monitor.get_recommendation(components, requirements)
    
    assert recommendation.available_memory_mb > 0
    assert recommendation.required_memory_mb == 350
    assert isinstance(recommendation.recommended_components, list)
    assert isinstance(recommendation.skip_components, list)


def test_start_stop_monitoring():
    """Test starting and stopping monitoring."""
    monitor = ResourceMonitor()
    
    monitor.start_monitoring(interval=0.5)
    assert monitor._monitoring
    
    time.sleep(1.5)  # Let it collect some snapshots
    
    monitor.stop_monitoring()
    assert not monitor._monitoring
    
    snapshots = monitor.get_snapshots()
    assert len(snapshots) > 0


def test_get_average_usage():
    """Test getting average usage."""
    monitor = ResourceMonitor()
    
    monitor.start_monitoring(interval=0.3)
    time.sleep(1.0)
    
    avg_cpu, avg_memory = monitor.get_average_usage(last_n=3)
    
    assert 0 <= avg_cpu <= 100
    assert 0 <= avg_memory <= 100
    
    monitor.stop_monitoring()


def test_format_recommendation():
    """Test formatting recommendation."""
    monitor = ResourceMonitor()
    
    components = ["comp1", "comp2"]
    requirements = {"comp1": 100, "comp2": 200}
    
    recommendation = monitor.get_recommendation(components, requirements)
    formatted = monitor.format_recommendation(recommendation)
    
    assert isinstance(formatted, str)
    assert "Available RAM" in formatted
    assert "Required RAM" in formatted


def test_singleton():
    """Test that get_resource_monitor returns singleton."""
    monitor1 = get_resource_monitor()
    monitor2 = get_resource_monitor()
    
    assert monitor1 is monitor2
