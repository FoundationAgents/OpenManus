"""
Tests for enhanced sandbox functionality.

This module tests Guardian validation, resource monitoring,
audit logging, and killswitch functionality.
"""

import asyncio
import pytest
import tempfile
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from app.sandbox.core.sandbox import DockerSandbox, SandboxMetadata
from app.sandbox.core.manager import SandboxManager
from app.sandbox.core.guardian import Guardian, OperationRequest, RiskLevel, SecurityRule
from app.sandbox.core.monitor import ResourceMonitor, ResourceLimits, ResourceAlert, TriggerType
from app.sandbox.core.audit import AuditLogger, OperationType, OperationStatus, AuditLog
from app.sandbox.core.exceptions import SandboxResourceError, SandboxTimeoutError
from app.config import SandboxSettings


@pytest.fixture
def mock_docker_client():
    """Mock Docker client."""
    with patch('app.sandbox.core.sandbox.docker.from_env') as mock_client:
        yield mock_client


@pytest.fixture
def mock_container():
    """Mock Docker container."""
    container = Mock()
    container.id = "test_container_id"
    container.attrs = {
        "State": {
            "Status": "running",
            "StartedAt": "2024-01-01T00:00:00.000000000Z",
            "FinishedAt": "0001-01-01T00:00:00Z",
            "ExitCode": 0,
            "Error": None
        }
    }
    container.stats.return_value = {
        "cpu_stats": {"cpu_usage": {"total_usage": 1000000, "percpu_usage": [500000, 500000]}},
        "precpu_stats": {"cpu_usage": {"total_usage": 900000}, "system_cpu_usage": 2000000},
        "memory_stats": {"usage": 100 * 1024 * 1024},  # 100MB
        "networks": {"eth0": {"tx_bytes": 1000, "rx_bytes": 2000}}
    }
    return container


@pytest.fixture
def guardian():
    """Guardian instance for testing."""
    return Guardian()


@pytest.fixture
def audit_logger(tmp_path):
    """Audit logger with temporary database."""
    return AuditLogger(db_path=tmp_path / "test_audit.db")


@pytest.fixture
def resource_monitor(audit_logger):
    """Resource monitor for testing."""
    return ResourceMonitor(audit_logger=audit_logger)


@pytest.fixture
def sandbox_config():
    """Basic sandbox configuration."""
    return SandboxSettings(
        image="python:3.12-slim",
        memory_limit="512m",
        cpu_limit=1.0,
        timeout=60,
        network_enabled=False
    )


@pytest.fixture
def resource_limits():
    """Resource limits for testing."""
    return ResourceLimits(
        cpu_percent=80.0,
        memory_mb=512,
        disk_mb=1024,
        timeout_seconds=60
    )


class TestGuardian:
    """Test Guardian validation system."""

    @pytest.mark.asyncio
    async def test_approve_agent(self, guardian):
        """Test agent approval."""
        agent_id = "test_agent"
        
        # Initially not approved
        request = OperationRequest(agent_id=agent_id, operation="test")
        decision = await guardian.validate_operation(request)
        assert not decision.approved
        assert "not approved" in decision.reason.lower()
        
        # Approve agent
        guardian.approve_agent(agent_id)
        
        # Now approved
        decision = await guardian.validate_operation(request)
        assert decision.approved

    @pytest.mark.asyncio
    async def test_dangerous_command_blocking(self, guardian):
        """Test blocking of dangerous commands."""
        guardian.approve_agent("test_agent")
        
        dangerous_commands = [
            "rm -rf /",
            "shutdown -h now",
            "sudo su",
            "format /dev/sda1"
        ]
        
        for cmd in dangerous_commands:
            request = OperationRequest(
                agent_id="test_agent",
                operation="command_execute",
                command=cmd
            )
            decision = await guardian.validate_operation(request)
            assert not decision.approved
            assert decision.risk_level == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_safe_command_approval(self, guardian):
        """Test approval of safe commands."""
        guardian.approve_agent("test_agent")
        
        safe_commands = [
            "python script.py",
            "ls -la",
            "pip install requests",
            "echo 'hello world'"
        ]
        
        for cmd in safe_commands:
            request = OperationRequest(
                agent_id="test_agent",
                operation="command_execute",
                command=cmd
            )
            decision = await guardian.validate_operation(request)
            assert decision.approved
            assert decision.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

    @pytest.mark.asyncio
    async def test_volume_acl_validation(self, guardian):
        """Test volume ACL validation."""
        from app.sandbox.core.guardian import VolumeACL, AccessMode
        
        # Add restrictive ACL
        acl = VolumeACL(
            host_path="/safe/path",
            container_path="/safe/container",
            mode=AccessMode.READ_ONLY,
            allowed_patterns=[r".*\.py$"],
            blocked_patterns=[r".*\.sh$"]
        )
        guardian.add_volume_acl(acl)
        guardian.approve_agent("test_agent")
        
        # Test allowed binding
        request = OperationRequest(
            agent_id="test_agent",
            operation="sandbox_create",
            volume_bindings={"/safe/path": "/safe/container"}
        )
        decision = await guardian.validate_operation(request)
        assert decision.approved

    def test_security_rules_management(self, guardian):
        """Test security rule management."""
        initial_count = len(guardian.security_rules)
        
        # Add custom rule
        custom_rule = SecurityRule(
            name="test_rule",
            pattern=r"test.*command",
            risk_level=RiskLevel.MEDIUM,
            action="require_approval",
            description="Test rule"
        )
        guardian.security_rules.append(custom_rule)
        
        assert len(guardian.security_rules) == initial_count + 1
        
        # Test rule summary
        summary = guardian.get_security_summary()
        assert summary["total_rules"] == initial_count + 1
        assert "test_rule" in [rule.name for rule in guardian.security_rules]


