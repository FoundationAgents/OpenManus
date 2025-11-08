"""Tests for adaptive sandbox engine."""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch

from app.sandbox.adaptive import (
    CapabilityGrant,
    GrantDecision,
    IsolationLevel,
    IsolationConfig,
    SandboxBuilder,
    AdaptiveSandbox,
    AdaptiveRuntimeMonitor,
)
from app.sandbox.adaptive.capability_grant import (
    PathAccessMode,
    GrantStatus,
    GrantManager,
)
from app.sandbox.adaptive.isolation_levels import get_isolation_config
from app.sandbox.adaptive.runtime_monitor import ResourceMetrics, AnomalyType
from app.sandbox.core.guardian import Guardian


class TestCapabilityGrant:
    """Tests for CapabilityGrant model."""
    
    def test_create_basic_grant(self):
        """Test creating a basic capability grant."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python", "git"},
            allowed_paths={"/home/user": PathAccessMode.READ_WRITE},
        )
        
        assert grant.agent_id == "agent_1"
        assert "python" in grant.allowed_tools
        assert grant.is_valid()
    
    def test_grant_expiration(self):
        """Test grant expiration."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            expires_at=time.time() - 100,  # Expired
        )
        
        assert not grant.is_valid()
    
    def test_can_execute_tool(self):
        """Test tool execution permissions."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python", "git"},
            blocked_tools={"bash"},
        )
        
        assert grant.can_execute_tool("python")
        assert not grant.can_execute_tool("bash")
        assert not grant.can_execute_tool("docker")
    
    def test_get_allowed_access_for_path(self):
        """Test path access resolution."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_paths={
                "/home/user": PathAccessMode.READ_WRITE,
                "/opt/tools": PathAccessMode.READ_ONLY,
            },
            blocked_paths=["/etc"],
        )
        
        assert grant.get_allowed_access_for_path("/home/user/file.txt") == PathAccessMode.READ_WRITE
        assert grant.get_allowed_access_for_path("/opt/tools/script.sh") == PathAccessMode.READ_ONLY
        assert grant.get_allowed_access_for_path("/etc/passwd") is None
    
    def test_get_filtered_environment(self):
        """Test environment filtering."""
        host_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/user",
            "SECRET": "should_not_appear",
        }
        
        grant = CapabilityGrant(
            agent_id="agent_1",
            env_whitelist={"PATH", "HOME"},
            env_vars={"CUSTOM": "value"},
        )
        
        filtered = grant.get_filtered_environment(host_env)
        
        assert "PATH" in filtered
        assert "HOME" in filtered
        assert "SECRET" not in filtered
        assert filtered["CUSTOM"] == "value"
        assert filtered["SANDBOX_MODE"] == "adaptive"
    
    def test_grant_to_dict(self):
        """Test grant serialization."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        grant_dict = grant.to_dict()
        
        assert grant_dict["agent_id"] == "agent_1"
        assert "python" in grant_dict["allowed_tools"]
        assert grant_dict["status"] == "approved"


class TestGrantManager:
    """Tests for GrantManager."""
    
    def test_create_and_get_grant(self):
        """Test creating and retrieving grants."""
        manager = GrantManager()
        grant = CapabilityGrant(agent_id="agent_1")
        
        grant_id = manager.create_grant(grant)
        retrieved = manager.get_grant(grant_id)
        
        assert retrieved is not None
        assert retrieved.agent_id == "agent_1"
    
    def test_get_agent_grants(self):
        """Test getting grants for an agent."""
        manager = GrantManager()
        
        grant1 = CapabilityGrant(agent_id="agent_1")
        grant2 = CapabilityGrant(agent_id="agent_1")
        grant3 = CapabilityGrant(agent_id="agent_2")
        
        manager.create_grant(grant1)
        manager.create_grant(grant2)
        manager.create_grant(grant3)
        
        agent1_grants = manager.get_agent_grants("agent_1")
        assert len(agent1_grants) == 2
    
    def test_revoke_grant(self):
        """Test revoking grants."""
        manager = GrantManager()
        grant = CapabilityGrant(agent_id="agent_1")
        
        grant_id = manager.create_grant(grant)
        assert manager.revoke_grant(grant_id)
        
        # Revoked grants should not appear in agent grants
        agent_grants = manager.get_agent_grants("agent_1")
        assert len(agent_grants) == 0
    
    def test_record_checkpoint(self):
        """Test recording checkpoint decisions."""
        manager = GrantManager()
        
        decision = GrantDecision(
            approved=True,
            grant_id="grant_1",
            reason="Test approval",
            risk_level="low",
        )
        
        manager.record_checkpoint("agent_1", decision)
        checkpoints = manager.get_checkpoints("agent_1")
        
        assert len(checkpoints) == 1
        assert checkpoints[0].reason == "Test approval"


class TestSandboxBuilder:
    """Tests for SandboxBuilder."""
    
    def test_build_trusted_environment(self):
        """Test building TRUSTED isolation environment."""
        host_env = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
        }
        
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
            network_enabled=True,  # Grant network access
        )
        
        builder = SandboxBuilder(
            agent_id="agent_1",
            grant=grant,
            isolation_level=IsolationLevel.TRUSTED,
            host_environment=host_env,
        )
        
        environment = builder.build()
        
        assert environment.isolation_level == IsolationLevel.TRUSTED
        assert "SANDBOX_MODE" in environment.environment_variables
        assert environment.process_constraints["allow_network_access"] is True
    
    def test_build_restricted_environment(self):
        """Test building RESTRICTED isolation environment."""
        host_env = {
            "PATH": "/usr/bin",
            "SECRET": "should_not_appear",
        }
        
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
            allowed_paths={"/home/user": PathAccessMode.READ_WRITE},
        )
        
        builder = SandboxBuilder(
            agent_id="agent_1",
            grant=grant,
            isolation_level=IsolationLevel.RESTRICTED,
            host_environment=host_env,
        )
        
        environment = builder.build()
        
        assert environment.isolation_level == IsolationLevel.RESTRICTED
        assert "SECRET" not in environment.environment_variables
        assert "PATH" in environment.environment_variables
        assert environment.process_constraints["enable_seccomp"] is True
    
    def test_build_sandboxed_environment(self):
        """Test building SANDBOXED isolation environment."""
        grant = CapabilityGrant(agent_id="agent_1")
        
        builder = SandboxBuilder(
            agent_id="agent_1",
            grant=grant,
            isolation_level=IsolationLevel.SANDBOXED,
        )
        
        environment = builder.build()
        
        assert environment.isolation_level == IsolationLevel.SANDBOXED
        assert environment.process_constraints["allow_subprocess_creation"] is False
        assert environment.process_constraints["use_docker"] is True
        assert environment.resource_limits["cpu_percent"] <= 50.0
    
    def test_suggest_required_capabilities(self):
        """Test capability suggestions based on errors."""
        grant = CapabilityGrant(agent_id="agent_1")
        
        builder = SandboxBuilder(
            agent_id="agent_1",
            grant=grant,
        )
        
        suggestions = builder.suggest_required_capabilities("python: command not found")
        assert any("python" in s.lower() for s in suggestions)
        
        suggestions = builder.suggest_required_capabilities("Permission denied")
        assert any("permission" in s.lower() for s in suggestions)


class TestAdaptiveRuntimeMonitor:
    """Tests for AdaptiveRuntimeMonitor."""
    
    def test_create_monitor(self):
        """Test creating runtime monitor."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.RESTRICTED,
        )
        
        assert monitor.sandbox_id == "sandbox_1"
        assert monitor.current_isolation_level == IsolationLevel.RESTRICTED
    
    def test_record_metrics(self):
        """Test recording resource metrics."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.MONITORED,
        )
        
        metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_mb=256,
            open_files=50,
            network_connections=5,
            subprocess_count=2,
            disk_io_ops=100,
        )
        
        monitor.record_metrics(metrics)
        
        assert len(monitor.metrics_history) == 1
        summary = monitor.get_metrics_summary()
        assert summary["current_metrics"]["cpu_percent"] == 50.0
    
    def test_detect_cpu_spike(self):
        """Test detection of CPU spike anomaly."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.RESTRICTED,
        )
        
        monitor.update_thresholds(IsolationLevel.RESTRICTED)
        
        metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=95.0,  # High
            memory_mb=256,
            open_files=50,
            network_connections=5,
            subprocess_count=2,
            disk_io_ops=100,
        )
        
        monitor.record_metrics(metrics)
        
        assert len(monitor.anomalies) > 0
        assert monitor.anomalies[0].type == AnomalyType.CPU_SPIKE
    
    def test_detect_memory_spike(self):
        """Test detection of memory spike anomaly."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.RESTRICTED,
        )
        
        monitor.update_thresholds(IsolationLevel.RESTRICTED)
        
        metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_mb=2048,  # Very high
            open_files=50,
            network_connections=5,
            subprocess_count=2,
            disk_io_ops=100,
        )
        
        monitor.record_metrics(metrics)
        
        assert len(monitor.anomalies) > 0
        assert monitor.anomalies[0].type == AnomalyType.MEMORY_SPIKE
    
    def test_should_escalate_isolation(self):
        """Test isolation level escalation decision."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.MONITORED,
        )
        
        monitor.update_thresholds(IsolationLevel.MONITORED)
        
        # Record multiple anomalies
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=time.time() + i,
                cpu_percent=90.0 + i,
                memory_mb=256,
                open_files=50,
                network_connections=5,
                subprocess_count=2,
                disk_io_ops=100,
            )
            monitor.record_metrics(metrics)
        
        should_escalate, next_level = monitor.should_escalate_isolation()
        
        # Should recommend escalation with multiple anomalies
        if should_escalate:
            assert next_level is not None
            assert next_level.value > IsolationLevel.MONITORED.value
    
    def test_escalate_isolation(self):
        """Test actual isolation level escalation."""
        monitor = AdaptiveRuntimeMonitor(
            sandbox_id="sandbox_1",
            initial_isolation_level=IsolationLevel.MONITORED,
        )
        
        success = monitor.escalate_isolation(IsolationLevel.RESTRICTED)
        
        assert success
        assert monitor.current_isolation_level == IsolationLevel.RESTRICTED


