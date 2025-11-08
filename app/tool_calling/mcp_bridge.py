"""MCP bridge for fallback tool execution.

When pattern matching fails or for additional tool support,
this module provides fallback to MCP protocol.
"""

from typing import Any, Dict, Optional

from app.logger import logger
from app.tool.base import ToolResult


class MCPBridge:
    """Bridge to MCP server for tool execution fallback."""
    
    def __init__(self):
        """Initialize MCP bridge."""
        self._mcp_available = False
        self._check_mcp_availability()
    
    def _check_mcp_availability(self):
        """Check if MCP server is available."""
        try:
            from app.mcp.server import MCPServer
            self._mcp_available = True
            logger.info("MCP bridge initialized successfully")
        except Exception as e:
            logger.warning(f"MCP bridge unavailable: {e}")
            self._mcp_available = False
    
    def is_available(self) -> bool:
        """Check if MCP is available.
        
        Returns:
            True if MCP is available
        """
        return self._mcp_available
    
    async def execute_via_mcp(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool via MCP protocol.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            ToolResult
        """
        if not self._mcp_available:
            return ToolResult(
                error="MCP bridge is not available"
            )
        
        try:
            # Import MCP server
            from app.mcp.server import MCPServer
            from app.tool.tool_registry import get_tool_class
            
            # Get tool instance
            tool_class = get_tool_class(tool_name)
            if not tool_class:
                return ToolResult(
                    error=f"Tool '{tool_name}' not found in MCP registry"
                )
            
            # Create tool instance
            tool_instance = tool_class()
            
            # Execute tool
            logger.debug(f"Executing {tool_name} via MCP bridge")
            result = await tool_instance.execute(**arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"MCP execution failed for {tool_name}: {e}")
            return ToolResult(
                error=f"MCP execution failed: {str(e)}"
            )
    
    async def get_available_tools(self) -> list:
        """Get list of available tools from MCP.
        
        Returns:
            List of tool names
        """
        if not self._mcp_available:
            return []
        
        try:
            from app.tool.tool_registry import get_registered_tools_info
            
            tools_info = get_registered_tools_info()
            return list(tools_info.keys())
            
        except Exception as e:
            logger.error(f"Failed to get MCP tools: {e}")
            return []
    
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool schema dictionary or None
        """
        if not self._mcp_available:
            return None
        
        try:
            from app.tool.tool_registry import get_tool_registration
            
            registration = get_tool_registration(tool_name)
            if not registration:
                return None
            
            return {
                "name": tool_name,
                "description": registration.description,
                "requires_guardian": registration.requires_guardian
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {tool_name}: {e}")
            return None


class FallbackStrategy:
    """Strategy for handling tool calling fallback."""
    
    def __init__(self, enable_mcp_fallback: bool = True):
        """Initialize fallback strategy.
        
        Args:
            enable_mcp_fallback: Whether to enable MCP fallback
        """
        self.enable_mcp_fallback = enable_mcp_fallback
        self.mcp_bridge = MCPBridge() if enable_mcp_fallback else None
        
        logger.info(f"Fallback strategy initialized (MCP enabled: {enable_mcp_fallback})")
    
    async def try_fallback(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        primary_error: str
    ) -> ToolResult:
        """Try fallback execution methods.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            primary_error: Error from primary execution attempt
            
        Returns:
            ToolResult from fallback or error
        """
        logger.info(f"Attempting fallback for {tool_name}")
        
        # Try MCP fallback
        if self.mcp_bridge and self.mcp_bridge.is_available():
            logger.debug(f"Trying MCP fallback for {tool_name}")
            result = await self.mcp_bridge.execute_via_mcp(tool_name, arguments)
            
            if not result.error:
                logger.info(f"MCP fallback successful for {tool_name}")
                return result
            else:
                logger.warning(f"MCP fallback failed for {tool_name}: {result.error}")
        
        # All fallbacks exhausted
        return ToolResult(
            error=f"Primary execution failed: {primary_error}. "
                  f"All fallback methods exhausted."
        )
    
    def get_fallback_options(self) -> list:
        """Get available fallback options.
        
        Returns:
            List of fallback method names
        """
        options = []
        
        if self.mcp_bridge and self.mcp_bridge.is_available():
            options.append("MCP Protocol")
        
        return options


# Global instance
_global_mcp_bridge: Optional[MCPBridge] = None


def get_mcp_bridge() -> MCPBridge:
    """Get the global MCP bridge instance.
    
    Returns:
        Global MCPBridge
    """
    global _global_mcp_bridge
    
    if _global_mcp_bridge is None:
        _global_mcp_bridge = MCPBridge()
    
    return _global_mcp_bridge


def set_mcp_bridge(bridge: MCPBridge):
    """Set the global MCP bridge instance.
    
    Args:
        bridge: MCPBridge instance
    """
    global _global_mcp_bridge
    _global_mcp_bridge = bridge
