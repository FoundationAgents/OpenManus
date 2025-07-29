"""Event processing middleware system.

This module provides middleware components for event processing including
error handling, retry mechanisms, logging, and metrics collection.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List
from dataclasses import dataclass

from app.logger import logger
from app.event.core.base import BaseEvent


@dataclass
class MiddlewareContext:
    """Context passed through middleware chain."""

    event: BaseEvent
    handler_name: str
    attempt: int = 1
    start_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.start_time == 0.0:
            self.start_time = time.time()


class BaseMiddleware(ABC):
    """Base class for event processing middleware."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Process the event through this middleware.

        Args:
            context: The middleware context
            next_middleware: The next middleware in the chain

        Returns:
            bool: True if processing should continue, False otherwise
        """
        pass


class TestMiddleware(BaseMiddleware):
    """Middleware for testing."""

    def __init__(self):
        super().__init__("test")

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Process the event through this middleware."""
        print("Test middleware processing")
        return await next_middleware(context)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging event processing."""

    def __init__(self, log_level: str = "DEBUG"):
        super().__init__("logging")
        self.log_level = log_level.upper()

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Log event processing details."""
        event = context.event
        handler_name = context.handler_name

        # Log start
        if self.log_level == "DEBUG":
            logger.debug(
                f"[{handler_name}] Processing event {event.event_id} "
                f"({event.event_type}) - attempt {context.attempt}"
            )

        start_time = time.time()

        try:
            # Call next middleware
            result = await next_middleware(context)

            # Log success
            duration = time.time() - start_time
            if result:
                logger.info(
                    f"[{handler_name}] Successfully processed event {event.event_id} "
                    f"in {duration:.3f}s"
                )
            else:
                logger.warning(
                    f"[{handler_name}] Failed to process event {event.event_id} "
                    f"after {duration:.3f}s"
                )

            return result

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"[{handler_name}] Error processing event {event.event_id} "
                f"after {duration:.3f}s: {str(e)}"
            )
            raise


class RetryMiddleware(BaseMiddleware):
    """Middleware for handling retries on failure."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
        super().__init__("retry")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Handle retries for failed event processing."""
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            context.attempt = attempt

            try:
                result = await next_middleware(context)
                if result:
                    return True

                # If handler returned False, don't retry
                if attempt == 1:
                    return False

            except Exception as e:
                last_exception = e

                if attempt == self.max_retries:
                    # Last attempt failed, re-raise the exception
                    logger.error(
                        f"Handler '{context.handler_name}' failed after {self.max_retries} attempts: {str(e)}"
                    )
                    raise

                # Calculate delay for next attempt
                delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
                logger.warning(
                    f"Handler '{context.handler_name}' attempt {attempt} failed: {str(e)}. "
                    f"Retrying in {delay:.1f}s..."
                )

                await asyncio.sleep(delay)

        return False


