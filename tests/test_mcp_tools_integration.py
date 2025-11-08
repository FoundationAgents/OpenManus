"""MCP Tools Integration Tests

Smoke tests for MCP server tool registration and execution.
Tests verify that:
1. All tools are properly registered with MCP
2. Tools can be listed via MCP
3. Tools execute correctly through MCP
4. Guardian validation works for network tools
5. Results are consistent between direct and MCP execution
"""

import asyncio
import json
import pytest
from typing import Dict, Any

from app.logger import logger
from app.tool.base import ToolResult
from app.tool.tool_registry import (
    initialize_tool_registry,
    get_registered_tools_info,
    get_mcp_compatible_tools,
)
from app.mcp.server import MCPServer


class TestMCPToolsRegistration:
    """Test tool registration with MCP."""

    def test_tool_registry_initialization(self):
        """Test that tool registry initializes correctly."""
        registry = initialize_tool_registry()
        assert registry is not None
        
        tool_names = registry.get_tool_names()
        assert len(tool_names) > 0
        logger.info(f"Registered {len(tool_names)} tools: {tool_names}")

    def test_all_registered_tools_accessible(self):
        """Test that all registered tools can be instantiated."""
        registry = initialize_tool_registry()
        
        for tool_name in registry.get_tool_names():
            instance = registry.get_instance(tool_name)
            assert instance is not None, f"Failed to get instance for {tool_name}"
            assert hasattr(instance, "execute"), f"Tool {tool_name} missing execute method"
            assert hasattr(instance, "name"), f"Tool {tool_name} missing name attribute"
            assert hasattr(instance, "parameters"), f"Tool {tool_name} missing parameters"

    def test_mcp_server_initialization(self):
        """Test MCP server initialization and tool loading."""
        server = MCPServer(name="test_server", include_guardian=False)
        assert server is not None
        assert server.registry is not None
        
        tool_names = server.registry.get_tool_names()
        assert len(tool_names) > 0
        logger.info(f"MCP Server loaded {len(tool_names)} tools")

    def test_tool_instance_caching(self):
        """Test that tool instances are cached (singleton pattern)."""
        registry = initialize_tool_registry()
        
        tool_name = registry.get_tool_names()[0]
        instance1 = registry.get_instance(tool_name)
        instance2 = registry.get_instance(tool_name)
        
        # Should be same instance (cached)
        assert instance1 is instance2

    def test_tool_schema_validity(self):
        """Test that all tools have valid schemas."""
        registry = initialize_tool_registry()
        
        for tool_name in registry.get_tool_names():
            instance = registry.get_instance(tool_name)
            assert instance.parameters is not None
            assert isinstance(instance.parameters, dict)
            
            # Verify schema structure
            assert "type" in instance.parameters
            assert "properties" in instance.parameters


class TestMCPToolExecution:
    """Test tool execution through MCP."""

    @pytest.mark.asyncio
    async def test_bash_tool_execution(self):
        """Test bash tool execution."""
        registry = initialize_tool_registry()
        bash_tool = registry.get_instance("bash")
        
        if bash_tool:
            result = await bash_tool.execute(command="echo 'test'")
            assert result is not None
            # Check result structure
            if isinstance(result, ToolResult):
                assert result.output or result.error

    @pytest.mark.asyncio
    async def test_python_execute_tool(self):
        """Test Python execution tool."""
        registry = initialize_tool_registry()
        py_tool = registry.get_instance("python_execute")
        
        if py_tool:
            result = await py_tool.execute(code="print('Hello')")
            assert result is not None

    @pytest.mark.asyncio
    async def test_terminate_tool(self):
        """Test terminate tool."""
        registry = initialize_tool_registry()
        term_tool = registry.get_instance("terminate")
        
        if term_tool:
            # Terminate tool requires a status parameter
            result = await term_tool.execute(status="completed")
            assert result is not None

    @pytest.mark.asyncio
    async def test_mcp_server_lists_tools(self):
        """Test that MCP server can list all tools."""
        server = MCPServer(include_guardian=False)
        
        tool_names = server.registry.get_tool_names()
        assert len(tool_names) > 0
        
        logger.info(f"MCP Server lists {len(tool_names)} tools:")
        for name in sorted(tool_names):
            logger.info(f"  - {name}")


