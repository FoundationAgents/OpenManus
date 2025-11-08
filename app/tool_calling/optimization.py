"""Performance optimization for tool calling.

Provides:
- Parallel tool execution
- Result caching
- Batch request optimization
- Early termination
"""

import asyncio
import hashlib
import json
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from app.logger import logger
from app.tool.base import ToolResult


class ToolExecutionCache:
    """Cache for tool execution results."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize cache.
        
        Args:
            max_size: Maximum number of cached results
            ttl: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[ToolResult, float]] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate cache key.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            
        Returns:
            Cache key
        """
        # Sort args for consistent hashing
        args_str = json.dumps(args, sort_keys=True)
        key_str = f"{tool_name}:{args_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Optional[ToolResult]:
        """Get cached result.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            
        Returns:
            Cached result or None
        """
        key = self._generate_key(tool_name, args)
        
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                
                # Check if expired
                import time
                if time.time() - timestamp <= self.ttl:
                    self._hits += 1
                    logger.debug(f"Cache hit for {tool_name}")
                    return result
                else:
                    # Remove expired entry
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: ToolResult
    ):
        """Cache a result.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            result: Tool result
        """
        key = self._generate_key(tool_name, args)
        
        with self._lock:
            import time
            self._cache[key] = (result, time.time())
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                # Remove oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            logger.debug("Cleared tool execution cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'total': total,
                'hit_rate': hit_rate,
                'size': len(self._cache),
                'max_size': self.max_size
            }


class ParallelExecutor:
    """Execute multiple tools in parallel."""
    
    def __init__(self, max_workers: int = 5):
        """Initialize executor.
        
        Args:
            max_workers: Maximum number of parallel executions
        """
        self.max_workers = max_workers
    
    async def execute_parallel(
        self,
        tool_calls: List[Tuple[str, Any, Dict[str, Any]]],
        timeout: Optional[float] = None
    ) -> Dict[str, ToolResult]:
        """Execute multiple tool calls in parallel.
        
        Args:
            tool_calls: List of (call_id, tool_instance, args) tuples
            timeout: Optional timeout for all executions
            
        Returns:
            Dictionary mapping call_ids to results
        """
        if not tool_calls:
            return {}
        
        logger.info(f"Executing {len(tool_calls)} tools in parallel")
        
        # Create tasks
        tasks = []
        call_ids = []
        
        for call_id, tool_instance, args in tool_calls:
            call_ids.append(call_id)
            task = self._execute_single(tool_instance, args)
            tasks.append(task)
        
        # Execute with timeout
        try:
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            logger.error(f"Parallel execution timed out after {timeout}s")
            return {
                call_id: ToolResult(error=f"Execution timed out after {timeout}s")
                for call_id in call_ids
            }
        
        # Map results to call IDs
        result_dict = {}
        for call_id, result in zip(call_ids, results):
            if isinstance(result, Exception):
                result_dict[call_id] = ToolResult(error=str(result))
            else:
                result_dict[call_id] = result
        
        return result_dict
    
    async def _execute_single(self, tool_instance: Any, args: Dict[str, Any]) -> ToolResult:
        """Execute a single tool.
        
        Args:
            tool_instance: Tool instance
            args: Tool arguments
            
        Returns:
            ToolResult
        """
        try:
            result = await tool_instance.execute(**args)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(error=str(e))


class DependencyAnalyzer:
    """Analyze dependencies between tool calls."""
    
    def __init__(self):
        self._dependencies: Dict[str, Set[str]] = {}
    
    def add_dependency(self, dependent: str, depends_on: str):
        """Add a dependency.
        
        Args:
            dependent: Tool call that depends on another
            depends_on: Tool call that must execute first
        """
        if dependent not in self._dependencies:
            self._dependencies[dependent] = set()
        self._dependencies[dependent].add(depends_on)
    
    def get_independent_groups(
        self,
        call_ids: List[str]
    ) -> List[List[str]]:
        """Get groups of independent tool calls.
        
        Args:
            call_ids: List of tool call IDs
            
        Returns:
            List of groups, where each group can be executed in parallel
        """
        # Simple implementation: all tools are independent by default
        # TODO: Implement actual dependency analysis
        
        return [call_ids]  # Single group for now
    
    def is_independent(self, call_id1: str, call_id2: str) -> bool:
        """Check if two tool calls are independent.
        
        Args:
            call_id1: First tool call ID
            call_id2: Second tool call ID
            
        Returns:
            True if independent
        """
        # Check if either depends on the other
        if call_id1 in self._dependencies.get(call_id2, set()):
            return False
        if call_id2 in self._dependencies.get(call_id1, set()):
            return False
        return True


class OptimizationManager:
    """Manage tool execution optimization."""
    
    def __init__(
        self,
        enable_caching: bool = True,
        enable_parallel: bool = True,
        cache_ttl: int = 3600,
        max_parallel: int = 5
    ):
        """Initialize optimization manager.
        
        Args:
            enable_caching: Enable result caching
            enable_parallel: Enable parallel execution
            cache_ttl: Cache TTL in seconds
            max_parallel: Maximum parallel executions
        """
        self.enable_caching = enable_caching
        self.enable_parallel = enable_parallel
        
        self.cache = ToolExecutionCache(ttl=cache_ttl) if enable_caching else None
        self.executor = ParallelExecutor(max_workers=max_parallel) if enable_parallel else None
        self.dependency_analyzer = DependencyAnalyzer()
        
        logger.info(
            f"Optimization manager initialized "
            f"(caching={enable_caching}, parallel={enable_parallel})"
        )
    
    def should_cache(self, tool_name: str) -> bool:
        """Determine if tool results should be cached.
        
        Args:
            tool_name: Tool name
            
        Returns:
            True if should cache
        """
        # Don't cache tools that have side effects or are time-sensitive
        no_cache_tools = {'bash', 'python_execute', 'terminate'}
        return tool_name not in no_cache_tools
    
    def get_cached_result(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Optional[ToolResult]:
        """Get cached result if available.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            
        Returns:
            Cached result or None
        """
        if not self.enable_caching or not self.cache:
            return None
        
        if not self.should_cache(tool_name):
            return None
        
        return self.cache.get(tool_name, args)
    
    def cache_result(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: ToolResult
    ):
        """Cache a result.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            result: Tool result
        """
        if not self.enable_caching or not self.cache:
            return
        
        if not self.should_cache(tool_name):
            return
        
        self.cache.set(tool_name, args, result)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Statistics dictionary
        """
        if self.cache:
            return self.cache.get_stats()
        return {}


# Global instance
_global_optimization_manager: Optional[OptimizationManager] = None
_manager_lock = threading.RLock()


def get_optimization_manager() -> OptimizationManager:
    """Get the global optimization manager.
    
    Returns:
        Global OptimizationManager
    """
    global _global_optimization_manager
    
    with _manager_lock:
        if _global_optimization_manager is None:
            _global_optimization_manager = OptimizationManager()
        
        return _global_optimization_manager


def set_optimization_manager(manager: OptimizationManager):
    """Set the global optimization manager.
    
    Args:
        manager: OptimizationManager instance
    """
    global _global_optimization_manager
    with _manager_lock:
        _global_optimization_manager = manager
