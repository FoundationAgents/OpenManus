"""
Integration tests for MCP Bridge functionality.
Tests tool execution with and without native tool support.
"""

import asyncio
import json
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import config
from app.mcp.bridge import MCPBridge, ModelCapabilityDetector
from app.tool.base import ToolResult


class TestModelCapabilityDetector:
    """Test model capability detection logic."""

    def test_supports_tools_explicit_true(self):
        """Test explicit supports_tools=true."""
        model_config = {"supports_tools": True}
        assert ModelCapabilityDetector.supports_tools(model_config) is True

    def test_supports_tools_explicit_false(self):
        """Test explicit supports_tools=false."""
        model_config = {"supports_tools": False}
        assert ModelCapabilityDetector.supports_tools(model_config) is False

    def test_supports_tools_unsupported_api_types(self):
        """Test unsupported API types."""
        for api_type in ["ollama", "custom", "text-only"]:
            model_config = {"api_type": api_type}
            assert ModelCapabilityDetector.supports_tools(model_config) is False

    def test_supports_tools_unsupported_urls(self):
        """Test unsupported base URLs."""
        for url in ["http://localhost:11434", "https://ollama.example.com"]:
            model_config = {"base_url": url}
            assert ModelCapabilityDetector.supports_tools(model_config) is False

    def test_supports_tools_default_true(self):
        """Test default assumption is True."""
        model_config = {"api_type": "openai", "base_url": "https://api.openai.com"}
        assert ModelCapabilityDetector.supports_tools(model_config) is True

    def test_should_use_fallback_disabled(self):
        """Test fallback disabled in config."""
        model_config = {"supports_tools": False}
        
        with patch.object(config, 'mcp_config') as mock_config:
            mock_config.enable_fallback = False
            assert ModelCapabilityDetector.should_use_fallback(model_config) is False

    def test_should_use_fallback_enabled_no_support(self):
        """Test fallback enabled when no tool support."""
        model_config = {"supports_tools": False}
        
        with patch.object(config, 'mcp_config') as mock_config:
            mock_config.enable_fallback = True
            assert ModelCapabilityDetector.should_use_fallback(model_config) is True