class TestAuditLogger:
    """Test audit logging system."""

    @pytest.mark.asyncio
    async def test_log_operation(self, audit_logger):
        """Test basic operation logging."""
        log_entry = AuditLog(
            timestamp=time.time(),
            agent_id="test_agent",
            sandbox_id="test_sandbox",
            operation_type=OperationType.COMMAND_EXECUTE,
            status=OperationStatus.SUCCESS,
            details={"command": "echo 'test'", "output": "test"}
        )
        
        await audit_logger.log_operation(log_entry)
        
        # Retrieve and verify
        logs = await audit_logger.get_logs(agent_id="test_agent")
        assert len(logs) == 1
        assert logs[0].agent_id == "test_agent"
        assert logs[0].operation_type == OperationType.COMMAND_EXECUTE
        assert logs[0].status == OperationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_log_filtering(self, audit_logger):
        """Test log filtering capabilities."""
        # Add multiple logs
        operations = [
            (OperationType.SANDBOX_CREATE, OperationStatus.SUCCESS),
            (OperationType.COMMAND_EXECUTE, OperationStatus.SUCCESS),
            (OperationType.COMMAND_EXECUTE, OperationStatus.FAILURE),
            (OperationType.SANDBOX_DELETE, OperationStatus.SUCCESS)
        ]
        
        for i, (op_type, status) in enumerate(operations):
            log = AuditLog(
                timestamp=time.time() + i,
                agent_id="test_agent",
                sandbox_id="test_sandbox",
                operation_type=op_type,
                status=status,
                details={}
            )
            await audit_logger.log_operation(log)
        
        # Test filtering by operation type
        cmd_logs = await audit_logger.get_logs(operation_type=OperationType.COMMAND_EXECUTE)
        assert len(cmd_logs) == 2
        
        # Test filtering by status
        success_logs = await audit_logger.get_logs(status=OperationStatus.SUCCESS)
        assert len(success_logs) == 3

    @pytest.mark.asyncio
    async def test_agent_summary(self, audit_logger):
        """Test agent activity summary."""
        # Add logs for an agent
        for i in range(10):
            log = AuditLog(
                timestamp=time.time(),
                agent_id="test_agent",
                sandbox_id="test_sandbox",
                operation_type=OperationType.COMMAND_EXECUTE,
                status=OperationStatus.SUCCESS if i < 8 else OperationStatus.FAILURE,
                details={},
                duration_ms=1000 + i * 100
            )
            await audit_logger.log_operation(log)
        
        summary = await audit_logger.get_agent_summary("test_agent", days=1)
        
        assert summary["agent_id"] == "test_agent"
        assert summary["total_operations"] == 10
        assert summary["error_count"] == 2
        assert summary["total_duration_ms"] == sum(1000 + i * 100 for i in range(10))

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, audit_logger):
        """Test cleanup of old logs."""
        # Add old log
        old_timestamp = time.time() - (31 * 24 * 3600)  # 31 days ago
        old_log = AuditLog(
            timestamp=old_timestamp,
            agent_id="test_agent",
            sandbox_id="test_sandbox",
            operation_type=OperationType.COMMAND_EXECUTE,
            status=OperationStatus.SUCCESS,
            details={}
        )
        await audit_logger.log_operation(old_log)
        
        # Add recent log
        recent_log = AuditLog(
            timestamp=time.time(),
            agent_id="test_agent",
            sandbox_id="test_sandbox",
            operation_type=OperationType.COMMAND_EXECUTE,
            status=OperationStatus.SUCCESS,
            details={}
        )
        await audit_logger.log_operation(recent_log)
        
        # Cleanup old logs (keep 30 days)
        deleted_count = await audit_logger.cleanup_old_logs(days_to_keep=30)
        assert deleted_count == 1
        
        # Verify only recent log remains
        logs = await audit_logger.get_logs()
        assert len(logs) == 1
        assert logs[0].timestamp > old_timestamp


