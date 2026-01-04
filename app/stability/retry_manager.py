"""
FreEco.ai Platform - Retry Manager
Enhanced OpenManus with intelligent retry logic and exponential backoff

This module provides robust retry mechanisms for handling transient failures
in LLM calls, API requests, and other operations that may fail temporarily.

Part of Enhancement #3: Error Handling, Stability & Adaptation
"""

import functools
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


@dataclass
class RetryStats:
    """Statistics for retry operations"""

    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_delay_seconds: float = 0.0
    last_attempt_time: Optional[datetime] = None
    errors_by_type: dict = field(default_factory=dict)

    def record_attempt(
        self, success: bool, error_type: Optional[str] = None, delay: float = 0.0
    ):
        """Record a retry attempt"""
        self.total_attempts += 1
        self.total_delay_seconds += delay
        self.last_attempt_time = datetime.now()

        if success:
            self.successful_retries += 1
        else:
            self.failed_retries += 1
            if error_type:
                self.errors_by_type[error_type] = (
                    self.errors_by_type.get(error_type, 0) + 1
                )

    def get_success_rate(self) -> float:
        """Calculate retry success rate"""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_retries / self.total_attempts

    def get_average_delay(self) -> float:
        """Calculate average delay per retry"""
        if self.total_attempts == 0:
            return 0.0
        return self.total_delay_seconds / self.total_attempts


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    timeout: Optional[float] = None  # Overall timeout in seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF

    # Error types that should be retried
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        Exception,  # Catch-all, but will be filtered by is_recoverable
    )

    # Error types that should never be retried
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        KeyboardInterrupt,
        SystemExit,
        ValueError,  # Usually indicates bad input
        TypeError,  # Usually indicates programming error
    )


