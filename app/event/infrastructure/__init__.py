"""Infrastructure layer components.

This module contains the concrete implementations of the event system
infrastructure including registries, middleware, and bus implementations.
"""

# Registry system
from .registry import (
    EventHandlerRegistry,
    HandlerInfo,
    event_handler,
    get_global_registry
)

# Middleware system
from .middleware import (
    BaseMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    LoggingMiddleware,
    RetryMiddleware,
    ErrorIsolationMiddleware,
    MetricsMiddleware,
    create_default_middleware_chain
)

# Bus implementations
from .bus import (
    SimpleEventBus,
    ChainableEventBus,
    get_global_bus,
    set_global_bus,
    publish_event,
    subscribe_handler,
    unsubscribe_handler,
    get_bus_stats
)

__all__ = [
    # Registry system
    "EventHandlerRegistry",
    "HandlerInfo",
    "event_handler",
    "get_global_registry",
    
    # Middleware system
    "BaseMiddleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "LoggingMiddleware",
    "RetryMiddleware",
    "ErrorIsolationMiddleware",
    "MetricsMiddleware",
    "create_default_middleware_chain",
    
    # Bus implementations
    "SimpleEventBus",
    "ChainableEventBus",
    "get_global_bus",
    "set_global_bus",
    "publish_event",
    "subscribe_handler",
    "unsubscribe_handler",
    "get_bus_stats"
]
