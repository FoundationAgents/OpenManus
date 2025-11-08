"""Tests for response parser module."""

import pytest

from app.tool_calling.response_parser import (
    ResponseParser,
    ToolCall,
    ToolCallParseError,
    extract_and_clean_response,
    parse_tool_calls,
)


class TestToolCall:
    """Tests for ToolCall class."""
    
    def test_tool_call_creation(self):
        """Test creating a tool call."""
        tool_call = ToolCall(
            name="test_tool",
            args={"arg1": "value1", "arg2": "value2"}
        )
        
        assert tool_call.name == "test_tool"
        assert tool_call.args == {"arg1": "value1", "arg2": "value2"}
    
    def test_tool_call_to_dict(self):
        """Test converting tool call to dictionary."""
        tool_call = ToolCall(name="test_tool", args={"key": "value"})
        result = tool_call.to_dict()
        
        assert result == {"name": "test_tool", "args": {"key": "value"}}


class TestResponseParser:
    """Tests for ResponseParser class."""
    
    def test_extract_single_tool_call(self):
        """Test extracting a single tool call."""
        parser = ResponseParser()
        response = """
        Let me search for that.
        <tool_call>
        {"name": "web_search", "args": {"query": "python async"}}
        </tool_call>
        I'll analyze the results.
        """
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "web_search"
        assert tool_calls[0].args == {"query": "python async"}
    
    def test_extract_multiple_tool_calls(self):
        """Test extracting multiple tool calls."""
        parser = ResponseParser()
        response = """
        <tool_call>
        {"name": "tool1", "args": {"key1": "value1"}}
        </tool_call>
        Some text here.
        <tool_call>
        {"name": "tool2", "args": {"key2": "value2"}}
        </tool_call>
        """
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 2
        assert tool_calls[0].name == "tool1"
        assert tool_calls[1].name == "tool2"
    
    def test_extract_no_tool_calls(self):
        """Test extracting from response with no tool calls."""
        parser = ResponseParser()
        response = "This is a regular response with no tool calls."
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 0
    
    def test_parse_with_whitespace(self):
        """Test parsing with extra whitespace."""
        parser = ResponseParser()
        response = """
        <tool_call>
        
        {"name": "test_tool", "args": {"key": "value"}}
        
        </tool_call>
        """
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "test_tool"
    
    def test_parse_invalid_json(self):
        """Test parsing with invalid JSON (non-strict mode)."""
        parser = ResponseParser(strict_mode=False)
        response = """
        <tool_call>
        {invalid json}
        </tool_call>
        """
        
        # Should return empty list in non-strict mode
        tool_calls = parser.extract_tool_calls(response)
        assert len(tool_calls) == 0
    
    def test_parse_invalid_json_strict(self):
        """Test parsing with invalid JSON (strict mode)."""
        parser = ResponseParser(strict_mode=True)
        response = """
        <tool_call>
        {invalid json}
        </tool_call>
        """
        
        # Should raise exception in strict mode
        with pytest.raises(ToolCallParseError):
            parser.extract_tool_calls(response)
    
    def test_parse_missing_name(self):
        """Test parsing with missing 'name' field."""
        parser = ResponseParser(strict_mode=False)
        response = """
        <tool_call>
        {"args": {"key": "value"}}
        </tool_call>
        """
        
        tool_calls = parser.extract_tool_calls(response)
        assert len(tool_calls) == 0
    
    def test_parse_arguments_vs_args(self):
        """Test parsing with 'arguments' instead of 'args'."""
        parser = ResponseParser()
        response = """
        <tool_call>
        {"name": "test", "arguments": {"key": "value"}}
        </tool_call>
        """
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].args == {"key": "value"}
    
    def test_remove_tool_calls(self):
        """Test removing tool call tags."""
        parser = ResponseParser()
        response = """
        Before tool call
        <tool_call>
        {"name": "test", "args": {}}
        </tool_call>
        After tool call
        """
        
        cleaned = parser.remove_tool_calls(response)
        
        assert "<tool_call>" not in cleaned
        assert "</tool_call>" not in cleaned
        assert "Before tool call" in cleaned
        assert "After tool call" in cleaned
    
    def test_extract_and_clean(self):
        """Test extract and clean in one call."""
        parser = ResponseParser()
        response = """
        Text before
        <tool_call>
        {"name": "tool1", "args": {"key": "value"}}
        </tool_call>
        Text after
        """
        
        tool_calls, cleaned = parser.extract_and_clean(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "tool1"
        assert "<tool_call>" not in cleaned
        assert "Text before" in cleaned
        assert "Text after" in cleaned
    
    def test_validate_tool_call(self):
        """Test validating tool call."""
        parser = ResponseParser()
        tool_call = ToolCall(name="test_tool", args={"key": "value"})
        
        available_tools = {"test_tool": {}, "other_tool": {}}
        
        is_valid, error = parser.validate_tool_call(tool_call, available_tools)
        
        assert is_valid
        assert error is None
    
    def test_validate_unknown_tool(self):
        """Test validating unknown tool."""
        parser = ResponseParser()
        tool_call = ToolCall(name="unknown_tool", args={})
        
        available_tools = {"test_tool": {}, "other_tool": {}}
        
        is_valid, error = parser.validate_tool_call(tool_call, available_tools)
        
        assert not is_valid
        assert "not found" in error


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_parse_tool_calls_function(self):
        """Test parse_tool_calls convenience function."""
        response = '<tool_call>{"name": "test", "args": {}}</tool_call>'
        
        tool_calls = parse_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "test"
    
    def test_extract_and_clean_response_function(self):
        """Test extract_and_clean_response convenience function."""
        response = 'Before <tool_call>{"name": "test", "args": {}}</tool_call> After'
        
        tool_calls, cleaned = extract_and_clean_response(response)
        
        assert len(tool_calls) == 1
        assert "<tool_call>" not in cleaned


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_case_insensitive_tags(self):
        """Test case-insensitive tool call tags."""
        parser = ResponseParser()
        response = '<TOOL_CALL>{"name": "test", "args": {}}</TOOL_CALL>'
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
    
    def test_multiline_json(self):
        """Test parsing multiline JSON."""
        parser = ResponseParser()
        response = """
        <tool_call>
        {
            "name": "test_tool",
            "args": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        </tool_call>
        """
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "test_tool"
        assert len(tool_calls[0].args) == 2
    
    def test_empty_args(self):
        """Test parsing with empty args."""
        parser = ResponseParser()
        response = '<tool_call>{"name": "test"}</tool_call>'
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].args == {}
    
    def test_nested_json_in_args(self):
        """Test parsing with nested JSON in args."""
        parser = ResponseParser()
        response = '''
        <tool_call>
        {"name": "test", "args": {"nested": {"key": "value"}}}
        </tool_call>
        '''
        
        tool_calls = parser.extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].args == {"nested": {"key": "value"}}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
