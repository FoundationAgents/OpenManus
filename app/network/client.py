"""
HTTP client with caching, retry logic, and Guardian integration.

Provides a feature-rich HTTP client built on httpx with response caching,
automatic retries, rate limiting, proxy support, and security validation.
"""

import asyncio
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.network.cache import ResponseCache
from app.network.guardian import Guardian, OperationType, get_guardian
from app.network.rate_limiter import RateLimiter, RateLimitConfig
from app.utils.logger import logger


class HTTPClientConfig(BaseModel):
    """Configuration for HTTP client."""
    
    timeout: float = 30.0
    max_redirects: int = 10
    verify_ssl: bool = True
    
    # Caching
    enable_cache: bool = True
    cache_max_size: int = 1000
    cache_max_memory_mb: int = 100
    cache_default_ttl: int = 3600
    cache_persist_path: Optional[str] = None
    cache_enable_persistence: bool = False
    
    # Retry policy
    max_retries: int = 3
    retry_delay_min: float = 1.0
    retry_delay_max: float = 10.0
    
    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_per_second: float = 10.0
    rate_limit_burst: int = 20
    
    # Proxy
    proxy_url: Optional[str] = None
    proxy_auth: Optional[tuple] = None
    
    # Headers
    default_headers: Dict[str, str] = Field(default_factory=dict)
    user_agent: str = "AgentFlow-NetworkToolkit/1.0"


class HTTPResponse(BaseModel):
    """Standardized HTTP response."""
    
    status_code: int
    headers: Dict[str, str]
    content: Union[str, bytes, Dict]
    url: str
    from_cache: bool = False
    request_time: float = 0.0
    
    class Config:
        arbitrary_types_allowed = True


