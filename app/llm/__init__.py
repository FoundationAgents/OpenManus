"""
LLM API integration module for OpenAI-compatible endpoints.

This module provides:
- OpenAI-compatible API client with streaming support
- Graceful API fallback mechanism
- Context window management with smart compression
- Token usage tracking and monitoring
- Endpoint health checking
"""

from app.llm.api_client import (
    OpenAICompatibleClient,
    APIClientError,
    APITimeoutError,
    APIRateLimitError,
    APIServerError,
)
from app.llm.api_fallback import APIFallbackManager, FallbackEndpoint
from app.llm.context_manager import ContextManager
from app.llm.token_counter import TokenCounter, TokenUsageRecord, TokenBudget
from app.llm.health_check import HealthChecker, HealthStatus, EndpointHealth

__all__ = [
    "OpenAICompatibleClient",
    "APIClientError",
    "APITimeoutError",
    "APIRateLimitError",
    "APIServerError",
    "APIFallbackManager",
    "FallbackEndpoint",
    "ContextManager",
    "TokenCounter",
    "TokenUsageRecord",
    "TokenBudget",
    "HealthChecker",
    "HealthStatus",
    "EndpointHealth",
]
