import logging
import sys


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

import argparse
import asyncio
import atexit
import json
from inspect import Parameter, Signature
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_registry import initialize_tool_registry, get_registered_tools_info


class MCPServer:
    """MCP Server implementation with tool registration and management.
    
    Features:
    - Automatic tool discovery and registration from tool registry
    - Thread-safe tool instantiation
    - Guardian security validation for each tool execution
    - Consistent MCP schema support across all tools
    """

    def __init__(self, name: str = "openmanus", include_guardian: bool = True):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}
        self.include_guardian = include_guardian
        
        # Initialize tool registry
        self.registry = initialize_tool_registry()
        logger.info("Tool registry initialized with MCP-compatible tools")

    async def _validate_with_guardian(self, tool_name: str, kwargs: Dict[str, Any]) -> Optional[ToolResult]:
        """Validate tool execution with Guardian if enabled.
        
        Args:
            tool_name: Name of the tool being executed
            kwargs: Tool execution parameters
            
        Returns:
            ToolResult with error if validation fails, None if validation passes
        """
        if not self.include_guardian:
            return None
            
        try:
            from app.network.guardian import Guardian, OperationType
            
            guardian = Guardian()
            
            # Map tools to operations for Guardian assessment
            operation_map = {
                "http_request": OperationType.HTTP_POST,
                "bash": OperationType.API_CALL,
                "python_execute": OperationType.API_CALL,
                "str_replace_editor": OperationType.API_CALL,
                "browser": OperationType.API_CALL,
                "web_search": OperationType.API_CALL,
                "dns_lookup": OperationType.DNS_LOOKUP,
                "ping": OperationType.ICMP_PING,
                "traceroute": OperationType.ICMP_TRACEROUTE,
            }
            
            operation = operation_map.get(tool_name, OperationType.API_CALL)
            
            # Assess risk - Guardian primarily checks network operations
            # For non-network tools, we do basic logging
            if operation in [OperationType.DNS_LOOKUP, OperationType.ICMP_PING, 
                           OperationType.ICMP_TRACEROUTE, OperationType.HTTP_POST]:
                assessment = guardian.assess_risk(
                    operation=operation,
                    host=kwargs.get("host", "localhost"),
                    port=kwargs.get("port"),
                    data_size=len(str(kwargs)) if kwargs else 0,
                )
                
                if not assessment.approved:
                    logger.warning(f"Guardian blocked execution of {tool_name}: {assessment.reasons}")
                    return ToolResult(error=f"Security check failed: {', '.join(assessment.reasons)}")
            else:
                logger.debug(f"Tool {tool_name} passed Guardian validation (non-network operation)")
                
        except Exception as e:
            logger.warning(f"Guardian validation failed for {tool_name}: {e}")
            # Don't block execution if Guardian validation fails
            
        return None

    def register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation, documentation, and Guardian support."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")
            
            # Guardian validation
            guardian_result = await self._validate_with_guardian(tool_name, kwargs)
            if guardian_result is not None:
                return json.dumps(guardian_result.model_dump())
            
            result = await tool.execute(**kwargs)

            logger.info(f"Result of {tool_name}: {result}")

            # Handle different types of results (match original logic)
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema (important for tools that access it programmatically)
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        tool_method._parameter_schema = {
            param_name: {
                "description": param_details.get("description", ""),
                "type": param_details.get("type", "any"),
                "required": param_name in required_params,
            }
            for param_name, param_details in param_props.items()
        }

        # Register with server
        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        # Build docstring (match original format)
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = (
                    "(required)" if param_name in required_params else "(optional)"
                )
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += (
                    f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
                )

        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        """Build a function signature from tool function metadata."""
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        # Follow original type mapping
        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types (same as original)
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list

            # Create parameter with same structure as original
            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up resources")
        # Follow original cleanup logic - only clean browser tool
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()

    def register_all_tools(self) -> None:
        """Register all tools from the registry with the server.
        
        This method:
        1. Gets all registered tool names from the registry
        2. Creates or retrieves singleton instances of each tool
        3. Registers each tool with the MCP server
        """
        tool_names = self.registry.get_tool_names()
        logger.info(f"Registering {len(tool_names)} tools: {tool_names}")
        
        for tool_name in tool_names:
            try:
                # Get or create singleton instance
                tool_instance = self.registry.get_instance(tool_name)
                if tool_instance:
                    self.tools[tool_name] = tool_instance
                    self.register_tool(tool_instance, method_name=tool_name)
                else:
                    logger.warning(f"Failed to get instance for tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to register tool {tool_name}: {e}", exc_info=True)

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server."""
        # Register all tools
        self.register_all_tools()

        # Register cleanup function (match original behavior)
        atexit.register(lambda: asyncio.run(self.cleanup()))

        # Start server (with same logging as original)
        logger.info(f"Starting OpenManus server ({transport} mode)")
        self.server.run(transport=transport)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OpenManus MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Communication method: stdio or http (default: stdio)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Create and run server (maintaining original flow)
    server = MCPServer()
    server.run(transport=args.transport)
