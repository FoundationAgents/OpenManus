"""Tests for rate limiter."""

import pytest
import asyncio
import time
from app.network.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    TokenBucket,
)


@pytest.mark.asyncio
async def test_rate_limiter_initialization():
    """Test rate limiter initialization."""
    config = RateLimitConfig(requests_per_second=10, burst_size=20)
    limiter = RateLimiter(config)
    
    assert limiter.config.requests_per_second == 10
    assert limiter.config.burst_size == 20


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests():
    """Test that rate limiter allows requests under limit."""
    config = RateLimitConfig(requests_per_second=100, burst_size=100)
    limiter = RateLimiter(config)
    
    # Should allow multiple rapid requests
    for _ in range(10):
        result = await limiter.acquire(wait=False)
        assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excess():
    """Test that rate limiter blocks excess requests."""
    config = RateLimitConfig(requests_per_second=1, burst_size=5)
    limiter = RateLimiter(config)
    
    # Use up burst
    for _ in range(5):
        await limiter.acquire(wait=False)
    
    # Next request should be blocked
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(wait=False)


@pytest.mark.asyncio
async def test_rate_limiter_waits():
    """Test that rate limiter waits when told to."""
    config = RateLimitConfig(requests_per_second=10, burst_size=2)
    limiter = RateLimiter(config)
    
    # Use up burst
    await limiter.acquire(wait=False)
    await limiter.acquire(wait=False)
    
    # This should wait and succeed
    start = time.time()
    result = await limiter.acquire(wait=True)
    elapsed = time.time() - start
    
    assert result is True
    assert elapsed > 0  # Should have waited


@pytest.mark.asyncio
async def test_rate_limiter_per_host():
    """Test per-host rate limiting."""
    config = RateLimitConfig(requests_per_second=1, burst_size=2, per_host=True)
    limiter = RateLimiter(config)
    
    # Use up burst for host1
    await limiter.acquire(host="host1", wait=False)
    await limiter.acquire(host="host1", wait=False)
    
    # host1 should be blocked
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(host="host1", wait=False)
    
    # host2 should still be allowed
    result = await limiter.acquire(host="host2", wait=False)
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_reset_host():
    """Test resetting rate limit for specific host."""
    config = RateLimitConfig(requests_per_second=1, burst_size=2, per_host=True)
    limiter = RateLimiter(config)
    
    # Use up burst for host1
    await limiter.acquire(host="host1", wait=False)
    await limiter.acquire(host="host1", wait=False)
    
    # Reset host1
    limiter.reset_host("host1")
    
    # Should be allowed again
    result = await limiter.acquire(host="host1", wait=False)
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_reset_all():
    """Test resetting all rate limits."""
    config = RateLimitConfig(requests_per_second=1, burst_size=2)
    limiter = RateLimiter(config)
    
    # Use up burst
    await limiter.acquire(wait=False)
    await limiter.acquire(wait=False)
    
    # Reset all
    limiter.reset_all()
    
    # Should be allowed again
    result = await limiter.acquire(wait=False)
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_stats():
    """Test rate limiter statistics."""
    config = RateLimitConfig(requests_per_second=10, burst_size=20, per_host=True)
    limiter = RateLimiter(config)
    
    # Make some requests
    await limiter.acquire(host="host1", wait=False)
    await limiter.acquire(host="host2", wait=False)
    
    stats = limiter.get_stats()
    
    assert "global_tokens_available" in stats
    assert "global_rate" in stats
    assert stats["per_host_enabled"] is True
    assert stats["host_count"] == 2


@pytest.mark.asyncio
async def test_token_bucket():
    """Test token bucket directly."""
    bucket = TokenBucket(rate=10, burst_size=20)
    
    # Should have full burst initially
    assert bucket.get_available_tokens() == 20
    
    # Acquire some tokens
    await bucket.acquire(tokens=5, wait=False)
    
    # Should have fewer tokens
    assert bucket.get_available_tokens() < 20


@pytest.mark.asyncio
async def test_token_bucket_refill():
    """Test token bucket refill over time."""
    bucket = TokenBucket(rate=10, burst_size=10)  # 10 tokens/sec
    
    # Use all tokens
    await bucket.acquire(tokens=10, wait=False)
    assert bucket.get_available_tokens() < 1
    
    # Wait for refill
    await asyncio.sleep(0.2)  # 0.2 seconds = 2 tokens
    
    # Should have refilled some tokens
    available = bucket.get_available_tokens()
    assert available >= 1  # At least 1 token refilled


@pytest.mark.asyncio
async def test_token_bucket_wait():
    """Test token bucket waiting for tokens."""
    bucket = TokenBucket(rate=5, burst_size=1)  # 5 tokens/sec, burst of 1
    
    # Use the one token
    await bucket.acquire(tokens=1, wait=False)
    
    # Request more - should wait
    start = time.time()
    await bucket.acquire(tokens=1, wait=True)
    elapsed = time.time() - start
    
    # Should have waited ~0.2 seconds for 1 token at 5/sec
    assert elapsed >= 0.15  # Allow some slack
