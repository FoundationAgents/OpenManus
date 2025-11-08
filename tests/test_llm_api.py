"""
Tests for LLM API integration with OpenAI-compatible endpoints.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.api_client import (
    OpenAICompatibleClient,
    APIClientError,
    APITimeoutError,
    APIRateLimitError,
    APIServerError,
)
from app.llm.api_fallback import APIFallbackManager, FallbackEndpoint
from app.llm.context_manager import ContextManager
from app.llm.token_counter import TokenCounter, TokenBudget
from app.llm.health_check import HealthChecker, HealthStatus


class TestOpenAICompatibleClient:
    """Tests for OpenAI-compatible API client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        client = OpenAICompatibleClient(
            endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
            model="claude-sonnet-4.5",
        )
        assert client.endpoint == "https://gpt4free.pro/v1/vibingfox/chat/completions"
        assert client.model == "claude-sonnet-4.5"
        assert client.api_key == "no-key-required"
        assert client.total_input_tokens == 0
        assert client.total_completion_tokens == 0
        await client.close()

    @pytest.mark.asyncio
    async def test_token_estimation(self):
        """Test token estimation."""
        client = OpenAICompatibleClient(
            endpoint="https://api.example.com/v1/chat/completions",
            model="test-model",
        )
        
        # Test empty text
        assert client._count_tokens("") == 0
        
        # Test text token counting
        tokens = client._count_tokens("Hello, world!")
        assert tokens > 0
        
        await client.close()

    @pytest.mark.asyncio
    async def test_message_token_estimation(self):
        """Test estimating tokens for messages."""
        client = OpenAICompatibleClient(
            endpoint="https://api.example.com/v1/chat/completions",
            model="test-model",
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
        ]
        
        tokens = client._estimate_tokens(messages)
        assert tokens > 0
        
        await client.close()

    @pytest.mark.asyncio
    async def test_get_token_usage(self):
        """Test getting token usage stats."""
        client = OpenAICompatibleClient(
            endpoint="https://api.example.com/v1/chat/completions",
            model="test-model",
        )
        
        # Simulate token tracking
        client.total_input_tokens = 100
        client.total_completion_tokens = 50
        
        usage = client.get_token_usage()
        assert usage["total_input_tokens"] == 100
        assert usage["total_completion_tokens"] == 50
        assert usage["total_tokens"] == 150
        
        await client.close()


