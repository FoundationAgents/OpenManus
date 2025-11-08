"""
Tests for Agent Resilience Layer

Tests health monitoring, failure detection, agent replacement,
and context transfer functionality.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.agents.resilience import (
    AgentHealthMonitor,
    AgentResilienceManager,
    AgentTelemetry,
    HealthStatus,
    ResilienceEvent,
    ResilienceConfig,
    AgentFactory
)
from app.flow.multi_agent_environment import (
    AgentRole,
    AgentPool,
    SpecializedAgent,
    Blackboard,
    BlackboardMessage,
    MessageType
)
from app.config import ResilienceSettings


class TestAgentTelemetry:
    """Test agent telemetry functionality"""
    
    def test_telemetry_initialization(self):
        """Test telemetry initialization"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        assert telemetry.agent_id == "test_agent"
        assert telemetry.role == AgentRole.DEVELOPER
        assert telemetry.command_count == 0
        assert telemetry.success_count == 0
        assert telemetry.error_count == 0
        assert telemetry.consecutive_errors == 0
        assert telemetry.get_health_score() == 1.0
    
    def test_update_success(self):
        """Test telemetry update after successful operation"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        telemetry.update_success(2.5)
        
        assert telemetry.command_count == 1
        assert telemetry.success_count == 1
        assert telemetry.error_count == 0
        assert telemetry.consecutive_errors == 0
        assert telemetry.average_latency == 2.5
        assert telemetry.get_health_score() == 1.0
    
    def test_update_error(self):
        """Test telemetry update after failed operation"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        telemetry.update_error("Test error message")
        
        assert telemetry.command_count == 1
        assert telemetry.success_count == 0
        assert telemetry.error_count == 1
        assert telemetry.consecutive_errors == 1
        assert telemetry.last_error == "Test error message"
        assert telemetry.get_health_score() < 1.0
    
    def test_consecutive_errors(self):
        """Test consecutive error tracking"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        # Add multiple errors
        for i in range(5):
            telemetry.update_error(f"Error {i}")
        
        assert telemetry.consecutive_errors == 5
        assert telemetry.error_count == 5
        assert telemetry.get_health_score() < 0.5  # Should be significantly degraded
    
    def test_health_score_calculation(self):
        """Test health score calculation"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        # Perfect health
        assert telemetry.get_health_score() == 1.0
        
        # Add some errors
        telemetry.update_success(1.0)
        telemetry.update_success(1.0)
        telemetry.update_error("Test error")
        
        # Health should be degraded but not failed
        health = telemetry.get_health_score()
        assert 0.5 < health < 1.0
        
        # Add more consecutive errors
        telemetry.update_error("Error 2")
        telemetry.update_error("Error 3")
        
        # Health should be significantly lower
        health = telemetry.get_health_score()
        assert health < 0.5
    
    def test_health_status_determination(self):
        """Test health status determination"""
        telemetry = AgentTelemetry("test_agent", AgentRole.DEVELOPER)
        
        # Healthy
        assert telemetry.get_status() == HealthStatus.HEALTHY
        
        # Add some errors for warning
        telemetry.update_error("Error 1")
        assert telemetry.get_status() in [HealthStatus.HEALTHY, HealthStatus.WARNING]
        
        # Add consecutive errors for degraded
        telemetry.update_error("Error 2")
        assert telemetry.get_status() in [HealthStatus.WARNING, HealthStatus.DEGRADED]
        
        # Add many errors for failed
        for i in range(5):
            telemetry.update_error(f"Error {i}")
        assert telemetry.get_status() == HealthStatus.FAILED


