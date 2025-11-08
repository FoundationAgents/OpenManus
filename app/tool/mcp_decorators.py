"""MCP decorators and helpers for registering tools with MCP server.

This module provides decorators and utilities to:
- Register tools with MCP bridge
- Ensure thread-safe tool instantiation
- Wrap tool execution with Guardian validation
- Maintain consistent schemas and service naming
"""

import functools
import threading
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from app.logger import logger
from app.tool.base import BaseTool, ToolResult

T = TypeVar("T", bound=BaseTool)

# Global registry for MCP-compatible tools
_TOOL_REGISTRY: Dict[str, Type[BaseTool]] = {}
_TOOL_INSTANCES: Dict[str, BaseTool] = {}
_REGISTRY_LOCK = threading.RLock()


class MCPToolRegistration:
    """Registration metadata for an MCP tool."""

    def __init__(
        self,
        name: str,
        tool_class: Type[BaseTool],
        description: Optional[str] = None,
        mcp_compatible: bool = True,
        requires_guardian: bool = True,
    ):
        self.name = name
        self.tool_class = tool_class
        self.description = description or tool_class.__doc__ or ""
        self.mcp_compatible = mcp_compatible
        self.requires_guardian = requires_guardian


def mcp_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    mcp_compatible: bool = True,
    requires_guardian: bool = True,
) -> Callable[[Type[T]], Type[T]]:
    """Decorator to register a tool class as MCP-compatible.

    Args:
        name: Tool name for MCP (defaults to class name in lowercase)
        description: Tool description for MCP
        mcp_compatible: Whether this tool is MCP compatible
        requires_guardian: Whether to wrap execution with Guardian checks

    Returns:
        Decorated class
    """

    def decorator(tool_class: Type[T]) -> Type[T]:
        tool_name = name or tool_class.__name__.lower()

        with _REGISTRY_LOCK:
            _TOOL_REGISTRY[tool_name] = tool_class
            logger.info(
                f"Registered MCP tool: {tool_name} "
                f"(class: {tool_class.__name__}, "
                f"requires_guardian: {requires_guardian})"
            )

        return tool_class

    return decorator


def get_tool_instance(tool_name: str) -> Optional[BaseTool]:
    """Get or create a singleton instance of a registered tool.

    Ensures thread-safe, idempotent tool instantiation.

    Args:
        tool_name: Name of the registered tool

    Returns:
        Tool instance or None if not registered
    """
    with _REGISTRY_LOCK:
        # Return cached instance if exists
        if tool_name in _TOOL_INSTANCES:
            return _TOOL_INSTANCES[tool_name]

        # Check if tool is registered
        if tool_name not in _TOOL_REGISTRY:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None

        # Create new instance
        tool_class = _TOOL_REGISTRY[tool_name]
        try:
            instance = tool_class()
            _TOOL_INSTANCES[tool_name] = instance
            logger.debug(f"Created singleton instance for tool: {tool_name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate tool '{tool_name}': {e}")
            return None


def get_all_registered_tools() -> Dict[str, Type[BaseTool]]:
    """Get all registered MCP tools.

    Returns:
        Dictionary mapping tool names to tool classes
    """
    with _REGISTRY_LOCK:
        return dict(_TOOL_REGISTRY)


def get_registered_tool_names() -> List[str]:
    """Get list of all registered tool names.

    Returns:
        List of tool names
    """
    with _REGISTRY_LOCK:
        return list(_TOOL_REGISTRY.keys())


def reset_tool_instances() -> None:
    """Reset all cached tool instances.

    Useful for testing or refreshing tool state.
    """
    with _REGISTRY_LOCK:
        _TOOL_INSTANCES.clear()
        logger.debug("Reset all cached tool instances")


def with_guardian(
    guardian_check: Optional[Callable[..., bool]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to wrap tool execution with Guardian validation.

    Args:
        guardian_check: Optional custom guardian check function

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular imports
            from app.network.guardian import Guardian, OperationType, RiskLevel

            tool_name = getattr(func, "__self__", None).__class__.__name__

            if guardian_check:
                if not guardian_check(*args, **kwargs):
                    logger.warning(
                        f"Guardian check failed for tool: {tool_name}"
                    )
                    return ToolResult(
                        error=f"Guardian check failed for {tool_name}"
                    )

            try:
                result = func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result
                return result
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                return ToolResult(error=str(e))

        return wrapper

    return decorator


class ThreadSafeToolRegistry:
    """Thread-safe registry for managing tool instances and metadata.

    Provides synchronized access to tool instances with lazy initialization.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._metadata: Dict[str, MCPToolRegistration] = {}
        self._lock = threading.RLock()

    def register(
        self,
        registration: MCPToolRegistration,
    ) -> None:
        """Register a tool with metadata.

        Args:
            registration: Tool registration metadata
        """
        with self._lock:
            self._metadata[registration.name] = registration
            logger.info(f"Registered tool metadata: {registration.name}")

    def get_instance(self, name: str) -> Optional[BaseTool]:
        """Get or create a tool instance (thread-safe singleton).

        Args:
            name: Tool name

        Returns:
            Tool instance or None
        """
        with self._lock:
            if name in self._tools:
                return self._tools[name]

            if name not in self._metadata:
                return None

            registration = self._metadata[name]
            try:
                instance = registration.tool_class()
                self._tools[name] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to create tool instance '{name}': {e}")
                return None

    def get_all_metadata(self) -> Dict[str, MCPToolRegistration]:
        """Get all registered tool metadata (thread-safe).

        Returns:
            Dictionary mapping tool names to registration metadata
        """
        with self._lock:
            return dict(self._metadata)

    def get_tool_names(self) -> List[str]:
        """Get list of all registered tool names (thread-safe).

        Returns:
            List of tool names
        """
        with self._lock:
            return list(self._metadata.keys())

    def clear(self) -> None:
        """Clear all cached instances and metadata."""
        with self._lock:
            self._tools.clear()
            self._metadata.clear()
            logger.debug("Cleared tool registry")


# Global instance
_global_registry = ThreadSafeToolRegistry()


def get_global_tool_registry() -> ThreadSafeToolRegistry:
    """Get the global thread-safe tool registry.

    Returns:
        Global registry instance
    """
    return _global_registry