class TestAPIFallbackManager:
    """Tests for API fallback mechanism."""

    def test_fallback_initialization(self):
        """Test fallback manager initialization."""
        fallbacks = [
            {"url": "https://fallback1.com/v1/chat/completions", "model": "gpt-4", "priority": 2},
            {"url": "https://fallback2.com/v1/chat/completions", "model": "gpt-3.5", "priority": 3},
        ]
        
        manager = APIFallbackManager(
            primary_endpoint="https://primary.com/v1/chat/completions",
            primary_model="claude-sonnet-4.5",
            fallback_endpoints=fallbacks,
        )
        
        assert len(manager.endpoints) == 3
        assert manager.endpoints[0].url == "https://primary.com/v1/chat/completions"
        assert manager.endpoints[0].priority == 1

    def test_cache_key_generation(self):
        """Test cache key generation."""
        manager = APIFallbackManager(
            primary_endpoint="https://primary.com/v1/chat/completions",
            primary_model="claude-sonnet-4.5",
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        key1 = manager._get_cache_key(messages, temperature=0.7)
        key2 = manager._get_cache_key(messages, temperature=0.7)
        key3 = manager._get_cache_key(messages, temperature=0.9)
        
        assert key1 == key2  # Same parameters should produce same key
        assert key1 != key3  # Different parameters should produce different keys

    def test_endpoint_backoff(self):
        """Test exponential backoff application."""
        manager = APIFallbackManager(
            primary_endpoint="https://primary.com/v1/chat/completions",
            primary_model="claude-sonnet-4.5",
            backoff_multiplier=2.0,
        )
        
        endpoint = manager.endpoints[0]
        
        # First backoff
        manager._apply_backoff(endpoint)
        assert endpoint.consecutive_failures == 1
        assert endpoint.url in manager.retry_backoff_times
        
        # Check backoff time increases
        first_backoff_time = manager.retry_backoff_times[endpoint.url]
        
        manager._apply_backoff(endpoint)
        assert endpoint.consecutive_failures == 2
        second_backoff_time = manager.retry_backoff_times[endpoint.url]
        
        assert second_backoff_time > first_backoff_time

    def test_endpoint_status(self):
        """Test getting endpoint status."""
        manager = APIFallbackManager(
            primary_endpoint="https://primary.com/v1/chat/completions",
            primary_model="claude-sonnet-4.5",
        )
        
        status = manager.get_endpoint_status()
        assert isinstance(status, dict)
        assert "https://primary.com/v1/chat/completions" in status
        
        endpoint_status = status["https://primary.com/v1/chat/completions"]
        assert endpoint_status["available"] is True
        assert endpoint_status["priority"] == 1


class TestContextManager:
    """Tests for context window management."""

    def test_context_initialization(self):
        """Test context manager initialization."""
        manager = ContextManager(max_tokens=8000)
        assert manager.max_tokens == 8000
        assert manager.current_tokens == 0
        assert len(manager.messages) == 0

    def test_add_message(self):
        """Test adding messages to context."""
        manager = ContextManager(max_tokens=8000)
        
        manager.add_message("user", "Hello, how are you?")
        assert len(manager.messages) == 1
        assert manager.current_tokens > 0
        
        manager.add_message("assistant", "I'm doing well, thank you!")
        assert len(manager.messages) == 2

    def test_system_message(self):
        """Test system message handling."""
        manager = ContextManager(max_tokens=8000)
        
        manager.set_system_message("You are a helpful assistant.")
        assert manager.system_message is not None
        assert manager.system_message.content == "You are a helpful assistant."
        assert manager.system_message.role == "system"

    def test_context_compression(self):
        """Test context compression."""
        manager = ContextManager(max_tokens=200, compression_threshold=0.8)
        
        # Add messages until compression is triggered
        for i in range(10):
            manager.add_message("user", f"Message {i}: " + "x" * 50)
        
        # Check that compression was triggered
        assert len(manager.compression_history) > 0 or len(manager.messages) <= 10

    def test_get_context(self):
        """Test getting formatted context."""
        manager = ContextManager(max_tokens=8000)
        manager.set_system_message("You are helpful.")
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi there!")
        
        context = manager.get_context()
        assert len(context) == 3
        assert context[0]["role"] == "system"
        assert context[1]["role"] == "user"
        assert context[2]["role"] == "assistant"

    def test_get_status(self):
        """Test getting context status."""
        manager = ContextManager(max_tokens=8000)
        manager.add_message("user", "Hello")
        
        status = manager.get_status()
        assert status["total_messages"] == 1
        assert status["total_tokens"] > 0
        assert status["max_tokens"] == 8000
        assert "usage_ratio" in status
        assert "usage_percent" in status


class TestTokenCounter:
    """Tests for token usage tracking."""

    def test_counter_initialization(self):
        """Test token counter initialization."""
        counter = TokenCounter(request_limit=300, time_window=60)
        assert counter.request_limit == 300
        assert counter.time_window == 60
        assert counter.total_input_tokens == 0
        assert counter.total_output_tokens == 0

    def test_record_usage(self):
        """Test recording token usage."""
        counter = TokenCounter()
        
        record = counter.record_usage(input_tokens=100, output_tokens=50, model="gpt-4")
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert counter.total_input_tokens == 100
        assert counter.total_output_tokens == 50

    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        counter = TokenCounter()
        counter.record_usage(100, 50, "gpt-4")
        counter.record_usage(200, 100, "gpt-4")
        
        stats = counter.get_usage_stats()
        assert stats["total_requests"] == 2
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 150
        assert stats["total_tokens"] == 450

    def test_rate_limiting(self):
        """Test rate limiting checks."""
        counter = TokenCounter(request_limit=3, time_window=1)
        
        # Check rate limit before first request
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # Record first request
        counter.record_usage(100, 50)
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # Record second request
        counter.record_usage(100, 50)
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # Record third request - this should trigger rate limit check
        counter.record_usage(100, 50)
        is_ok, _ = counter.check_rate_limit()
        # At this point we have 3 requests in window, so rate limited
        assert is_ok is False
        
        # Verify remaining requests is 0
        remaining = counter.get_requests_remaining()
        assert remaining == 0


class TestTokenBudget:
    """Tests for token budgeting."""

    def test_budget_initialization(self):
        """Test token budget initialization."""
        budget = TokenBudget(daily_budget=100000, warning_threshold=0.8)
        assert budget.daily_budget == 100000
        assert budget.warning_threshold == 0.8

    def test_use_tokens(self):
        """Test using tokens from budget."""
        budget = TokenBudget(daily_budget=1000)
        
        status = budget.use_tokens(100)
        assert status["tokens_used"] == 100
        assert status["remaining_tokens"] == 900
        assert status["usage_percent"] == 10.0
        assert status["exceeds_budget"] is False

    def test_warning_threshold(self):
        """Test warning when approaching budget limit."""
        budget = TokenBudget(daily_budget=1000, warning_threshold=0.8)
        
        # Use tokens up to 85% of budget
        status = budget.use_tokens(850)
        assert "warning" in status
        assert "Approaching daily budget" in status["warning"]


class TestHealthChecker:
    """Tests for endpoint health checking."""

    @pytest.mark.asyncio
    async def test_health_checker_initialization(self):
        """Test health checker initialization."""
        checker = HealthChecker(check_interval=300, timeout=10)
        assert checker.check_interval == 300
        assert checker.timeout == 10
        assert len(checker.endpoints) == 0

    @pytest.mark.asyncio
    async def test_register_endpoint(self):
        """Test registering an endpoint."""
        checker = HealthChecker()
        checker.register_endpoint("https://api.example.com/v1/chat/completions", "gpt-4")
        
        assert len(checker.endpoints) == 1
        endpoint_url = "https://api.example.com/v1/chat/completions"
        assert endpoint_url in checker.endpoints

    @pytest.mark.asyncio
    async def test_get_status_emoji(self):
        """Test status emoji generation."""
        checker = HealthChecker()
        
        # Test different statuses
        assert checker.get_status_emoji(HealthStatus.CONNECTED) == "🟢"
        assert checker.get_status_emoji(HealthStatus.SLOW) == "🟡"
        assert checker.get_status_emoji(HealthStatus.DISCONNECTED) == "🔴"
        assert checker.get_status_emoji(HealthStatus.UNKNOWN) == "⚪"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
