"""
Legacy Agent Management Module

DEPRECATED: This module is maintained for backward compatibility only.
All code has been consolidated into app.agent (singular).

New code should import directly from app.agent instead:
    from app.agent import PoolManager, AgentResilienceManager
    from app.agent.resilience import AgentHealthMonitor

This module will be removed in a future version.
"""

import warnings

# Redirect all imports to consolidated location in app.agent
from app.agent.resilience import (
    AgentHealthMonitor,
    AgentResilienceManager,
    AgentTelemetry,
    HealthStatus,
    ResilienceEvent,
    ResilienceConfig,
    AgentFactory
)

from app.agent.pool_manager import (
    PoolManager,
    TaskAssignment,
    PoolMetrics,
    PoolAgent,
    LoadBalancingStrategy,
    TaskComplexity,
    get_pool_manager
)

warnings.warn(
    "app.agents is deprecated. Use app.agent instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "AgentHealthMonitor",
    "AgentResilienceManager", 
    "AgentTelemetry",
    "HealthStatus",
    "ResilienceEvent",
    "ResilienceConfig",
    "AgentFactory",
    "PoolManager",
    "TaskAssignment",
    "PoolMetrics",
    "PoolAgent",
    "LoadBalancingStrategy",
    "TaskComplexity",
    "get_pool_manager"
]
