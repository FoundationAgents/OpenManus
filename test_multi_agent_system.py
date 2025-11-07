"""
Comprehensive Test Suite for Enhanced Multi-Agent Environment
Tests all components of the autonomous development environment
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, patch, AsyncMock
import time
import json
from pathlib import Path

from app.flow.multi_agent_environment import (
    AutonomousMultiAgentEnvironment,
    AgentRole,
    TaskPriority,
    DevelopmentTask,
    Blackboard,
    BlackboardMessage,
    MessageType,
    AgentPool,
    SpecializedAgent
)
from app.flow.enhanced_async_flow import (
    EnhancedAsyncFlow,
    FlowState,
    UserInteraction,
    UserInteractionType
)
from app.flow.specialized_agents import (
    ArchitectAgent,
    DeveloperAgent,
    TesterAgent,
    DevOpsAgent,
    SecurityAgent
)
from app.config import config


class TestBlackboard(unittest.TestCase):
    """Test blackboard communication system"""
    
    def setUp(self):
        self.blackboard = Blackboard()
    
    def test_message_posting(self):
        """Test message posting functionality"""
        message = BlackboardMessage(
            id="test_msg_1",
            type=MessageType.INFO,
            sender="test_agent",
            content="Test message",
            priority=TaskPriority.MEDIUM
        )
        
        self.blackboard.post_message(message)
        
        # Check message is in history
        self.assertEqual(len(self.blackboard.message_history), 1)
        self.assertEqual(self.blackboard.message_history[0].id, "test_msg_1")
    
    def test_message_subscription(self):
        """Test agent subscription to message types"""
        agent_id = "test_agent"
        message_types = [MessageType.TASK, MessageType.RESULT]
        
        self.blackboard.subscribe(agent_id, message_types)
        
        self.assertEqual(self.blackboard.subscriptions[agent_id], set(message_types))
    
    def test_message_filtering(self):
        """Test message filtering for agents"""
        # Post messages of different types
        messages = [
            BlackboardMessage("msg1", MessageType.TASK, "sender1", None, "Task content"),
            BlackboardMessage("msg2", MessageType.RESULT, "sender2", None, "Result content"),
            BlackboardMessage("msg3", MessageType.ERROR, "sender3", None, "Error content")
        ]
        
        for msg in messages:
            self.blackboard.post_message(msg)
        
        # Get only task messages
        task_messages = self.blackboard.get_messages(
            "test_agent", 
            message_types=[MessageType.TASK]
        )
        
        self.assertEqual(len(task_messages), 1)
        self.assertEqual(task_messages[0].type, MessageType.TASK)


class TestAgentPool(unittest.TestCase):
    """Test agent pool management"""
    
    def setUp(self):
        self.pool = AgentPool(AgentRole.DEVELOPER, max_workers=3)
    
    def test_agent_addition(self):
        """Test adding agents to pool"""
        agent_id = "dev_1"
        self.pool.add_agent(agent_id)
        
        self.assertIn(agent_id, self.pool.agents)
        self.assertEqual(self.pool.available_agents.qsize(), 1)
    
    def test_agent_acquisition(self):
        """Test acquiring agents for tasks"""
        # Add agents
        for i in range(3):
            self.pool.add_agent(f"dev_{i+1}")
        
        # Create task
        task = DevelopmentTask(
            id="task_1",
            title="Test Task",
            description="Test description",
            role=AgentRole.DEVELOPER,
            priority=TaskPriority.HIGH
        )
        
        # Acquire agent
        agent_id = self.pool.acquire_agent(task)
        
        self.assertIsNotNone(agent_id)
        self.assertIn(agent_id, self.pool.busy_agents)
        self.assertEqual(self.pool.available_agents.qsize(), 2)
    
    def test_agent_release(self):
        """Test releasing agents back to pool"""
        # Add and acquire agent
        self.pool.add_agent("dev_1")
        task = DevelopmentTask(
            id="task_1",
            title="Test Task",
            description="Test description",
            role=AgentRole.DEVELOPER,
            priority=TaskPriority.HIGH
        )
        agent_id = self.pool.acquire_agent(task)
        
        # Release agent
        self.pool.release_agent(agent_id)
        
        self.assertNotIn(agent_id, self.pool.busy_agents)
        self.assertEqual(self.pool.available_agents.qsize(), 1)


class TestDevelopmentTask(unittest.TestCase):
    """Test development task management"""
    
    def test_task_creation(self):
        """Test task creation and properties"""
        task = DevelopmentTask(
            id="task_1",
            title="Implementation Task",
            description="Implement feature X",
            role=AgentRole.DEVELOPER,
            priority=TaskPriority.HIGH,
            dependencies=["task_0"]
        )
        
        self.assertEqual(task.id, "task_1")
        self.assertEqual(task.role, AgentRole.DEVELOPER)
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertIn("task_0", task.dependencies)
        self.assertEqual(task.status, "pending")
    
    def test_task_serialization(self):
        """Test task to dictionary conversion"""
        task = DevelopmentTask(
            id="task_1",
            title="Test Task",
            description="Test description",
            role=AgentRole.TESTER,
            priority=TaskPriority.MEDIUM
        )
        
        task_dict = task.to_dict()
        
        self.assertEqual(task_dict["id"], "task_1")
        self.assertEqual(task_dict["role"], "tester")
        self.assertEqual(task_dict["priority"], TaskPriority.MEDIUM.value)
        self.assertIsInstance(task_dict["dependencies"], list)


class TestSpecializedAgents(unittest.TestCase):
    """Test specialized agent implementations"""
    
    def setUp(self):
        self.blackboard = Blackboard()
    
    def test_architect_agent_initialization(self):
        """Test architect agent initialization"""
        agent = ArchitectAgent("arch_1", self.blackboard)
        
        self.assertEqual(agent.role, AgentRole.ARCHITECT)
        self.assertEqual(agent.name, "arch_1")
        self.assertIsNotNone(agent.system_prompt)
        self.assertIn("Software Architect", agent.system_prompt)
    
    def test_developer_agent_initialization(self):
        """Test developer agent initialization"""
        agent = DeveloperAgent("dev_1", self.blackboard)
        
        self.assertEqual(agent.role, AgentRole.DEVELOPER)
        self.assertEqual(agent.name, "dev_1")
        self.assertIsNotNone(agent.system_prompt)
        self.assertIn("Senior Software Developer", agent.system_prompt)
    
    def test_thought_addition(self):
        """Test agent thought tracking"""
        agent = ArchitectAgent("arch_1", self.blackboard)
        
        thought = "Considering microservices architecture"
        agent.add_thought(thought)
        
        self.assertIn(thought, agent.thoughts)
        self.assertEqual(len(self.blackboard.message_history), 1)
        self.assertEqual(self.blackboard.message_history[0].type, MessageType.INFO)


class TestAutonomousMultiAgentEnvironment(unittest.TestCase):
    """Test the main multi-agent environment"""
    
    def setUp(self):
        self.env = AutonomousMultiAgentEnvironment()
    
    def test_environment_initialization(self):
        """Test environment initialization"""
        self.assertIsNotNone(self.env.blackboard)
        self.assertIsNotNone(self.env.agent_pools)
        self.assertIsNotNone(self.env.agents)
        
        # Check that all role pools are created
        expected_roles = list(AgentRole)
        for role in expected_roles:
            self.assertIn(role, self.env.agent_pools)
    
    def test_agent_creation(self):
        """Test agent creation and assignment to pools"""
        # Check that agents are created for each pool
        total_agents = 0
        for role, pool in self.env.agent_pools.items():
            total_agents += len(pool.agents)
            self.assertGreater(len(pool.agents), 0)
        
        self.assertGreater(total_agents, 0)
    
    def test_project_status(self):
        """Test project status reporting"""
        status = self.env.get_project_status()
        
        self.assertIn("tasks", status)
        self.assertIn("agent_pools", status)
        self.assertIn("roadmap", status)
        self.assertIn("current_phase", status)
        
        # Check agent pools status
        for role_str, pool_status in status["agent_pools"].items():
            self.assertIn("total_agents", pool_status)
            self.assertIn("available", pool_status)
            self.assertIn("busy", pool_status)


class TestEnhancedAsyncFlow(unittest.TestCase):
    """Test enhanced async flow functionality"""
    
    def setUp(self):
        # Mock agents for testing
        self.agents = {
            "manus": Mock(),
            "data_analysis": Mock()
        }
        self.flow = EnhancedAsyncFlow(agents=self.agents)
    
    def test_flow_initialization(self):
        """Test flow initialization"""
        self.assertEqual(self.flow.flow_state, FlowState.INITIALIZING)
        self.assertIsNotNone(self.flow.multi_agent_env)
        self.assertEqual(len(self.flow.agents), 2)
    
    def test_user_guidance(self):
        """Test user guidance functionality"""
        guidance = "Focus on performance optimization"
        interaction_type = UserInteractionType.GUIDANCE
        
        self.flow.provide_user_guidance(guidance, interaction_type)
        
        self.assertEqual(len(self.flow.user_interactions), 1)
        self.assertEqual(self.flow.user_interactions[0].content, guidance)
        self.assertEqual(self.flow.user_interactions[0].type, interaction_type)
    
    def test_execution_status(self):
        """Test execution status reporting"""
        status = self.flow.get_execution_status()
        
        self.assertIn("flow_state", status)
        self.assertIn("current_project", status)
        self.assertIn("roadmap_progress", status)
        self.assertIn("agent_thoughts", status)
        self.assertIn("user_interactions", status)
        self.assertIn("metrics", status)
        self.assertIn("multi_agent_status", status)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @patch('app.llm.LLM.ask')
    async def test_simple_project_execution(self, mock_llm_ask):
        """Test simple project execution"""
        # Mock LLM responses
        mock_llm_ask.return_value = json.dumps({
            "title": "Test Project",
            "description": "Simple test project",
            "phases": [
                {
                    "name": "planning",
                    "description": "Project planning",
                    "duration_hours": 2,
                    "tasks": ["Plan requirements"],
                    "required_roles": ["product_manager"],
                    "deliverables": ["Requirements document"],
                    "dependencies": []
                }
            ],
            "estimated_duration_hours": 10,
            "resources_required": {"product_manager": 1},
            "success_criteria": ["Requirements documented"],
            "risk_factors": ["Scope creep"]
        })
        
        # Create flow
        agents = {"manus": Mock()}
        flow = EnhancedAsyncFlow(agents=agents)
        
        # Execute simple project
        result = await flow.execute("Create a simple web application")
        
        # Verify execution completed
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertIn("Autonomous Development Environment", result)
    
    def test_configuration_loading(self):
        """Test that new configuration sections are loaded"""
        # Test that configuration has new sections
        self.assertIsNotNone(config.agent_pools)
        self.assertIsNotNone(config.blackboard)
        self.assertIsNotNone(config.interaction)
        self.assertIsNotNone(config.project_management)
        self.assertIsNotNone(config.quality_assurance)
        self.assertIsNotNone(config.deployment)
        self.assertIsNotNone(config.monitoring)
    
    def test_api_configuration(self):
        """Test that API configuration is set correctly"""
        llm_config = config.llm["default"]
        
        self.assertEqual(llm_config.model, "claude-sonnet-4.5")
        self.assertEqual(llm_config.base_url, "https://gpt4free.pro/v1/vibingfox/chat/completions")
        self.assertEqual(llm_config.api_key, "")
        self.assertFalse(llm_config.requires_api_key)


class TestPerformance(unittest.TestCase):
    """Performance and stress tests"""
    
    def test_message_throughput(self):
        """Test blackboard message throughput"""
        blackboard = Blackboard()
        
        start_time = time.time()
        
        # Post many messages
        for i in range(1000):
            message = BlackboardMessage(
                id=f"msg_{i}",
                type=MessageType.INFO,
                sender="perf_test",
                content=f"Message {i}",
                priority=TaskPriority.MEDIUM
            )
            blackboard.post_message(message)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 1000 messages quickly
        self.assertLess(duration, 1.0)
        self.assertEqual(len(blackboard.message_history), 1000)
    
    def test_agent_pool_scalability(self):
        """Test agent pool scalability"""
        pool = AgentPool(AgentRole.DEVELOPER, max_workers=50)
        
        start_time = time.time()
        
        # Add many agents
        for i in range(50):
            pool.add_agent(f"dev_{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 50 agents quickly
        self.assertLess(duration, 0.1)
        self.assertEqual(len(pool.agents), 50)
        self.assertEqual(pool.available_agents.qsize(), 50)


def run_comprehensive_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestBlackboard,
        TestAgentPool,
        TestDevelopmentTask,
        TestSpecializedAgents,
        TestAutonomousMultiAgentEnvironment,
        TestEnhancedAsyncFlow,
        TestIntegration,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    }


if __name__ == "__main__":
    print("🧪 Running Comprehensive Multi-Agent Environment Tests")
    print("=" * 60)
    
    results = run_comprehensive_tests()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Tests Run: {results['tests_run']}")
    print(f"   Failures: {results['failures']}")
    print(f"   Errors: {results['errors']}")
    print(f"   Success Rate: {results['success_rate']:.1f}%")
    
    if results['failures'] == 0 and results['errors'] == 0:
        print("\n✅ All tests passed! The multi-agent environment is ready.")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    print("=" * 60)