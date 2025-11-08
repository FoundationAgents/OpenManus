"""
Tests for Agent Pool Manager
Tests pool creation, task assignment, load balancing, and metrics persistence
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from app.agents.pool_manager import (
    PoolManager, TaskAssignment, PoolMetrics, PoolAgent,
    LoadBalancingStrategy, TaskComplexity
)
from app.config import SpecializedPoolConfig, PoolManagerSettings
from app.database.database_service import DatabaseService
from app.system_integration.event_bus import EventBus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        yield db_path


@pytest.fixture
async def db_service(temp_db):
    """Create and initialize database service"""
    service = DatabaseService(temp_db)
    await service.initialize()
    yield service
    await service.close()


@pytest.fixture
async def event_bus():
    """Create and start event bus"""
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def pool_manager(db_service, event_bus):
    """Create pool manager with test configuration"""
    manager = PoolManager(db_service, event_bus)
    
    # Create test pools
    pool1 = SpecializedPoolConfig(
        pool_id="test_pool_1",
        name="Test Pool 1",
        size=5,
        priority=100,
        roles=["developer"],
        capabilities=["testing", "coding"]
    )
    
    pool2 = SpecializedPoolConfig(
        pool_id="test_pool_2",
        name="Test Pool 2",
        size=3,
        priority=90,
        roles=["tester"],
        capabilities=["testing", "qa"]
    )
    
    manager.pool_config = PoolManagerSettings(
        enable_pool_manager=True,
        pools=[pool1, pool2],
        load_balancer_strategy="least_loaded",
        rebalance_interval_seconds=10,
        metrics_retention_days=7
    )
    
    # Initialize pools
    await manager.create_pool(pool1)
    await manager.create_pool(pool2)
    
    yield manager
    
    await manager.stop()


@pytest.mark.asyncio
async def test_pool_creation(pool_manager):
    """Test pool creation"""
    pools = pool_manager.pools
    assert len(pools) == 2
    assert "test_pool_1" in pools
    assert "test_pool_2" in pools
    
    pool1_info = pools["test_pool_1"]
    assert pool1_info["config"].name == "Test Pool 1"
    assert pool1_info["config"].size == 5
    assert pool1_info["status"] == "active"


@pytest.mark.asyncio
async def test_add_agent_to_pool(pool_manager):
    """Test adding agents to pools"""
    result = await pool_manager.add_agent_to_pool("test_pool_1", "agent_1", "developer")
    assert result is True
    
    agents = pool_manager.pool_agents["test_pool_1"]
    assert len(agents) == 1
    assert agents[0].agent_id == "agent_1"
    assert agents[0].pool_id == "test_pool_1"
    assert agents[0].agent_role == "developer"


@pytest.mark.asyncio
async def test_add_multiple_agents_to_pool(pool_manager):
    """Test adding multiple agents to a pool"""
    for i in range(5):
        result = await pool_manager.add_agent_to_pool("test_pool_1", f"agent_{i}", "developer")
        assert result is True
    
    agents = pool_manager.pool_agents["test_pool_1"]
    assert len(agents) == 5


@pytest.mark.asyncio
async def test_duplicate_agent_rejection(pool_manager):
    """Test that adding duplicate agents is rejected"""
    result1 = await pool_manager.add_agent_to_pool("test_pool_1", "agent_dup", "developer")
    assert result1 is True
    
    result2 = await pool_manager.add_agent_to_pool("test_pool_1", "agent_dup", "developer")
    assert result2 is False
    
    agents = pool_manager.pool_agents["test_pool_1"]
    assert len(agents) == 1


@pytest.mark.asyncio
async def test_task_assignment_least_loaded_strategy(pool_manager):
    """Test task assignment with least_loaded strategy"""
    # Add agents to pools
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    await pool_manager.add_agent_to_pool("test_pool_2", "agent_2")
    
    # Assign first task - should go to least loaded pool
    task1 = await pool_manager.assign_task(
        "task_1",
        task_type="general",
        priority=2,
        complexity=TaskComplexity.MEDIUM
    )
    assert task1 is not None
    
    # Both pools should have one task, so next task goes to first available
    task2 = await pool_manager.assign_task(
        "task_2",
        task_type="general",
        priority=2,
        complexity=TaskComplexity.MEDIUM
    )
    assert task2 is not None


@pytest.mark.asyncio
async def test_task_assignment_target_pool(pool_manager):
    """Test task assignment to specific target pool"""
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    await pool_manager.add_agent_to_pool("test_pool_2", "agent_2")
    
    # Assign task to specific pool
    task = await pool_manager.assign_task(
        "task_1",
        task_type="testing",
        priority=3,
        complexity=TaskComplexity.HIGH,
        target_pool_id="test_pool_2"
    )
    
    assert task is not None
    assert task.pool_id == "test_pool_2"
    assert task.task_type == "testing"
    assert task.priority == 3
    assert task.complexity == TaskComplexity.HIGH


@pytest.mark.asyncio
async def test_pool_metrics_tracking(pool_manager):
    """Test pool metrics tracking"""
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    
    metrics = pool_manager.get_pool_metrics("test_pool_1")
    assert metrics is not None
    assert metrics.pool_id == "test_pool_1"
    
    # Assign tasks and check queue length
    for i in range(3):
        await pool_manager.assign_task(f"task_{i}", target_pool_id="test_pool_1")
    
    pool_manager._update_pool_metrics("test_pool_1")
    metrics = pool_manager.get_pool_metrics("test_pool_1")
    assert metrics.queue_length == 3


@pytest.mark.asyncio
async def test_pool_status_retrieval(pool_manager):
    """Test getting pool status"""
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_2")
    
    for i in range(2):
        await pool_manager.assign_task(f"task_{i}", target_pool_id="test_pool_1")
    
    status = await pool_manager.get_pool_status("test_pool_1")
    assert status is not None
    assert status["pool_id"] == "test_pool_1"
    assert status["name"] == "Test Pool 1"
    assert status["status"] == "active"
    assert status["size"] == 5
    assert status["agents"] == 2
    assert status["queued_tasks"] == 2


@pytest.mark.asyncio
async def test_all_pool_status(pool_manager):
    """Test getting status of all pools"""
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    await pool_manager.add_agent_to_pool("test_pool_2", "agent_2")
    
    all_status = await pool_manager.get_all_pool_status()
    assert len(all_status) == 2
    assert "test_pool_1" in all_status
    assert "test_pool_2" in all_status


@pytest.mark.asyncio
async def test_suspend_resume_pool(pool_manager):
    """Test suspending and resuming pools"""
    # Suspend pool
    result = await pool_manager.suspend_pool("test_pool_1", "Testing suspension")
    assert result is True
    
    status = await pool_manager.get_pool_status("test_pool_1")
    assert status["status"] == "suspended"
    
    # Resume pool
    result = await pool_manager.resume_pool("test_pool_1")
    assert result is True
    
    status = await pool_manager.get_pool_status("test_pool_1")
    assert status["status"] == "active"


@pytest.mark.asyncio
async def test_task_status_update(pool_manager):
    """Test updating task status"""
    await pool_manager.assign_task("task_1", target_pool_id="test_pool_1")
    
    # Update task status to completed
    await pool_manager.update_task_status(
        "task_1",
        status="completed",
        result="Test result"
    )
    
    # Verify in local task queue
    found = False
    for task in pool_manager.task_queue["test_pool_1"]:
        if task.task_id == "task_1":
            assert task.status == "completed"
            assert task.result == "Test result"
            found = True
    
    assert found


@pytest.mark.asyncio
async def test_load_balancing_priority_based_strategy():
    """Test priority-based load balancing strategy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db_service = DatabaseService(db_path)
        await db_service.initialize()
        
        pool_manager = PoolManager(db_service)
        
        # Create pools with different priorities
        high_priority = SpecializedPoolConfig(
            pool_id="high_priority",
            name="High Priority Pool",
            size=2,
            priority=200,
            roles=["developer"]
        )
        
        low_priority = SpecializedPoolConfig(
            pool_id="low_priority",
            name="Low Priority Pool",
            size=10,
            priority=50,
            roles=["tester"]
        )
        
        pool_manager.pool_config = PoolManagerSettings(
            enable_pool_manager=True,
            pools=[high_priority, low_priority],
            load_balancer_strategy="priority_based"
        )
        
        await pool_manager.create_pool(high_priority)
        await pool_manager.create_pool(low_priority)
        
        # Add agents
        await pool_manager.add_agent_to_pool("high_priority", "agent_h1")
        await pool_manager.add_agent_to_pool("low_priority", "agent_l1")
        
        # Assign tasks - with priority_based, should prefer higher priority pool when not saturated
        task1 = await pool_manager.assign_task("task_1")
        assert task1 is not None
        
        await pool_manager.stop()
        await db_service.close()