class TestMCPBridge:
    """Test MCP Bridge functionality."""

    @pytest.fixture
    async def bridge(self):
        """Create a bridge instance for testing."""
        bridge = MCPBridge()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    def native_model_config(self):
        """Model config that supports tools."""
        return {
            "model": "gpt-4",
            "api_type": "openai",
            "supports_tools": True,
            "base_url": "https://api.openai.com/v1"
        }

    @pytest.fixture
    def fallback_model_config(self):
        """Model config that doesn't support tools."""
        return {
            "model": "llama2",
            "api_type": "ollama",
            "supports_tools": False,
            "base_url": "http://localhost:11434"
        }

    async def test_initialize_native_mode(self, bridge, native_model_config):
        """Test bridge initialization in native mode."""
        await bridge.initialize(native_model_config)
        
        assert bridge.is_fallback_active() is False
        assert len(bridge.native_tools) > 0
        assert "bash" in bridge.native_tools
        assert "editor" in bridge.native_tools

    async def test_initialize_fallback_mode(self, bridge, fallback_model_config):
        """Test bridge initialization in fallback mode."""
        with patch.object(bridge, '_start_internal_servers') as mock_start:
            with patch.object(bridge, '_connect_internal_servers') as mock_connect:
                await bridge.initialize(fallback_model_config)
                
                assert bridge.is_fallback_active() is True
                mock_start.assert_called_once()
                mock_connect.assert_called_once()

    async def test_execute_native_tool(self, bridge, native_model_config):
        """Test native tool execution."""
        await bridge.initialize(native_model_config)
        
        # Mock the bash tool execution
        with patch.object(bridge.native_tools["bash"], 'execute') as mock_execute:
            mock_execute.return_value = ToolResult(output="mocked output")
            
            result = await bridge.execute_tool("bash", command="echo test")
            
            assert result.output == "mocked output"
            mock_execute.assert_called_once_with(command="echo test")

    async def test_execute_mcp_tool(self, bridge, fallback_model_config):
        """Test MCP tool execution in fallback mode."""
        await bridge.initialize(fallback_model_config)
        
        # Mock MCP tool
        mock_tool = AsyncMock()
        mock_tool.execute.return_value = ToolResult(output="mcp output")
        bridge.mcp_clients.tool_map["test_tool"] = mock_tool
        
        result = await bridge.execute_tool("test_tool", param="value")
        
        assert result.output == "mcp output"
        mock_tool.execute.assert_called_once_with(param="value")

    async def test_execute_unknown_tool(self, bridge, native_model_config):
        """Test executing unknown tool."""
        await bridge.initialize(native_model_config)
        
        result = await bridge.execute_tool("unknown_tool")
        
        assert result.error is not None
        assert "Unknown tool" in result.error

    async def test_list_tools_native(self, bridge, native_model_config):
        """Test listing tools in native mode."""
        await bridge.initialize(native_model_config)
        
        tools = await bridge.list_tools()
        
        assert len(tools) > 0
        tool_names = [tool["name"] for tool in tools]
        assert "bash" in tool_names
        assert "editor" in tool_names

    async def test_list_tools_fallback(self, bridge, fallback_model_config):
        """Test listing tools in fallback mode."""
        await bridge.initialize(fallback_model_config)
        
        # Mock MCP tools response
        mock_response = MagicMock()
        mock_response.tools = [
            MagicMock(name="tool1", description="desc1", inputSchema={"type": "object"}),
            MagicMock(name="tool2", description="desc2", inputSchema={"type": "object"}),
        ]
        
        with patch.object(bridge.mcp_clients, 'list_tools', return_value=mock_response):
            tools = await bridge.list_tools()
            
            assert len(tools) == 2
            assert tools[0]["name"] == "tool1"
            assert tools[1]["name"] == "tool2"

    def test_get_tool_names_native(self, bridge, native_model_config):
        """Test getting tool names in native mode."""
        # Manually set up native tools without async initialization
        bridge.fallback_active = False
        bridge.native_tools = {"bash": MagicMock(), "editor": MagicMock()}
        
        names = bridge.get_tool_names()
        
        assert set(names) == {"bash", "editor"}

    def test_get_tool_names_fallback(self, bridge):
        """Test getting tool names in fallback mode."""
        # Manually set up fallback mode
        bridge.fallback_active = True
        bridge.mcp_clients.tool_map = {"mcp_tool1": MagicMock(), "mcp_tool2": MagicMock()}
        
        names = bridge.get_tool_names()
        
        assert set(names) == {"mcp_tool1", "mcp_tool2"}

    def test_get_status(self, bridge):
        """Test getting bridge status."""
        bridge.fallback_active = True
        bridge.native_tools = {"bash": MagicMock()}
        bridge.mcp_clients.tool_map = {"mcp_tool": MagicMock()}
        bridge.mcp_clients.sessions = {"server1": MagicMock()}
        
        status = bridge.get_status()
        
        assert status["fallback_active"] is True
        assert status["native_tools_count"] == 1
        assert status["mcp_tools_count"] == 1
        assert status["mcp_connections"] == 1
        assert "bash" in status["tool_names"]
        assert "mcp_tool" in status["tool_names"]

    async def test_cleanup(self, bridge):
        """Test bridge cleanup."""
        # Set up mock resources
        bridge.mcp_clients.sessions = {"server1": MagicMock()}
        bridge._server_processes = {"proc1": MagicMock()}
        
        # Mock the cleanup methods
        with patch.object(bridge.mcp_clients, 'disconnect') as mock_disconnect:
            await bridge.cleanup()
            
            mock_disconnect.assert_called_once()
            # Check that processes are terminated
            bridge._server_processes["proc1"].terminate.assert_called_once()


class TestMCPBridgeIntegration:
    """Integration tests for MCP Bridge."""

    @pytest.mark.asyncio
    async def test_end_to_end_native_flow(self):
        """Test complete flow with native tool support."""
        bridge = MCPBridge()
        
        try:
            # Initialize with native model
            native_config = {
                "model": "gpt-4",
                "api_type": "openai",
                "supports_tools": True
            }
            await bridge.initialize(native_config)
            
            # Verify native mode
            assert bridge.is_fallback_active() is False
            
            # Test tool execution
            if "bash" in bridge.get_tool_names():
                result = await bridge.execute_tool("bash", command="echo 'test'")
                assert result.error is None  # Should execute without error
            
            # Verify status
            status = bridge.get_status()
            assert status["fallback_active"] is False
            assert status["native_tools_count"] > 0
            
        finally:
            await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_end_to_end_fallback_flow(self):
        """Test complete flow with fallback to MCP."""
        bridge = MCPBridge()
        
        try:
            # Initialize with fallback model
            fallback_config = {
                "model": "llama2",
                "api_type": "ollama",
                "supports_tools": False
            }
            
            # Mock the server startup to avoid actual process creation
            with patch.object(bridge, '_start_server_process'):
                with patch.object(bridge, '_connect_to_server'):
                    await bridge.initialize(fallback_config)
            
            # Verify fallback mode
            assert bridge.is_fallback_active() is True
            
            # Verify status
            status = bridge.get_status()
            assert status["fallback_active"] is True
            
        finally:
            await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_config_integration(self):
        """Test integration with configuration system."""
        # Test that config loads properly
        mcp_config = config.mcp_config
        
        assert hasattr(mcp_config, 'enable_fallback')
        assert hasattr(mcp_config, 'default_transport')
        assert hasattr(mcp_config, 'internal_servers')
        
        # Test loading bridge config
        bridge_config = type(mcp_config).load_bridge_config()
        assert isinstance(bridge_config, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])