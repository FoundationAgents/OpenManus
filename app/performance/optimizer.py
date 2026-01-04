"""
FreEco.ai Platform - Performance Optimizer
Enhanced OpenManus with intelligent performance optimization

This module provides comprehensive performance optimization features:
- LRU caching for frequent queries
- Parallel execution for I/O-bound tasks
- Performance profiling and bottleneck detection
- Query optimization
- Memory management

Part of Enhancement #5: Performance, UX & Evaluation
"""

import functools
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def access(self):
        """Record access to this entry"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class ProfileReport:
    """Performance profiling report"""

    function_name: str
    total_calls: int
    total_time_seconds: float
    average_time_seconds: float
    min_time_seconds: float
    max_time_seconds: float
    last_call_time: datetime

    def __str__(self) -> str:
        return (
            f"{self.function_name}:\n"
            f"  Calls: {self.total_calls}\n"
            f"  Total time: {self.total_time_seconds:.3f}s\n"
            f"  Average: {self.average_time_seconds:.3f}s\n"
            f"  Min: {self.min_time_seconds:.3f}s\n"
            f"  Max: {self.max_time_seconds:.3f}s\n"
        )


@dataclass
class MemoryReport:
    """Memory usage report"""

    timestamp: datetime
    cache_entries: int
    cache_size_mb: float
    thread_pool_size: int
    active_threads: int

    def __str__(self) -> str:
        return (
            f"Memory Report ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}):\n"
            f"  Cache entries: {self.cache_entries}\n"
            f"  Cache size: {self.cache_size_mb:.2f} MB\n"
            f"  Thread pool: {self.thread_pool_size}\n"
            f"  Active threads: {self.active_threads}\n"
        )


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache

    Features:
    - Automatic eviction of least recently used items
    - TTL (Time To Live) support
    - Thread-safe operations
    - Access statistics
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        """
        Initialize LRU cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.access()
            self.hits += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (overrides default)
        """
        with self.lock:
            # Remove if exists
            if key in self.cache:
                del self.cache[key]

            # Evict if at capacity
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)  # Remove oldest

            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl or self.default_ttl,
            )
            self.cache[key] = entry

    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was removed
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
            }


class PerformanceOptimizer:
    """
    Performance optimization system

    Features:
    - Caching with LRU eviction
    - Parallel execution for I/O-bound tasks
    - Performance profiling
    - Memory management
    - Query optimization

    Example:
        optimizer = PerformanceOptimizer()

        # Cache expensive function
        @optimizer.cache(ttl=300)
        def expensive_function(x):
            time.sleep(1)
            return x * 2

        # Parallel execution
        results = optimizer.execute_parallel([
            lambda: task1(),
            lambda: task2(),
            lambda: task3(),
        ])

        # Profile function
        @optimizer.profile
        def slow_function():
            time.sleep(0.5)
    """

    def __init__(
        self,
        cache_size: int = 1000,
        default_ttl: Optional[int] = 3600,
        max_workers: int = 10,
    ):
        """
        Initialize performance optimizer

        Args:
            cache_size: Maximum cache entries
            default_ttl: Default cache TTL in seconds
            max_workers: Maximum parallel workers
        """
        self.cache = LRUCache(max_size=cache_size, default_ttl=default_ttl)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers

        # Profiling data
        self.profile_data: Dict[str, List[float]] = {}
        self.profile_lock = threading.RLock()

    def cache_result(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ):
        """
        Cache a result

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds
        """
        self.cache.set(key, value, ttl)
        logger.debug(f"Cached result: {key}")

    def get_cached(self, key: str) -> Optional[Any]:
        """
        Get cached result

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        return self.cache.get(key)

    def cache(
        self,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None,
    ) -> Callable:
        """
        Decorator for caching function results

        Args:
            ttl: Cache TTL in seconds
            key_func: Custom function to generate cache key

        Returns:
            Decorated function with caching

        Example:
            @optimizer.cache(ttl=300)
            def expensive_query(user_id: int):
                return database.query(user_id)
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func.__name__, args, kwargs)

                # Check cache
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return cached_value

                # Execute function
                logger.debug(f"Cache miss: {func.__name__}")
                result = func(*args, **kwargs)

                # Cache result
                self.cache.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator

    def execute_parallel(
        self,
        tasks: List[Callable],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """
        Execute tasks in parallel

        Args:
            tasks: List of callables to execute
            timeout: Timeout in seconds for all tasks

        Returns:
            List of results in same order as tasks

        Example:
            results = optimizer.execute_parallel([
                lambda: fetch_user(1),
                lambda: fetch_user(2),
                lambda: fetch_user(3),
            ])
        """
        if not tasks:
            return []

        # Submit all tasks
        future_to_index = {}
        for i, task in enumerate(tasks):
            future = self.executor.submit(task)
            future_to_index[future] = i

        # Collect results
        results = [None] * len(tasks)

        try:
            for future in as_completed(future_to_index.keys(), timeout=timeout):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    logger.error(f"Task {index} failed: {e}")
                    results[index] = None

        except TimeoutError:
            logger.error(f"Parallel execution timed out after {timeout}s")

        return results

    def profile(self, func: Callable) -> Callable:
        """
        Decorator for profiling function performance

        Args:
            func: Function to profile

        Returns:
            Decorated function with profiling

        Example:
            @optimizer.profile
            def slow_function():
                time.sleep(1)
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result

            finally:
                duration = time.time() - start_time

                with self.profile_lock:
                    if func.__name__ not in self.profile_data:
                        self.profile_data[func.__name__] = []
                    self.profile_data[func.__name__].append(duration)

                logger.debug(f"Profiled {func.__name__}: {duration:.3f}s")

        return wrapper

    def profile_function(self, func: Callable) -> ProfileReport:
        """
        Get profiling report for a function

        Args:
            func: Function to get report for

        Returns:
            ProfileReport with statistics
        """
        with self.profile_lock:
            func_name = func.__name__

            if func_name not in self.profile_data:
                return ProfileReport(
                    function_name=func_name,
                    total_calls=0,
                    total_time_seconds=0.0,
                    average_time_seconds=0.0,
                    min_time_seconds=0.0,
                    max_time_seconds=0.0,
                    last_call_time=datetime.now(),
                )

            times = self.profile_data[func_name]

            return ProfileReport(
                function_name=func_name,
                total_calls=len(times),
                total_time_seconds=sum(times),
                average_time_seconds=sum(times) / len(times),
                min_time_seconds=min(times),
                max_time_seconds=max(times),
                last_call_time=datetime.now(),
            )

    def get_all_profiles(self) -> List[ProfileReport]:
        """Get profiling reports for all functions"""
        with self.profile_lock:
            reports = []
            for func_name in self.profile_data.keys():
                # Create a dummy function object for reporting
                class DummyFunc:
                    __name__ = func_name

                reports.append(self.profile_function(DummyFunc()))

            return sorted(reports, key=lambda r: r.total_time_seconds, reverse=True)

    def manage_memory(self) -> MemoryReport:
        """
        Perform memory management and return report

        Returns:
            MemoryReport with current memory usage
        """
        import sys
        import threading

        # Get cache size estimate
        cache_size_bytes = sum(
            sys.getsizeof(entry.value) for entry in self.cache.cache.values()
        )
        cache_size_mb = cache_size_bytes / (1024 * 1024)

        # Get thread info
        active_threads = threading.active_count()

        report = MemoryReport(
            timestamp=datetime.now(),
            cache_entries=len(self.cache.cache),
            cache_size_mb=cache_size_mb,
            thread_pool_size=self.max_workers,
            active_threads=active_threads,
        )

        # Clean up expired cache entries
        with self.cache.lock:
            expired_keys = [
                key for key, entry in self.cache.cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self.cache.cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return report

    def _generate_cache_key(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
    ) -> str:
        """
        Generate cache key from function name and arguments

        Args:
            func_name: Function name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create hashable representation
        key_parts = [func_name]

        # Add args
        for arg in args:
            try:
                key_parts.append(json.dumps(arg, sort_keys=True))
            except (TypeError, ValueError):
                key_parts.append(str(arg))

        # Add kwargs
        for k, v in sorted(kwargs.items()):
            try:
                key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
            except (TypeError, ValueError):
                key_parts.append(f"{k}={str(v)}")

        # Hash to fixed length
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def log_performance(self, metric_name: str, value: float):
        """
        Log a custom performance metric

        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        with self.profile_lock:
            if metric_name not in self.profile_data:
                self.profile_data[metric_name] = []
            self.profile_data[metric_name].append(value)

        logger.info(f"Performance metric: {metric_name} = {value:.3f}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()

    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")

    def shutdown(self):
        """Shutdown optimizer and cleanup resources"""
        self.executor.shutdown(wait=True)
        self.cache.clear()
        logger.info("Performance optimizer shut down")


# Global optimizer instance
default_optimizer = PerformanceOptimizer()
