"""Infrastructure layer components.

This module contains the concrete implementations of the event system
infrastructure including registries, middleware, and bus implementations.
"""

# Bus implementations
from .bus import EventBus, bus

# Middleware system
from .middleware import (
    BaseMiddleware,
    ErrorIsolationMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewareChain,
    MiddlewareContext,
    RetryMiddleware,
    create_default_middleware_chain,
)

# Registry system
from .registry import (
    EventHandlerRegistry,
    HandlerInfo,
    event_handler,
    get_global_registry,
)

# WebSocket forwarder middleware
from .websocket_forwarder import WebSocketForwarderMiddleware

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
    "WebSocketForwarderMiddleware",
    # Bus implementations
    "bus",
    "EventBus",
    "ChainableEventBus",
]