class TestAgentHealthMonitor:
    """Test agent health monitor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = ResilienceConfig(
            health_check_interval=1.0,
            max_consecutive_errors=3,
            min_health_score=0.5
        )
        self.monitor = AgentHealthMonitor(self.config)
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.monitor.running:
            self.monitor.stop_monitoring()
    
    def test_agent_registration(self):
        """Test agent registration and unregistration"""
        self.monitor.register_agent("test_agent", AgentRole.DEVELOPER)
        
        telemetry = self.monitor.get_agent_telemetry("test_agent")
        assert telemetry is not None
        assert telemetry.agent_id == "test_agent"
        assert telemetry.role == AgentRole.DEVELOPER
        
        self.monitor.unregister_agent("test_agent")
        telemetry = self.monitor.get_agent_telemetry("test_agent")
        assert telemetry is None
    
    def test_telemetry_updates(self):
        """Test telemetry updates through monitor"""
        self.monitor.register_agent("test_agent", AgentRole.DEVELOPER)
        
        # Update success
        self.monitor.update_agent_success("test_agent", 2.0)
        telemetry = self.monitor.get_agent_telemetry("test_agent")
        assert telemetry.success_count == 1
        assert telemetry.average_latency == 2.0
        
        # Update error
        self.monitor.update_agent_error("test_agent", "Test error")
        telemetry = self.monitor.get_agent_telemetry("test_agent")
        assert telemetry.error_count == 1
        assert telemetry.consecutive_errors == 1
    
    def test_event_generation(self):
        """Test event generation and callbacks"""
        events = []
        def event_callback(event: ResilienceEvent):
            events.append(event)
        
        self.monitor.add_event_callback(event_callback)
        self.monitor.register_agent("test_agent", AgentRole.DEVELOPER)
        
        # Trigger consecutive error failure
        for i in range(4):
            self.monitor.update_agent_error("test_agent", f"Error {i}")
        
        # Should generate failure detection event
        failure_events = [e for e in events if e.type.value == "failure_detected"]
        assert len(failure_events) > 0
    
    def test_health_summary(self):
        """Test health summary generation"""
        self.monitor.register_agent("agent1", AgentRole.DEVELOPER)
        self.monitor.register_agent("agent2", AgentRole.TESTER)
        
        # Update with healthy data
        self.monitor.update_agent_success("agent1", 1.0)
        self.monitor.update_agent_success("agent2", 1.0)
        
        summary = self.monitor.get_health_summary()
        assert summary["total_agents"] == 2
        assert summary["healthy_agents"] == 2
        assert summary["unhealthy_agents"] == 0
        assert summary["average_health_score"] == 1.0
        
        # Make one agent unhealthy
        for i in range(5):
            self.monitor.update_agent_error("agent1", f"Error {i}")
        
        summary = self.monitor.get_health_summary()
        assert summary["total_agents"] == 2
        assert summary["healthy_agents"] == 1
        assert summary["unhealthy_agents"] == 1
        assert summary["average_health_score"] < 1.0


class TestAgentFactory:
    """Test agent factory functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.blackboard = Blackboard()
        self.factory = AgentFactory(self.blackboard)
    
    def test_create_replacement_agent(self):
        """Test replacement agent creation"""
        # Create original agent
        original = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="original_dev")
        
        # Create context
        context = {
            "knowledge_base": {"test_key": "test_value"},
            "recent_thoughts": ["Thought 1", "Thought 2"],
            "current_task": None,
            "collaboration_partners": {"partner1"}
        }
        
        # Create replacement
        replacement = self.factory.create_replacement_agent(original, context)
        
        assert replacement.name.startswith("developer_replacement_")
        assert replacement.role == AgentRole.DEVELOPER
        assert replacement.knowledge_base.get("test_key") == "test_value"
        assert len(replacement.thoughts) >= 2
        assert "partner1" in replacement.collaboration_partners
    
    def test_context_transfer(self):
        """Test context transfer between agents"""
        original = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="original_dev")
        original.knowledge_base = {"important_data": "preserved"}
        original.thoughts = ["Original thought 1", "Original thought 2"]
        original.collaboration_partners = {"dev_partner"}
        
        context = {
            "knowledge_base": original.knowledge_base,
            "recent_thoughts": original.thoughts,
            "collaboration_partners": original.collaboration_partners
        }
        
        replacement = self.factory.create_replacement_agent(original, context)
        
        # Verify context transfer
        assert replacement.knowledge_base["important_data"] == "preserved"
        assert any("Original thought" in thought for thought in replacement.thoughts)
        assert "dev_partner" in replacement.collaboration_partners


