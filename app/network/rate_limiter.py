"""
Rate limiting for network requests.

Implements token bucket and sliding window algorithms to prevent
excessive API calls and respect rate limits.
"""

import asyncio
import time
from collections import deque
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.utils.logger import logger


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    
    requests_per_second: float = 10.0
    burst_size: int = 20
    per_host: bool = True


class TokenBucket:
    """
    Token bucket rate limiter.
    
    Allows bursts up to burst_size, refilling at rate tokens per second.
    """
    
    def __init__(self, rate: float, burst_size: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second
            burst_size: Maximum burst size
        """
        self.rate = rate
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1, wait: bool = True) -> bool:
        """
        Acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            wait: Whether to wait for tokens to become available
            
        Returns:
            True if tokens acquired, False if not available and not waiting
            
        Raises:
            RateLimitExceeded: If wait=False and tokens not available
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not wait:
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {tokens} tokens needed, "
                    f"{self.tokens:.2f} available"
                )
            
            # Calculate wait time
            needed_tokens = tokens - self.tokens
            wait_time = needed_tokens / self.rate
            
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for tokens")
            await asyncio.sleep(wait_time)
            
            # Acquire after waiting
            self.tokens = 0
            self.last_update = time.time()
            return True
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        return min(
            self.burst_size,
            self.tokens + elapsed * self.rate
        )


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    
    Tracks requests in a sliding time window.
    """
    
    def __init__(self, max_requests: int, window_seconds: float):
        """
        Initialize sliding window rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            wait: Whether to wait if limit exceeded
            
        Returns:
            True if request allowed
            
        Raises:
            RateLimitExceeded: If wait=False and limit exceeded
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            if not wait:
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.max_requests} requests "
                    f"per {self.window_seconds}s"
                )
            
            # Calculate wait time until oldest request expires
            wait_time = self.requests[0] + self.window_seconds - now
            
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
            # Retry acquisition
            return await self.acquire(wait=False)
    
    def get_current_rate(self) -> float:
        """Get current requests per second rate."""
        now = time.time()
        recent_requests = [
            ts for ts in self.requests
            if ts > now - self.window_seconds
        ]
        return len(recent_requests) / self.window_seconds if recent_requests else 0.0


class RateLimiter:
    """
    Composite rate limiter supporting multiple strategies and per-host limiting.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        
        # Global rate limiters
        self.global_bucket = TokenBucket(
            rate=self.config.requests_per_second,
            burst_size=self.config.burst_size
        )
        
        # Per-host rate limiters
        self.host_buckets: Dict[str, TokenBucket] = {}
        
        logger.info(
            f"RateLimiter initialized: {self.config.requests_per_second} req/s, "
            f"burst: {self.config.burst_size}, per_host: {self.config.per_host}"
        )
    
    async def acquire(self, host: Optional[str] = None, wait: bool = True) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            host: Target host (for per-host limiting)
            wait: Whether to wait if limit exceeded
            
        Returns:
            True if request allowed
            
        Raises:
            RateLimitExceeded: If wait=False and limit exceeded
        """
        # Always check global limit
        await self.global_bucket.acquire(tokens=1, wait=wait)
        
        # Check per-host limit if enabled
        if self.config.per_host and host:
            if host not in self.host_buckets:
                self.host_buckets[host] = TokenBucket(
                    rate=self.config.requests_per_second,
                    burst_size=self.config.burst_size
                )
            
            await self.host_buckets[host].acquire(tokens=1, wait=wait)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        stats = {
            "global_tokens_available": self.global_bucket.get_available_tokens(),
            "global_rate": self.config.requests_per_second,
            "global_burst": self.config.burst_size,
            "per_host_enabled": self.config.per_host,
            "host_count": len(self.host_buckets),
        }
        
        if self.config.per_host:
            stats["hosts"] = {
                host: {
                    "tokens_available": bucket.get_available_tokens()
                }
                for host, bucket in self.host_buckets.items()
            }
        
        return stats
    
    def reset_host(self, host: str):
        """Reset rate limit for a specific host."""
        if host in self.host_buckets:
            del self.host_buckets[host]
            logger.info(f"Rate limit reset for host: {host}")
    
    def reset_all(self):
        """Reset all rate limits."""
        self.host_buckets.clear()
        self.global_bucket.tokens = self.global_bucket.burst_size
        self.global_bucket.last_update = time.time()
        logger.info("All rate limits reset")
