"""Tests for response cache."""

import pytest
import time
from app.network.cache import ResponseCache, CacheEntry


def test_cache_initialization():
    """Test cache initialization."""
    cache = ResponseCache(max_size=100, default_ttl=60)
    assert len(cache) == 0
    assert cache.max_size == 100
    assert cache.default_ttl == 60


def test_cache_set_and_get():
    """Test setting and getting cached values."""
    cache = ResponseCache(default_ttl=60)
    
    # Set value
    cache.set("GET", "http://example.com", {"data": "test"})
    
    # Get value
    result = cache.get("GET", "http://example.com")
    assert result is not None
    assert result["data"] == "test"


def test_cache_miss():
    """Test cache miss."""
    cache = ResponseCache()
    
    result = cache.get("GET", "http://nonexistent.com")
    assert result is None


def test_cache_expiration():
    """Test cache entry expiration."""
    cache = ResponseCache(default_ttl=1)  # 1 second TTL
    
    # Set value
    cache.set("GET", "http://example.com", {"data": "test"})
    
    # Should be available immediately
    result = cache.get("GET", "http://example.com")
    assert result is not None
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired
    result = cache.get("GET", "http://example.com")
    assert result is None


def test_cache_custom_ttl():
    """Test custom TTL for cache entry."""
    cache = ResponseCache(default_ttl=60)
    
    # Set with custom TTL
    cache.set("GET", "http://example.com", {"data": "test"}, ttl=2)
    
    # Should be available
    result = cache.get("GET", "http://example.com")
    assert result is not None
    
    # Wait for custom TTL
    time.sleep(2.1)
    
    # Should be expired
    result = cache.get("GET", "http://example.com")
    assert result is None


def test_cache_lru_eviction():
    """Test LRU eviction when cache is full."""
    cache = ResponseCache(max_size=3)
    
    # Fill cache
    cache.set("GET", "http://example.com/1", {"data": "1"})
    cache.set("GET", "http://example.com/2", {"data": "2"})
    cache.set("GET", "http://example.com/3", {"data": "3"})
    
    assert len(cache) == 3
    
    # Add one more - should evict oldest (1)
    cache.set("GET", "http://example.com/4", {"data": "4"})
    
    assert len(cache) == 3
    
    # First entry should be evicted
    result = cache.get("GET", "http://example.com/1")
    assert result is None
    
    # Others should still be there
    assert cache.get("GET", "http://example.com/2") is not None
    assert cache.get("GET", "http://example.com/3") is not None
    assert cache.get("GET", "http://example.com/4") is not None


def test_cache_invalidate():
    """Test cache invalidation."""
    cache = ResponseCache()
    
    # Set value
    cache.set("GET", "http://example.com", {"data": "test"})
    assert cache.get("GET", "http://example.com") is not None
    
    # Invalidate
    cache.invalidate("GET", "http://example.com")
    
    # Should be gone
    result = cache.get("GET", "http://example.com")
    assert result is None


def test_cache_clear():
    """Test clearing entire cache."""
    cache = ResponseCache()
    
    # Add multiple entries
    cache.set("GET", "http://example.com/1", {"data": "1"})
    cache.set("GET", "http://example.com/2", {"data": "2"})
    cache.set("GET", "http://example.com/3", {"data": "3"})
    
    assert len(cache) == 3
    
    # Clear cache
    cache.clear()
    
    assert len(cache) == 0


def test_cache_stats():
    """Test cache statistics."""
    cache = ResponseCache()
    
    # Set and get some values
    cache.set("GET", "http://example.com/1", {"data": "1"})
    cache.set("GET", "http://example.com/2", {"data": "2"})
    
    # Cache hit
    cache.get("GET", "http://example.com/1")
    
    # Cache miss
    cache.get("GET", "http://nonexistent.com")
    
    stats = cache.get_stats()
    
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.entry_count == 2
    assert 0 < stats.hit_rate <= 1.0


def test_cache_key_generation():
    """Test cache key generation with different parameters."""
    cache = ResponseCache()
    
    # Same URL, different params
    cache.set("GET", "http://example.com", {"data": "1"}, params={"a": "1"})
    cache.set("GET", "http://example.com", {"data": "2"}, params={"a": "2"})
    
    # Should be different entries
    result1 = cache.get("GET", "http://example.com", params={"a": "1"})
    result2 = cache.get("GET", "http://example.com", params={"a": "2"})
    
    assert result1["data"] == "1"
    assert result2["data"] == "2"


def test_cache_entry_is_expired():
    """Test CacheEntry expiration check."""
    # Non-expiring entry
    entry1 = CacheEntry(
        key="test",
        value="data",
        timestamp=time.time(),
        ttl=0  # No expiration
    )
    assert entry1.is_expired() is False
    
    # Expired entry
    entry2 = CacheEntry(
        key="test",
        value="data",
        timestamp=time.time() - 10,
        ttl=5  # 5 seconds, expired 5 seconds ago
    )
    assert entry2.is_expired() is True
    
    # Not yet expired
    entry3 = CacheEntry(
        key="test",
        value="data",
        timestamp=time.time(),
        ttl=60  # 60 seconds
    )
    assert entry3.is_expired() is False


def test_cache_memory_limit():
    """Test cache memory limit enforcement."""
    # Small memory limit
    cache = ResponseCache(max_memory_mb=1)
    
    # Add large entries
    large_data = "x" * 100000  # ~100KB
    
    for i in range(20):
        cache.set("GET", f"http://example.com/{i}", {"data": large_data})
    
    # Cache should have evicted some entries to stay under limit
    stats = cache.get_stats()
    assert stats.total_size_bytes < 1 * 1024 * 1024  # Under 1MB


def test_cache_hit_count():
    """Test cache entry hit count tracking."""
    cache = ResponseCache()
    
    cache.set("GET", "http://example.com", {"data": "test"})
    
    # Access multiple times
    for _ in range(5):
        cache.get("GET", "http://example.com")
    
    stats = cache.get_stats()
    assert stats.hits == 5