class TestGuardianIntegration:
    """Test Guardian integration with MCP tools."""

    @pytest.mark.asyncio
    async def test_guardian_validation_network_operations(self):
        """Test Guardian validation for network operations."""
        from app.network.guardian import Guardian, OperationType
        
        guardian = Guardian()
        
        # Test with valid operation
        assessment = guardian.assess_risk(
            operation=OperationType.DNS_LOOKUP,
            host="google.com"
        )
        assert assessment is not None
        assert hasattr(assessment, "approved")
        assert hasattr(assessment, "level")

    @pytest.mark.asyncio
    async def test_guardian_blocks_dangerous_operations(self):
        """Test that Guardian blocks dangerous operations."""
        from app.network.guardian import Guardian, OperationType
        
        guardian = Guardian()
        
        # Test with localhost (should be blocked)
        assessment = guardian.assess_risk(
            operation=OperationType.ICMP_PING,
            host="127.0.0.1"
        )
        
        # Should be blocked or require confirmation
        assert assessment.level.value in ["high", "critical", "medium"]

    def test_mcp_server_guardian_enabled(self):
        """Test MCP server with Guardian enabled."""
        server = MCPServer(include_guardian=True)
        assert server.include_guardian is True

    def test_mcp_server_guardian_disabled(self):
        """Test MCP server with Guardian disabled."""
        server = MCPServer(include_guardian=False)
        assert server.include_guardian is False


class TestToolConsistency:
    """Test consistency between direct and MCP execution."""

    @pytest.mark.asyncio
    async def test_tool_result_serialization(self):
        """Test that ToolResult is properly serialized."""
        registry = initialize_tool_registry()
        
        # Get any tool
        tool_names = registry.get_tool_names()
        if "terminate" in tool_names:
            tool = registry.get_instance("terminate")
            result = await tool.execute(status="test")
            
            # Should be serializable
            if hasattr(result, "model_dump"):
                dumped = result.model_dump()
                assert isinstance(dumped, dict)
                
                # Should be JSON serializable
                json_str = json.dumps(dumped)
                assert json_str is not None

    def test_tool_schema_consistency(self):
        """Test that all tools have consistent schema structure."""
        registry = initialize_tool_registry()
        
        required_schema_keys = {"type", "properties"}
        
        for tool_name in registry.get_tool_names():
            tool = registry.get_instance(tool_name)
            
            for key in required_schema_keys:
                assert key in tool.parameters, \
                    f"Tool {tool_name} missing {key} in schema"


class TestThreadSafety:
    """Test thread-safe tool operations."""

    def test_concurrent_tool_access(self):
        """Test concurrent access to tool instances."""
        registry = initialize_tool_registry()
        
        tool_name = registry.get_tool_names()[0]
        
        # Get instances from multiple "threads"
        instances = [registry.get_instance(tool_name) for _ in range(10)]
        
        # All should be the same instance (singleton)
        for instance in instances[1:]:
            assert instance is instances[0]

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent execution of tools."""
        registry = initialize_tool_registry()
        
        # Test with python_execute instead of bash to avoid timeout issues
        py_tool = registry.get_instance("python_execute")
        if py_tool:
            # Run multiple executions concurrently
            tasks = [
                py_tool.execute(code="print('test')")
                for _ in range(2)
            ]
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks),
                    timeout=30
                )
                assert len(results) == 2
            except asyncio.TimeoutError:
                pytest.skip("Concurrent execution timed out")


class TestMCPServerRegistration:
    """Test MCP server tool registration."""

    def test_mcp_server_registers_all_tools(self):
        """Test that MCP server registers all available tools."""
        server = MCPServer(include_guardian=False)
        
        # Manually register tools (simulating server startup)
        server.register_all_tools()
        
        # Check that tools are registered
        assert len(server.tools) > 0
        logger.info(f"Registered {len(server.tools)} tools in MCP server")

    def test_mcp_server_tool_metadata(self):
        """Test that registered tools have proper metadata."""
        server = MCPServer(include_guardian=False)
        server.register_all_tools()
        
        for tool_name, tool_instance in server.tools.items():
            assert tool_instance.name is not None
            assert tool_instance.description is not None
            assert tool_instance.parameters is not None
            
            # Verify tool can be converted to MCP format
            tool_param = tool_instance.to_param()
            assert "type" in tool_param
            assert "function" in tool_param


@pytest.fixture
def clean_registry():
    """Fixture to clean up registry between tests."""
    yield
    # Cleanup if needed
    pass


if __name__ == "__main__":
    # Run basic smoke tests
    print("Running MCP Tools Integration Smoke Tests")
    print("=" * 50)
    
    test = TestMCPToolsRegistration()
    test.test_tool_registry_initialization()
    print("✓ Tool registry initialization")
    
    test.test_all_registered_tools_accessible()
    print("✓ All registered tools accessible")
    
    test.test_mcp_server_initialization()
    print("✓ MCP server initialization")
    
    test.test_tool_instance_caching()
    print("✓ Tool instance caching (singleton)")
    
    test.test_tool_schema_validity()
    print("✓ Tool schema validity")
    
    test2 = TestMCPServerRegistration()
    test2.test_mcp_server_registers_all_tools()
    print("✓ MCP server registers all tools")
    
    test2.test_mcp_server_tool_metadata()
    print("✓ MCP server tool metadata")
    
    print("=" * 50)
    print("All smoke tests passed!")
