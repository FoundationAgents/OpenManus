"""
OpenAI-compatible API client for vibingfox and other compatible endpoints.

Supports streaming responses, custom system prompts, temperature tuning,
max tokens configuration, and token counting for budget awareness.
"""

import asyncio
import json
import time
from typing import AsyncIterator, Dict, List, Optional, Union

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import config
from app.logger import logger
from app.schema import Message


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class APITimeoutError(APIClientError):
    """Raised when API request times out."""
    pass


class APIRateLimitError(APIClientError):
    """Raised when rate limited (429)."""
    pass


class APIServerError(APIClientError):
    """Raised on server errors (5xx)."""
    pass


class OpenAICompatibleClient:
    """
    Client for OpenAI-compatible APIs with streaming support, retries, and token counting.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize the OpenAI-compatible API client.

        Args:
            endpoint: The API endpoint URL (e.g., https://gpt4free.pro/v1/vibingfox/chat/completions)
            model: Model name to use for requests
            api_key: Optional API key (some endpoints don't require it)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key or "no-key-required"
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

        # Token tracking
        self.total_input_tokens = 0
        self.total_completion_tokens = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OpenManus-LLM-Client/1.0",
        }
        if self.api_key and self.api_key != "no-key-required":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def load_available_models(self) -> List[str]:
        """
        Load available models from the /models endpoint.

        Returns:
            List of available model names
        """
        try:
            # Extract base URL from endpoint (remove /chat/completions)
            base_url = self.endpoint.rsplit("/chat/completions", 1)[0]
            models_url = f"{base_url}/models"

            response = await self.http_client.get(models_url)
            response.raise_for_status()

            data = response.json()
            models = [model["id"] for model in data.get("data", [])]
            logger.info(f"Available models from {models_url}: {models}")
            return models
        except Exception as e:
            logger.warning(f"Failed to load models from {models_url}: {e}")
            return [self.model]  # Fall back to default model

    @retry(
        wait=wait_exponential(multiplier=2, min=1, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((APIRateLimitError, APIServerError, asyncio.TimeoutError)),
    )
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> Union[str, AsyncIterator[str]]:
        """
        Create a completion using the API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream the response
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend to messages

        Returns:
            Full response text (non-streaming) or async iterator of tokens (streaming)

        Raises:
            APITimeoutError: If request times out
            APIRateLimitError: If rate limited (429)
            APIServerError: If server error (5xx)
            APIClientError: For other errors
        """
        try:
            # Prepare messages with optional system prompt
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

            # Track input tokens
            input_tokens = self._estimate_tokens(messages)
            self.total_input_tokens += input_tokens

            # Build request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": stream,
            }

            logger.debug(f"Sending request to {self.endpoint}: {payload}")

            response = await self.http_client.post(
                self.endpoint,
                json=payload,
                headers=self._get_headers(),
            )

            # Handle response status codes
            if response.status_code == 429:
                logger.warning("Rate limited (429)")
                raise APIRateLimitError("Rate limited")
            elif response.status_code >= 500:
                logger.error(f"Server error ({response.status_code}): {response.text}")
                raise APIServerError(f"Server error: {response.status_code}")
            elif response.status_code == 408:
                logger.warning("Request timeout (408)")
                raise APITimeoutError("Request timeout")

            response.raise_for_status()

            if stream:
                return self._handle_streaming_response(response)
            else:
                return self._handle_non_streaming_response(response)

        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {self.timeout}s")
            raise APITimeoutError(f"Request timeout after {self.timeout}s")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise APIClientError(f"Request error: {e}")

    async def _handle_non_streaming_response(self, response: httpx.Response) -> str:
        """Handle non-streaming response."""
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Track completion tokens
        if "usage" in data:
            self.total_completion_tokens += data["usage"].get("completion_tokens", 0)

        logger.debug(f"Non-streaming response: {content[:100]}...")
        return content

    async def _handle_streaming_response(self, response: httpx.Response) -> AsyncIterator[str]:
        """
        Handle streaming response line by line.

        Yields:
            Token strings as they arrive
        """
        completion_tokens = 0
        async with response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        logger.debug(f"Stream completed. Tokens: {completion_tokens}")
                        self.total_completion_tokens += completion_tokens
                        break

                    try:
                        data = json.loads(data_str)
                        chunk_content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if chunk_content:
                            completion_tokens += self._count_tokens(chunk_content)
                            yield chunk_content
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON: {data_str}")

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for messages.

        Uses a simple heuristic: ~4 tokens per word + base overhead.
        For accurate counting, use the token_counter module with proper tokenizer.

        Args:
            messages: List of message dictionaries

        Returns:
            Estimated token count
        """
        total = 0
        for message in messages:
            # Base tokens per message
            total += 4
            # Approximate tokens from content
            content = message.get("content", "")
            total += self._count_tokens(content)
        return total

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using simple heuristic.

        Uses ~1.3 chars per token (rough average for English).

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if not text:
            return 0
        # Rough heuristic: 1 token ≈ 4 characters
        return len(text) // 4 + 1

    def get_token_usage(self) -> Dict[str, int]:
        """
        Get cumulative token usage statistics.

        Returns:
            Dictionary with total_input_tokens and total_completion_tokens
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_input_tokens + self.total_completion_tokens,
        }

    async def health_check(self) -> bool:
        """
        Perform a quick health check of the API endpoint.

        Returns:
            True if endpoint is reachable and working, False otherwise
        """
        try:
            # Try to load models as a health check
            models = await self.load_available_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client connection."""
        await self.http_client.aclose()

    def __del__(self):
        """Cleanup on destruction."""
        try:
            asyncio.get_event_loop().run_until_complete(self.close())
        except Exception:
            pass
