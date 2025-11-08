"""Tests for optimization module."""

import pytest

from app.tool.base import ToolResult
from app.tool_calling.optimization import (
    OptimizationManager,
    ToolExecutionCache,
    get_optimization_manager,
)


class TestToolExecutionCache:
    """Tests for ToolExecutionCache."""
    
    def test_cache_creation(self):
        """Test creating a cache."""
        cache = ToolExecutionCache(max_size=100, ttl=60)
        
        assert cache.max_size == 100
        assert cache.ttl == 60
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache."""
        cache = ToolExecutionCache()
        
        result = ToolResult(output="test output")
        cache.set("test_tool", {"arg": "value"}, result)
        
        cached = cache.get("test_tool", {"arg": "value"})
        
        assert cached is not None
        assert cached.output == "test output"
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = ToolExecutionCache()
        
        cached = cache.get("test_tool", {"arg": "value"})
        
        assert cached is None
    
    def test_cache_different_args(self):
        """Test cache with different arguments."""
        cache = ToolExecutionCache()
        
        result1 = ToolResult(output="output1")
        result2 = ToolResult(output="output2")
        
        cache.set("test_tool", {"arg": "value1"}, result1)
        cache.set("test_tool", {"arg": "value2"}, result2)
        
        cached1 = cache.get("test_tool", {"arg": "value1"})
        cached2 = cache.get("test_tool", {"arg": "value2"})
        
        assert cached1.output == "output1"
        assert cached2.output == "output2"
    
    def test_cache_eviction(self):
        """Test cache eviction when full."""
        cache = ToolExecutionCache(max_size=2)
        
        result1 = ToolResult(output="output1")
        result2 = ToolResult(output="output2")
        result3 = ToolResult(output="output3")
        
        cache.set("tool1", {}, result1)
        cache.set("tool2", {}, result2)
        cache.set("tool3", {}, result3)
        
        # Should have evicted oldest entry
        stats = cache.get_stats()
        assert stats['size'] == 2
    
    def test_cache_clear(self):
        """Test clearing cache."""
        cache = ToolExecutionCache()
        
        cache.set("test_tool", {"arg": "value"}, ToolResult(output="test"))
        cache.clear()
        
        cached = cache.get("test_tool", {"arg": "value"})
        assert cached is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = ToolExecutionCache()
        
        result = ToolResult(output="test")
        cache.set("test_tool", {"arg": "value"}, result)
        
        # Hit
        cache.get("test_tool", {"arg": "value"})
        
        # Miss
        cache.get("test_tool", {"arg": "different"})
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['total'] == 2
        assert stats['hit_rate'] == 0.5


class TestOptimizationManager:
    """Tests for OptimizationManager."""
    
    def test_manager_creation(self):
        """Test creating optimization manager."""
        manager = OptimizationManager(
            enable_caching=True,
            enable_parallel=True
        )
        
        assert manager.enable_caching
        assert manager.enable_parallel
        assert manager.cache is not None
    
    def test_manager_no_caching(self):
        """Test manager with caching disabled."""
        manager = OptimizationManager(enable_caching=False)
        
        assert not manager.enable_caching
        assert manager.cache is None
    
    def test_should_cache(self):
        """Test determining if tool should be cached."""
        manager = OptimizationManager()
        
        # Should cache most tools
        assert manager.should_cache("web_search")
        assert manager.should_cache("http_request")
        
        # Should not cache tools with side effects
        assert not manager.should_cache("bash")
        assert not manager.should_cache("python_execute")
    
    def test_get_cached_result(self):
        """Test getting cached result."""
        manager = OptimizationManager(enable_caching=True)
        
        # Should return None if not cached
        result = manager.get_cached_result("web_search", {"query": "test"})
        assert result is None
    
    def test_cache_result(self):
        """Test caching a result."""
        manager = OptimizationManager(enable_caching=True)
        
        result = ToolResult(output="test output")
        manager.cache_result("web_search", {"query": "test"}, result)
        
        cached = manager.get_cached_result("web_search", {"query": "test"})
        assert cached is not None
        assert cached.output == "test output"
    
    def test_cache_stats(self):
        """Test getting cache statistics."""
        manager = OptimizationManager(enable_caching=True)
        
        stats = manager.get_cache_stats()
        
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'size' in stats


class TestGlobalOptimizationManager:
    """Tests for global optimization manager."""
    
    def test_get_global_manager(self):
        """Test getting global manager."""
        manager = get_optimization_manager()
        
        assert manager is not None
        assert isinstance(manager, OptimizationManager)
    
    def test_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        manager1 = get_optimization_manager()
        manager2 = get_optimization_manager()
        
        assert manager1 is manager2


class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_same_args_same_key(self):
        """Test that same arguments generate same key."""
        cache = ToolExecutionCache()
        
        result1 = ToolResult(output="test")
        cache.set("tool", {"a": 1, "b": 2}, result1)
        
        # Should hit cache with same args (different order)
        cached = cache.get("tool", {"b": 2, "a": 1})
        assert cached is not None
    
    def test_different_args_different_key(self):
        """Test that different arguments generate different keys."""
        cache = ToolExecutionCache()
        
        result1 = ToolResult(output="test1")
        cache.set("tool", {"a": 1}, result1)
        
        # Should miss cache with different args
        cached = cache.get("tool", {"a": 2})
        assert cached is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