class ErrorIsolationMiddleware(BaseMiddleware):
    """Middleware for isolating errors to prevent cascade failures."""

    def __init__(self, isolate_errors: bool = True):
        super().__init__("error_isolation")
        self.isolate_errors = isolate_errors

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Isolate errors to prevent them from affecting other handlers."""
        if not self.isolate_errors:
            return await next_middleware(context)

        try:
            return await next_middleware(context)
        except Exception as e:
            # Log the error but don't let it propagate
            logger.error(
                f"Handler '{context.handler_name}' failed with isolated error: {str(e)}"
            )

            # Mark event as failed
            context.event.mark_failed(f"Handler '{context.handler_name}' error: {str(e)}")

            # Return False to indicate failure, but don't raise
            return False


class MetricsMiddleware(BaseMiddleware):
    """Middleware for collecting processing metrics."""

    def __init__(self):
        super().__init__("metrics")
        self.metrics = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "handler_stats": {},
            "event_type_stats": {},
        }

    async def process(self, context: MiddlewareContext, next_middleware: Callable) -> bool:
        """Collect metrics during event processing."""
        event = context.event
        handler_name = context.handler_name

        # Initialize handler stats if needed
        if handler_name not in self.metrics["handler_stats"]:
            self.metrics["handler_stats"][handler_name] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0
            }

        # Initialize event type stats if needed
        if event.event_type not in self.metrics["event_type_stats"]:
            self.metrics["event_type_stats"][event.event_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }

        start_time = time.time()

        try:
            result = await next_middleware(context)
            duration = time.time() - start_time

            # Update metrics
            self.metrics["total_events"] += 1
            self.metrics["handler_stats"][handler_name]["total"] += 1
            self.metrics["handler_stats"][handler_name]["total_duration"] += duration
            self.metrics["event_type_stats"][event.event_type]["total"] += 1

            if result:
                self.metrics["successful_events"] += 1
                self.metrics["handler_stats"][handler_name]["successful"] += 1
                self.metrics["event_type_stats"][event.event_type]["successful"] += 1
            else:
                self.metrics["failed_events"] += 1
                self.metrics["handler_stats"][handler_name]["failed"] += 1
                self.metrics["event_type_stats"][event.event_type]["failed"] += 1

            # Update average duration
            handler_stats = self.metrics["handler_stats"][handler_name]
            handler_stats["avg_duration"] = handler_stats["total_duration"] / handler_stats["total"]

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Update failure metrics
            self.metrics["total_events"] += 1
            self.metrics["failed_events"] += 1
            self.metrics["handler_stats"][handler_name]["total"] += 1
            self.metrics["handler_stats"][handler_name]["failed"] += 1
            self.metrics["handler_stats"][handler_name]["total_duration"] += duration
            self.metrics["event_type_stats"][event.event_type]["total"] += 1
            self.metrics["event_type_stats"][event.event_type]["failed"] += 1

            # Update average duration
            handler_stats = self.metrics["handler_stats"][handler_name]
            handler_stats["avg_duration"] = handler_stats["total_duration"] / handler_stats["total"]

            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "handler_stats": {},
            "event_type_stats": {},
        }


class MiddlewareChain:
    """Manages a chain of middleware for event processing."""

    def __init__(self, middlewares: List[BaseMiddleware] = None):
        self.middlewares = middlewares or []

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """Add middleware to the chain."""
        # 检查是否已存在同名中间件，避免重复添加
        for existing_middleware in self.middlewares:
            if existing_middleware.name == middleware.name:
                logger.warning(f"Middleware '{middleware.name}' already exists in chain, skipping")
                return

        self.middlewares.append(middleware)
        logger.debug(f"Added middleware '{middleware.name}' to chain")

    def remove_middleware(self, name: str) -> bool:
        """Remove middleware by name."""
        for i, middleware in enumerate(self.middlewares):
            if middleware.name == name:
                del self.middlewares[i]
                return True
        return False

    async def process(self, context: MiddlewareContext, handler: Callable) -> bool:
        """Process event through the middleware chain."""
        if not self.middlewares:
            # No middleware, call handler directly
            return await self._call_handler(handler, context)

        # Create the middleware chain
        async def create_chain(index: int):
            if index >= len(self.middlewares):
                # End of chain, call the actual handler
                return await self._call_handler(handler, context)

            # Call current middleware with next middleware as continuation
            middleware = self.middlewares[index]
            return await middleware.process(context, lambda _: create_chain(index + 1))

        return await create_chain(0)

    async def _call_handler(self, handler: Callable, context: MiddlewareContext) -> bool:
        """Call the actual event handler."""
        import inspect

        if inspect.iscoroutinefunction(handler):
            return await handler(context.event)
        else:
            return handler(context.event)


# Default middleware chain factory
def create_default_middleware_chain(
    enable_logging: bool = True,
    enable_retry: bool = True,
    enable_error_isolation: bool = True,
    enable_metrics: bool = True,
    enable_Test: bool = False,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    log_level: str = "INFO"
) -> MiddlewareChain:
    """Create a default middleware chain with common middleware."""
    middlewares = []

    if enable_logging:
        middlewares.append(LoggingMiddleware(log_level))

    if enable_metrics:
        middlewares.append(MetricsMiddleware())

    if enable_error_isolation:
        middlewares.append(ErrorIsolationMiddleware())

    if enable_retry:
        middlewares.append(RetryMiddleware(max_retries, retry_delay))

    if enable_Test:
        middlewares.append(TestMiddleware())

    return MiddlewareChain(middlewares)
