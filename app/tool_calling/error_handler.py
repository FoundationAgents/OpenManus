"""Error handler for tool calling emulation.

Provides graceful degradation and helpful error messages for:
- Malformed tool calls
- Unknown tools
- Tool execution failures
- Timeouts
"""

from enum import Enum
from typing import List, Optional

from app.logger import logger
from app.tool.base import ToolResult


class ErrorType(Enum):
    """Types of tool calling errors."""
    PARSE_ERROR = "parse_error"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_ARGS = "invalid_args"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    GUARDIAN_BLOCKED = "guardian_blocked"
    MAX_ITERATIONS = "max_iterations"


class ToolCallError:
    """Represents a tool calling error."""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        tool_name: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        self.error_type = error_type
        self.message = message
        self.tool_name = tool_name
        self.suggestion = suggestion
    
    def __repr__(self) -> str:
        return f"ToolCallError({self.error_type.value}: {self.message})"
    
    def to_result(self) -> ToolResult:
        """Convert to ToolResult."""
        error_msg = self.message
        if self.suggestion:
            error_msg += f"\n\nSuggestion: {self.suggestion}"
        return ToolResult(error=error_msg)


class ErrorHandler:
    """Handle tool calling errors with graceful degradation."""
    
    def __init__(
        self,
        available_tools: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """Initialize error handler.
        
        Args:
            available_tools: List of available tool names
            strict_mode: If True, raise exceptions. If False, return error results.
        """
        self.available_tools = available_tools or []
        self.strict_mode = strict_mode
    
    def handle_parse_error(
        self,
        raw_text: str,
        error: Exception
    ) -> ToolCallError:
        """Handle tool call parsing error.
        
        Args:
            raw_text: The text that failed to parse
            error: The exception that occurred
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Failed to parse tool call: {error}")
        
        message = f"Failed to parse tool call: {str(error)}"
        suggestion = (
            "Make sure your tool call follows this format:\n"
            '<tool_call>\n'
            '{\n'
            '  "name": "tool_name",\n'
            '  "args": {"key": "value"}\n'
            '}\n'
            '</tool_call>'
        )
        
        return ToolCallError(
            error_type=ErrorType.PARSE_ERROR,
            message=message,
            suggestion=suggestion
        )
    
    def handle_tool_not_found(
        self,
        tool_name: str
    ) -> ToolCallError:
        """Handle unknown tool error.
        
        Args:
            tool_name: Name of the unknown tool
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Tool not found: {tool_name}")
        
        message = f"Tool '{tool_name}' is not available."
        
        # Find similar tool names (simple string matching)
        suggestions = self._find_similar_tools(tool_name)
        if suggestions:
            suggestion = f"Did you mean: {', '.join(suggestions)}?"
        else:
            suggestion = f"Available tools: {', '.join(self.available_tools)}"
        
        return ToolCallError(
            error_type=ErrorType.TOOL_NOT_FOUND,
            message=message,
            tool_name=tool_name,
            suggestion=suggestion
        )
    
    def handle_invalid_args(
        self,
        tool_name: str,
        error: str
    ) -> ToolCallError:
        """Handle invalid arguments error.
        
        Args:
            tool_name: Tool name
            error: Error description
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Invalid arguments for {tool_name}: {error}")
        
        message = f"Invalid arguments for tool '{tool_name}': {error}"
        suggestion = "Check the tool's parameter requirements and try again."
        
        return ToolCallError(
            error_type=ErrorType.INVALID_ARGS,
            message=message,
            tool_name=tool_name,
            suggestion=suggestion
        )
    
    def handle_execution_error(
        self,
        tool_name: str,
        error: Exception
    ) -> ToolCallError:
        """Handle tool execution error.
        
        Args:
            tool_name: Tool name
            error: Exception that occurred
            
        Returns:
            ToolCallError object
        """
        logger.error(f"Tool execution failed for {tool_name}: {error}")
        
        message = f"Tool '{tool_name}' execution failed: {str(error)}"
        suggestion = "The tool encountered an error. Try adjusting your arguments or using a different approach."
        
        return ToolCallError(
            error_type=ErrorType.EXECUTION_ERROR,
            message=message,
            tool_name=tool_name,
            suggestion=suggestion
        )
    
    def handle_timeout(
        self,
        tool_name: str,
        timeout: float
    ) -> ToolCallError:
        """Handle tool execution timeout.
        
        Args:
            tool_name: Tool name
            timeout: Timeout duration in seconds
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Tool {tool_name} timed out after {timeout}s")
        
        message = f"Tool '{tool_name}' timed out after {timeout} seconds."
        suggestion = "Try breaking down your request into smaller operations or increase the timeout."
        
        return ToolCallError(
            error_type=ErrorType.TIMEOUT,
            message=message,
            tool_name=tool_name,
            suggestion=suggestion
        )
    
    def handle_guardian_blocked(
        self,
        tool_name: str,
        reason: str
    ) -> ToolCallError:
        """Handle Guardian security block.
        
        Args:
            tool_name: Tool name
            reason: Reason for block
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Guardian blocked {tool_name}: {reason}")
        
        message = f"Tool '{tool_name}' was blocked by security policy: {reason}"
        suggestion = "This operation is not allowed due to security restrictions."
        
        return ToolCallError(
            error_type=ErrorType.GUARDIAN_BLOCKED,
            message=message,
            tool_name=tool_name,
            suggestion=suggestion
        )
    
    def handle_max_iterations(
        self,
        max_iterations: int
    ) -> ToolCallError:
        """Handle maximum iterations exceeded.
        
        Args:
            max_iterations: Maximum allowed iterations
            
        Returns:
            ToolCallError object
        """
        logger.warning(f"Maximum iterations ({max_iterations}) exceeded")
        
        message = f"Maximum tool calling iterations ({max_iterations}) exceeded."
        suggestion = "Please provide a more direct response or break down your task into separate requests."
        
        return ToolCallError(
            error_type=ErrorType.MAX_ITERATIONS,
            message=message,
            suggestion=suggestion
        )
    
    def _find_similar_tools(self, tool_name: str) -> List[str]:
        """Find tools with similar names.
        
        Args:
            tool_name: Tool name to match
            
        Returns:
            List of similar tool names
        """
        similar = []
        tool_lower = tool_name.lower()
        
        for available in self.available_tools:
            available_lower = available.lower()
            
            # Check for substring match
            if tool_lower in available_lower or available_lower in tool_lower:
                similar.append(available)
            # Check for common prefixes
            elif tool_lower[:3] == available_lower[:3] and len(tool_lower) > 3:
                similar.append(available)
        
        return similar[:3]  # Return top 3 matches
    
    def create_error_message_for_llm(
        self,
        error: ToolCallError
    ) -> str:
        """Create a formatted error message for the LLM.
        
        Args:
            error: ToolCallError object
            
        Returns:
            Formatted error message
        """
        msg = f"⚠️ TOOL CALL ERROR ⚠️\n\n"
        msg += f"Error Type: {error.error_type.value}\n"
        if error.tool_name:
            msg += f"Tool: {error.tool_name}\n"
        msg += f"\n{error.message}\n"
        
        if error.suggestion:
            msg += f"\n💡 {error.suggestion}\n"
        
        msg += "\nPlease correct your tool call and try again."
        
        return msg
    
    def should_retry(self, error: ToolCallError) -> bool:
        """Determine if operation should be retried.
        
        Args:
            error: ToolCallError object
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry these errors
        no_retry = {
            ErrorType.TOOL_NOT_FOUND,
            ErrorType.GUARDIAN_BLOCKED,
            ErrorType.MAX_ITERATIONS
        }
        
        return error.error_type not in no_retry


def handle_tool_error(
    error_type: ErrorType,
    message: str,
    tool_name: Optional[str] = None,
    available_tools: Optional[List[str]] = None
) -> str:
    """Convenience function to handle tool error.
    
    Args:
        error_type: Type of error
        message: Error message
        tool_name: Tool name
        available_tools: List of available tools
        
    Returns:
        Formatted error message for LLM
    """
    handler = ErrorHandler(available_tools=available_tools)
    
    if error_type == ErrorType.TOOL_NOT_FOUND and tool_name:
        error = handler.handle_tool_not_found(tool_name)
    elif error_type == ErrorType.EXECUTION_ERROR and tool_name:
        error = handler.handle_execution_error(tool_name, Exception(message))
    else:
        error = ToolCallError(error_type, message, tool_name)
    
    return handler.create_error_message_for_llm(error)
