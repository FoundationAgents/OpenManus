"""
Agent Pool Manager
Manages specialized agent pools (Main, GameDev, ReverseEngineering, LowLevel, Network)
with dynamic load balancing and metrics persistence.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from threading import RLock

import aiosqlite
from pydantic import BaseModel

from app.logger import logger
from app.config import config, SpecializedPoolConfig, PoolManagerSettings
from app.database.database_service import DatabaseService

# Lazy import to avoid circular dependencies
EventBus = None  # type: ignore


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    PRIORITY_BASED = "priority_based"


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskAssignment:
    """Represents a task assignment to a pool"""
    task_id: str
    pool_id: str
    assigned_agent_id: Optional[str] = None
    task_type: str = "general"
    priority: int = 2
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    status: str = "pending"
    assigned_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PoolMetrics:
    """Pool performance metrics"""
    pool_id: str
    queue_length: int = 0
    active_agents: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 1.0
    avg_task_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PoolAgent:
    """Represents an agent in a pool"""
    agent_id: str
    pool_id: str
    agent_role: Optional[str] = None
    status: str = "idle"
    current_task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class PoolManager:
    """Manages specialized agent pools with load balancing"""
    
    def __init__(self, db_service: DatabaseService, event_bus: Optional["EventBus"] = None):
        self.db_service = db_service
        self.event_bus = event_bus
        self.pools: Dict[str, Dict[str, Any]] = {}
        self.pool_agents: Dict[str, List[PoolAgent]] = {}
        self.task_queue: Dict[str, List[TaskAssignment]] = {}
        self.metrics: Dict[str, PoolMetrics] = {}
        self.pool_config: Optional[PoolManagerSettings] = None
        self._lock = RLock()
        self._running = False
        self._rebalance_task: Optional[asyncio.Task] = None
        self._metrics_cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the pool manager with configured pools"""
        logger.info("Initializing pool manager...")
        
        # Load configuration
        self.pool_config = config.pool_manager
        if not self.pool_config or not self.pool_config.enable_pool_manager:
            logger.info("Pool manager is disabled in configuration")
            return
        
        # Initialize default pools if none configured
        if not self.pool_config.pools:
            self._initialize_default_pools()
        
        # Create pools from configuration
        for pool_config in self.pool_config.pools:
            await self.create_pool(pool_config)
        
        # Start background tasks
        await self.start()
        
        logger.info(f"Pool manager initialized with {len(self.pools)} pools")
    
    def _initialize_default_pools(self):
        """Initialize default specialized pools"""
        default_pools = [
            SpecializedPoolConfig(
                pool_id="main",
                name="Main Agent Pool",
                description="General purpose agent pool",
                size=5,
                priority=100,
                roles=["developer", "architect"],
                capabilities=["general_coding", "architecture"]
            ),
            SpecializedPoolConfig(
                pool_id="gamedev",
                name="GameDev Pool",
                description="Game development specialized pool",
                size=3,
                priority=90,
                roles=["developer"],
                capabilities=["game_development", "graphics", "physics"]
            ),
            SpecializedPoolConfig(
                pool_id="reverse_engineering",
                name="Reverse Engineering Pool",
                description="Reverse engineering specialized pool",
                size=3,
                priority=80,
                roles=["security", "developer"],
                capabilities=["reverse_engineering", "binary_analysis"]
            ),
            SpecializedPoolConfig(
                pool_id="low_level",
                name="Low Level Pool",
                description="Low-level systems programming pool",
                size=3,
                priority=85,
                roles=["developer"],
                capabilities=["systems_programming", "kernel", "c_cpp"]
            ),
            SpecializedPoolConfig(
                pool_id="network",
                name="Network Pool",
                description="Network and infrastructure pool",
                size=4,
                priority=95,
                roles=["devops", "developer"],
                capabilities=["networking", "devops", "infrastructure"]
            ),
        ]
        self.pool_config.pools = default_pools
    
    async def create_pool(self, pool_config: SpecializedPoolConfig) -> bool:
        """Create a new agent pool"""
        with self._lock:
            if pool_config.pool_id in self.pools:
                logger.warning(f"Pool {pool_config.pool_id} already exists")
                return False
            
            # Store pool configuration
            self.pools[pool_config.pool_id] = {
                "config": pool_config,
                "created_at": time.time(),
                "status": "active"
            }
            
            # Initialize empty agent list and task queue
            self.pool_agents[pool_config.pool_id] = []
            self.task_queue[pool_config.pool_id] = []
            self.metrics[pool_config.pool_id] = PoolMetrics(pool_id=pool_config.pool_id)
            
            logger.info(f"Created pool {pool_config.pool_id} with size {pool_config.size}")
        
        # Persist to database
        await self._save_pool_to_db(pool_config)
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit("pool_created", {
                "pool_id": pool_config.pool_id,
                "name": pool_config.name,
                "size": pool_config.size
            })
        
        return True
    
    async def _save_pool_to_db(self, pool_config: SpecializedPoolConfig):
        """Save pool configuration to database"""
        try:
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO agent_pools 
                    (pool_id, name, description, size, priority, capabilities, roles, 
                     max_queue_size, timeout_seconds, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pool_config.pool_id,
                        pool_config.name,
                        pool_config.description,
                        pool_config.size,
                        pool_config.priority,
                        json.dumps(pool_config.capabilities),
                        json.dumps(pool_config.roles),
                        pool_config.max_queue_size,
                        pool_config.timeout_seconds,
                        pool_config.enabled
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save pool to database: {e}")
    
    async def add_agent_to_pool(self, pool_id: str, agent_id: str, agent_role: Optional[str] = None) -> bool:
        """Add an agent to a pool"""
        with self._lock:
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return False
            
            # Check if agent already exists
            for agent in self.pool_agents[pool_id]:
                if agent.agent_id == agent_id:
                    logger.warning(f"Agent {agent_id} already in pool {pool_id}")
                    return False
            
            agent = PoolAgent(agent_id=agent_id, pool_id=pool_id, agent_role=agent_role)
            self.pool_agents[pool_id].append(agent)
            
            logger.info(f"Added agent {agent_id} to pool {pool_id}")
        
        # Persist to database
        await self._save_pool_agent_to_db(agent)
        
        # Update metrics
        self._update_pool_metrics(pool_id)
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit("agent_added_to_pool", {
                "pool_id": pool_id,
                "agent_id": agent_id
            })
        
        return True
    
    async def _save_pool_agent_to_db(self, agent: PoolAgent):
        """Save pool agent to database"""
        try:
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO pool_agents (pool_id, agent_id, agent_role, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (agent.pool_id, agent.agent_id, agent.agent_role, agent.status)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save pool agent to database: {e}")
    
    async def assign_task(self, task_id: str, task_type: str = "general", 
                         priority: int = 2, complexity: TaskComplexity = TaskComplexity.MEDIUM,
                         target_pool_id: Optional[str] = None) -> Optional[TaskAssignment]:
        """Assign a task to an appropriate pool"""
        with self._lock:
            # Select target pool
            pool_id = target_pool_id
            if not pool_id:
                pool_id = await self._select_pool_for_task(task_type, priority, complexity)
            
            if not pool_id or pool_id not in self.pools:
                logger.error(f"No suitable pool found for task {task_id}")
                return None
            
            # Create task assignment
            assignment = TaskAssignment(
                task_id=task_id,
                pool_id=pool_id,
                task_type=task_type,
                priority=priority,
                complexity=complexity
            )
            
            self.task_queue[pool_id].append(assignment)
            logger.info(f"Assigned task {task_id} to pool {pool_id}")
        
        # Persist to database
        await self._save_task_assignment_to_db(assignment)
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit("task_assigned", {
                "task_id": task_id,
                "pool_id": pool_id,
                "complexity": complexity.value
            })
        
        return assignment
    
    async def _select_pool_for_task(self, task_type: str, priority: int, 
                                    complexity: TaskComplexity) -> Optional[str]:
        """Select the best pool for a task based on load balancing strategy"""
        strategy = LoadBalancingStrategy(self.pool_config.load_balancer_strategy)
        
        # Filter enabled pools
        enabled_pools = [
            pool_id for pool_id, pool_info in self.pools.items()
            if pool_info["config"].enabled
        ]
        
        if not enabled_pools:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return enabled_pools[0]  # Simple round-robin
        
        elif strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Select pool with least queue length
            min_queue_pool = min(
                enabled_pools,
                key=lambda p: len(self.task_queue.get(p, []))
            )
            return min_queue_pool
        
        elif strategy == LoadBalancingStrategy.PRIORITY_BASED:
            # Select based on pool priority and current load
            best_pool = None
            best_score = float('inf')
            
            for pool_id in enabled_pools:
                pool_config = self.pools[pool_id]["config"]
                queue_length = len(self.task_queue.get(pool_id, []))
                
                # Lower score is better
                score = (queue_length / pool_config.size) * (1 / pool_config.priority)
                
                if score < best_score:
                    best_score = score
                    best_pool = pool_id
            
            return best_pool
        
        return enabled_pools[0]
    
    async def _save_task_assignment_to_db(self, assignment: TaskAssignment):
        """Save task assignment to database"""
        try:
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO task_assignments 
                    (task_id, pool_id, assigned_agent_id, task_type, priority, complexity, status, assigned_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assignment.task_id,
                        assignment.pool_id,
                        assignment.assigned_agent_id,
                        assignment.task_type,
                        assignment.priority,
                        assignment.complexity.value,
                        assignment.status,
                        assignment.assigned_at
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save task assignment to database: {e}")
    
    def get_pool_metrics(self, pool_id: str) -> Optional[PoolMetrics]:
        """Get metrics for a specific pool"""
        with self._lock:
            return self.metrics.get(pool_id)
    
    def get_all_pool_metrics(self) -> Dict[str, PoolMetrics]:
        """Get metrics for all pools"""
        with self._lock:
            return dict(self.metrics)
    
    def _update_pool_metrics(self, pool_id: str):
        """Update metrics for a pool"""
        with self._lock:
            if pool_id not in self.metrics:
                return
            
            metrics = self.metrics[pool_id]
            metrics.queue_length = len(self.task_queue.get(pool_id, []))
            
            # Count active agents
            active_count = 0
            for agent in self.pool_agents.get(pool_id, []):
                if agent.status == "active" or agent.current_task_id:
                    active_count += 1
            metrics.active_agents = active_count
            metrics.timestamp = time.time()
    
    async def persist_metrics_to_db(self, pool_id: str):
        """Persist current metrics to database"""
        try:
            metrics = self.get_pool_metrics(pool_id)
            if not metrics:
                return
            
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO pool_metrics 
                    (pool_id, queue_length, active_agents, total_tasks, completed_tasks, 
                     failed_tasks, success_rate, avg_task_duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metrics.pool_id,
                        metrics.queue_length,
                        metrics.active_agents,
                        metrics.total_tasks,
                        metrics.completed_tasks,
                        metrics.failed_tasks,
                        metrics.success_rate,
                        metrics.avg_task_duration
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist metrics to database: {e}")
    
    async def update_task_status(self, task_id: str, status: str, 
                                 result: Optional[str] = None, 
                                 error: Optional[str] = None):
        """Update task assignment status"""
        try:
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    """
                    UPDATE task_assignments 
                    SET status = ?, result = ?, error = ?, completed_at = ?
                    WHERE task_id = ?
                    """,
                    (status, result, error, time.time(), task_id)
                )
                await db.commit()
                
                # Update in-memory metrics
                for pool_id, tasks in self.task_queue.items():
                    for task in tasks:
                        if task.task_id == task_id:
                            task.status = status
                            task.result = result
                            task.error = error
                            task.completed_at = time.time()
                            
                            metrics = self.metrics[pool_id]
                            if status == "completed":
                                metrics.completed_tasks += 1
                            elif status == "failed":
                                metrics.failed_tasks += 1
                            
                            if metrics.total_tasks > 0:
                                metrics.success_rate = metrics.completed_tasks / metrics.total_tasks
                            break
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
    
    async def suspend_pool(self, pool_id: str, reason: str = ""):
        """Suspend a pool (for resilience/incident response)"""
        with self._lock:
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return False
            
            self.pools[pool_id]["status"] = "suspended"
            self.pools[pool_id]["config"].enabled = False
            logger.warning(f"Suspended pool {pool_id}: {reason}")
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit("pool_suspended", {
                "pool_id": pool_id,
                "reason": reason
            })
        
        return True
    
    async def resume_pool(self, pool_id: str):
        """Resume a suspended pool"""
        with self._lock:
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return False
            
            self.pools[pool_id]["status"] = "active"
            self.pools[pool_id]["config"].enabled = True
            logger.info(f"Resumed pool {pool_id}")
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit("pool_resumed", {
                "pool_id": pool_id
            })
        
        return True
    
    async def get_pool_status(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a pool"""
        with self._lock:
            if pool_id not in self.pools:
                return None
            
            pool_info = self.pools[pool_id]
            metrics = self.metrics[pool_id]
            
            return {
                "pool_id": pool_id,
                "name": pool_info["config"].name,
                "status": pool_info["status"],
                "size": pool_info["config"].size,
                "agents": len(self.pool_agents.get(pool_id, [])),
                "active_agents": metrics.active_agents,
                "queued_tasks": metrics.queue_length,
                "total_tasks": metrics.total_tasks,
                "completed_tasks": metrics.completed_tasks,
                "failed_tasks": metrics.failed_tasks,
                "success_rate": metrics.success_rate,
                "avg_task_duration": metrics.avg_task_duration,
                "priority": pool_info["config"].priority,
                "capabilities": pool_info["config"].capabilities
            }
    
    async def get_all_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all pools"""
        status_dict = {}
        for pool_id in list(self.pools.keys()):
            status = await self.get_pool_status(pool_id)
            if status:
                status_dict[pool_id] = status
        return status_dict
    
    async def start(self):
        """Start background tasks"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting pool manager background tasks")
        
        # Start rebalance task
        self._rebalance_task = asyncio.create_task(self._rebalance_loop())
        
        # Start metrics cleanup task
        self._metrics_cleanup_task = asyncio.create_task(self._metrics_cleanup_loop())
    
    async def stop(self):
        """Stop background tasks"""
        self._running = False
        logger.info("Stopping pool manager background tasks")
        
        if self._rebalance_task:
            self._rebalance_task.cancel()
            try:
                await self._rebalance_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_cleanup_task:
            self._metrics_cleanup_task.cancel()
            try:
                await self._metrics_cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _rebalance_loop(self):
        """Periodically rebalance tasks across pools"""
        while self._running:
            try:
                await asyncio.sleep(self.pool_config.rebalance_interval_seconds)
                await self._rebalance_tasks()
            except Exception as e:
                logger.error(f"Error in rebalance loop: {e}")
    
    async def _rebalance_tasks(self):
        """Rebalance tasks across pools based on load"""
        with self._lock:
            for pool_id, pool_info in self.pools.items():
                if not pool_info["config"].enabled:
                    continue
                
                metrics = self.metrics[pool_id]
                queue_length = len(self.task_queue.get(pool_id, []))
                
                # Check if pool is saturated
                saturation_ratio = queue_length / pool_info["config"].size
                
                if saturation_ratio > 1.5:  # Pool is overloaded
                    logger.info(f"Pool {pool_id} is overloaded (ratio: {saturation_ratio:.2f})")
                    
                    # Emit event for potential auto-scaling
                    if self.event_bus:
                        await self.event_bus.emit("pool_overloaded", {
                            "pool_id": pool_id,
                            "saturation_ratio": saturation_ratio,
                            "queue_length": queue_length,
                            "pool_size": pool_info["config"].size
                        })
    
    async def _metrics_cleanup_loop(self):
        """Periodically clean old metrics from database"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                await self._cleanup_old_metrics()
            except Exception as e:
                logger.error(f"Error in metrics cleanup loop: {e}")
    
    async def _cleanup_old_metrics(self):
        """Delete metrics older than retention period"""
        if not self.pool_config:
            return
        
        try:
            retention_date = datetime.now() - timedelta(days=self.pool_config.metrics_retention_days)
            
            async with await self.db_service.get_connection() as db:
                await db.execute(
                    "DELETE FROM pool_metrics WHERE timestamp < ?",
                    (retention_date.isoformat(),)
                )
                await db.commit()
                logger.debug("Cleaned up old pool metrics")
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")


# Global pool manager instance
_pool_manager: Optional[PoolManager] = None


async def get_pool_manager() -> PoolManager:
    """Get or create the global pool manager instance"""
    global _pool_manager
    
    if _pool_manager is None:
        # Get database service from config
        db_service = DatabaseService()
        await db_service.initialize()
        
        # Get event bus if available (avoiding circular imports)
        event_bus = None
        try:
            if EventBus is not None:
                from app.system_integration.event_bus import EventBus as EventBusClass
                # Try to get existing event bus if available
                try:
                    from app.system_integration.integration_service import integration_service
                    event_bus = integration_service.event_bus if hasattr(integration_service, 'event_bus') else None
                except:
                    pass
        except:
            pass
        
        _pool_manager = PoolManager(db_service, event_bus)
        await _pool_manager.initialize()
    
    return _pool_manager
