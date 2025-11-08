"""
SerpAPI backend implementation with HTTP/2 support.
"""

import json
from typing import Any, Dict, List

import httpx

from app.logger import logger
from app.tool.search.backends.base import ModernSearchBackend, StructuredSearchResult


class SerpApiBackend(ModernSearchBackend):
    """SerpAPI backend with modern HTTP/2 support."""
    
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("serpapi_key")
        if not self.api_key:
            logger.warning("SerpAPI key not provided - backend will not work")
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> List[StructuredSearchResult]:
        """Search using SerpAPI with HTTP/2."""
        if not self.api_key:
            logger.error("SerpAPI key not configured")
            return []
        
        # Prepare parameters
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": min(num_results, 100),  # SerpAPI limit
            "hl": lang,
            "gl": country,
            "safe": "active",
        }
        
        # Add optional parameters
        if "location" in kwargs:
            params["location"] = kwargs["location"]
        if "device" in kwargs:
            params["device"] = kwargs["device"]
        if "search_type" in kwargs:
            params["tbm"] = kwargs["search_type"]  # images, news, videos
        
        try:
            response = await self._make_request("GET", self.BASE_URL, params=params)
            return self._parse_response(response, query, num_results)
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []
    
    def _parse_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse SerpAPI response into structured results."""
        try:
            data = response.json()
            
            # Check for errors
            if data.get("error"):
                logger.error(f"SerpAPI error: {data['error']}")
                return []
            
            results = []
            organic_results = data.get("organic_results", [])
            
            # Include featured snippets if available
            if data.get("answer_box"):
                featured_snippet = self._parse_featured_snippet(
                    data["answer_box"], query, len(results)
                )
                if featured_snippet:
                    results.append(featured_snippet)
            
            # Parse organic results
            for i, item in enumerate(organic_results[:num_results]):
                result = self._parse_organic_result(item, query, i)
                if result:
                    results.append(result)
            
            # Include knowledge graph if available
            if data.get("knowledge_graph"):
                kg_result = self._parse_knowledge_graph(
                    data["knowledge_graph"], query, len(results)
                )
                if kg_result:
                    results.append(kg_result)
            
            logger.info(f"SerpAPI returned {len(results)} results for query: {query}")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SerpAPI JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing SerpAPI response: {e}")
            return []
    
    def _parse_organic_result(
        self, 
        item: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse an organic search result."""
        # Extract structured data
        structured_data = {}
        if item.get("rich_snippet"):
            structured_data["rich_snippet"] = item["rich_snippet"]
        
        return StructuredSearchResult(
            position=position + 1,
            url=item.get("link", ""),
            title=item.get("title", ""),
            description=item.get("snippet", ""),
            source=self.name,
            structured_data=structured_data if structured_data else None,
            rich_snippet=item.get("rich_snippet"),
            author=item.get("author"),
            relevance_score=item.get("position_rank"),
            result_type="organic",
            cache_key=f"serpapi:{item.get('link', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _parse_featured_snippet(
        self, 
        answer_box: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse featured snippet/answer box."""
        snippet_text = (
            answer_box.get("answer") or 
            answer_box.get("snippet") or 
            answer_box.get("title", "")
        )
        
        return StructuredSearchResult(
            position=position + 1,
            url=answer_box.get("link", ""),
            title=answer_box.get("title", "Featured Snippet"),
            description=snippet_text,
            source=self.name,
            rich_snippet=snippet_text,
            result_type="featured_snippet",
            relevance_score=1.0,  # Highest relevance
            cache_key=f"serpapi:featured:{answer_box.get('link', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _parse_knowledge_graph(
        self, 
        kg: Dict[str, Any], 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse knowledge graph result."""
        # Build description from knowledge graph data
        description_parts = []
        
        if kg.get("description"):
            description_parts.append(kg["description"])
        
        if kg.get("source"):
            description_parts.append(f"Source: {kg['source']}")
        
        # Add key facts if available
        if kg.get("knowledge_graph"):
            for key, value in kg["knowledge_graph"].items():
                if isinstance(value, str) and len(value) < 200:
                    description_parts.append(f"{key}: {value}")
        
        return StructuredSearchResult(
            position=position + 1,
            url=kg.get("knowledge_graph_link", ""),
            title=kg.get("title", "Knowledge Graph"),
            description=" | ".join(description_parts),
            source=self.name,
            structured_data={"knowledge_graph": kg},
            result_type="knowledge_graph",
            relevance_score=0.95,
            cache_key=f"serpapi:kg:{kg.get('title', '')}",
            query_hash=self._hash_query(query),
        )
    
    def _hash_query(self, query: str) -> str:
        """Create a simple hash for the query."""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]