class TestResourceMonitor:
    """Test resource monitoring system."""

    def test_monitor_initialization(self, resource_monitor):
        """Test monitor initialization."""
        assert not resource_monitor._is_running
        assert len(resource_monitor._monitored_sandboxes) == 0
        
        stats = resource_monitor.get_monitoring_stats()
        assert stats["is_running"] is False
        assert stats["monitored_sandboxes"] == 0

    def test_add_remove_sandbox(self, resource_monitor, mock_container):
        """Test adding and removing sandboxes."""
        sandbox_id = "test_sandbox"
        agent_id = "test_agent"
        limits = ResourceLimits(cpu_percent=80.0, memory_mb=512, timeout_seconds=60)
        
        # Add sandbox
        resource_monitor.add_sandbox(sandbox_id, mock_container, agent_id, limits)
        assert len(resource_monitor._monitored_sandboxes) == 1
        assert sandbox_id in resource_monitor._monitored_sandboxes
        
        sandbox_info = resource_monitor._monitored_sandboxes[sandbox_id]
        assert sandbox_info["agent_id"] == agent_id
        assert sandbox_info["limits"] == limits
        assert not sandbox_info["kill_triggered"]
        
        # Remove sandbox
        resource_monitor.remove_sandbox(sandbox_id)
        assert len(resource_monitor._monitored_sandboxes) == 0

    @pytest.mark.asyncio
    async def test_resource_usage_calculation(self, resource_monitor, mock_container):
        """Test resource usage calculation."""
        sandbox_id = "test_sandbox"
        agent_id = "test_agent"
        limits = ResourceLimits()
        
        resource_monitor.add_sandbox(sandbox_id, mock_container, agent_id, limits)
        
        usage = await resource_monitor._get_resource_usage(sandbox_id, resource_monitor._monitored_sandboxes[sandbox_id])
        
        assert usage is not None
        assert usage.cpu_percent >= 0
        assert usage.memory_mb > 0
        assert usage.disk_mb >= 0

    @pytest.mark.asyncio
    async def test_killswitch_trigger(self, resource_monitor, mock_container):
        """Test killswitch triggering."""
        sandbox_id = "test_sandbox"
        agent_id = "test_agent"
        limits = ResourceLimits(timeout_seconds=1)  # Very short timeout
        
        # Mock container kill method
        mock_container.kill = Mock()
        
        resource_monitor.add_sandbox(sandbox_id, mock_container, agent_id, limits)
        
        # Simulate timeout by setting old start time
        sandbox_info = resource_monitor._monitored_sandboxes[sandbox_id]
        sandbox_info["start_time"] = time.time() - 10  # 10 seconds ago
        
        # Check resources (should trigger killswitch)
        await resource_monitor._check_all_sandboxes()
        
        # Verify killswitch was triggered
        assert sandbox_info["kill_triggered"]
        mock_container.kill.assert_called_once()

    def test_killswitch_handlers(self, resource_monitor):
        """Test custom killswitch handlers."""
        handler_called = False
        
        def test_handler(sandbox_id, alert):
            nonlocal handler_called
            handler_called = True
            assert sandbox_id == "test_sandbox"
            assert alert.trigger_type == TriggerType.CPU_LIMIT
        
        resource_monitor.add_killswitch_handler(test_handler)
        assert len(resource_monitor._killswitch_handlers) == 1