class RetryManager:
    """
    Intelligent retry manager with multiple strategies

    Features:
    - Multiple retry strategies (exponential, linear, fixed, fibonacci)
    - Configurable backoff parameters
    - Jitter to prevent thundering herd
    - Selective retries based on error type
    - Comprehensive statistics tracking
    - Timeout support
    - Fallback strategies

    Example:
        retry_manager = RetryManager()

        @retry_manager.retry(max_retries=3)
        def call_api():
            return requests.get("https://api.example.com")

        result = call_api()
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry manager

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        self._fibonacci_cache = [1, 1]  # For fibonacci backoff

    def retry(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        strategy: Optional[RetryStrategy] = None,
        timeout: Optional[float] = None,
        fallback: Optional[Callable] = None,
    ) -> Callable:
        """
        Decorator for adding retry logic to functions

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            strategy: Retry strategy to use
            timeout: Overall timeout (seconds)
            fallback: Fallback function to call if all retries fail

        Returns:
            Decorated function with retry logic

        Example:
            @retry_manager.retry(max_retries=5, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
            def unstable_function():
                # May fail occasionally
                return call_external_api()
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                return self.retry_with_backoff(
                    func,
                    args=args,
                    kwargs=kwargs,
                    max_retries=max_retries,
                    base_delay=base_delay,
                    strategy=strategy,
                    timeout=timeout,
                    fallback=fallback,
                )

            return wrapper

        return decorator

    def retry_with_backoff(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        strategy: Optional[RetryStrategy] = None,
        timeout: Optional[float] = None,
        fallback: Optional[Callable] = None,
    ) -> Any:
        """
        Execute function with retry logic and backoff

        Args:
            func: Function to execute
            args: Positional arguments for function
            kwargs: Keyword arguments for function
            max_retries: Maximum retry attempts (overrides config)
            base_delay: Base delay between retries (overrides config)
            strategy: Retry strategy (overrides config)
            timeout: Overall timeout (overrides config)
            fallback: Fallback function if all retries fail

        Returns:
            Result of successful function call

        Raises:
            Last exception if all retries fail and no fallback provided
        """
        kwargs = kwargs or {}
        max_retries = (
            max_retries if max_retries is not None else self.config.max_retries
        )
        base_delay = base_delay if base_delay is not None else self.config.base_delay
        strategy = strategy or self.config.strategy
        timeout = timeout if timeout is not None else self.config.timeout

        start_time = time.time()
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    logger.warning(f"Timeout exceeded after {attempt} attempts")
                    raise TimeoutError(f"Operation timed out after {timeout} seconds")

                # Execute function
                result = func(*args, **kwargs)

                # Record successful attempt
                if attempt > 0:
                    delay = time.time() - start_time
                    self.stats.record_attempt(success=True, delay=delay)
                    logger.info(f"Function succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Check if error is retryable
                if not self.is_recoverable(e):
                    logger.error(f"Non-recoverable error: {error_type}: {e}")
                    self.stats.record_attempt(success=False, error_type=error_type)
                    raise

                # Check if we have retries left
                if attempt >= max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded")
                    self.stats.record_attempt(success=False, error_type=error_type)
                    break

                # Calculate delay
                delay = self._calculate_delay(attempt, base_delay, strategy)

                # Log retry attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed with {error_type}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # Record failed attempt
                self.stats.record_attempt(
                    success=False, error_type=error_type, delay=delay
                )

                # Wait before retry
                time.sleep(delay)

        # All retries failed
        if fallback:
            logger.info("Executing fallback strategy")
            try:
                return self.execute_fallback(fallback, last_exception, args, kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise last_exception

        # No fallback, raise last exception
        raise last_exception

    def _calculate_delay(
        self, attempt: int, base_delay: float, strategy: RetryStrategy
    ) -> float:
        """
        Calculate delay for next retry based on strategy

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            strategy: Retry strategy to use

        Returns:
            Delay in seconds before next retry
        """
        if strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (self.config.exponential_base**attempt)

        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * (attempt + 1)

        elif strategy == RetryStrategy.FIXED_DELAY:
            delay = base_delay

        elif strategy == RetryStrategy.FIBONACCI_BACKOFF:
            # Generate fibonacci number for this attempt
            while len(self._fibonacci_cache) <= attempt:
                self._fibonacci_cache.append(
                    self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
                )
            delay = base_delay * self._fibonacci_cache[attempt]

        else:
            delay = base_delay

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter if enabled
        if self.config.jitter:
            import random

            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)  # Ensure non-negative

    def is_recoverable(self, error: Exception) -> bool:
        """
        Check if an error is recoverable (should be retried)

        Args:
            error: Exception to check

        Returns:
            True if error should be retried, False otherwise
        """
        # Check non-retryable exceptions first
        if isinstance(error, self.config.non_retryable_exceptions):
            return False

        # Check retryable exceptions
        if isinstance(error, self.config.retryable_exceptions):
            # Additional checks for specific error types
            error_msg = str(error).lower()

            # Common transient error patterns
            transient_patterns = [
                "timeout",
                "connection",
                "temporary",
                "rate limit",
                "throttle",
                "503",  # Service unavailable
                "502",  # Bad gateway
                "504",  # Gateway timeout
                "429",  # Too many requests
            ]

            for pattern in transient_patterns:
                if pattern in error_msg:
                    return True

            # If it's a generic Exception, be conservative
            if type(error) == Exception:
                return False

            return True

        return False

    def execute_fallback(
        self,
        fallback: Callable,
        error: Exception,
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """
        Execute fallback strategy when all retries fail

        Args:
            fallback: Fallback function to execute
            error: Last exception that occurred
            args: Original function arguments
            kwargs: Original function keyword arguments

        Returns:
            Result of fallback function
        """
        try:
            # Pass error to fallback if it accepts it
            import inspect

            sig = inspect.signature(fallback)

            if "error" in sig.parameters:
                return fallback(*args, error=error, **kwargs)
            else:
                return fallback(*args, **kwargs)

        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            raise

    def get_retry_stats(self) -> RetryStats:
        """
        Get retry statistics

        Returns:
            RetryStats object with current statistics
        """
        return self.stats

    def reset_stats(self):
        """Reset retry statistics"""
        self.stats = RetryStats()

    def set_timeout(self, seconds: float):
        """
        Set overall timeout for retry operations

        Args:
            seconds: Timeout in seconds
        """
        self.config.timeout = seconds

    def log_retry(self, attempt: int, error: Exception):
        """
        Log retry attempt

        Args:
            attempt: Attempt number
            error: Exception that triggered retry
        """
        logger.info(f"Retry attempt {attempt}: {type(error).__name__}: {error}")


# Global retry manager instance
default_retry_manager = RetryManager()


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    timeout: Optional[float] = None,
    fallback: Optional[Callable] = None,
) -> Callable:
    """
    Convenience decorator using default retry manager

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (seconds)
        strategy: Retry strategy to use
        timeout: Overall timeout (seconds)
        fallback: Fallback function if all retries fail

    Returns:
        Decorated function with retry logic

    Example:
        @retry(max_retries=5, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        def call_api():
            return requests.get("https://api.example.com")
    """
    return default_retry_manager.retry(
        max_retries=max_retries,
        base_delay=base_delay,
        strategy=strategy,
        timeout=timeout,
        fallback=fallback,
    )
