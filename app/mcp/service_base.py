import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from mcp.server.fastmcp import FastMCP

from app.logger import logger
from app.tool.base import BaseTool


class MCPServiceBase(ABC):
    """Base class for MCP services."""

    def __init__(self, name: str, namespace: str = "ixlinx-agent"):
        self.name = name
        self.namespace = namespace
        self.server = FastMCP(f"{namespace}.{name}")
        self.tools: Dict[str, BaseTool] = {}

    @abstractmethod
    def get_tools(self) -> Dict[str, BaseTool]:
        """Get the tools provided by this service."""
        pass

    def register_tools(self) -> None:
        """Register all tools with the MCP server."""
        tools = self.get_tools()
        for tool_name, tool in tools.items():
            self._register_tool(tool, tool_name)

    def _register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation and documentation."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {self.namespace}.{tool_name}: {kwargs}")
            result = await tool.execute(**kwargs)
            logger.info(f"Result of {self.namespace}.{tool_name}: {result}")

            # Handle different types of results
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema
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
        logger.info(f"Registered tool: {self.namespace}.{tool_name}")

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

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

    def _build_signature(self, tool_function: dict):
        """Build a function signature from tool function metadata."""
        from inspect import Parameter, Signature

        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types
            from typing import Any

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

            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up service resources."""
        logger.info(f"Cleaning up {self.namespace}.{self.name} service")

    def get_server_info(self) -> Dict[str, Any]:
        """Get information about this service."""
        return {
            "name": self.name,
            "namespace": self.namespace,
            "tools": list(self.get_tools().keys()),
            "server_name": f"{self.namespace}.{self.name}",
        }


class ToolsService(MCPServiceBase):
    """MCP service for standard OpenManus tools."""

    def __init__(self):
        super().__init__("tools", "openmanus")
        self._load_tools()

    def _load_tools(self) -> None:
        """Load standard tools."""
        from app.tool.bash import Bash
        from app.tool.browser_use_tool import BrowserUseTool
        from app.tool.str_replace_editor import StrReplaceEditor
        from app.tool.terminate import Terminate

        self.tools = {
            "bash": Bash(),
            "browser": BrowserUseTool(),
            "editor": StrReplaceEditor(),
            "terminate": Terminate(),
        }

    def get_tools(self) -> Dict[str, BaseTool]:
        """Get the tools provided by this service."""
        return self.tools

    async def cleanup(self) -> None:
        """Clean up browser tool resources."""
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()
        await super().cleanup()


class KnowledgeService(MCPServiceBase):
    """MCP service for knowledge base operations."""

    def __init__(self):
        super().__init__("knowledge", "openmanus")

    def get_tools(self) -> Dict[str, BaseTool]:
        """Get knowledge base tools."""
        # Placeholder for future knowledge base tools
        return {}


class MemoryService(MCPServiceBase):
    """MCP service for memory operations."""

    def __init__(self):
        super().__init__("memory", "openmanus")

    def get_tools(self) -> Dict[str, BaseTool]:
        """Get memory tools."""
        # Placeholder for future memory tools
        return {}


# Registry of available services
SERVICE_REGISTRY: Dict[str, Type[MCPServiceBase]] = {
    "tools": ToolsService,
    "knowledge": KnowledgeService,
    "memory": MemoryService,
}


def register_service(name: str, service_class: Type[MCPServiceBase]) -> None:
    """Register a new service class."""
    SERVICE_REGISTRY[name] = service_class


def get_service(name: str) -> Optional[Type[MCPServiceBase]]:
    """Get a service class by name."""
    return SERVICE_REGISTRY.get(name)


def list_services() -> List[str]:
    """List all registered service names."""
    return list(SERVICE_REGISTRY.keys())