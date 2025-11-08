"""
Brave Search API backend implementation with HTTP/2 support.
"""

import json
from typing import Any, Dict, List

import httpx

from app.logger import logger
from app.tool.search.backends.base import ModernSearchBackend, StructuredSearchResult


class BraveSearchBackend(ModernSearchBackend):
    """Brave Search API backend with modern HTTP/2 support."""
    
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("brave_api_key")
        if not self.api_key:
            logger.warning("Brave Search API key not provided - backend will not work")
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> List[StructuredSearchResult]:
        """Search using Brave Search API with HTTP/2."""
        if not self.api_key:
            logger.error("Brave Search API key not configured")
            return []
        
        # Prepare parameters
        params = {
            "q": query,
            "count": min(num_results, 20),  # Brave API limit
            "text_decorations": "false",
            "search_lang": lang,
            "ui_lang": lang,
            "safesearch": "moderate",
        }
        
        # Add optional parameters
        if "offset" in kwargs:
            params["offset"] = kwargs["offset"]
        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]  # pd, pw, pm, py
        if "result_filter" in kwargs:
            params["result_filter"] = kwargs["result_filter"]  # news, videos, images
        
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            }
            
            response = await self._make_request("GET", self.BASE_URL, params=params, headers=headers)
            return self._parse_response(response, query, num_results)
        except Exception as e:
            logger.error(f"Brave Search API failed: {e}")
            return []
    
    def _parse_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse Brave Search API response into structured results."""
        try:
            data = response.json()
            
            # Check for errors
            if data.get("error"):
                logger.error(f"Brave Search API error: {data['error']}")
                return []
            
            results = []
            web_results = data.get("web", {}).get("results", [])
            
            # Parse web results
            for i, item in enumerate(web_results[:num_results]):
                result = self._parse_web_result(item, query, i)
                if result:
                    results.append(result)
            
            # Include mixed results if available (news, videos, etc.)
            mixed_results = data.get("mixed", {}).get("results", [])
            for item in mixed_results:
                if item.get("type") in ["news", "videos"]:
                    mixed_result = self._parse_mixed_result(item, query, len(results))
                    if mixed_result:
                        results.append(mixed_result)
            
            logger.info(f"Brave Search API returned {len(results)} results for query: {query}")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Brave Search API JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing Brave Search API response: {e}")
            return []
    
    def _parse_web_result(
        self, 
        item: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse a web search result."""
        # Extract structured data
        structured_data = {}
        
        # Add meta information if available
        if item.get("meta"):
            structured_data["meta"] = item["meta"]
        
        # Add age/freshness information
        if item.get("age"):
            structured_data["age"] = item["age"]
        
        # Add language information
        if item.get("language"):
            structured_data["language"] = item["language"]
        
        return StructuredSearchResult(
            position=position + 1,
            url=item.get("url", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            source=self.name,
            structured_data=structured_data if structured_data else None,
            # Brave doesn't provide rich snippets in the same way
            rich_snippet=None,
            date_published=item.get("age"),
            # Brave doesn't provide author info directly
            author=None,
            relevance_score=None,  # Brave doesn't expose relevance scores
            result_type="web",
            cache_key=f"brave:{item.get('url', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _parse_mixed_result(
        self, 
        item: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse mixed results (news, videos, etc.)."""
        result_type = item.get("type", "mixed")
        
        # Extract type-specific information
        structured_data = {"mixed_type": result_type}
        
        # Add meta information if available
        if item.get("meta"):
            structured_data["meta"] = item["meta"]
        
        # For news results, extract publication info
        if result_type == "news" and item.get("meta"):
            meta = item["meta"]
            if isinstance(meta, dict):
                if meta.get("source"):
                    structured_data["news_source"] = meta["source"]
                if meta.get("published_time"):
                    structured_data["published_time"] = meta["published_time"]
        
        return StructuredSearchResult(
            position=position + 1,
            url=item.get("url", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            source=self.name,
            structured_data=structured_data,
            result_type=result_type,
            cache_key=f"brave:{result_type}:{item.get('url', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _hash_query(self, query: str) -> str:
        """Create a simple hash for the query."""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]