class TestEnhancedSandbox:
    """Test enhanced DockerSandbox functionality."""

    @pytest.mark.asyncio
    async def test_sandbox_creation_with_guardian(self, sandbox_config, guardian, audit_logger, mock_docker_client):
        """Test sandbox creation with Guardian validation."""
        # Setup mocks
        mock_container = Mock()
        mock_container.id = "test_container"
        mock_docker_client.return_value.api.create_container.return_value = {"Id": "test_container"}
        mock_docker_client.return_value.containers.get.return_value = mock_container
        mock_docker_client.return_value.api.create_host_config.return_value = {}
        
        # Approve agent
        guardian.approve_agent("test_agent")
        
        # Create sandbox
        sandbox = DockerSandbox(
            config=sandbox_config,
            agent_id="test_agent",
            guardian=guardian,
            audit_logger=audit_logger
        )
        
        with patch('app.sandbox.core.sandbox.AsyncDockerizedTerminal') as mock_terminal:
            mock_terminal.return_value.init = AsyncMock()
            
            await sandbox.create()
            
            assert sandbox.sandbox_id is not None
            assert sandbox.metadata.agent_id == "test_agent"
            assert sandbox.container is not None

    @pytest.mark.asyncio
    async def test_guardian_denial(self, sandbox_config, guardian, audit_logger, mock_docker_client):
        """Test sandbox creation denial by Guardian."""
        # Don't approve agent
        sandbox = DockerSandbox(
            config=sandbox_config,
            agent_id="unapproved_agent",
            guardian=guardian,
            audit_logger=audit_logger
        )
        
        with pytest.raises(SandboxResourceError, match="Guardian denied"):
            await sandbox.create()

    @pytest.mark.asyncio
    async def test_command_execution_with_validation(self, sandbox_config, guardian, audit_logger):
        """Test command execution with Guardian validation."""
        guardian.approve_agent("test_agent")
        
        sandbox = DockerSandbox(
            config=sandbox_config,
            agent_id="test_agent",
            guardian=guardian,
            audit_logger=audit_logger
        )
        
        # Mock terminal
        mock_terminal = Mock()
        mock_terminal.run_command = AsyncMock(return_value="test output")
        sandbox.terminal = mock_terminal
        
        # Execute safe command
        result = await sandbox.run_command("echo 'test'")
        assert result == "test output"
        mock_terminal.run_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_dangerous_command_blocking(self, sandbox_config, guardian, audit_logger):
        """Test blocking of dangerous commands."""
        guardian.approve_agent("test_agent")
        
        sandbox = DockerSandbox(
            config=sandbox_config,
            agent_id="test_agent",
            guardian=guardian,
            audit_logger=audit_logger
        )
        
        sandbox.terminal = Mock()
        
        # Try dangerous command
        with pytest.raises(SandboxResourceError, match="Guardian denied"):
            await sandbox.run_command("rm -rf /")

    def test_sandbox_status(self, sandbox_config):
        """Test sandbox status reporting."""
        sandbox = DockerSandbox(
            config=sandbox_config,
            agent_id="test_agent",
            tags={"environment": "test"}
        )
        
        status = sandbox.get_status()
        
        assert status["sandbox_id"] == sandbox.sandbox_id
        assert status["agent_id"] == "test_agent"
        assert status["config"]["image"] == sandbox_config.image
        assert status["resource_limits"]["timeout_seconds"] == sandbox_config.timeout
        assert status["tags"]["environment"] == "test"


