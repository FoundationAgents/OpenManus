"""Custom exceptions for the LLM service layer."""

from typing import Optional


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(message)


class TokenLimitExceededError(LLMServiceError):
    """Raised when token limits are exceeded."""

    def __init__(
        self,
        message: str,
        current_tokens: int = 0,
        requested_tokens: int = 0,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
    ):
        self.current_tokens = current_tokens
        self.requested_tokens = requested_tokens
        self.max_tokens = max_tokens
        super().__init__(message, provider)


class ProviderNotFoundError(LLMServiceError):
    """Raised when a requested LLM provider is not found or supported."""

    def __init__(self, provider_name: str):
        super().__init__(f"LLM provider '{provider_name}' not found or supported", provider_name)


class ProviderConfigurationError(LLMServiceError):
    """Raised when provider configuration is invalid."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(f"Configuration error: {message}", provider)


class ProviderAuthenticationError(LLMServiceError):
    """Raised when provider authentication fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(f"Authentication error: {message}", provider)


class ProviderRateLimitError(LLMServiceError):
    """Raised when provider rate limits are exceeded."""

    def __init__(self, message: str, provider: Optional[str] = None, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit error: {message}", provider)


class ProviderAPIError(LLMServiceError):
    """Raised when provider API returns an error."""

    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(f"API error: {message}", provider)


class MessageFormattingError(LLMServiceError):
    """Raised when message formatting fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(f"Message formatting error: {message}", provider)


class UnsupportedFeatureError(LLMServiceError):
    """Raised when a requested feature is not supported by the provider."""

    def __init__(self, feature: str, provider: Optional[str] = None):
        super().__init__(f"Feature '{feature}' not supported by provider", provider)