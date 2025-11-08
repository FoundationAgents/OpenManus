"""
Unified Agent System - consolidated agent implementations and management.

This module provides:
- Specialized agent implementations (Browser, Calendar, Email, SWE, etc.)
- Agent pool management and load balancing
- Agent resilience, health monitoring, and automatic recovery
- Team learning and work distribution
- Communication orchestration

All agent management has been consolidated from app.agents into this single
module for unified architecture.
"""

# Try to import base agents, but gracefully handle failures
# This allows team management modules to be used independently
try:
    from app.agent.base import BaseAgent
    from app.agent.browser import BrowserAgent
    from app.agent.calendar_agent import CalendarAgent
    from app.agent.communication_orchestrator import CommunicationOrchestrator
    from app.agent.email_agent import EmailAgent
    from app.agent.mcp import MCPAgent
    from app.agent.message_agent import MessageAgent
    from app.agent.react import ReActAgent
    from app.agent.report_agent import ReportAgent
    from app.agent.social_media_agent import SocialMediaAgent
    from app.agent.swe import SWEAgent
    from app.agent.toolcall import ToolCallAgent
    _base_agents_available = True
except ImportError:
    # Base agents unavailable, but team management can still work
    _base_agents_available = False

# Consolidated agent management (from legacy app.agents)
try:
    from app.agent.pool_manager import (
        PoolManager,
        TaskAssignment,
        PoolMetrics,
        PoolAgent,
        LoadBalancingStrategy,
        TaskComplexity,
        get_pool_manager,
    )
    from app.agent.resilience import (
        AgentHealthMonitor,
        AgentResilienceManager,
        AgentTelemetry,
        HealthStatus,
        ResilienceEvent,
        ResilienceConfig,
        AgentFactory,
    )
    _pool_management_available = True
except ImportError:
    _pool_management_available = False


__all__ = []

if _base_agents_available:
    __all__.extend([
        "BaseAgent",
        "BrowserAgent",
        "ReActAgent",
        "SWEAgent",
        "ToolCallAgent",
        "MCPAgent",
        "EmailAgent",
        "MessageAgent",
        "SocialMediaAgent",
        "CalendarAgent",
        "ReportAgent",
        "CommunicationOrchestrator",
    ])

if _pool_management_available:
    __all__.extend([
        "PoolManager",
        "TaskAssignment",
        "PoolMetrics",
        "PoolAgent",
        "LoadBalancingStrategy",
        "TaskComplexity",
        "get_pool_manager",
        "AgentHealthMonitor",
        "AgentResilienceManager",
        "AgentTelemetry",
        "HealthStatus",
        "ResilienceEvent",
        "ResilienceConfig",
        "AgentFactory",
    ])
