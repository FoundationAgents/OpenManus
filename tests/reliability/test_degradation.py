"""
Tests for graceful degradation system
"""

import asyncio

import pytest

from app.reliability.degradation import (
    GracefulDegradationManager,
    DegradationLevel,
    ComponentFallback,
)


@pytest.mark.asyncio
async def test_degradation_manager_initialization():
    """Test degradation manager initialization"""
    manager = GracefulDegradationManager()
    assert manager._degradation_level == DegradationLevel.NORMAL


@pytest.mark.asyncio
async def test_register_fallback():
    """Test fallback registration"""
    manager = GracefulDegradationManager()

    fallback = ComponentFallback(
        component_name="llm",
        fallback_type="knowledge_base",
        description="Use knowledge base when LLM is unavailable",
    )

    manager.register_fallback(fallback)
    assert "llm" in manager._fallbacks


@pytest.mark.asyncio
async def test_register_component_handler():
    """Test component handler registration"""
    manager = GracefulDegradationManager()

    async def mock_handler():
        return True

    manager.register_component_handler("llm", mock_handler)
    assert "llm" in manager._component_handlers


@pytest.mark.asyncio
async def test_component_failure_handling():
    """Test handling component failure"""
    manager = GracefulDegradationManager()

    await manager.handle_component_failure("llm", Exception("LLM unavailable"))

    assert manager.is_component_failed("llm")
    assert manager.is_degraded()


@pytest.mark.asyncio
async def test_multiple_component_failures():
    """Test multiple component failures"""
    manager = GracefulDegradationManager()

    await manager.handle_component_failure("llm", Exception("LLM failed"))
    await manager.handle_component_failure("database", Exception("DB failed"))
    await manager.handle_component_failure("cache", Exception("Cache failed"))

    status = manager.get_degradation_status()
    assert len(status["failed_components"]) == 3
    assert status["level"] == DegradationLevel.CRITICAL.value


@pytest.mark.asyncio
async def test_degradation_status():
    """Test degradation status reporting"""
    manager = GracefulDegradationManager()

    status = manager.get_degradation_status()
    assert status["level"] == DegradationLevel.NORMAL.value
    assert len(status["failed_components"]) == 0


@pytest.mark.asyncio
async def test_degraded_capabilities():
    """Test degraded capabilities reporting"""
    manager = GracefulDegradationManager()

    capabilities = manager.get_degraded_capabilities()
    assert capabilities["llm_available"]
    assert capabilities["database_available"]
    assert capabilities["cache_available"]

    # Fail LLM
    await manager.handle_component_failure("llm", Exception("LLM failed"))

    capabilities = manager.get_degraded_capabilities()
    assert not capabilities["llm_available"]
    assert capabilities["database_available"]


@pytest.mark.asyncio
async def test_is_critical_state():
    """Test critical state detection"""
    manager = GracefulDegradationManager()

    assert not manager.is_critical()

    # Fail critical component
    await manager.handle_component_failure("database", Exception("DB failed"))
    assert manager.is_critical()


@pytest.mark.asyncio
async def test_wait_for_recovery():
    """Test waiting for component recovery"""
    manager = GracefulDegradationManager()

    # Simulate component failure
    await manager.handle_component_failure("llm", Exception("LLM failed"))

    # Start a task that simulates recovery
    async def simulate_recovery():
        await asyncio.sleep(0.5)
        with manager._lock:
            manager._failed_components.pop("llm", None)

    task = asyncio.create_task(simulate_recovery())

    # Wait for recovery
    recovered = await manager.wait_for_recovery("llm", timeout=2)
    await task
    assert recovered


@pytest.mark.asyncio
async def test_wait_for_recovery_timeout():
    """Test recovery wait timeout"""
    manager = GracefulDegradationManager()

    await manager.handle_component_failure("llm", Exception("LLM failed"))

    # Wait for recovery with short timeout
    recovered = await manager.wait_for_recovery("llm", timeout=0.1)
    assert not recovered


@pytest.mark.asyncio
async def test_concurrent_failures():
    """Test concurrent component failures"""
    manager = GracefulDegradationManager()

    # Simulate concurrent failures
    tasks = [
        manager.handle_component_failure(f"component_{i}", Exception(f"Failed {i}"))
        for i in range(5)
    ]

    await asyncio.gather(*tasks)

    status = manager.get_degradation_status()
    assert len(status["failed_components"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
