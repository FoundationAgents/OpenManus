"""Tool registry initialization for MCP compatibility.

This module initializes and registers all OpenManus tools as MCP-compatible,
ensuring they can be used both locally and through MCP servers.
"""

from typing import Dict, List, Optional

from app.logger import logger
from app.tool.base import BaseTool
from app.tool.mcp_decorators import (
    MCPToolRegistration,
    ThreadSafeToolRegistry,
    get_global_tool_registry,
)

# Lazy imports to avoid circular dependencies
_tool_modules = {}


def _import_tool(module_path: str, class_name: str) -> Optional[type]:
    """Lazy import a tool class.

    Args:
        module_path: Module path (e.g., 'app.tool.bash')
        class_name: Class name (e.g., 'Bash')

    Returns:
        Tool class or None
    """
    try:
        if module_path not in _tool_modules:
            # Import the module by its full path
            module = __import__(module_path, fromlist=[class_name])
            _tool_modules[module_path] = module
        else:
            module = _tool_modules[module_path]

        return getattr(module, class_name, None)
    except Exception as e:
        logger.warning(f"Failed to import {class_name} from {module_path}: {e}", exc_info=True)
        return None


def get_tool_class(tool_name: str) -> Optional[type]:
    """Get tool class by name.

    Args:
        tool_name: Tool name

    Returns:
        Tool class or None
    """
    tool_map = get_registered_tools_info()
    for info in tool_map.values():
        if info["name"] == tool_name:
            return _import_tool(info["module"], info["class"])
    return None


def get_registered_tools_info() -> Dict[str, Dict[str, str]]:
    """Get information about all registered tools.

    Returns:
        Dictionary mapping tool names to their metadata
    """
    return {
        "bash": {
            "name": "bash",
            "module": "app.tool.bash",
            "class": "Bash",
            "description": "Execute bash commands",
            "requires_guardian": True,
        },
        "python_execute": {
            "name": "python_execute",
            "module": "app.tool.python_execute",
            "class": "PythonExecute",
            "description": "Execute Python code",
            "requires_guardian": True,
        },
        "str_replace_editor": {
            "name": "str_replace_editor",
            "module": "app.tool.str_replace_editor",
            "class": "StrReplaceEditor",
            "description": "View, create, and edit files",
            "requires_guardian": True,
        },
        "browser": {
            "name": "browser",
            "module": "app.tool.browser_use_tool",
            "class": "BrowserUseTool",
            "description": "Control a browser for web automation",
            "requires_guardian": True,
        },
        "web_search": {
            "name": "web_search",
            "module": "app.tool.web_search",
            "class": "WebSearch",
            "description": "Search the web using various search engines",
            "requires_guardian": False,
        },
        "crawl4ai": {
            "name": "crawl4ai",
            "module": "app.tool.crawl4ai",
            "class": "Crawl4aiTool",
            "description": "Crawl websites and extract content",
            "requires_guardian": True,
        },
        "create_chat_completion": {
            "name": "create_chat_completion",
            "module": "app.tool.create_chat_completion",
            "class": "CreateChatCompletion",
            "description": "Create chat completions with LLM",
            "requires_guardian": False,
        },
        "planning": {
            "name": "planning",
            "module": "app.tool.planning",
            "class": "PlanningTool",
            "description": "Plan tasks and workflows",
            "requires_guardian": False,
        },
        "terminate": {
            "name": "terminate",
            "module": "app.tool.terminate",
            "class": "Terminate",
            "description": "Terminate the current session",
            "requires_guardian": False,
        },
        "http_request": {
            "name": "http_request",
            "module": "app.tool.network_tools",
            "class": "HTTPRequestTool",
            "description": "Make HTTP requests",
            "requires_guardian": True,
        },
        "dns_lookup": {
            "name": "dns_lookup",
            "module": "app.tool.network_tools",
            "class": "DNSLookupTool",
            "description": "Perform DNS lookups",
            "requires_guardian": True,
        },
        "ping": {
            "name": "ping",
            "module": "app.tool.network_tools",
            "class": "PingTool",
            "description": "Ping a host",
            "requires_guardian": True,
        },
        "traceroute": {
            "name": "traceroute",
            "module": "app.tool.network_tools",
            "class": "TracerouteTool",
            "description": "Trace route to a host",
            "requires_guardian": True,
        },
    }


def initialize_tool_registry() -> ThreadSafeToolRegistry:
    """Initialize the global tool registry with all registered tools.

    This function should be called once at application startup to ensure
    all tools are available for MCP registration and local use.

    Returns:
        Initialized tool registry
    """
    registry = get_global_tool_registry()

    # Register all tools
    for tool_name, tool_info in get_registered_tools_info().items():
        tool_class = _import_tool(tool_info["module"], tool_info["class"])
        if tool_class and issubclass(tool_class, BaseTool):
            registration = MCPToolRegistration(
                name=tool_name,
                tool_class=tool_class,
                description=tool_info.get("description", ""),
                mcp_compatible=True,
                requires_guardian=tool_info.get("requires_guardian", False),
            )
            registry.register(registration)
            logger.info(f"Registered tool: {tool_name}")
        else:
            logger.warning(f"Failed to register tool {tool_name}: class not found")

    return registry


def get_mcp_compatible_tools() -> List[str]:
    """Get list of all MCP-compatible tools.

    Returns:
        List of tool names
    """
    registry = get_global_tool_registry()
    return registry.get_tool_names()


def get_tool_registration(
    tool_name: str,
) -> Optional[MCPToolRegistration]:
    """Get registration metadata for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Registration metadata or None
    """
    registry = get_global_tool_registry()
    metadata = registry.get_all_metadata()
    return metadata.get(tool_name)
