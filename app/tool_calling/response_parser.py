"""Response parser for extracting tool calls from LLM text responses.

This module provides functionality to:
- Extract tool call blocks from LLM responses
- Parse JSON tool call data
- Validate tool calls against schemas
- Remove tool call tags from text
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger


class ToolCallParseError(Exception):
    """Exception raised when tool call parsing fails."""
    pass


class ToolCall:
    """Represents a parsed tool call."""
    
    def __init__(self, name: str, args: Dict[str, Any], raw_text: Optional[str] = None):
        self.name = name
        self.args = args
        self.raw_text = raw_text
    
    def __repr__(self) -> str:
        return f"ToolCall(name='{self.name}', args={self.args})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "args": self.args
        }


class ResponseParser:
    """Parser for extracting tool calls from LLM responses.
    
    Supports:
    - Multiple tool calls per response
    - XML-style tags: <tool_call>...</tool_call>
    - JSON parsing with error handling
    - Text cleanup (removing tool call tags)
    """
    
    # Regex pattern to match tool call blocks
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>\s*(\{[^}]*\})\s*</tool_call>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Alternative patterns for robustness
    TOOL_CALL_PATTERN_MULTILINE = re.compile(
        r'<tool_call>(.*?)</tool_call>',
        re.DOTALL | re.IGNORECASE
    )
    
    def __init__(self, strict_mode: bool = False):
        """Initialize parser.
        
        Args:
            strict_mode: If True, raise exceptions on parse errors.
                        If False, log warnings and continue.
        """
        self.strict_mode = strict_mode
    
    def extract_tool_calls(self, response: str) -> List[ToolCall]:
        """Extract all tool calls from a response.
        
        Args:
            response: LLM response text
            
        Returns:
            List of parsed ToolCall objects
            
        Raises:
            ToolCallParseError: If strict_mode=True and parsing fails
        """
        tool_calls = []
        
        # Try primary pattern first
        matches = self.TOOL_CALL_PATTERN_MULTILINE.findall(response)
        
        if not matches:
            logger.debug("No tool calls found in response")
            return []
        
        logger.debug(f"Found {len(matches)} potential tool call(s)")
        
        for i, match in enumerate(matches):
            try:
                tool_call = self._parse_tool_call(match.strip())
                tool_calls.append(tool_call)
                logger.debug(f"Parsed tool call {i+1}: {tool_call}")
            except Exception as e:
                error_msg = f"Failed to parse tool call {i+1}: {e}"
                if self.strict_mode:
                    raise ToolCallParseError(error_msg) from e
                else:
                    logger.warning(error_msg)
                    continue
        
        return tool_calls
    
    def _parse_tool_call(self, json_str: str) -> ToolCall:
        """Parse a single tool call JSON string.
        
        Args:
            json_str: JSON string containing tool call data
            
        Returns:
            ToolCall object
            
        Raises:
            ToolCallParseError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ToolCallParseError(f"Invalid JSON in tool call: {e}") from e
        
        # Validate required fields
        if not isinstance(data, dict):
            raise ToolCallParseError(f"Tool call must be a JSON object, got {type(data)}")
        
        if "name" not in data:
            raise ToolCallParseError("Tool call missing required field: 'name'")
        
        name = data["name"]
        args = data.get("args", data.get("arguments", {}))
        
        if not isinstance(args, dict):
            raise ToolCallParseError(f"Tool call 'args' must be an object, got {type(args)}")
        
        return ToolCall(name=name, args=args, raw_text=json_str)
    
    def remove_tool_calls(self, response: str) -> str:
        """Remove tool call tags from response text.
        
        Args:
            response: Original response with tool call tags
            
        Returns:
            Response text with tool call tags removed
        """
        # Replace tool call blocks with a placeholder or empty string
        cleaned = self.TOOL_CALL_PATTERN_MULTILINE.sub('', response)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def extract_and_clean(self, response: str) -> Tuple[List[ToolCall], str]:
        """Extract tool calls and return cleaned text.
        
        Args:
            response: Original response
            
        Returns:
            Tuple of (tool_calls, cleaned_text)
        """
        tool_calls = self.extract_tool_calls(response)
        cleaned_text = self.remove_tool_calls(response)
        return tool_calls, cleaned_text
    
    def validate_tool_call(
        self,
        tool_call: ToolCall,
        available_tools: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate a tool call against available tools.
        
        Args:
            tool_call: Tool call to validate
            available_tools: Dictionary of available tools with schemas
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if tool exists
        if tool_call.name not in available_tools:
            available = ", ".join(available_tools.keys())
            return False, f"Tool '{tool_call.name}' not found. Available tools: {available}"
        
        # TODO: Add schema validation for arguments
        # This would validate args against the tool's parameter schema
        
        return True, None
    
    def format_validation_error(
        self,
        tool_call: ToolCall,
        error: str,
        available_tools: List[str]
    ) -> str:
        """Format a validation error message for the LLM.
        
        Args:
            tool_call: Invalid tool call
            error: Error message
            available_tools: List of available tool names
            
        Returns:
            Formatted error message
        """
        msg = f"ERROR: {error}\n\n"
        msg += f"You attempted to call tool: '{tool_call.name}'\n"
        msg += f"Available tools: {', '.join(available_tools)}\n\n"
        msg += "Please correct your tool call and try again."
        return msg


def parse_tool_calls(response: str, strict: bool = False) -> List[ToolCall]:
    """Convenience function to parse tool calls from a response.
    
    Args:
        response: LLM response text
        strict: Whether to use strict mode
        
    Returns:
        List of ToolCall objects
    """
    parser = ResponseParser(strict_mode=strict)
    return parser.extract_tool_calls(response)


def extract_and_clean_response(response: str) -> Tuple[List[ToolCall], str]:
    """Convenience function to extract tool calls and clean text.
    
    Args:
        response: LLM response text
        
    Returns:
        Tuple of (tool_calls, cleaned_text)
    """
    parser = ResponseParser()
    return parser.extract_and_clean(response)
