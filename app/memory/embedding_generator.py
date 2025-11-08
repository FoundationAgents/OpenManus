"""Embedding generator with support for multiple providers."""

import asyncio
import hashlib
import json
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from anthropic import Anthropic, APIError, RateLimitError
from openai import OpenAI, APIError as OpenAIAPIError, RateLimitError as OpenAIRateLimitError


class EmbeddingCache:
    """In-memory cache for embeddings."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
    
    def get(self, text_hash: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        with self._lock:
            return self.cache.get(text_hash)
    
    def set(self, text_hash: str, embedding: List[float]):
        """Set embedding in cache."""
        with self._lock:
            if len(self.cache) >= self.max_size:
                self.cache.pop(next(iter(self.cache)))
            self.cache[text_hash] = embedding
    
    def clear(self):
        """Clear the cache."""
        with self._lock:
            self.cache.clear()


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        self.last_request_time = time.time()
        self.tokens = self.requests_per_second
        self._lock = threading.Lock()
    
    def acquire(self):
        """Acquire a token, blocking if necessary."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            self.tokens = min(self.requests_per_second, self.tokens + elapsed * self.requests_per_second)
            self.last_request_time = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            
            wait_time = (1.0 - self.tokens) / self.requests_per_second
            time.sleep(wait_time)
            self.tokens = 0.0


