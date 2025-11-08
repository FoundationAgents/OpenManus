"""Caching layer for retrieval results and embeddings."""

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


@dataclass
class CacheEntry:
    """Represents a cache entry with TTL support."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: Optional[int] = None  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def get_age(self) -> float:
        """Get the age of the entry in seconds."""
        return time.time() - self.created_at


class RetrievalCache(BaseModel):
    """Cache for retrieval results and queries."""
    
    cache: Dict[str, CacheEntry] = Field(default_factory=dict)
    max_size: int = Field(default=1000)
    default_ttl: Optional[int] = Field(default=3600, description="Default TTL in seconds")
    
    class Config:
        arbitrary_types_allowed = True
    
    def _hash_key(self, key: str) -> str:
        """Generate hash key for caching."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Put a value in the cache."""
        # Use default TTL if not specified
        cache_ttl = ttl if ttl is not None else self.default_ttl
        
        hash_key = self._hash_key(key)
        
        # Remove expired entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict()
        
        self.cache[hash_key] = CacheEntry(
            key=key,
            value=value,
            ttl=cache_ttl
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        hash_key = self._hash_key(key)
        
        if hash_key not in self.cache:
            return None
        
        entry = self.cache[hash_key]
        
        if entry.is_expired():
            del self.cache[hash_key]
            return None
        
        return entry.value
    
    def remove(self, key: str) -> bool:
        """Remove a value from the cache."""
        hash_key = self._hash_key(key)
        if hash_key in self.cache:
            del self.cache[hash_key]
            return True
        return False
    
    def contains(self, key: str) -> bool:
        """Check if a key is in the cache."""
        hash_key = self._hash_key(key)
        
        if hash_key not in self.cache:
            return False
        
        entry = self.cache[hash_key]
        
        if entry.is_expired():
            del self.cache[hash_key]
            return False
        
        return True
    
    def _evict(self) -> None:
        """Evict expired or least recently used entries."""
        # First, remove all expired entries
        expired_keys = []
        for hash_key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(hash_key)
        
        for hash_key in expired_keys:
            del self.cache[hash_key]
        
        # If still over size, remove oldest entries
        if len(self.cache) >= self.max_size:
            # Sort by creation time and remove oldest
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].created_at
            )
            
            # Remove oldest 10% of entries
            remove_count = max(1, len(self.cache) // 10)
            for hash_key, _ in sorted_entries[:remove_count]:
                del self.cache[hash_key]
    
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get the current cache size."""
        return len(self.cache)
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries and return count."""
        expired_keys = []
        for hash_key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(hash_key)
        
        for hash_key in expired_keys:
            del self.cache[hash_key]
        
        return len(expired_keys)


class EmbeddingCache(BaseModel):
    """Specialized cache for text embeddings."""
    
    embeddings: Dict[str, List[float]] = Field(default_factory=dict)
    max_size: int = Field(default=10000)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def put(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding for text."""
        if len(self.embeddings) >= self.max_size:
            # Simple LRU: remove first (oldest) entry
            first_key = next(iter(self.embeddings))
            del self.embeddings[first_key]
        
        hash_key = self._hash_text(text)
        self.embeddings[hash_key] = embedding
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text."""
        hash_key = self._hash_text(text)
        return self.embeddings.get(hash_key)
    
    def batch_get(self, texts: List[str]) -> Tuple[List[str], List[int]]:
        """Get cached embeddings and return uncached texts with their indices."""
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if self.get(text) is None:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        return uncached_texts, uncached_indices
    
    def clear(self) -> None:
        """Clear the embedding cache."""
        self.embeddings.clear()
    
    def size(self) -> int:
        """Get the cache size."""
        return len(self.embeddings)
