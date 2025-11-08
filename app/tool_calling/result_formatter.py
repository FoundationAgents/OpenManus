"""Result formatter for tool execution results.

This module formats tool results for LLM consumption:
- Truncates large results
- Converts to text representation
- Adds context and metadata
- Formats for readability
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from app.logger import logger
from app.tool.base import ToolResult


class ResultFormatter:
    """Format tool results for LLM consumption."""
    
    def __init__(
        self,
        max_length: int = 10000,
        truncate_message: str = "\n\n[Result truncated due to length. Use more specific queries to get detailed information.]"
    ):
        """Initialize formatter.
        
        Args:
            max_length: Maximum length of formatted result
            truncate_message: Message to append when truncating
        """
        self.max_length = max_length
        self.truncate_message = truncate_message
    
    def format_result(
        self,
        tool_name: str,
        result: ToolResult,
        execution_time: Optional[float] = None,
        include_metadata: bool = True
    ) -> str:
        """Format a tool execution result.
        
        Args:
            tool_name: Name of the tool that was executed
            result: Tool execution result
            execution_time: Execution time in seconds
            include_metadata: Whether to include metadata header
            
        Returns:
            Formatted result string
        """
        formatted = ""
        
        # Add metadata header
        if include_metadata:
            formatted += f"=== Tool Execution Result ===\n"
            formatted += f"Tool: {tool_name}\n"
            if execution_time:
                formatted += f"Execution Time: {execution_time:.2f}s\n"
            formatted += f"Status: {'Success' if not result.error else 'Error'}\n"
            formatted += "=" * 30 + "\n\n"
        
        # Handle error
        if result.error:
            formatted += f"ERROR: {result.error}\n"
            return formatted
        
        # Handle output
        if result.output:
            output_str = self._format_output(result.output)
            formatted += output_str
        
        # Handle system messages
        if result.system:
            formatted += f"\n\nSystem: {result.system}"
        
        # Handle images
        if result.base64_image:
            formatted += f"\n\n[Image output available - base64 encoded]"
        
        # Truncate if needed
        if len(formatted) > self.max_length:
            formatted = formatted[:self.max_length] + self.truncate_message
        
        return formatted
    
    def _format_output(self, output: Any) -> str:
        """Format the output part of a result.
        
        Args:
            output: Output data
            
        Returns:
            Formatted string
        """
        if isinstance(output, str):
            return output
        elif isinstance(output, (dict, list)):
            return json.dumps(output, indent=2)
        else:
            return str(output)
    
    def format_multiple_results(
        self,
        results: Dict[str, ToolResult],
        execution_times: Optional[Dict[str, float]] = None
    ) -> str:
        """Format multiple tool results.
        
        Args:
            results: Dictionary mapping tool names to results
            execution_times: Optional execution times for each tool
            
        Returns:
            Formatted results string
        """
        if not results:
            return "No results to display."
        
        formatted = f"=== Multiple Tool Results ({len(results)} tools) ===\n\n"
        
        for i, (tool_name, result) in enumerate(results.items(), 1):
            exec_time = execution_times.get(tool_name) if execution_times else None
            
            formatted += f"Result {i}/{len(results)}:\n"
            formatted += self.format_result(
                tool_name=tool_name,
                result=result,
                execution_time=exec_time,
                include_metadata=False
            )
            formatted += "\n" + "-" * 50 + "\n\n"
        
        return formatted
    
    def format_error(
        self,
        tool_name: str,
        error_message: str,
        suggestion: Optional[str] = None
    ) -> str:
        """Format an error message.
        
        Args:
            tool_name: Name of the tool
            error_message: Error message
            suggestion: Optional suggestion for fixing the error
            
        Returns:
            Formatted error message
        """
        formatted = f"=== Tool Execution Error ===\n"
        formatted += f"Tool: {tool_name}\n"
        formatted += f"Error: {error_message}\n"
        
        if suggestion:
            formatted += f"\nSuggestion: {suggestion}\n"
        
        return formatted
    
    def format_for_conversation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: ToolResult,
        execution_time: Optional[float] = None
    ) -> str:
        """Format result for injection back into conversation.
        
        This creates a natural-looking result that can be added to the
        conversation history as a system message.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            result: Tool result
            execution_time: Execution time
            
        Returns:
            Formatted message for conversation
        """
        msg = f"[Tool '{tool_name}' was executed"
        
        # Add key arguments
        if args:
            key_args = self._extract_key_args(args)
            if key_args:
                msg += f" with {key_args}"
        
        if execution_time:
            msg += f" ({execution_time:.2f}s)"
        
        msg += "]\n\n"
        
        # Add result
        if result.error:
            msg += f"Error: {result.error}"
        elif result.output:
            output = self._format_output(result.output)
            # Truncate for conversation context
            if len(output) > 2000:
                output = output[:2000] + "\n...[truncated]"
            msg += f"Result:\n{output}"
        
        return msg
    
    def _extract_key_args(self, args: Dict[str, Any]) -> str:
        """Extract key arguments for display.
        
        Args:
            args: Argument dictionary
            
        Returns:
            Human-readable argument summary
        """
        # Common important argument names
        key_params = ['query', 'url', 'code', 'command', 'path', 'file', 'data']
        
        for param in key_params:
            if param in args:
                value = args[param]
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                return f"{param}='{value}'"
        
        # If no key params, show first arg
        if args:
            key = list(args.keys())[0]
            value = args[key]
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            return f"{key}='{value}'"
        
        return ""
    
    def create_tool_response_message(
        self,
        tool_name: str,
        result: ToolResult,
        role: str = "system"
    ) -> Dict[str, str]:
        """Create a message object for tool response.
        
        Args:
            tool_name: Tool name
            result: Tool result
            role: Message role (default: system)
            
        Returns:
            Message dictionary
        """
        content = self.format_result(
            tool_name=tool_name,
            result=result,
            include_metadata=True
        )
        
        return {
            "role": role,
            "content": content
        }


def format_tool_result(
    tool_name: str,
    result: ToolResult,
    max_length: int = 10000
) -> str:
    """Convenience function to format a tool result.
    
    Args:
        tool_name: Tool name
        result: Tool result
        max_length: Maximum result length
        
    Returns:
        Formatted result string
    """
    formatter = ResultFormatter(max_length=max_length)
    return formatter.format_result(tool_name, result)