class EmbeddingGenerator:
    """Generates embeddings using configurable providers."""
    
    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        fallback_provider: str = "openai",
        fallback_model: str = "text-embedding-3-small",
        batch_size: int = 10,
        rate_limit_rpm: int = 3000,
        cache_embeddings: bool = True,
        cache_max_size: int = 10000,
        api_key: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
    ):
        """Initialize the embedding generator.
        
        Args:
            provider: Primary embedding provider (anthropic, openai)
            model: Primary embedding model
            fallback_provider: Fallback provider
            fallback_model: Fallback model
            batch_size: Batch size for requests
            rate_limit_rpm: Requests per minute rate limit
            cache_embeddings: Whether to cache embeddings
            cache_max_size: Maximum cache size
            api_key: API key for primary provider
            fallback_api_key: API key for fallback provider
        """
        self.provider = provider
        self.model = model
        self.fallback_provider = fallback_provider
        self.fallback_model = fallback_model
        self.batch_size = batch_size
        self.rate_limit_rpm = rate_limit_rpm
        
        self._init_clients(api_key, fallback_api_key)
        
        self.cache = EmbeddingCache(max_size=cache_max_size) if cache_embeddings else None
        self.rate_limiter = RateLimiter(rate_limit_rpm)
        self._lock = threading.RLock()
        self.request_history: Deque[datetime] = deque(maxlen=100)
    
    def _init_clients(self, api_key: Optional[str] = None, fallback_api_key: Optional[str] = None):
        """Initialize API clients."""
        if self.provider == "anthropic":
            self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        elif self.provider == "openai":
            self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        else:
            self.client = None
        
        if self.fallback_provider == "anthropic":
            self.fallback_client = Anthropic(api_key=fallback_api_key) if fallback_api_key else Anthropic()
        elif self.fallback_provider == "openai":
            self.fallback_client = OpenAI(api_key=fallback_api_key) if fallback_api_key else OpenAI()
        else:
            self.fallback_client = None
    
    def _get_text_hash(self, text: str) -> str:
        """Get hash of text for caching."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None on failure
        """
        with self._lock:
            text_hash = self._get_text_hash(text)
            
            if self.cache:
                cached = self.cache.get(text_hash)
                if cached:
                    return cached
            
            self.rate_limiter.acquire()
            
            embedding = self._generate_with_provider(
                text,
                self.provider,
                self.model,
                self.client,
            )
            
            if embedding is None and self.fallback_client:
                embedding = self._generate_with_provider(
                    text,
                    self.fallback_provider,
                    self.fallback_model,
                    self.fallback_client,
                )
            
            if embedding and self.cache:
                self.cache.set(text_hash, embedding)
            
            self.request_history.append(datetime.now(timezone.utc))
            
            return embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (or None for failed items)
        """
        results = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = []
            
            for text in batch:
                embedding = self.generate_embedding(text)
                batch_results.append(embedding)
            
            results.extend(batch_results)
        
        return results
    
    async def generate_embedding_async(self, text: str) -> Optional[List[float]]:
        """Generate embedding asynchronously.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None on failure
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_embedding, text)
    
    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts asynchronously.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        tasks = [self.generate_embedding_async(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _generate_with_provider(
        self,
        text: str,
        provider: str,
        model: str,
        client: Any,
    ) -> Optional[List[float]]:
        """Generate embedding using a specific provider.
        
        Args:
            text: Text to embed
            provider: Provider name
            model: Model name
            client: API client
            
        Returns:
            Embedding vector or None on failure
        """
        if not client:
            return None
        
        try:
            if provider == "openai":
                response = client.embeddings.create(
                    input=text,
                    model=model,
                )
                return response.data[0].embedding
            
            elif provider == "anthropic":
                response = client.messages.create(
                    model=model,
                    max_tokens=1024,
                    system="You are an embedding generator. Return a JSON array representing the semantic embedding of the input text. The embedding should be a list of 1536 float values between -1 and 1.",
                    messages=[
                        {
                            "role": "user",
                            "content": f"Generate embedding for: {text}",
                        }
                    ],
                )
                
                try:
                    content = response.content[0].text
                    embedding = json.loads(content)
                    if isinstance(embedding, list) and len(embedding) > 0:
                        return embedding[:1536]
                except (json.JSONDecodeError, IndexError, TypeError):
                    pass
            
            return None
        
        except (RateLimitError, OpenAIRateLimitError) as e:
            time.sleep(60)
            return self._generate_with_provider(text, provider, model, client)
        
        except (APIError, OpenAIAPIError) as e:
            return None
    
    def clear_cache(self):
        """Clear the embedding cache."""
        if self.cache:
            self.cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding generator statistics.
        
        Returns:
            Dictionary containing statistics
        """
        with self._lock:
            return {
                "provider": self.provider,
                "model": self.model,
                "fallback_provider": self.fallback_provider,
                "fallback_model": self.fallback_model,
                "cache_enabled": self.cache is not None,
                "cache_size": len(self.cache.cache) if self.cache else 0,
                "recent_requests": len(self.request_history),
                "rate_limit_rpm": self.rate_limit_rpm,
            }


class EmbeddingService:
    """Service for managing embeddings across the system."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.generator: Optional[EmbeddingGenerator] = None
            self._initialized = True
    
    def initialize(
        self,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        fallback_provider: str = "openai",
        fallback_model: str = "text-embedding-3-small",
        batch_size: int = 10,
        rate_limit_rpm: int = 3000,
        cache_embeddings: bool = True,
        cache_max_size: int = 10000,
        api_key: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
    ):
        """Initialize the embedding service.
        
        Args:
            provider: Primary embedding provider
            model: Primary embedding model
            fallback_provider: Fallback provider
            fallback_model: Fallback model
            batch_size: Batch size for requests
            rate_limit_rpm: Requests per minute rate limit
            cache_embeddings: Whether to cache embeddings
            cache_max_size: Maximum cache size
            api_key: API key for primary provider
            fallback_api_key: API key for fallback provider
        """
        self.generator = EmbeddingGenerator(
            provider=provider,
            model=model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            batch_size=batch_size,
            rate_limit_rpm=rate_limit_rpm,
            cache_embeddings=cache_embeddings,
            cache_max_size=cache_max_size,
            api_key=api_key,
            fallback_api_key=fallback_api_key,
        )
    
    def get_generator(self) -> Optional[EmbeddingGenerator]:
        """Get the embedding generator."""
        return self.generator
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.generator:
            raise ValueError("Embedding service not initialized")
        return self.generator.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        if not self.generator:
            raise ValueError("Embedding service not initialized")
        return self.generator.generate_embeddings_batch(texts)


def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service."""
    return EmbeddingService()
