"""Tests for tool calling emulator."""

import pytest

from app.tool.base import BaseTool, ToolResult
from app.tool_calling import (
    ToolCallingEmulator,
    create_emulator,
)


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    parameters: dict = {
        "query": {"type": "string", "description": "Test query"}
    }
    
    async def execute(self, **kwargs):
        """Mock execution."""
        query = kwargs.get("query", "")
        return ToolResult(output=f"Mock result for: {query}")


class FailingTool(BaseTool):
    """Tool that always fails."""
    
    name: str = "failing_tool"
    description: str = "A tool that fails"
    parameters: dict = {}
    
    async def execute(self, **kwargs):
        """Mock execution that fails."""
        raise Exception("Tool execution failed")


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    return {
        "mock_tool": MockTool(),
        "failing_tool": FailingTool()
    }


@pytest.fixture
def emulator(mock_tool_registry):
    """Create an emulator instance."""
    config = {
        'max_iterations': 3,
        'timeout_per_tool': 30.0,
        'parallel_execution': False,  # Disable for simpler testing
        'caching_enabled': False,  # Disable for predictable testing
        'enable_fallback': False
    }
    return create_emulator(mock_tool_registry, config)


class TestToolCallingEmulator:
    """Tests for ToolCallingEmulator class."""
    
    def test_emulator_creation(self, mock_tool_registry):
        """Test creating an emulator."""
        emulator = create_emulator(mock_tool_registry)
        
        assert emulator is not None
        assert len(emulator.get_available_tools()) == 2
    
    def test_generate_system_prompt(self, emulator):
        """Test generating system prompt."""
        prompt = emulator.generate_system_prompt()
        
        assert "mock_tool" in prompt
        assert "tool_call" in prompt.lower()
        assert len(prompt) > 100
    
    def test_generate_system_prompt_no_examples(self, emulator):
        """Test generating system prompt without examples."""
        prompt = emulator.generate_system_prompt(include_examples=False)
        
        assert "mock_tool" in prompt
        # Should be shorter without examples
        prompt_with_examples = emulator.generate_system_prompt(include_examples=True)
        assert len(prompt) < len(prompt_with_examples)
    
    @pytest.mark.asyncio
    async def test_process_response_no_tool_calls(self, emulator):
        """Test processing response without tool calls."""
        response = "This is a regular response with no tool calls."
        
        result = await emulator.process_response(response)
        
        assert not result['has_tool_calls']
        assert result['cleaned_response'] == response
        assert len(result['tool_results']) == 0
    
    @pytest.mark.asyncio
    async def test_process_response_with_tool_call(self, emulator):
        """Test processing response with a tool call."""
        response = '''
        Let me search for that.
        <tool_call>
        {"name": "mock_tool", "args": {"query": "test query"}}
        </tool_call>
        '''
        
        result = await emulator.process_response(response)
        
        assert result['has_tool_calls']
        assert len(result['tool_results']) == 1
        assert 'formatted_results' in result
    
    @pytest.mark.asyncio
    async def test_process_response_unknown_tool(self, emulator):
        """Test processing response with unknown tool."""
        response = '''
        <tool_call>
        {"name": "unknown_tool", "args": {}}
        </tool_call>
        '''
        
        result = await emulator.process_response(response)
        
        assert result['has_tool_calls']
        # Should have error result
        for tool_result in result['tool_results'].values():
            assert tool_result.error is not None
    
    @pytest.mark.asyncio
    async def test_process_response_failing_tool(self, emulator):
        """Test processing response with failing tool."""
        response = '''
        <tool_call>
        {"name": "failing_tool", "args": {}}
        </tool_call>
        '''
        
        result = await emulator.process_response(response)
        
        assert result['has_tool_calls']
        # Should have error result
        for tool_result in result['tool_results'].values():
            assert tool_result.error is not None
    
    def test_get_available_tools(self, emulator):
        """Test getting available tools."""
        tools = emulator.get_available_tools()
        
        assert len(tools) == 2
        assert "mock_tool" in tools
        assert "failing_tool" in tools
    
    def test_get_tool_info(self, emulator):
        """Test getting tool info."""
        info = emulator.get_tool_info("mock_tool")
        
        assert info is not None
        assert info['name'] == "mock_tool"
        assert 'description' in info
        assert 'parameters' in info
    
    def test_get_tool_info_unknown(self, emulator):
        """Test getting info for unknown tool."""
        info = emulator.get_tool_info("unknown_tool")
        
        assert info is None


class TestEmulatorConfiguration:
    """Tests for emulator configuration."""
    
    def test_custom_max_iterations(self, mock_tool_registry):
        """Test custom max iterations."""
        config = {'max_iterations': 10}
        emulator = create_emulator(mock_tool_registry, config)
        
        assert emulator.config['max_iterations'] == 10
    
    def test_custom_timeout(self, mock_tool_registry):
        """Test custom timeout."""
        config = {'timeout_per_tool': 60.0}
        emulator = create_emulator(mock_tool_registry, config)
        
        assert emulator.config['timeout_per_tool'] == 60.0
    
    def test_default_config(self, mock_tool_registry):
        """Test default configuration."""
        emulator = create_emulator(mock_tool_registry)
        
        # Should have sensible defaults
        assert emulator.config.get('max_iterations', 5) > 0
        assert emulator.config.get('timeout_per_tool', 30.0) > 0


class TestMultipleToolCalls:
    """Tests for multiple tool calls in one response."""
    
    @pytest.mark.asyncio
    async def test_multiple_tool_calls_sequential(self, emulator):
        """Test multiple tool calls executed sequentially."""
        response = '''
        <tool_call>
        {"name": "mock_tool", "args": {"query": "query1"}}
        </tool_call>
        <tool_call>
        {"name": "mock_tool", "args": {"query": "query2"}}
        </tool_call>
        '''
        
        result = await emulator.process_response(response)
        
        assert result['has_tool_calls']
        assert len(result['tool_results']) == 2
    
    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, emulator):
        """Test mix of successful and failing tool calls."""
        response = '''
        <tool_call>
        {"name": "mock_tool", "args": {"query": "test"}}
        </tool_call>
        <tool_call>
        {"name": "failing_tool", "args": {}}
        </tool_call>
        '''
        
        result = await emulator.process_response(response)
        
        assert result['has_tool_calls']
        assert len(result['tool_results']) == 2
        
        # Check that we have both success and failure
        has_success = any(not r.error for r in result['tool_results'].values())
        has_failure = any(r.error for r in result['tool_results'].values())
        
        assert has_success
        assert has_failure


class TestConversationTracking:
    """Tests for conversation tracking."""
    
    @pytest.mark.asyncio
    async def test_conversation_id_generation(self, emulator):
        """Test that conversation IDs are generated."""
        response = '<tool_call>{"name": "mock_tool", "args": {"query": "test"}}</tool_call>'
        
        result = await emulator.process_response(response)
        
        # Should have iteration information
        assert 'iteration' in result
        assert 'max_iterations' in result
    
    @pytest.mark.asyncio
    async def test_custom_conversation_id(self, emulator):
        """Test using custom conversation ID."""
        response = '<tool_call>{"name": "mock_tool", "args": {"query": "test"}}</tool_call>'
        
        result = await emulator.process_response(
            response,
            conversation_id="custom_id_123"
        )
        
        assert result['has_tool_calls']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
