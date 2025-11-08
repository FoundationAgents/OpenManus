"""
Unit tests for specialist agents

Tests the domain-specific functionality of:
- GameDevAgent
- ReverseEngineeringAgent
- LowLevelAgent
- NetworkAgent
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time

from app.flow.multi_agent_environment import (
    Blackboard,
    DevelopmentTask,
    AgentRole,
    TaskPriority,
    BlackboardMessage,
    MessageType
)
from app.agent.specialists import (
    GameDevAgent,
    ReverseEngineeringAgent,
    LowLevelAgent,
    NetworkAgent
)


@pytest.fixture
def blackboard():
    """Create a test blackboard"""
    return Blackboard()


@pytest.fixture
def mock_llm():
    """Create a mock LLM"""
    llm = Mock()
    llm.ask = AsyncMock(return_value="Mock LLM response with implementation details")
    return llm


class TestGameDevAgent:
    """Tests for GameDevAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, blackboard):
        """Test GameDevAgent initialization"""
        agent = GameDevAgent("gamedev_001", blackboard)
        
        assert agent.role == AgentRole.GAME_DEV
        assert agent.name == "gamedev_001"
        assert "unity" in agent.game_engines
        assert "unreal" in agent.game_engines
        assert "DirectX" in agent.domain_knowledge["rendering"]
    
    @pytest.mark.asyncio
    async def test_engine_integration_task(self, blackboard, mock_llm):
        """Test game engine integration task handling"""
        agent = GameDevAgent("gamedev_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_001",
            title="Unity Integration",
            description="Set up Unity project with custom rendering pipeline",
            role=AgentRole.GAME_DEV,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_graphics_programming_task(self, blackboard, mock_llm):
        """Test graphics programming task handling"""
        agent = GameDevAgent("gamedev_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_002",
            title="Shader Implementation",
            description="Implement custom shader for water rendering with reflections",
            role=AgentRole.GAME_DEV,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_task_classification(self, blackboard):
        """Test task classification"""
        agent = GameDevAgent("gamedev_001", blackboard)
        
        engine_task = DevelopmentTask(
            id="t1", title="Test", description="Unity engine setup",
            role=AgentRole.GAME_DEV, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(engine_task) == "engine_integration"
        
        graphics_task = DevelopmentTask(
            id="t2", title="Test", description="Implement shader for lighting",
            role=AgentRole.GAME_DEV, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(graphics_task) == "graphics_programming"
        
        performance_task = DevelopmentTask(
            id="t3", title="Test", description="Optimize rendering performance for 60 FPS",
            role=AgentRole.GAME_DEV, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(performance_task) == "performance_optimization"


class TestReverseEngineeringAgent:
    """Tests for ReverseEngineeringAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, blackboard):
        """Test ReverseEngineeringAgent initialization"""
        agent = ReverseEngineeringAgent("reveng_001", blackboard)
        
        assert agent.role == AgentRole.REVERSE_ENGINEERING
        assert agent.name == "reveng_001"
        assert "Ghidra" in agent.analysis_tools["disassemblers"]
        assert "x86" in agent.architectures
        assert agent.sandbox_requirements["isolation"] == "high"
    
    @pytest.mark.asyncio
    async def test_binary_analysis_task(self, blackboard, mock_llm):
        """Test binary analysis task handling"""
        agent = ReverseEngineeringAgent("reveng_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_001",
            title="Binary Analysis",
            description="Analyze binary executable for code structure and functionality",
            role=AgentRole.REVERSE_ENGINEERING,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_security_clearance_check(self, blackboard, mock_llm):
        """Test security clearance verification"""
        agent = ReverseEngineeringAgent("reveng_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_002",
            title="Malware Analysis",
            description="Analyze potential malware sample",
            role=AgentRole.REVERSE_ENGINEERING,
            priority=TaskPriority.CRITICAL
        )
        
        clearance = await agent._verify_security_clearance(task)
        
        assert "approved" in clearance
        assert clearance["approved"] in [True, False]
    
    @pytest.mark.asyncio
    async def test_task_classification(self, blackboard):
        """Test task classification"""
        agent = ReverseEngineeringAgent("reveng_001", blackboard)
        
        binary_task = DevelopmentTask(
            id="t1", title="Test", description="Disassemble binary executable",
            role=AgentRole.REVERSE_ENGINEERING, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(binary_task) == "binary_analysis"
        
        vuln_task = DevelopmentTask(
            id="t2", title="Test", description="Research vulnerability CVE-2024-1234",
            role=AgentRole.REVERSE_ENGINEERING, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(vuln_task) == "vulnerability_research"
        
        malware_task = DevelopmentTask(
            id="t3", title="Test", description="Analyze malware sample for IOCs",
            role=AgentRole.REVERSE_ENGINEERING, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(malware_task) == "malware_analysis"


class TestLowLevelAgent:
    """Tests for LowLevelAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, blackboard):
        """Test LowLevelAgent initialization"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        
        assert agent.role == AgentRole.LOW_LEVEL
        assert agent.name == "lowlevel_001"
        assert "C" in agent.programming_languages
        assert "Assembly" in agent.programming_languages
        assert "x86_64" in agent.architectures
        assert "paging" in agent.domain_knowledge["memory_management"]
    
    @pytest.mark.asyncio
    async def test_kernel_development_task(self, blackboard, mock_llm):
        """Test kernel development task handling"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_001",
            title="Kernel Module Development",
            description="Develop kernel module for device driver",
            role=AgentRole.LOW_LEVEL,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_embedded_systems_task(self, blackboard, mock_llm):
        """Test embedded systems task handling"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_002",
            title="ESP32 Firmware",
            description="Develop firmware for ESP32 microcontroller with WiFi",
            role=AgentRole.LOW_LEVEL,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_task_classification(self, blackboard):
        """Test task classification"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        
        kernel_task = DevelopmentTask(
            id="t1", title="Test", description="Develop kernel subsystem",
            role=AgentRole.LOW_LEVEL, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(kernel_task) == "kernel_development"
        
        embedded_task = DevelopmentTask(
            id="t2", title="Test", description="Program Arduino microcontroller",
            role=AgentRole.LOW_LEVEL, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(embedded_task) == "embedded_systems"
        
        driver_task = DevelopmentTask(
            id="t3", title="Test", description="Write device driver for hardware",
            role=AgentRole.LOW_LEVEL, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(driver_task) == "driver_development"
    
    @pytest.mark.asyncio
    async def test_architecture_detection(self, blackboard):
        """Test target architecture detection"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        
        task_x86 = DevelopmentTask(
            id="t1", title="Test", description="Optimize for x86 architecture",
            role=AgentRole.LOW_LEVEL, priority=TaskPriority.HIGH
        )
        arch = await agent._get_target_architecture(task_x86)
        assert arch == "x86"
        
        task_arm = DevelopmentTask(
            id="t2", title="Test", description="Develop for ARM processor",
            role=AgentRole.LOW_LEVEL, priority=TaskPriority.HIGH
        )
        arch = await agent._get_target_architecture(task_arm)
        assert arch == "ARM"


class TestNetworkAgent:
    """Tests for NetworkAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, blackboard):
        """Test NetworkAgent initialization"""
        agent = NetworkAgent("network_001", blackboard)
        
        assert agent.role == AgentRole.NETWORK
        assert agent.name == "network_001"
        assert "TCP/IP" in agent.protocols
        assert "WebSocket" in agent.protocols
        assert "REST" in agent.api_styles
        assert "HTTPClientWithCaching" in agent.network_toolkit_integration.values()
    
    @pytest.mark.asyncio
    async def test_api_design_task(self, blackboard, mock_llm):
        """Test API design task handling"""
        agent = NetworkAgent("network_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_001",
            title="REST API Design",
            description="Design RESTful API for user management system",
            role=AgentRole.NETWORK,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_protocol_implementation_task(self, blackboard, mock_llm):
        """Test protocol implementation task handling"""
        agent = NetworkAgent("network_001", blackboard)
        agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_002",
            title="WebSocket Implementation",
            description="Implement WebSocket server with real-time messaging",
            role=AgentRole.NETWORK,
            priority=TaskPriority.HIGH
        )
        
        result = await agent._execute_role_specific_task(task)
        
        assert "completed" in result.lower()
        assert mock_llm.ask.called
    
    @pytest.mark.asyncio
    async def test_task_classification(self, blackboard):
        """Test task classification"""
        agent = NetworkAgent("network_001", blackboard)
        
        api_task = DevelopmentTask(
            id="t1", title="Test", description="Design REST API endpoints",
            role=AgentRole.NETWORK, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(api_task) == "api_design"
        
        protocol_task = DevelopmentTask(
            id="t2", title="Test", description="Implement TCP protocol handler",
            role=AgentRole.NETWORK, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(protocol_task) == "protocol_implementation"
        
        distributed_task = DevelopmentTask(
            id="t3", title="Test", description="Design microservices architecture",
            role=AgentRole.NETWORK, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(distributed_task) == "distributed_systems"
        
        security_task = DevelopmentTask(
            id="t4", title="Test", description="Implement TLS encryption",
            role=AgentRole.NETWORK, priority=TaskPriority.HIGH
        )
        assert agent._classify_task(security_task) == "network_security"
    
    @pytest.mark.asyncio
    async def test_network_toolkit_integration(self, blackboard):
        """Test network toolkit integration awareness"""
        agent = NetworkAgent("network_001", blackboard)
        
        assert agent.network_toolkit_integration["http_client"] == "HTTPClientWithCaching"
        assert agent.network_toolkit_integration["websocket"] == "WebSocketHandler"
        assert agent.network_toolkit_integration["diagnostics"] == "NetworkDiagnostics"
        assert agent.network_toolkit_integration["guardian"] == "Guardian"


class TestSpecialistAgentIntegration:
    """Integration tests for specialist agents working together"""
    
    @pytest.mark.asyncio
    async def test_agent_collaboration(self, blackboard, mock_llm):
        """Test collaboration between specialist agents"""
        gamedev_agent = GameDevAgent("gamedev_001", blackboard)
        gamedev_agent.llm = mock_llm
        
        perf_agent = NetworkAgent("network_001", blackboard)
        perf_agent.llm = mock_llm
        
        task = DevelopmentTask(
            id="task_001",
            title="Game Networking",
            description="Implement multiplayer networking for game",
            role=AgentRole.GAME_DEV,
            priority=TaskPriority.HIGH
        )
        
        result = await gamedev_agent._execute_role_specific_task(task)
        assert "completed" in result.lower()
    
    @pytest.mark.asyncio
    async def test_knowledge_retrieval(self, blackboard, mock_llm):
        """Test knowledge retrieval functionality"""
        agent = LowLevelAgent("lowlevel_001", blackboard)
        agent.llm = mock_llm
        
        with patch.object(agent, 'retrieve_knowledge', new=AsyncMock(return_value=[])):
            task = DevelopmentTask(
                id="task_001",
                title="Memory Optimization",
                description="Optimize memory layout for cache efficiency",
                role=AgentRole.LOW_LEVEL,
                priority=TaskPriority.HIGH
            )
            
            result = await agent._execute_role_specific_task(task)
            assert "completed" in result.lower()
    
    @pytest.mark.asyncio
    async def test_blackboard_messaging(self, blackboard):
        """Test blackboard message sharing"""
        agent = NetworkAgent("network_001", blackboard)
        
        task = DevelopmentTask(
            id="task_001",
            title="Test Task",
            description="Test task for blackboard",
            role=AgentRole.NETWORK,
            priority=TaskPriority.HIGH
        )
        
        result_data = {
            "type": "test",
            "implementation": "test implementation"
        }
        
        agent._share_result(task, result_data)
        
        messages = blackboard.get_messages(agent.name)
        assert len(messages) > 0


@pytest.mark.asyncio
async def test_all_agents_have_unique_roles(blackboard):
    """Test that all specialist agents have unique roles"""
    gamedev = GameDevAgent("gamedev_001", blackboard)
    reveng = ReverseEngineeringAgent("reveng_001", blackboard)
    lowlevel = LowLevelAgent("lowlevel_001", blackboard)
    network = NetworkAgent("network_001", blackboard)
    
    roles = {gamedev.role, reveng.role, lowlevel.role, network.role}
    assert len(roles) == 4


@pytest.mark.asyncio
async def test_all_agents_have_tool_access(blackboard):
    """Test that all specialist agents have tool access defined"""
    agents = [
        GameDevAgent("gamedev_001", blackboard),
        ReverseEngineeringAgent("reveng_001", blackboard),
        LowLevelAgent("lowlevel_001", blackboard),
        NetworkAgent("network_001", blackboard)
    ]
    
    for agent in agents:
        assert hasattr(agent, 'allowed_tools')
        assert len(agent.allowed_tools) > 0
        assert "bash" in agent.allowed_tools or "python_execute" in agent.allowed_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