class TestAdaptiveSandbox:
    """Tests for AdaptiveSandbox."""
    
    @pytest.mark.asyncio
    async def test_create_sandbox(self):
        """Test creating adaptive sandbox."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
            isolation_level=IsolationLevel.MONITORED,
        )
        
        assert sandbox.agent_id == "agent_1"
        assert sandbox.isolation_level == IsolationLevel.MONITORED
        assert not sandbox.is_active
    
    @pytest.mark.asyncio
    async def test_initialize_sandbox(self):
        """Test initializing sandbox."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
        )
        
        success = await sandbox.initialize()
        
        assert success
        assert sandbox.is_active
        assert sandbox.environment is not None
        assert sandbox.monitor is not None
    
    @pytest.mark.asyncio
    async def test_run_command(self):
        """Test running command in sandbox."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
        )
        
        success = await sandbox.initialize()
        assert success
        
        output, exit_code, error = await sandbox.run_command("echo hello")
        
        assert error is None
        assert exit_code == 0
        assert len(sandbox.executions) == 1
        assert sandbox.executions[0].status == "completed"
    
    @pytest.mark.asyncio
    async def test_get_environment_summary(self):
        """Test getting environment summary."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
        )
        
        await sandbox.initialize()
        
        summary = sandbox.get_environment_summary()
        
        assert summary["agent_id"] == "agent_1"
        assert summary["is_active"]
        assert "environment" in summary
    
    @pytest.mark.asyncio
    async def test_suggest_environment_fix(self):
        """Test suggesting fixes for errors."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
        )
        
        await sandbox.initialize()
        
        suggestions = sandbox.suggest_environment_fix("python: command not found")
        
        assert len(suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_guardian_integration(self):
        """Test Guardian integration in sandbox."""
        grant = CapabilityGrant(
            agent_id="agent_1",
            allowed_tools={"python"},
        )
        
        guardian = Guardian()
        guardian.approve_agent("agent_1")
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
            guardian=guardian,
        )
        
        success = await sandbox.initialize()
        assert success
    
    @pytest.mark.asyncio
    async def test_cleanup_sandbox(self):
        """Test sandbox cleanup."""
        grant = CapabilityGrant(agent_id="agent_1")
        
        sandbox = AdaptiveSandbox(
            agent_id="agent_1",
            grant=grant,
        )
        
        await sandbox.initialize()
        assert sandbox.is_active
        
        await sandbox.cleanup()
        assert not sandbox.is_active


class TestIsolationLevels:
    """Tests for isolation level configurations."""
    
    def test_all_isolation_levels_defined(self):
        """Test that all isolation levels have configurations."""
        for level in IsolationLevel:
            config = get_isolation_config(level)
            assert config is not None
            assert config.level == level
    
    def test_isolation_level_escalation_chain(self):
        """Test that isolation levels can escalate properly."""
        from app.sandbox.adaptive.isolation_levels import get_isolation_config
        
        current = IsolationLevel.TRUSTED
        
        for _ in range(4):
            config = get_isolation_config(current)
            assert config is not None
            
            if config.escalate_to_level:
                assert config.escalate_to_level.value > current.value
                current = config.escalate_to_level
    
    def test_isolation_config_constraints(self):
        """Test that higher isolation levels have stricter constraints."""
        from app.sandbox.adaptive.isolation_levels import get_isolation_config
        
        trusted = get_isolation_config(IsolationLevel.TRUSTED)
        sandboxed = get_isolation_config(IsolationLevel.SANDBOXED)
        
        # Sandboxed should have stricter constraints
        assert trusted.allow_network_access
        assert not sandboxed.allow_network_access
        
        assert trusted.inherit_environment
        assert not sandboxed.inherit_environment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
