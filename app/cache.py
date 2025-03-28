import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Union

from diskcache import Cache

from app.config import config
from app.schema import Message


class LLMCache:
    """Cache for LLM responses to reduce API calls for identical requests."""

    def __init__(self):
        """
        Initialize the LLM cache.
        """
        self.cache_dir = config.cache_config.cache_dir
        self.cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), self.cache_dir
        )
        os.makedirs(self.cache_dir, exist_ok=True)

        self.ttl = config.cache_config.ttl
        self.cache = Cache(self.cache_dir)

    def generate_key(
        self,
        messages: List[Union[dict, Message]],
        model: str,
        tools: Optional[List[dict]] = None,
    ) -> str:
        """Generate a unique cache key based on request parameters."""
        # Convert Message objects to dicts for consistent hashing
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, Message):
                formatted_messages.append(msg.to_dict())
            else:
                formatted_messages.append(msg)

        # Create a deterministic representation of the request
        key_data = {
            "messages": formatted_messages,
            "model": model,
        }

        # Add tools to key if provided
        if tools:
            key_data["tools"] = tools

        # Create a hash of the request data
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached response if it exists and is valid."""
        cached = self.cache.get(key)
        if cached is None:
            return None

        data, timestamp = cached
        if time.time() - timestamp > self.ttl:
            # Expired cache entry
            self.cache.delete(key)
            return None

        return data

    def set(self, key: str, data: Any) -> None:
        """Store a response in the cache with the current timestamp."""
        self.cache.set(key, (data, time.time()))

    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Return cache statistics."""
        return {
            "size": len(self.cache),
            "hits": self.cache.stats(enable=True)["hits"],
            "misses": self.cache.stats(enable=True)["misses"],
        }
