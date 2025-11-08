"""
Graceful API fallback mechanism for LLM queries.

Implements a fallback chain:
1. Try primary endpoint (vibingfox)
2. If timeout (>120s): Try fallback
3. If 429 (rate limited): Exponential backoff
4. If 5xx (server error): Try next endpoint
5. If success: return response
6. If all fail: Use cached responses (degraded mode)
"""

import asyncio
import time
from typing import Dict, List, Optional, Union, AsyncIterator

from app.logger import logger
from app.llm.api_client import (
    OpenAICompatibleClient,
    APIClientError,
    APITimeoutError,
    APIRateLimitError,
    APIServerError,
)


class FallbackEndpoint:
    """Represents a fallback endpoint with priority and metrics."""

    def __init__(self, url: str, model: str, priority: int, api_key: Optional[str] = None):
        self.url = url
        self.model = model
        self.priority = priority
        self.api_key = api_key
        self.last_success_time = 0
        self.consecutive_failures = 0
        self.is_available = True


class APIFallbackManager:
    """
    Manages fallback chain for API requests with exponential backoff and caching.
    """

    def __init__(
        self,
        primary_endpoint: str,
        primary_model: str,
        fallback_endpoints: Optional[List[Dict]] = None,
        cache_responses: bool = True,
        backoff_multiplier: float = 2.0,
        max_consecutive_failures: int = 3,
    ):
        """
        Initialize the fallback manager.

        Args:
            primary_endpoint: Primary API endpoint URL
            primary_model: Primary model name
            fallback_endpoints: List of fallback endpoints with format:
                [{"url": "...", "model": "...", "priority": 2, "api_key": "..."}]
            cache_responses: Whether to cache successful responses
            backoff_multiplier: Multiplier for exponential backoff
            max_consecutive_failures: Max failures before marking endpoint unavailable
        """
        self.primary_endpoint = primary_endpoint
        self.primary_model = primary_model
        self.backoff_multiplier = backoff_multiplier
        self.max_consecutive_failures = max_consecutive_failures
        self.cache_responses = cache_responses
        self.response_cache: Dict[str, str] = {}

        # Initialize endpoints
        self.endpoints = self._initialize_endpoints(fallback_endpoints or [])

        # Retry state
        self.retry_backoff_times: Dict[str, float] = {}

    def _initialize_endpoints(self, fallback_endpoints: List[Dict]) -> List[FallbackEndpoint]:
        """Initialize endpoint list with primary endpoint first."""
        endpoints = [
            FallbackEndpoint(
                url=self.primary_endpoint,
                model=self.primary_model,
                priority=1,
            )
        ]

        # Add fallback endpoints sorted by priority
        for endpoint_config in sorted(fallback_endpoints, key=lambda x: x.get("priority", 999)):
            endpoints.append(
                FallbackEndpoint(
                    url=endpoint_config["url"],
                    model=endpoint_config.get("model", self.primary_model),
                    priority=endpoint_config.get("priority", 999),
                    api_key=endpoint_config.get("api_key"),
                )
            )

        logger.info(f"Initialized {len(endpoints)} endpoints (1 primary + {len(endpoints)-1} fallbacks)")
        return endpoints

    def _get_cache_key(self, messages: List[Dict], **kwargs) -> str:
        """Generate a cache key for a request."""
        import hashlib
        import json

        cache_data = {
            "messages": messages,
            "model": kwargs.get("model", self.primary_model),
            "temperature": kwargs.get("temperature", 0.7),
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

    async def query(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        **kwargs,
    ) -> Union[str, AsyncIterator[str]]:
        """
        Execute a query with automatic fallback.

        Args:
            messages: List of message dictionaries
            stream: Whether to stream the response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Response text or async iterator of tokens

        Raises:
            APIClientError: If all endpoints fail
        """
        cache_key = self._get_cache_key(messages, **kwargs)

        # Try each endpoint in order
        last_error = None
        for endpoint in self.endpoints:
            if not endpoint.is_available:
                logger.debug(f"Skipping unavailable endpoint: {endpoint.url}")
                continue

            # Check backoff time
            if not self._can_retry_endpoint(endpoint):
                logger.debug(f"Endpoint still in backoff: {endpoint.url}")
                continue

            try:
                logger.info(f"Trying endpoint: {endpoint.url}")
                client = OpenAICompatibleClient(
                    endpoint=f"{endpoint.url}/chat/completions" if not endpoint.url.endswith("/chat/completions") else endpoint.url,
                    model=endpoint.model,
                    api_key=endpoint.api_key,
                )

                response = await client.create_completion(
                    messages=messages,
                    stream=stream,
                    **kwargs,
                )

                # Cache successful response (non-streaming only)
                if not stream and self.cache_responses:
                    self.response_cache[cache_key] = response

                # Reset failure counter on success
                endpoint.consecutive_failures = 0
                endpoint.last_success_time = time.time()
                await client.close()

                return response

            except APIRateLimitError as e:
                logger.warning(f"Rate limited on {endpoint.url}, backing off...")
                self._apply_backoff(endpoint)
                last_error = e

            except APIServerError as e:
                logger.warning(f"Server error on {endpoint.url}, trying next endpoint...")
                endpoint.consecutive_failures += 1
                if endpoint.consecutive_failures >= self.max_consecutive_failures:
                    endpoint.is_available = False
                    logger.error(f"Marked endpoint as unavailable: {endpoint.url}")
                last_error = e

            except APITimeoutError as e:
                logger.warning(f"Timeout on {endpoint.url}, trying next endpoint...")
                endpoint.consecutive_failures += 1
                if endpoint.consecutive_failures >= self.max_consecutive_failures:
                    endpoint.is_available = False
                last_error = e

            except APIClientError as e:
                logger.error(f"Client error on {endpoint.url}: {e}")
                last_error = e

            finally:
                try:
                    await client.close()
                except:
                    pass

        # All endpoints failed, try cache if available
        if self.cache_responses and cache_key in self.response_cache:
            logger.warning("All endpoints failed, using cached response")
            return self.response_cache[cache_key]

        # All failed
        error_msg = f"All {len(self.endpoints)} endpoints failed. Last error: {last_error}"
        logger.error(error_msg)
        raise APIClientError(error_msg)

    def _apply_backoff(self, endpoint: FallbackEndpoint):
        """Apply exponential backoff to an endpoint."""
        backoff_time = 2 ** endpoint.consecutive_failures * self.backoff_multiplier
        backoff_time = min(backoff_time, 300)  # Cap at 5 minutes
        endpoint.consecutive_failures += 1
        self.retry_backoff_times[endpoint.url] = time.time() + backoff_time
        logger.info(f"Applied {backoff_time}s backoff to {endpoint.url}")

    def _can_retry_endpoint(self, endpoint: FallbackEndpoint) -> bool:
        """Check if endpoint is ready to retry."""
        if endpoint.url not in self.retry_backoff_times:
            return True
        return time.time() >= self.retry_backoff_times[endpoint.url]

    def get_endpoint_status(self) -> Dict[str, any]:
        """Get status of all endpoints."""
        status = {}
        for endpoint in self.endpoints:
            status[endpoint.url] = {
                "available": endpoint.is_available,
                "priority": endpoint.priority,
                "consecutive_failures": endpoint.consecutive_failures,
                "last_success": endpoint.last_success_time,
            }
        return status

    def reset_endpoint(self, endpoint_url: str):
        """Reset an endpoint to available state."""
        for endpoint in self.endpoints:
            if endpoint.url == endpoint_url:
                endpoint.is_available = True
                endpoint.consecutive_failures = 0
                if endpoint.url in self.retry_backoff_times:
                    del self.retry_backoff_times[endpoint.url]
                logger.info(f"Reset endpoint: {endpoint.url}")
                break

    def clear_cache(self):
        """Clear response cache."""
        self.response_cache.clear()
        logger.info("Cleared response cache")