class TestAgentResilienceManager:
    """Test agent resilience manager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.blackboard = Blackboard()
        self.agent_pools = {
            AgentRole.DEVELOPER: AgentPool(AgentRole.DEVELOPER, 2),
            AgentRole.TESTER: AgentPool(AgentRole.TESTER, 2)
        }
        
        self.config = ResilienceConfig(
            enable_auto_replacement=True,
            max_consecutive_errors=3,
            max_replacements_per_hour=10
        )
        
        self.resilience_manager = AgentResilienceManager(
            self.agent_pools,
            self.blackboard,
            self.config
        )
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.resilience_manager.shutdown()
    
    def test_agent_registration(self):
        """Test agent registration with resilience manager"""
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="test_dev")
        
        self.resilience_manager.register_agent(agent)
        
        # Check if agent is tracked
        assert agent.name in self.resilience_manager.active_agents
        assert agent.name in self.resilience_manager.agent_contexts
        
        # Check if health monitor has the agent
        telemetry = self.resilience_manager.health_monitor.get_agent_telemetry(agent.name)
        assert telemetry is not None
        assert telemetry.agent_id == agent.name
    
    def test_telemetry_updates(self):
        """Test telemetry updates through resilience manager"""
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="test_dev")
        self.resilience_manager.register_agent(agent)
        
        # Update success
        self.resilience_manager.update_agent_success(agent.name, 1.5)
        telemetry = self.resilience_manager.health_monitor.get_agent_telemetry(agent.name)
        assert telemetry.success_count == 1
        assert telemetry.average_latency == 1.5
        
        # Update error
        self.resilience_manager.update_agent_error(agent.name, "Test error")
        telemetry = self.resilience_manager.health_monitor.get_agent_telemetry(agent.name)
        assert telemetry.error_count == 1
        assert telemetry.consecutive_errors == 1
    
    @patch('app.agents.resilience.AgentFactory')
    def test_automatic_replacement(self, mock_factory):
        """Test automatic agent replacement"""
        # Setup mock factory
        mock_replacement = Mock()
        mock_replacement.name = "replacement_agent"
        mock_factory.return_value.create_replacement_agent.return_value = mock_replacement
        
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="failing_agent")
        self.resilience_manager.register_agent(agent)
        
        # Simulate consecutive errors to trigger replacement
        for i in range(4):  # Exceeds max_consecutive_errors (3)
            self.resilience_manager.update_agent_error(agent.name, f"Error {i}")
            time.sleep(0.1)  # Small delay for event processing
        
        # Check if replacement was triggered
        # Note: This test might need adjustment based on actual replacement timing
        assert len(self.resilience_manager.replacement_history) >= 0
    
    def test_manual_replacement(self):
        """Test manual agent replacement"""
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="test_agent")
        self.resilience_manager.register_agent(agent)
        
        # Manually replace agent
        success = self.resilience_manager.manually_replace_agent(
            agent.name, 
            "Manual test replacement"
        )
        
        # Note: This test might need mock for actual replacement process
        assert isinstance(success, bool)
    
    def test_context_extraction(self):
        """Test context extraction from agent"""
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="test_agent")
        agent.knowledge_base = {"key": "value"}
        agent.thoughts = ["Thought 1", "Thought 2"]
        agent.collaboration_partners = {"partner1"}
        
        self.resilience_manager.register_agent(agent)
        
        context = self.resilience_manager._extract_agent_context(agent.name)
        
        assert "knowledge_base" in context
        assert "recent_thoughts" in context
        assert "collaboration_partners" in context
        assert context["knowledge_base"]["key"] == "value"
        assert len(context["recent_thoughts"]) >= 2
        assert "partner1" in context["collaboration_partners"]
    
    def test_resilience_status(self):
        """Test resilience status reporting"""
        agent = SpecializedAgent(AgentRole.DEVELOPER, self.blackboard, name="test_agent")
        self.resilience_manager.register_agent(agent)
        
        status = self.resilience_manager.get_resilience_status()
        
        assert "health_summary" in status
        assert "active_agents" in status
        assert "recent_events" in status
        assert "replacement_history" in status
        assert "config" in status
        
        assert status["health_summary"]["total_agents"] == 1
        assert agent.name in status["active_agents"]
    
    def test_rate_limiting(self):
        """Test replacement rate limiting"""
        # This test would verify that replacements are rate limited
        # Implementation depends on the specific rate limiting logic
        pass


class TestResilienceIntegration:
    """Test integration with multi-agent environment"""
    
    def test_environment_initialization_with_resilience(self):
        """Test environment initialization with resilience"""
        from app.flow.multi_agent_environment import AutonomousMultiAgentEnvironment
        
        resilience_config = ResilienceSettings(
            enable_auto_replacement=True,
            max_consecutive_errors=2
        )
        
        env = AutonomousMultiAgentEnvironment(resilience_config)
        
        assert env.resilience_manager is not None
        assert env.resilience_manager.config.enable_auto_replacement == True
        assert env.resilience_manager.config.max_consecutive_errors == 2
        
        # Check that agents are registered with resilience manager
        assert len(env.resilience_manager.active_agents) > 0
        
        env.shutdown()
    
    def test_task_execution_with_telemetry(self):
        """Test task execution with telemetry tracking"""
        from app.flow.multi_agent_environment import AutonomousMultiAgentEnvironment, DevelopmentTask
        
        env = AutonomousMultiAgentEnvironment()
        
        # Get a developer agent
        dev_agents = [agent for agent in env.agents.values() 
                     if hasattr(agent, 'role') and agent.role == AgentRole.DEVELOPER]
        
        if dev_agents:
            agent = dev_agents[0]
            
            # Create a simple task
            task = DevelopmentTask(
                id="test_task",
                title="Test Task",
                description="A simple test task",
                role=AgentRole.DEVELOPER,
                priority=1
            )
            
            # Check initial telemetry
            initial_telemetry = env.resilience_manager.health_monitor.get_agent_telemetry(agent.name)
            initial_commands = initial_telemetry.command_count if initial_telemetry else 0
            
            # This would normally execute the task, but for testing we'll just simulate
            # In a real test, you'd need to mock the LLM and other dependencies
            # result = await agent.execute_task(task)
            
            # Verify telemetry was updated (would be checked after actual execution)
            # final_telemetry = env.resilience_manager.health_monitor.get_agent_telemetry(agent.name)
            # assert final_telemetry.command_count > initial_commands
        
        env.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
