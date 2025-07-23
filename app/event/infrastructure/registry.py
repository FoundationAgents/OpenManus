"""Event handler registry system with decorator support.

This module provides automatic handler registration, wildcard pattern matching,
dependency resolution for event handlers.
"""

import fnmatch
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from app.logger import logger


@dataclass
class HandlerInfo:
    """Information about a registered event handler."""

    name: str
    handler: Callable
    patterns: List[str]
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 3
    retry_delay: float = 1.0
    enabled: bool = True

    def matches_event(self, event_type: str) -> bool:
        """Check if this handler matches the given event type."""
        return any(fnmatch.fnmatch(event_type, pattern) for pattern in self.patterns)


class EventHandlerRegistry:
    """Registry for managing event handlers with advanced features."""

    def __init__(self):
        self._handlers: Dict[str, HandlerInfo] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._execution_order_cache: Dict[str, List[str]] = {}

    def register_handler(
        self,
        name: str,
        handler: Callable,
        patterns: List[str],
        depends_on: Optional[List[str]] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        enabled: bool = True
    ) -> None:
        """Register an event handler with the registry.

        Args:
            name: Unique name for the handler
            handler: The handler function (async or sync)
            patterns: List of event type patterns to match (supports wildcards)
            depends_on: List of handler names this handler depends on
            retry_count: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            enabled: Whether the handler is enabled
        """
        if name in self._handlers:
            logger.warning(f"Handler '{name}' already registered, overwriting")

        depends_on = depends_on or []

        # Validate dependencies
        for dep in depends_on:
            if dep not in self._handlers and dep != name:
                logger.warning(f"Handler '{name}' depends on unregistered handler '{dep}'")

        handler_info = HandlerInfo(
            name=name,
            handler=handler,
            patterns=patterns,
            depends_on=depends_on,
            retry_count=retry_count,
            retry_delay=retry_delay,
            enabled=enabled
        )

        self._handlers[name] = handler_info
        self._update_dependency_graph(name, depends_on)
        self._clear_cache()

        logger.debug(f"Registered handler '{name}' for patterns {patterns}")

    def unregister_handler(self, name: str) -> bool:
        """Unregister a handler by name.

        Args:
            name: Name of the handler to unregister

        Returns:
            bool: True if handler was found and removed
        """
        if name in self._handlers:
            del self._handlers[name]
            self._remove_from_dependency_graph(name)
            self._clear_cache()
            logger.debug(f"Unregistered handler '{name}'")
            return True
        return False

    def get_handlers_for_event(self, event_type: str) -> tuple[List[HandlerInfo], List[HandlerInfo]]:
        """Get handlers that can process the given event type, split by dependency.

        Args:
            event_type: The event type to match

        Returns:
            tuple: (independent_handlers, dependent_handlers)
        """
        if event_type in self._execution_order_cache:
            return self._execution_order_cache[event_type]

        # Find matching handlers
        matching_handlers = [
            handler for handler in self._handlers.values()
            if handler.enabled and handler.matches_event(event_type)
        ]

        # Split handlers by dependency
        independent_handlers = []
        dependent_handlers = []

        for handler in matching_handlers:
            if handler.depends_on:
                dependent_handlers.append(handler)
            else:
                independent_handlers.append(handler)

        # Resolve execution order for dependent handlers only
        if dependent_handlers:
            dependent_handlers = self._resolve_execution_order(dependent_handlers)

        result = (independent_handlers, dependent_handlers)

        # Cache the result
        self._execution_order_cache[event_type] = result

        return result

    def get_handler_info(self, name: str) -> Optional[HandlerInfo]:
        """Get information about a specific handler.

        Args:
            name: Name of the handler

        Returns:
            Optional[HandlerInfo]: Handler information if found
        """
        return self._handlers.get(name)

    def list_handlers(self) -> List[HandlerInfo]:
        """Get list of all registered handlers.

        Returns:
            List[HandlerInfo]: All registered handlers
        """
        return list(self._handlers.values())

    def enable_handler(self, name: str) -> bool:
        """Enable a handler.

        Args:
            name: Name of the handler to enable

        Returns:
            bool: True if handler was found and enabled
        """
        if name in self._handlers:
            self._handlers[name].enabled = True
            self._clear_cache()
            return True
        return False

    def disable_handler(self, name: str) -> bool:
        """Disable a handler.

        Args:
            name: Name of the handler to disable

        Returns:
            bool: True if handler was found and disabled
        """
        if name in self._handlers:
            self._handlers[name].enabled = False
            self._clear_cache()
            return True
        return False

    def _update_dependency_graph(self, name: str, depends_on: List[str]) -> None:
        """Update the dependency graph for a handler."""
        self._dependency_graph[name] = set(depends_on)

    def _remove_from_dependency_graph(self, name: str) -> None:
        """Remove a handler from the dependency graph."""
        # Remove the handler itself
        if name in self._dependency_graph:
            del self._dependency_graph[name]

        # Remove dependencies on this handler
        for handler_deps in self._dependency_graph.values():
            handler_deps.discard(name)

    def _resolve_execution_order(self, handlers: List[HandlerInfo]) -> List[HandlerInfo]:
        """Resolve the execution order based on dependencies.

        Args:
            handlers: List of handlers to order

        Returns:
            List[HandlerInfo]: Handlers in dependency order
        """
        if not handlers:
            return []

        # Create a subgraph with only the handlers we're interested in
        handler_names = {h.name for h in handlers}
        subgraph = {
            name: deps & handler_names
            for name, deps in self._dependency_graph.items()
            if name in handler_names
        }

        # Topological sort
        ordered = []
        visited = set()
        temp_visited = set()

        def visit(name: str) -> None:
            if name in temp_visited:
                logger.warning(f"Circular dependency detected involving handler '{name}'")
                return
            if name in visited:
                return

            temp_visited.add(name)

            # Visit dependencies first
            for dep in subgraph.get(name, set()):
                if dep in handler_names:
                    visit(dep)

            temp_visited.remove(name)
            visited.add(name)
            ordered.append(name)

        # Visit all handlers
        for handler in handlers:
            if handler.name not in visited:
                visit(handler.name)

        # Convert back to HandlerInfo objects
        handler_map = {h.name: h for h in handlers}
        result = []

        for name in ordered:
            if name in handler_map:
                result.append(handler_map[name])

        return result

    def _clear_cache(self) -> None:
        """Clear the execution order cache."""
        self._execution_order_cache.clear()


