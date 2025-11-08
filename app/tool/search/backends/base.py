"""
Base class for modern search backends with HTTP/2 support.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.logger import logger
from app.tool.search.base import SearchItem


class StructuredSearchResult(SearchItem):
    """Enhanced search result with structured data support."""
    
    # Basic search result fields
    position: int = Field(description="Position in search results")
    source: str = Field(description="Search backend name")
    
    # Structured data fields
    structured_data: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Parsed structured data (JSON-LD, microdata)"
    )
    rich_snippet: Optional[str] = Field(
        default=None, 
        description="Rich snippet or featured snippet content"
    )
    date_published: Optional[str] = Field(
        default=None, 
        description="Publication date if available"
    )
    author: Optional[str] = Field(
        default=None, 
        description="Author name if available"
    )
    
    # Relevance and ranking
    relevance_score: Optional[float] = Field(
        default=None, 
        description="Backend-provided relevance score"
    )
    result_type: Optional[str] = Field(
        default=None, 
        description="Type of result (web, image, news, video, etc.)"
    )
    
    # Metadata
    cache_key: Optional[str] = Field(
        default=None, 
        description="Cache key for this result"
    )
    query_hash: Optional[str] = Field(
        default=None, 
        description="Hash of the original query"
    )


class ModernSearchBackend(ABC):
    """Base class for modern search backends with HTTP/2 support."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Backend", "").lower()
        self._client: Optional[httpx.AsyncClient] = None
        self._user_agent_index = 0
        
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with modern features."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client with HTTP/2 and modern features."""
        # Configure limits for connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=self.config.get("max_connections_per_backend", 10),
            max_connections=self.config.get("max_connections_per_backend", 10) * 2,
        )
        
        # Configure timeout
        timeout = httpx.Timeout(
            connect=self.config.get("search_timeout", 30.0) / 3,
            read=self.config.get("search_timeout", 30.0),
            write=self.config.get("search_timeout", 30.0) / 3,
            pool=self.config.get("search_timeout", 30.0),
        )
        
        # Get User-Agent
        user_agent = self._get_user_agent()
        
        # Create client with HTTP/2 support
        client = httpx.AsyncClient(
            http2=self.config.get("enable_http2", True),
            limits=limits,
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            follow_redirects=True,
            verify=self.config.get("verify_ssl", True),
        )
        
        logger.debug(f"Created HTTP/2 client for {self.name} backend")
        return client
    
    def _get_user_agent(self) -> str:
        """Get User-Agent string, with rotation if enabled."""
        user_agents = self.config.get("user_agents", [])
        
        if not user_agents or not self.config.get("enable_user_agent_rotation", True):
            # Default fallback
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Rotate through user agents
        user_agent = user_agents[self._user_agent_index % len(user_agents)]
        self._user_agent_index += 1
        return user_agent
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> List[StructuredSearchResult]:
        """
        Perform search using the modern backend.
        
        Args:
            query: Search query
            num_results: Number of results to return
            lang: Language code
            country: Country code
            **kwargs: Additional backend-specific parameters
            
        Returns:
            List of structured search results
        """
        pass
    
    @abstractmethod
    def _parse_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse backend response into structured results."""
        pass
    
    def _extract_structured_data(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract structured data (JSON-LD, microdata) from content."""
        if not self.config.get("enable_structured_results", True):
            return None
            
        # This is a simplified implementation
        # In practice, you'd use libraries like extruct or microdata_parser
        structured_data = {}
        
        # Look for JSON-LD scripts
        import re
        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(json_ld_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            try:
                import json
                structured_data["json_ld"] = [json.loads(match.strip()) for match in matches]
            except json.JSONDecodeError:
                pass
        
        # Look for microdata (simplified)
        # In practice, you'd use a proper microdata parser
        microdata_pattern = r'<[^>]*itemscope[^>]*>(.*?)</[^>]*>'
        microdata_matches = re.findall(microdata_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if microdata_matches:
            structured_data["microdata"] = microdata_matches
        
        return structured_data if structured_data else None
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error for {self.name}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed for {self.name}: {e}")
            raise
    
    def __del__(self):
        """Cleanup when backend is destroyed."""
        if self._client and not self._client.is_closed:
            # Note: This is not ideal, but necessary for cleanup
            # In practice, use async context managers properly
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except:
                pass