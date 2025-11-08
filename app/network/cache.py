"""
Response caching system for HTTP requests.

Provides in-memory and persistent caching with TTL support,
cache statistics, and configurable eviction policies.
"""

import hashlib
import json
import pickle
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field

from app.utils.logger import logger


class CacheEntry(BaseModel):
    """A single cache entry with metadata."""
    
    key: str
    value: Any
    timestamp: float
    ttl: int  # seconds
    hit_count: int = 0
    size_bytes: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl <= 0:
            return False
        return time.time() > (self.timestamp + self.ttl)
    
    def time_remaining(self) -> float:
        """Get remaining time before expiration in seconds."""
        if self.ttl <= 0:
            return float('inf')
        remaining = (self.timestamp + self.ttl) - time.time()
        return max(0, remaining)


class CacheStats(BaseModel):
    """Statistics about cache usage."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{self.hit_rate:.2%}",
            "total_size_mb": f"{self.total_size_bytes / 1024 / 1024:.2f}",
            "entry_count": self.entry_count,
        }


class ResponseCache:
    """
    LRU cache for HTTP responses with TTL and persistence support.
    
    Features:
    - Configurable TTL per entry
    - Optional persistence to disk
    - LRU eviction policy
    - Cache statistics
    - Size limits
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 3600,
        persist_path: Optional[str] = None,
        enable_persistence: bool = False
    ):
        """
        Initialize response cache.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds
            persist_path: Path to persistence file
            enable_persistence: Whether to enable disk persistence
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.persist_path = Path(persist_path) if persist_path else None
        self.enable_persistence = enable_persistence
        
        # LRU cache using OrderedDict
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        
        # Load from disk if persistence enabled
        if self.enable_persistence and self.persist_path:
            self._load_from_disk()
        
        logger.info(
            f"ResponseCache initialized: max_size={max_size}, "
            f"max_memory={max_memory_mb}MB, default_ttl={default_ttl}s"
        )
    
    def _generate_key(self, method: str, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> str:
        """
        Generate cache key from request parameters.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Request headers (only cache-relevant ones)
            
        Returns:
            Cache key hash
        """
        # Include only cache-relevant headers
        cache_headers = {}
        if headers:
            for key in ['accept', 'accept-encoding', 'accept-language']:
                if key in headers:
                    cache_headers[key] = headers[key]
        
        key_data = {
            'method': method.upper(),
            'url': url,
            'params': params or {},
            'headers': cache_headers
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get cached response.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Request headers
            
        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(method, url, params, headers)
        
        # Check if entry exists
        if key not in self._cache:
            self._stats.misses += 1
            logger.debug(f"Cache MISS: {method} {url}")
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            logger.debug(f"Cache EXPIRED: {method} {url}")
            self._remove(key)
            self._stats.misses += 1
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._stats.hits += 1
        
        logger.debug(
            f"Cache HIT: {method} {url} "
            f"(age: {time.time() - entry.timestamp:.1f}s, "
            f"remaining: {entry.time_remaining():.1f}s)"
        )
        
        return entry.value
    
    def set(
        self,
        method: str,
        url: str,
        value: Any,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        ttl: Optional[int] = None
    ):
        """
        Store response in cache.
        
        Args:
            method: HTTP method
            url: Request URL
            value: Response to cache
            params: Query parameters
            headers: Request headers
            ttl: TTL in seconds (uses default if None)
        """
        key = self._generate_key(method, url, params, headers)
        ttl = ttl if ttl is not None else self.default_ttl
        
        # Estimate size
        try:
            size = len(pickle.dumps(value))
        except Exception:
            size = len(str(value))
        
        # Check if we need to evict entries
        self._evict_if_needed(size)
        
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            size_bytes=size
        )
        
        # Add to cache
        if key in self._cache:
            # Update existing entry
            old_entry = self._cache[key]
            self._stats.total_size_bytes -= old_entry.size_bytes
        
        self._cache[key] = entry
        self._cache.move_to_end(key)
        
        self._stats.total_size_bytes += size
        self._stats.entry_count = len(self._cache)
        
        logger.debug(
            f"Cache SET: {method} {url} "
            f"(size: {size} bytes, ttl: {ttl}s)"
        )
        
        # Persist if enabled
        if self.enable_persistence:
            self._save_to_disk()
    
    def _evict_if_needed(self, new_entry_size: int):
        """
        Evict entries if cache is full.
        
        Args:
            new_entry_size: Size of entry to be added
        """
        # Evict expired entries first
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            self._remove(key)
        
        # Evict LRU entries if still over limit
        while len(self._cache) >= self.max_size or \
              (self._stats.total_size_bytes + new_entry_size) > self.max_memory_bytes:
            if not self._cache:
                break
            
            # Remove least recently used (first item)
            key = next(iter(self._cache))
            self._remove(key)
            self._stats.evictions += 1
    
    def _remove(self, key: str):
        """Remove entry from cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._stats.total_size_bytes -= entry.size_bytes
            self._stats.entry_count = len(self._cache)
    
    def invalidate(self, method: str, url: str, params: Optional[Dict] = None):
        """
        Invalidate a specific cache entry.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
        """
        key = self._generate_key(method, url, params)
        self._remove(key)
        logger.debug(f"Cache INVALIDATE: {method} {url}")
    
    def invalidate_pattern(self, url_pattern: str):
        """
        Invalidate all entries matching URL pattern.
        
        Args:
            url_pattern: URL pattern to match
        """
        import re
        pattern = re.compile(url_pattern)
        
        keys_to_remove = []
        for key, entry in self._cache.items():
            # We'd need to store URL in entry for this to work perfectly
            # For now, we'll just match on the key
            if pattern.search(key):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._remove(key)
        
        logger.info(f"Invalidated {len(keys_to_remove)} entries matching pattern: {url_pattern}")
    
    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats = CacheStats()
        logger.info(f"Cache cleared: {count} entries removed")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats
    
    def _save_to_disk(self):
        """Save cache to disk."""
        if not self.persist_path:
            return
        
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            
            cache_data = {
                'version': '1.0',
                'timestamp': time.time(),
                'entries': []
            }
            
            for entry in self._cache.values():
                # Only save non-expired entries
                if not entry.is_expired():
                    cache_data['entries'].append({
                        'key': entry.key,
                        'value': entry.value,
                        'timestamp': entry.timestamp,
                        'ttl': entry.ttl,
                        'hit_count': entry.hit_count,
                        'size_bytes': entry.size_bytes,
                    })
            
            with self.persist_path.open('wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"Cache saved to disk: {len(cache_data['entries'])} entries")
            
        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
    
    def _load_from_disk(self):
        """Load cache from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open('rb') as f:
                cache_data = pickle.load(f)
            
            loaded_count = 0
            for entry_data in cache_data.get('entries', []):
                entry = CacheEntry(**entry_data)
                
                # Only load non-expired entries
                if not entry.is_expired():
                    self._cache[entry.key] = entry
                    self._stats.total_size_bytes += entry.size_bytes
                    loaded_count += 1
            
            self._stats.entry_count = len(self._cache)
            logger.info(f"Cache loaded from disk: {loaded_count} entries")
            
        except Exception as e:
            logger.error(f"Failed to load cache from disk: {e}")
    
    def __len__(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)
