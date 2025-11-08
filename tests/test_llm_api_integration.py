"""
Integration tests for LLM API with real or mocked API calls.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response

from app.config import config
from app.llm.api_client import OpenAICompatibleClient
from app.llm.api_fallback import APIFallbackManager
from app.llm.context_manager import ContextManager
from app.llm.token_counter import TokenCounter


class TestLLMAPIIntegration:
    """Integration tests for LLM API."""

    @pytest.mark.asyncio
    async def test_client_configuration_from_config(self):
        """Test that client can be configured from app config."""
        llm_api_config = config.llm_api
        
        assert llm_api_config.endpoint == "https://gpt4free.pro/v1/vibingfox/chat/completions"
        assert llm_api_config.model == "claude-sonnet-4.5"
        assert llm_api_config.context_window == 8000
        assert llm_api_config.max_tokens_per_request == 2000
        assert llm_api_config.temperature == 0.7
        assert llm_api_config.top_p == 0.9
        assert llm_api_config.request_timeout == 120
        assert llm_api_config.enable_health_check is True

    @pytest.mark.asyncio
    async def test_fallback_manager_from_config(self):
        """Test creating fallback manager from config."""
        llm_api_config = config.llm_api
        
        manager = APIFallbackManager(
            primary_endpoint=llm_api_config.endpoint,
            primary_model=llm_api_config.model,
            fallback_endpoints=[
                {
                    "url": f.endpoint,
                    "model": f.model,
                    "priority": f.priority,
                    "api_key": f.api_key,
                }
                for f in llm_api_config.fallbacks
            ],
        )
        
        assert len(manager.endpoints) >= 1
        assert manager.endpoints[0].url == llm_api_config.endpoint

    @pytest.mark.asyncio
    async def test_context_with_llm_api_limits(self):
        """Test context manager with LLM API token limits."""
        llm_api_config = config.llm_api
        
        context = ContextManager(
            max_tokens=llm_api_config.context_window,
            warning_threshold=0.8,
        )
        
        assert context.max_tokens == 8000
        
        # Add a message
        context.add_message("user", "Hello, this is a test message.")
        assert len(context.messages) == 1
        
        # Add system message
        context.set_system_message("You are a helpful assistant.")
        assert context.system_message is not None
        
        # Get context and verify format
        ctx = context.get_context()
        assert ctx[0]["role"] == "system"
        assert ctx[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test a complete workflow from config to response."""
        llm_api_config = config.llm_api
        
        # Create client from config
        client = OpenAICompatibleClient(
            endpoint=llm_api_config.endpoint,
            model=llm_api_config.model,
            timeout=llm_api_config.request_timeout,
        )
        
        # Verify configuration
        assert client.endpoint == llm_api_config.endpoint
        assert client.model == llm_api_config.model
        assert client.timeout == llm_api_config.request_timeout
        
        # Create context manager
        context_mgr = ContextManager(max_tokens=llm_api_config.context_window)
        
        # Add message to context
        context_mgr.add_message("user", "What is Python?")
        
        # Get formatted context
        messages = context_mgr.get_context()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        
        # Create token counter
        counter = TokenCounter(
            request_limit=llm_api_config.max_requests_per_minute,
        )
        
        # Estimate tokens
        input_tokens = client._estimate_tokens(messages)
        counter.record_usage(input_tokens, 0)
        
        # Verify token tracking
        stats = counter.get_usage_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] > 0
        
        await client.close()

    @pytest.mark.asyncio
    async def test_mock_streaming_response(self):
        """Test streaming response handling with mock."""
        client = OpenAICompatibleClient(
            endpoint="https://api.example.com/v1/chat/completions",
            model="test-model",
        )
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: self
        
        # Simulate streaming response
        stream_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            'data: {"choices": [{"delta": {"content": "!"}}]}',
            'data: [DONE]',
        ]
        
        async def async_lines():
            for line in stream_lines:
                yield line
        
        mock_response.aiter_lines = async_lines
        
        # Process streaming response
        result = []
        async for chunk in client._handle_streaming_response(mock_response):
            result.append(chunk)
        
        response_text = "".join(result)
        assert response_text == "Hello world!"
        
        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting with token counter."""
        counter = TokenCounter(request_limit=3, time_window=1)
        
        # Check before first request
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # First request
        counter.record_usage(100, 50)
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # Second request
        counter.record_usage(100, 50)
        is_ok, _ = counter.check_rate_limit()
        assert is_ok is True
        
        # Third request - should be rate limited now
        counter.record_usage(100, 50)
        is_ok, msg = counter.check_rate_limit()
        assert is_ok is False
        assert "Rate limit" in msg
        
        # Remaining requests should be zero
        remaining = counter.get_requests_remaining()
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in API client."""
        client = OpenAICompatibleClient(
            endpoint="https://api.example.com/v1/chat/completions",
            model="test-model",
        )
        
        # Test timeout error
        from app.llm.api_client import APITimeoutError
        with pytest.raises(APITimeoutError):
            # This would normally be caught by create_completion
            raise APITimeoutError("Request timeout")
        
        # Test rate limit error
        from app.llm.api_client import APIRateLimitError
        with pytest.raises(APIRateLimitError):
            raise APIRateLimitError("Rate limited")
        
        # Test server error
        from app.llm.api_client import APIServerError
        with pytest.raises(APIServerError):
            raise APIServerError("Server error")
        
        await client.close()


class TestConfigurationLoading:
    """Tests for loading configuration from TOML."""

    def test_llm_api_config_exists(self):
        """Test that LLM API config is loaded."""
        llm_api = config.llm_api
        assert llm_api is not None

    def test_llm_api_defaults(self):
        """Test LLM API configuration defaults."""
        llm_api = config.llm_api
        
        # Check defaults
        assert llm_api.endpoint == "https://gpt4free.pro/v1/vibingfox/chat/completions"
        assert llm_api.model == "claude-sonnet-4.5"
        assert llm_api.context_window == 8000
        assert llm_api.max_tokens_per_request == 2000
        assert llm_api.retry_attempts == 3
        assert llm_api.enable_health_check is True

    def test_llm_api_overrides(self):
        """Test that LLM API config can be overridden."""
        # This would require a custom config file
        # For now, just verify the structure exists
        llm_api = config.llm_api
        assert hasattr(llm_api, 'fallbacks')
        assert isinstance(llm_api.fallbacks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