class TestEnhancedSandboxManager:
    """Test enhanced SandboxManager functionality."""

    @pytest.mark.asyncio
    async def test_agent_sandbox_tracking(self, sandbox_config, guardian, audit_logger):
        """Test tracking of agent-sandbox relationships."""
        manager = SandboxManager(
            max_sandboxes=10,
            guardian=guardian,
            audit_logger=audit_logger,
            auto_start_monitoring=False
        )
        
        with patch('app.sandbox.core.manager.DockerSandbox') as mock_sandbox_class:
            mock_sandbox = Mock()
            mock_sandbox.sandbox_id = "test_sandbox_1"
            mock_sandbox.metadata.agent_id = "test_agent"
            mock_sandbox.create = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox
            
            # Create sandbox for agent
            sandbox_id = await manager.create_sandbox(
                config=sandbox_config,
                agent_id="test_agent"
            )
            
            assert sandbox_id == "test_sandbox_1"
            assert "test_agent" in manager._agent_sandboxes
            assert sandbox_id in manager._agent_sandboxes["test_agent"]
            
            # Get agent sandboxes
            agent_sandboxes = await manager.get_agent_sandboxes("test_agent")
            assert sandbox_id in agent_sandboxes

    @pytest.mark.asyncio
    async def test_kill_agent_sandboxes(self, sandbox_config, guardian, audit_logger):
        """Test killing all sandboxes for an agent."""
        manager = SandboxManager(
            max_sandboxes=10,
            guardian=guardian,
            audit_logger=audit_logger,
            auto_start_monitoring=False
        )
        
        with patch('app.sandbox.core.manager.DockerSandbox') as mock_sandbox_class:
            # Create multiple sandboxes
            sandbox_ids = []
            for i in range(3):
                mock_sandbox = Mock()
                sandbox_id = f"test_sandbox_{i}"
                mock_sandbox.sandbox_id = sandbox_id
                mock_sandbox.metadata.agent_id = "test_agent"
                mock_sandbox.create = AsyncMock()
                mock_sandbox.cleanup = AsyncMock()
                mock_sandbox_class.return_value = mock_sandbox
                
                sid = await manager.create_sandbox(
                    config=sandbox_config,
                    agent_id="test_agent"
                )
                sandbox_ids.append(sid)
                manager._sandboxes[sid] = mock_sandbox
            
            # Kill all agent sandboxes
            killed_count = await manager.kill_agent_sandboxes("test_agent")
            assert killed_count == 3
            assert "test_agent" not in manager._agent_sandboxes
            
            # Verify cleanup was called
            for mock_sandbox in manager._sandboxes.values():
                mock_sandbox.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhanced_statistics(self, sandbox_config, guardian, audit_logger):
        """Test enhanced statistics reporting."""
        manager = SandboxManager(
            max_sandboxes=10,
            guardian=guardian,
            audit_logger=audit_logger,
            auto_start_monitoring=False
        )
        
        with patch('app.sandbox.core.manager.DockerSandbox') as mock_sandbox_class:
            mock_sandbox = Mock()
            mock_sandbox.sandbox_id = "test_sandbox"
            mock_sandbox.metadata.agent_id = "test_agent"
            mock_sandbox.create = AsyncMock()
            mock_sandbox.get_metrics = AsyncMock(return_value={"cpu": 50.0})
            mock_sandbox_class.return_value = mock_sandbox
            
            await manager.create_sandbox(
                config=sandbox_config,
                agent_id="test_agent"
            )
            
            stats = manager.get_stats()
            
            assert "total_agents" in stats
            assert "agent_sandbox_counts" in stats
            assert "guardian" in stats
            assert "monitoring" in stats
            assert stats["total_agents"] == 1
            assert stats["agent_sandbox_counts"]["test_agent"] == 1


class TestIntegration:
    """Integration tests for the complete enhanced sandbox system."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_monitoring(self, sandbox_config, tmp_path):
        """Test complete sandbox lifecycle with all features."""
        audit_logger = AuditLogger(db_path=tmp_path / "integration_test.db")
        guardian = Guardian()
        monitor = ResourceMonitor(audit_logger=audit_logger)
        
        # Approve agent
        guardian.approve_agent("integration_agent")
        
        # Create manager
        manager = SandboxManager(
            guardian=guardian,
            monitor=monitor,
            audit_logger=audit_logger,
            auto_start_monitoring=False
        )
        
        with patch('app.sandbox.core.manager.DockerSandbox') as mock_sandbox_class:
            mock_sandbox = Mock()
            mock_sandbox.sandbox_id = "integration_sandbox"
            mock_sandbox.metadata.agent_id = "integration_agent"
            mock_sandbox.create = AsyncMock()
            mock_sandbox.run_command = AsyncMock(return_value="success")
            mock_sandbox.cleanup = AsyncMock()
            mock_sandbox.get_metrics = AsyncMock(return_value={
                "uptime_seconds": 60,
                "alerts_count": 0,
                "current_usage": {
                    "cpu_percent": 25.0,
                    "memory_mb": 128
                }
            })
            mock_sandbox_class.return_value = mock_sandbox
            
            # Create sandbox
            sandbox_id = await manager.create_sandbox(
                config=sandbox_config,
                agent_id="integration_agent"
            )
            
            # Execute commands
            await manager.get_sandbox(sandbox_id)
            await mock_sandbox.run_command("echo 'test'")
            
            # Get metrics
            metrics = await manager.get_sandbox_metrics(sandbox_id)
            assert metrics is not None
            assert metrics["uptime_seconds"] == 60
            
            # Get agent metrics
            agent_metrics = await manager.get_agent_metrics("integration_agent")
            assert agent_metrics["total_sandboxes"] == 1
            assert "aggregated_metrics" in agent_metrics
            
            # Cleanup
            await manager.delete_sandbox(sandbox_id)
            
            # Verify audit logs
            logs = await audit_logger.get_logs(agent_id="integration_agent")
            assert len(logs) >= 2  # create + command
            
            # Verify operations
            operations = [log.operation_type for log in logs]
            assert OperationType.SANDBOX_CREATE in operations
            assert OperationType.COMMAND_EXECUTE in operations
            
            await manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])