@pytest.mark.asyncio
async def test_pool_overload_detection(pool_manager):
    """Test pool overload detection and event emission"""
    pool_manager.pool_config.rebalance_interval_seconds = 1
    await pool_manager.start()
    
    # Add agents
    await pool_manager.add_agent_to_pool("test_pool_1", "agent_1")
    
    # Add many tasks to overload pool
    for i in range(10):
        await pool_manager.assign_task(f"task_{i}", target_pool_id="test_pool_1")
    
    # Trigger rebalance
    await pool_manager._rebalance_tasks()
    
    # Pool should be detected as overloaded
    metrics = pool_manager.get_pool_metrics("test_pool_1")
    assert metrics.queue_length == 10


@pytest.mark.asyncio
async def test_configuration_loading_default_pools():
    """Test loading default pools from configuration"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db_service = DatabaseService(db_path)
        await db_service.initialize()
        
        pool_manager = PoolManager(db_service)
        pool_manager.pool_config = PoolManagerSettings(
            enable_pool_manager=True,
            pools=[]  # Empty - should trigger default pool creation
        )
        
        # Initialize with default pools
        pool_manager._initialize_default_pools()
        
        # Check that default pools were created
        assert len(pool_manager.pool_config.pools) > 0
        pool_ids = [p.pool_id for p in pool_manager.pool_config.pools]
        assert "main" in pool_ids
        assert "gamedev" in pool_ids
        assert "network" in pool_ids
        
        await db_service.close()


@pytest.mark.asyncio
async def test_simulation_load_balancing():
    """Simulation test: verify load balancing under varying loads"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db_service = DatabaseService(db_path)
        await db_service.initialize()
        
        bus = EventBus()
        await bus.start()
        
        pool_manager = PoolManager(db_service, bus)
        
        # Create three pools with different sizes
        pools_config = [
            SpecializedPoolConfig(
                pool_id=f"pool_{i}",
                name=f"Pool {i}",
                size=5 + i*2,  # Increasing sizes
                priority=100 - i*10,
                roles=["developer"]
            )
            for i in range(3)
        ]
        
        pool_manager.pool_config = PoolManagerSettings(
            enable_pool_manager=True,
            pools=pools_config,
            load_balancer_strategy="least_loaded"
        )
        
        # Create pools
        for pool_config in pools_config:
            await pool_manager.create_pool(pool_config)
        
        # Add agents to each pool
        for pool_id, agents_count in [("pool_0", 5), ("pool_1", 7), ("pool_2", 9)]:
            for i in range(agents_count):
                await pool_manager.add_agent_to_pool(pool_id, f"{pool_id}_agent_{i}")
        
        # Assign 20 tasks
        for i in range(20):
            task = await pool_manager.assign_task(f"task_{i}")
            assert task is not None
        
        # Check load distribution
        queue_lengths = {}
        for pool_id in ["pool_0", "pool_1", "pool_2"]:
            queue_lengths[pool_id] = len(pool_manager.task_queue[pool_id])
        
        # Load should be distributed across pools
        total_tasks = sum(queue_lengths.values())
        assert total_tasks == 20
        
        # No single pool should have all tasks
        assert max(queue_lengths.values()) < 20
        
        await pool_manager.stop()
        await bus.stop()
        await db_service.close()


@pytest.mark.asyncio
async def test_invalid_pool_operations(pool_manager):
    """Test operations on non-existent pools"""
    # Try to add agent to non-existent pool
    result = await pool_manager.add_agent_to_pool("nonexistent", "agent_1")
    assert result is False
    
    # Try to get status of non-existent pool
    status = await pool_manager.get_pool_status("nonexistent")
    assert status is None
    
    # Try to suspend non-existent pool
    result = await pool_manager.suspend_pool("nonexistent")
    assert result is False
