"""
Google Custom Search API backend implementation with HTTP/2 support.
"""

import asyncio
import json
from typing import Any, Dict, List

import httpx

from app.logger import logger
from app.tool.search.backends.base import ModernSearchBackend, StructuredSearchResult


class GoogleCustomSearchBackend(ModernSearchBackend):
    """Google Custom Search API backend with modern HTTP/2 support."""
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("google_api_key")
        self.search_engine_id = config.get("google_search_engine_id")
        
        if not self.api_key:
            logger.warning("Google API key not provided - backend will not work")
        if not self.search_engine_id:
            logger.warning("Google Search Engine ID not provided - backend will not work")
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> List[StructuredSearchResult]:
        """Search using Google Custom Search API with HTTP/2."""
        if not self.api_key or not self.search_engine_id:
            logger.error("Google API key or Search Engine ID not configured")
            return []
        
        # Prepare parameters
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": min(max(num_results, 1), 10),  # Google API limit is 10 per request
            "hl": lang,
            "gl": country,
            "safe": "medium",
        }
        
        # Add optional parameters
        if "site_search" in kwargs:
            params["siteSearch"] = kwargs["site_search"]
        if "date_restrict" in kwargs:
            params["dateRestrict"] = kwargs["date_restrict"]  # d1, d7, m1, y1
        if "file_type" in kwargs:
            params["fileType"] = kwargs["file_type"]
        if "rights" in kwargs:
            params["rights"] = kwargs["rights"]  # cc_publicdomain, etc.
        
        # For more than 10 results, we need multiple requests
        all_results = []
        start_index = 1
        
        while len(all_results) < num_results:
            params["start"] = start_index
            
            try:
                response = await self._make_request("GET", self.BASE_URL, params=params)
                batch_results = self._parse_response(response, query, num_results)
                
                if not batch_results:
                    break  # No more results
                
                all_results.extend(batch_results)
                
                # Check if we got fewer results than requested (end of results)
                if len(batch_results) < 10:
                    break
                
                start_index += 10
                
                # Google API has rate limits, so be careful with multiple requests
                if len(all_results) < num_results:
                    await asyncio.sleep(1)  # Rate limiting
                    
            except Exception as e:
                logger.error(f"Google Custom Search API batch failed: {e}")
                break
        
        # Limit to requested number
        all_results = all_results[:num_results]
        
        logger.info(f"Google Custom Search API returned {len(all_results)} results for query: {query}")
        return all_results
    
    def _parse_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse Google Custom Search API response into structured results."""
        try:
            data = response.json()
            
            # Check for errors
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error(f"Google Custom Search API error: {error_msg}")
                return []
            
            results = []
            items = data.get("items", [])
            
            # Parse search results
            for i, item in enumerate(items):
                result = self._parse_search_item(item, query, i)
                if result:
                    results.append(result)
            
            # Include context information if available
            context = data.get("context", {})
            if context:
                for result in results:
                    if not result.structured_data:
                        result.structured_data = {}
                    result.structured_data["context"] = context
            
            # Include search information
            search_info = data.get("searchInformation", {})
            if search_info:
                for result in results:
                    if not result.structured_data:
                        result.structured_data = {}
                    result.structured_data["search_info"] = search_info
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Google Custom Search API JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing Google Custom Search API response: {e}")
            return []
    
    def _parse_search_item(
        self, 
        item: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse a single search result item."""
        # Extract structured data
        structured_data = {}
        
        # Add pagemap data if available (structured data from the page)
        if item.get("pagemap"):
            structured_data["pagemap"] = item["pagemap"]
            
            # Extract specific structured data
            pagemap = item["pagemap"]
            
            # Person information
            if "person" in pagemap:
                structured_data["person"] = pagemap["person"][0] if pagemap["person"] else {}
            
            # Organization information
            if "organization" in pagemap:
                structured_data["organization"] = pagemap["organization"][0] if pagemap["organization"] else {}
            
            # Product information
            if "product" in pagemap:
                structured_data["product"] = pagemap["product"][0] if pagemap["product"] else {}
            
            # Article information
            if "article" in pagemap:
                structured_data["article"] = pagemap["article"][0] if pagemap["article"] else {}
            
            # Review information
            if "review" in pagemap:
                structured_data["review"] = pagemap["review"][0] if pagemap["review"] else {}
        
        # Extract rich snippet information
        rich_snippet = None
        if "snippet" in item:
            rich_snippet = item["snippet"]
        
        # Extract author information
        author = None
        if structured_data.get("person", {}).get("name"):
            author = structured_data["person"]["name"]
        elif structured_data.get("article", {}).get("author"):
            author = structured_data["article"]["author"]
        
        # Extract date published
        date_published = None
        if structured_data.get("article", {}).get("datepublished"):
            date_published = structured_data["article"]["datepublished"]
        elif structured_data.get("person", {}).get("birthdate"):
            date_published = structured_data["person"]["birthdate"]
        
        # Determine result type
        result_type = "web"
        if "cse_image" in item.get("pagemap", {}):
            result_type = "image"
        elif "videoobject" in item.get("pagemap", {}):
            result_type = "video"
        elif "newsarticle" in item.get("pagemap", {}):
            result_type = "news"
        
        return StructuredSearchResult(
            position=position + 1,
            url=item.get("link", ""),
            title=item.get("title", ""),
            description=item.get("snippet", ""),
            source=self.name,
            structured_data=structured_data if structured_data else None,
            rich_snippet=rich_snippet,
            date_published=date_published,
            author=author,
            relevance_score=None,  # Google doesn't expose relevance scores
            result_type=result_type,
            cache_key=f"google:{item.get('link', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _hash_query(self, query: str) -> str:
        """Create a simple hash for the query."""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]