# Global registry instance
_global_registry = EventHandlerRegistry()


def get_global_registry() -> EventHandlerRegistry:
    """Get the global event handler registry."""
    return _global_registry


def event_handler(
    patterns: str | List[str],
    depends_on: Optional[List[str]] = None,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    name: Optional[str] = None,
    enabled: bool = True
):
    """Decorator for registering event handlers.

    Args:
        patterns: Event type pattern(s) to match (supports wildcards)
        depends_on: List of handler names this handler depends on (optional)
        retry_count: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        name: Custom name for the handler (defaults to function name)
        enabled: Whether the handler is enabled

    Example:
        @event_handler("user.*")
        async def handle_user_events(event: BaseEvent) -> bool:
            return True

        @event_handler(["agent.step.*", "agent.complete"], depends_on=["logger"])
        async def handle_agent_events(event: BaseEvent) -> bool:
            return True
    """
    if isinstance(patterns, str):
        patterns = [patterns]

    def decorator(func: Callable) -> Callable:
        handler_name = name or func.__name__

        # Register the handler
        _global_registry.register_handler(
            name=handler_name,
            handler=func,
            patterns=patterns,
            depends_on=depends_on,
            retry_count=retry_count,
            retry_delay=retry_delay,
            enabled=enabled
        )

        # Add metadata to the function
        func._event_handler_info = {
            'name': handler_name,
            'patterns': patterns,
            'depends_on': depends_on,
            'retry_count': retry_count,
            'retry_delay': retry_delay,
            'enabled': enabled
        }

        return func

    return decorator