class HTTPClientWithCaching:
    """
    Advanced HTTP client with caching, retries, and Guardian integration.
    
    Features:
    - Response caching with configurable TTL
    - Automatic retry with exponential backoff
    - Rate limiting per host
    - Proxy support
    - Guardian security validation
    - Request/response logging
    """
    
    def __init__(
        self,
        config: Optional[HTTPClientConfig] = None,
        guardian: Optional[Guardian] = None
    ):
        """
        Initialize HTTP client.
        
        Args:
            config: Client configuration
            guardian: Guardian instance for security validation
        """
        self.config = config or HTTPClientConfig()
        self.guardian = guardian or get_guardian()
        
        # Initialize cache
        if self.config.enable_cache:
            self.cache = ResponseCache(
                max_size=self.config.cache_max_size,
                max_memory_mb=self.config.cache_max_memory_mb,
                default_ttl=self.config.cache_default_ttl,
                persist_path=self.config.cache_persist_path,
                enable_persistence=self.config.cache_enable_persistence
            )
        else:
            self.cache = None
        
        # Initialize rate limiter
        if self.config.enable_rate_limiting:
            self.rate_limiter = RateLimiter(
                RateLimitConfig(
                    requests_per_second=self.config.rate_limit_per_second,
                    burst_size=self.config.rate_limit_burst,
                    per_host=True
                )
            )
        else:
            self.rate_limiter = None
        
        # Create httpx client
        self._client = None
        
        logger.info("HTTPClientWithCaching initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            # Build client config
            client_kwargs = {
                'timeout': self.config.timeout,
                'max_redirects': self.config.max_redirects,
                'verify': self.config.verify_ssl,
                'follow_redirects': True,
            }
            
            # Add proxy if configured
            if self.config.proxy_url:
                client_kwargs['proxies'] = self.config.proxy_url
            
            # Add default headers
            headers = {
                'User-Agent': self.config.user_agent,
                **self.config.default_headers
            }
            client_kwargs['headers'] = headers
            
            self._client = httpx.AsyncClient(**client_kwargs)
        
        return self._client
    
    def _parse_url(self, url: str) -> tuple:
        """Parse URL into host and port."""
        parsed = urlparse(url)
        host = parsed.hostname or parsed.netloc
        port = parsed.port
        
        if port is None:
            port = 443 if parsed.scheme == 'https' else 80
        
        return host, port
    
    async def _check_guardian(
        self,
        method: str,
        url: str,
        data: Optional[Any] = None
    ) -> bool:
        """
        Check Guardian approval for request.
        
        Args:
            method: HTTP method
            url: Request URL
            data: Request data
            
        Returns:
            True if approved
            
        Raises:
            PermissionError: If request is blocked by Guardian
        """
        host, port = self._parse_url(url)
        
        # Determine operation type
        operation_map = {
            'GET': OperationType.HTTP_GET,
            'POST': OperationType.HTTP_POST,
            'PUT': OperationType.HTTP_PUT,
            'DELETE': OperationType.HTTP_DELETE,
        }
        operation = operation_map.get(method.upper(), OperationType.HTTP_GET)
        
        # Calculate data size
        data_size = 0
        if data:
            if isinstance(data, (str, bytes)):
                data_size = len(data)
            else:
                data_size = len(str(data))
        
        # Assess risk
        assessment = self.guardian.assess_risk(
            operation=operation,
            host=host,
            port=port,
            data_size=data_size,
            url=url
        )
        
        if not assessment.approved:
            error_msg = (
                f"Request blocked by Guardian: {method} {url}\n"
                f"Risk Level: {assessment.level.value}\n"
                f"Reasons: {', '.join(assessment.reasons)}"
            )
            logger.warning(error_msg)
            raise PermissionError(error_msg)
        
        if assessment.requires_confirmation:
            logger.warning(
                f"Request requires confirmation: {method} {url} "
                f"(Risk: {assessment.level.value})"
            )
            # In a real implementation, this would trigger a UI confirmation dialog
            # For now, we'll check if it was pre-approved
            if not self.guardian.is_approved(operation, host, port):
                logger.warning("Request not pre-approved, blocking")
                raise PermissionError(
                    f"Request requires manual approval: {method} {url}"
                )
        
        return True
    
    async def _apply_rate_limit(self, url: str):
        """Apply rate limiting."""
        if self.rate_limiter:
            host, _ = self._parse_url(url)
            await self.rate_limiter.acquire(host=host, wait=True)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retries."""
        client = await self._get_client()
        
        logger.debug(f"Making request: {method} {url}")
        
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {method} {url}")
            raise
        except httpx.TimeoutException as e:
            logger.warning(f"Request timeout: {method} {url}")
            raise
        except httpx.NetworkError as e:
            logger.warning(f"Network error: {method} {url}")
            raise
    
    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs
    ) -> HTTPResponse:
        """
        Make HTTP request with caching and Guardian validation.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            json: JSON request body
            headers: Additional headers
            use_cache: Whether to use cache (for GET requests)
            cache_ttl: Custom cache TTL in seconds
            **kwargs: Additional httpx options
            
        Returns:
            HTTPResponse object
            
        Raises:
            PermissionError: If blocked by Guardian
            httpx.HTTPError: On HTTP errors
        """
        import time
        start_time = time.time()
        
        # Check Guardian approval
        await self._check_guardian(method, url, data or json)
        
        # Check cache for GET requests
        if method.upper() == 'GET' and use_cache and self.cache:
            cached = self.cache.get(method, url, params, headers)
            if cached is not None:
                return HTTPResponse(
                    status_code=cached.get('status_code', 200),
                    headers=cached.get('headers', {}),
                    content=cached.get('content'),
                    url=url,
                    from_cache=True,
                    request_time=time.time() - start_time
                )
        
        # Apply rate limiting
        await self._apply_rate_limit(url)
        
        # Make request
        response = await self._make_request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            **kwargs
        )
        
        # Parse response
        try:
            if 'application/json' in response.headers.get('content-type', ''):
                content = response.json()
            else:
                content = response.text
        except Exception:
            content = response.content
        
        http_response = HTTPResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=content,
            url=str(response.url),
            from_cache=False,
            request_time=time.time() - start_time
        )
        
        # Cache GET requests
        if method.upper() == 'GET' and self.cache:
            cache_data = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': content,
            }
            self.cache.set(
                method, url, cache_data, params, headers,
                ttl=cache_ttl
            )
        
        logger.info(
            f"Request completed: {method} {url} "
            f"[{response.status_code}] in {http_response.request_time:.2f}s"
        )
        
        return http_response
    
    async def get(self, url: str, **kwargs) -> HTTPResponse:
        """Make GET request."""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> HTTPResponse:
        """Make POST request."""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> HTTPResponse:
        """Make PUT request."""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> HTTPResponse:
        """Make DELETE request."""
        return await self.request('DELETE', url, **kwargs)
    
    async def head(self, url: str, **kwargs) -> HTTPResponse:
        """Make HEAD request."""
        return await self.request('HEAD', url, **kwargs)
    
    async def options(self, url: str, **kwargs) -> HTTPResponse:
        """Make OPTIONS request."""
        return await self.request('OPTIONS', url, **kwargs)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats().to_dict()
        return {}
    
    def get_rate_limit_stats(self) -> Dict:
        """Get rate limiter statistics."""
        if self.rate_limiter:
            return self.rate_limiter.get_stats()
        return {}
    
    def clear_cache(self):
        """Clear response cache."""
        if self.cache:
            self.cache.clear()
    
    def invalidate_cache(self, url: str):
        """Invalidate cache for specific URL."""
        if self.cache:
            self.cache.invalidate('GET', url)
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("HTTPClientWithCaching closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
