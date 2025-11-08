"""
Unified LLM Module - consolidation of legacy llm.py and modern modular components.

This module provides:
- Unified LLM client with singleton pattern
- Multi-provider support (OpenAI, Azure, AWS Bedrock, Ollama, custom)
- Consolidated token counting and limit checking
- Streaming and non-streaming support
- Tool/function calling
- Multimodal input support (text + images)
- Retry logic with exponential backoff
- Advanced API features (fallback, health checking, context management)

Core Exports:
    - LLM: Main client class for all LLM interactions
    - UnifiedTokenCounter: Token counting for text and images

Legacy Compatibility (Modern Modular Components):
    - OpenAICompatibleClient: Low-level API client
    - APIFallbackManager: Endpoint fallback mechanism
    - ContextManager: Context window management
    - TokenCounter: Advanced token tracking
    - HealthChecker: Endpoint health monitoring
"""

# Main unified client (consolidated from legacy llm.py)
from app.llm.client import LLM, UnifiedTokenCounter

# Modern modular components
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
    # Main unified client
    "LLM",
    "UnifiedTokenCounter",
    # Modern modular components
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
