"""Adaptive sandbox engine for dynamic, capability-based execution environments.

This module provides intelligent sandbox construction where agents request specific
tools, paths, and environment variables, and sandboxes are assembled just-in-time
with Guardian validation and dynamic isolation levels.

Key Components:
- AdaptiveSandbox: Dynamically constructed sandbox based on granted capabilities
- SandboxBuilder: Assembles sandbox with environment, volumes, and resource limits
- IsolationLevel: 5 levels of isolation (TRUSTED to ISOLATED)
- RuntimeMonitor: Monitors resource usage and escalates isolation on anomalies
- CapabilityGrant: Defines what capabilities an agent can use

Usage:
    grant = CapabilityGrant(
        agent_id="agent_1",
        allowed_tools=["python", "git"],
        allowed_paths={"/home/user/projects": "rw"},
        env_whitelist=["PATH", "PYTHONPATH"]
    )
    
    builder = SandboxBuilder(agent_id="agent_1", grant=grant)
    sandbox = await builder.build()
    
    result = await sandbox.run_command("python script.py")
"""

from app.sandbox.adaptive.capability_grant import CapabilityGrant, GrantDecision
from app.sandbox.adaptive.isolation_levels import IsolationLevel, IsolationConfig
from app.sandbox.adaptive.builder import SandboxBuilder
from app.sandbox.adaptive.adaptive_sandbox import AdaptiveSandbox
from app.sandbox.adaptive.runtime_monitor import AdaptiveRuntimeMonitor

__all__ = [
    "CapabilityGrant",
    "GrantDecision",
    "IsolationLevel",
    "IsolationConfig",
    "SandboxBuilder",
    "AdaptiveSandbox",
    "AdaptiveRuntimeMonitor",
]
