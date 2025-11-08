"""Unit tests for the EmbeddingGenerator module."""

import unittest
from unittest.mock import MagicMock, patch

from app.memory.embedding_generator import (
    EmbeddingCache,
    EmbeddingGenerator,
    EmbeddingService,
    RateLimiter,
    get_embedding_service,
)


class TestEmbeddingCache(unittest.TestCase):
    """Test cases for EmbeddingCache."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = EmbeddingCache(max_size=3)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cached embeddings."""
        text_hash = "test_hash"
        embedding = [0.1, 0.2, 0.3]
        
        self.cache.set(text_hash, embedding)
        retrieved = self.cache.get(text_hash)
        
        self.assertEqual(retrieved, embedding)
    
    def test_cache_miss(self):
        """Test cache miss."""
        retrieved = self.cache.get("nonexistent")
        self.assertIsNone(retrieved)
    
    def test_cache_eviction(self):
        """Test cache eviction when max size is reached."""
        self.cache.set("hash1", [1.0])
        self.cache.set("hash2", [2.0])
        self.cache.set("hash3", [3.0])
        self.cache.set("hash4", [4.0])
        
        self.assertEqual(len(self.cache.cache), 3)
    
    def test_cache_clear(self):
        """Test clearing the cache."""
        self.cache.set("hash1", [1.0])
        self.cache.set("hash2", [2.0])
        
        self.cache.clear()
        
        self.assertEqual(len(self.cache.cache), 0)


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=600)
        
        self.assertEqual(limiter.requests_per_minute, 600)
        self.assertGreater(limiter.requests_per_second, 0)
    
    def test_rate_limiter_acquire(self):
        """Test acquiring tokens."""
        limiter = RateLimiter(requests_per_minute=600)
        
        initial_tokens = limiter.tokens
        limiter.acquire()
        self.assertLessEqual(limiter.tokens, initial_tokens)


class TestEmbeddingGenerator(unittest.TestCase):
    """Test cases for EmbeddingGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('app.memory.embedding_generator.OpenAI'):
            with patch('app.memory.embedding_generator.Anthropic'):
                self.generator = EmbeddingGenerator(
                    provider="openai",
                    model="text-embedding-3-small",
                    fallback_provider="openai",
                    fallback_model="text-embedding-3-small",
                    cache_embeddings=True,
                    rate_limit_rpm=10000,
                    api_key="test-key",
                    fallback_api_key="test-key",
                )
    
    def test_initialization(self):
        """Test generator initialization."""
        self.assertEqual(self.generator.provider, "openai")
        self.assertEqual(self.generator.model, "text-embedding-3-small")
        self.assertIsNotNone(self.generator.cache)
    
    def test_get_text_hash(self):
        """Test text hashing."""
        text = "test text"
        hash1 = self.generator._get_text_hash(text)
        hash2 = self.generator._get_text_hash(text)
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)
    
    def test_cache_integration(self):
        """Test cache integration."""
        text = "test text"
        text_hash = self.generator._get_text_hash(text)
        embedding = [0.1, 0.2, 0.3]
        
        self.generator.cache.set(text_hash, embedding)
        
        retrieved = self.generator.generate_embedding(text)
        
        self.assertEqual(retrieved, embedding)
    
    def test_clear_cache(self):
        """Test cache clearing."""
        text = "test text"
        text_hash = self.generator._get_text_hash(text)
        self.generator.cache.set(text_hash, [0.1, 0.2])
        
        self.generator.clear_cache()
        
        self.assertEqual(len(self.generator.cache.cache), 0)
    
    @patch('app.memory.embedding_generator.OpenAI')
    def test_generate_embedding_openai(self, mock_openai_class):
        """Test embedding generation with OpenAI."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        
        generator = EmbeddingGenerator(
            provider="openai",
            model="text-embedding-3-small",
            cache_embeddings=False,
        )
        generator.client = mock_client
        
        embedding = generator.generate_embedding("test text")
        
        self.assertIsNotNone(embedding)
    
    def test_get_statistics(self):
        """Test getting generator statistics."""
        stats = self.generator.get_statistics()
        
        self.assertIn("provider", stats)
        self.assertIn("model", stats)
        self.assertIn("cache_enabled", stats)
        self.assertEqual(stats["provider"], "openai")


class TestEmbeddingService(unittest.TestCase):
    """Test cases for EmbeddingService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = EmbeddingService()
    
    def test_singleton_pattern(self):
        """Test that service follows singleton pattern."""
        service1 = EmbeddingService()
        service2 = EmbeddingService()
        
        self.assertIs(service1, service2)
    
    def test_get_embedding_service(self):
        """Test getting embedding service."""
        service = get_embedding_service()
        
        self.assertIsInstance(service, EmbeddingService)
    
    def test_initialization(self):
        """Test service initialization."""
        with patch('app.memory.embedding_generator.OpenAI'):
            with patch('app.memory.embedding_generator.Anthropic'):
                self.service.initialize(
                    provider="openai",
                    model="text-embedding-3-small",
                    rate_limit_rpm=10000,
                    api_key="test-key",
                    fallback_api_key="test-key",
                )
        
        self.assertIsNotNone(self.service.generator)
        self.assertEqual(self.service.generator.provider, "openai")
    
    def test_uninitialized_service_error(self):
        """Test error when service is not initialized."""
        service = EmbeddingService()
        service.generator = None
        
        with self.assertRaises(ValueError):
            service.generate_embedding("test")
    
    def test_get_generator(self):
        """Test getting the generator."""
        with patch('app.memory.embedding_generator.OpenAI'):
            with patch('app.memory.embedding_generator.Anthropic'):
                self.service.initialize(
                    api_key="test-key",
                    fallback_api_key="test-key",
                )
        
        generator = self.service.get_generator()
        self.assertIsNotNone(generator)
        self.assertIsInstance(generator, EmbeddingGenerator)


if __name__ == "__main__":
    unittest.main()
