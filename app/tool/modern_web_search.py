"""
Modern Web Search with HTTP/2, structured results, and RAG helper.

This module provides a modern web search implementation that replaces the legacy
search engines with HTTP/2-enabled backends and LLM-based semantic refinement.
"""

import asyncio
import hashlib
import random
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import config
from app.logger import logger
from app.network.guardian import Guardian, OperationType, get_guardian
from app.rag.search_rag_helper import SearchRAGHelper, SearchRAGResult
from app.tool.base import BaseTool, ToolResult
from app.tool.search.backends import (
    BraveSearchBackend,
    DuckDuckGoBackend,
    GoogleCustomSearchBackend,
    ModernSearchBackend,
    SerpApiBackend,
)
from app.tool.search.backends.base import StructuredSearchResult


class ModernSearchResult(BaseModel):
    """Enhanced search result with modern features."""
    
    # Basic fields
    position: int = Field(description="Position in search results")
    url: str = Field(description="URL of the search result")
    title: str = Field(default="", description="Title of the search result")
    description: str = Field(default="", description="Description of the search result")
    source: str = Field(description="Search backend that provided this result")
    
    # Enhanced fields
    structured_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Parsed structured data"
    )
    rich_snippet: Optional[str] = Field(
        default=None, description="Rich snippet content"
    )
    date_published: Optional[str] = Field(
        default=None, description="Publication date"
    )
    author: Optional[str] = Field(default=None, description="Author name")
    relevance_score: Optional[float] = Field(
        default=None, description="Relevance score (0.0-1.0)"
    )
    result_type: Optional[str] = Field(
        default=None, description="Type of result"
    )
    
    # RAG enhancement fields
    rag_reasoning: Optional[str] = Field(
        default=None, description="RAG reasoning for selection"
    )
    rag_ranking: Optional[int] = Field(
        default=None, description="Ranking by RAG helper"
    )
    key_insights: List[str] = Field(
        default_factory=list, description="Key insights from RAG analysis"
    )
    
    # Content fetching
    raw_content: Optional[str] = Field(
        default=None, description="Raw content from the page"
    )
    
    def __str__(self) -> str:
        """String representation of a modern search result."""
        return f"{self.title} ({self.url})"


class ModernSearchMetadata(BaseModel):
    """Metadata about the modern search operation."""
    
    total_results: int = Field(description="Total number of results found")
    backend_used: str = Field(description="Search backend that was used")
    query_reformulations: int = Field(description="Number of query reformulations")
    rag_iterations: int = Field(description="Number of RAG iterations")
    cache_hits: int = Field(description="Number of cache hits")
    search_time_seconds: float = Field(description="Total search time in seconds")
    http2_enabled: bool = Field(description="Whether HTTP/2 was used")
    structured_results_enabled: bool = Field(description="Whether structured parsing was enabled")


class ModernSearchResponse(ToolResult):
    """Enhanced response from the modern web search tool."""
    
    query: str = Field(description="The final search query that was executed")
    original_query: str = Field(description="The original search query")
    results: List[ModernSearchResult] = Field(
        default_factory=list, description="List of enhanced search results"
    )
    metadata: Optional[ModernSearchMetadata] = Field(
        default=None, description="Metadata about the search"
    )
    rag_result: Optional[SearchRAGResult] = Field(
        default=None, description="Full RAG analysis result"
    )
    reasoning_trace: List[str] = Field(
        default_factory=list, description="Complete reasoning trace"
    )
    
    @classmethod
    def from_rag_result(cls, rag_result: SearchRAGResult, backend_used: str, search_time: float) -> "ModernSearchResponse":
        """Create ModernSearchResponse from SearchRAGResult."""
        # Convert StructuredSearchResult to ModernSearchResult
        modern_results = []
        
        for i, structured_result in enumerate(rag_result.ranked_results):
            # Find corresponding ranking if available
            ranking = None
            for r in rag_result.rankings:
                if r.result_index < len(rag_result.original_results) and \
                   rag_result.original_results[r.result_index].url == structured_result.url:
                    ranking = r
                    break
            
            modern_result = ModernSearchResult(
                position=i + 1,
                url=structured_result.url,
                title=structured_result.title,
                description=structured_result.description,
                source=structured_result.source,
                structured_data=structured_result.structured_data,
                rich_snippet=structured_result.rich_snippet,
                date_published=structured_result.date_published,
                author=structured_result.author,
                relevance_score=structured_result.relevance_score,
                result_type=structured_result.result_type,
                rag_reasoning=ranking.ranking_reasoning if ranking else None,
                rag_ranking=ranking.result_index if ranking else None,
                key_insights=ranking.key_insights if ranking else [],
            )
            modern_results.append(modern_result)
        
        # Create metadata
        metadata = ModernSearchMetadata(
            total_results=len(rag_result.original_results),
            backend_used=backend_used,
            query_reformulations=len(rag_result.reformulations),
            rag_iterations=rag_result.iteration_count,
            cache_hits=rag_result.cache_hits,
            search_time_seconds=search_time,
            http2_enabled=getattr(config.search_config, "enable_http2", True),
            structured_results_enabled=getattr(config.search_config, "enable_structured_results", True),
        )
        
        return cls(
            status="success",
            query=rag_result.query,
            original_query=rag_result.query,
            results=modern_results,
            metadata=metadata,
            rag_result=rag_result,
            reasoning_trace=rag_result.reasoning_trace,
        )
    
    def model_dump_for_output(self) -> Dict[str, Any]:
        """Prepare data for output formatting."""
        data = self.dict()
        
        # Limit reasoning trace for output
        if data.get("reasoning_trace"):
            data["reasoning_trace"] = data["reasoning_trace"][-10:]  # Last 10 entries
        
        # Remove full RAG result to avoid too much output
        data.pop("rag_result", None)
        
        return data


class ModernWebSearch(BaseTool):
    """Modern web search tool with HTTP/2, structured results, and RAG helper."""
    
    name: str = "web_search"
    description: str = """Search the web using modern protocols with HTTP/2 support, structured results parsing, and LLM-based semantic refinement.
    
    Features:
    - Multiple search backends (SerpAPI, Brave, DuckDuckGo, Google)
    - HTTP/2 for faster queries
    - Structured data parsing (JSON-LD, microdata)
    - LLM-based query reformulation and result ranking
    - Semantic understanding without embeddings
    - SQLite-based caching (not vector store)
    - Reasoning traces for transparency
    
    Backends: serpapi (default), brave, duckduckgo, google
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) Number of results to return. Default is 10.",
                "default": 10,
            },
            "backend": {
                "type": "string",
                "description": "(optional) Search backend: serpapi, brave, duckduckgo, google. Default from config.",
                "enum": ["serpapi", "brave", "duckduckgo", "google"],
            },
            "lang": {
                "type": "string",
                "description": "(optional) Language code. Default: en.",
                "default": "en",
            },
            "country": {
                "type": "string",
                "description": "(optional) Country code. Default: us.",
                "default": "us",
            },
            "enable_rag": {
                "type": "boolean",
                "description": "(optional) Enable RAG helper for semantic refinement. Default from config.",
            },
            "fetch_content": {
                "type": "boolean",
                "description": "(optional) Fetch full content from result pages. Default: false.",
                "default": False,
            },
            "batch_search": {
                "type": "boolean",
                "description": "(optional) Enable batch search for multiple queries. Default: false.",
                "default": False,
            },
            "additional_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "(optional) Additional queries for batch search.",
            },
        },
        "required": ["query"],
    }
    
    def __init__(self):
        super().__init__()
        self._backends: Dict[str, ModernSearchBackend] = {}
        self._rag_helper: Optional[SearchRAGHelper] = None
        self._init_backends()
    
    def _init_backends(self):
        """Initialize search backends."""
        backend_config = {
            "serpapi_key": getattr(config.search_config, "serpapi_key", None),
            "brave_api_key": getattr(config.search_config, "brave_api_key", None),
            "google_api_key": getattr(config.search_config, "google_api_key", None),
            "google_search_engine_id": getattr(config.search_config, "google_search_engine_id", None),
            "enable_http2": getattr(config.search_config, "enable_http2", True),
            "enable_connection_pooling": getattr(config.search_config, "enable_connection_pooling", True),
            "max_connections_per_backend": getattr(config.search_config, "max_connections_per_backend", 10),
            "enable_request_compression": getattr(config.search_config, "enable_request_compression", True),
            "enable_response_compression": getattr(config.search_config, "enable_response_compression", True),
            "enable_structured_results": getattr(config.search_config, "enable_structured_results", True),
            "enable_user_agent_rotation": getattr(config.search_config, "enable_user_agent_rotation", True),
            "user_agents": getattr(config.search_config, "user_agents", []),
            "search_timeout": getattr(config.search_config, "search_timeout", 30.0),
            "verify_ssl": getattr(config.network_config, "http_verify_ssl", True) if hasattr(config, 'network_config') else True,
        }
        
        # Initialize backends
        self._backends["serpapi"] = SerpApiBackend(backend_config)
        self._backends["brave"] = BraveSearchBackend(backend_config)
        self._backends["duckduckgo"] = DuckDuckGoBackend(backend_config)
        self._backends["google"] = GoogleCustomSearchBackend(backend_config)
        
        # Initialize RAG helper if enabled
        if getattr(config.search_config, "search_rag_enabled", True):
            self._rag_helper = SearchRAGHelper()
    
    async def execute(
        self,
        query: str,
        num_results: int = 10,
        backend: Optional[str] = None,
        lang: Optional[str] = None,
        country: Optional[str] = None,
        enable_rag: Optional[bool] = None,
        fetch_content: bool = False,
        batch_search: bool = False,
        additional_queries: Optional[List[str]] = None,
        **kwargs
    ) -> ModernSearchResponse:
        """Execute modern web search."""
        start_time = asyncio.get_event_loop().time()
        
        # Get configuration values
        if backend is None:
            backend = getattr(config.search_config, "search_backend", "serpapi")
        
        if lang is None:
            lang = getattr(config.search_config, "lang", "en")
        
        if country is None:
            country = getattr(config.search_config, "country", "us")
        
        if enable_rag is None:
            enable_rag = getattr(config.search_config, "search_rag_enabled", True)
        
        # Validate backend
        if backend not in self._backends:
            return ModernSearchResponse(
                query=query,
                error=f"Unknown search backend: {backend}. Available: {list(self._backends.keys())}",
                results=[],
            )
        
        # Prepare search function
        search_backend = self._backends[backend]
        
        async def search_func(q: str, **search_kwargs) -> List[StructuredSearchResult]:
            return await search_backend.search(q, **search_kwargs)
        
        try:
            # Guardian validation for search operation
            guardian = get_guardian()
            if guardian:
                assessment = guardian.assess_risk(
                    operation=OperationType.WEB_SEARCH,
                    host="search",  # Generic host for web search
                    target=query,
                    metadata={
                        "backend": backend,
                        "num_results": num_results,
                        "lang": lang,
                        "country": country,
                        "enable_rag": enable_rag,
                        "fetch_content": fetch_content,
                    }
                )
                
                if not assessment.approved:
                    search_time = asyncio.get_event_loop().time() - start_time
                    
                    return ModernSearchResponse(
                        query=query,
                        original_query=query,
                        results=[],
                        metadata=ModernSearchMetadata(
                            total_results=0,
                            backend_used=backend,
                            query_reformulations=0,
                            rag_iterations=0,
                            cache_hits=0,
                            search_time_seconds=search_time,
                            http2_enabled=getattr(config.search_config, "enable_http2", True),
                            structured_results_enabled=getattr(config.search_config, "enable_structured_results", True),
                        ),
                        error=f"Search blocked by Guardian: {', '.join(assessment.reasons)}",
                    )
                
                logger.info(f"Guardian approved search operation with risk level: {assessment.level}")
            
            # Perform search with or without RAG
            if enable_rag and self._rag_helper:
                rag_result = await self._rag_helper.search(
                    query=query,
                    search_func=search_func,
                    num_results=num_results,
                    lang=lang,
                    country=country,
                    **kwargs
                )
                
                search_time = asyncio.get_event_loop().time() - start_time
                response = ModernSearchResponse.from_rag_result(rag_result, backend, search_time)
                
            else:
                # Direct search without RAG
                results = await search_func(query, num_results, lang, country, **kwargs)
                search_time = asyncio.get_event_loop().time() - start_time
                
                # Convert to modern results
                modern_results = []
                for i, result in enumerate(results):
                    modern_result = ModernSearchResult(
                        position=i + 1,
                        url=result.url,
                        title=result.title,
                        description=result.description,
                        source=result.source,
                        structured_data=result.structured_data,
                        rich_snippet=result.rich_snippet,
                        date_published=result.date_published,
                        author=result.author,
                        relevance_score=result.relevance_score,
                        result_type=result.result_type,
                    )
                    modern_results.append(modern_result)
                
                metadata = ModernSearchMetadata(
                    total_results=len(results),
                    backend_used=backend,
                    query_reformulations=0,
                    rag_iterations=1,
                    cache_hits=0,
                    search_time_seconds=search_time,
                    http2_enabled=getattr(config.search_config, "enable_http2", True),
                    structured_results_enabled=getattr(config.search_config, "enable_structured_results", True),
                )
                
                response = ModernSearchResponse(
                    status="success",
                    query=query,
                    original_query=query,
                    results=modern_results,
                    metadata=metadata,
                )
            
            # Fetch content if requested
            if fetch_content and response.results:
                response.results = await self._fetch_content_for_results(response.results)
            
            # Generate output
            response.output = self._format_output(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Modern web search failed: {e}")
            search_time = asyncio.get_event_loop().time() - start_time
            
            return ModernSearchResponse(
                query=query,
                error=f"Search failed: {str(e)}",
                results=[],
                metadata=ModernSearchMetadata(
                    total_results=0,
                    backend_used=backend,
                    query_reformulations=0,
                    rag_iterations=0,
                    cache_hits=0,
                    search_time_seconds=search_time,
                    http2_enabled=False,
                    structured_results_enabled=False,
                ),
            )
    
    async def _fetch_content_for_results(
        self, 
        results: List[ModernSearchResult]
    ) -> List[ModernSearchResult]:
        """Fetch full content for search results."""
        if not results:
            return results
        
        # Create tasks for parallel content fetching
        tasks = []
        for result in results:
            task = self._fetch_single_content(result)
            tasks.append(task)
        
        # Execute in parallel
        fetched_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update results with fetched content
        updated_results = []
        for i, fetched in enumerate(fetched_results):
            if isinstance(fetched, Exception):
                logger.warning(f"Failed to fetch content for result {i}: {fetched}")
                updated_results.append(results[i])
            else:
                updated_results.append(fetched)
        
        return updated_results
    
    async def _fetch_single_content(self, result: ModernSearchResult) -> ModernSearchResult:
        """Fetch content for a single result."""
        try:
            # Use a simple HTTP client for content fetching
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(result.url)
                if response.status_code == 200:
                    # Parse HTML content
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "header", "footer", "nav"]):
                        script.extract()
                    
                    # Get text content
                    text = soup.get_text(separator="\n", strip=True)
                    text = " ".join(text.split())
                    
                    # Limit content size
                    result.raw_content = text[:10000] if text else None
                else:
                    logger.warning(f"HTTP {response.status_code} for {result.url}")
        
        except Exception as e:
            logger.warning(f"Error fetching content from {result.url}: {e}")
        
        return result
    
    def _format_output(self, response: ModernSearchResponse) -> str:
        """Format the search response for output."""
        output_lines = []
        
        # Header
        output_lines.append(f"🔍 Modern Web Search Results")
        output_lines.append(f"Query: {response.original_query}")
        if response.query != response.original_query:
            output_lines.append(f"Refined Query: {response.query}")
        output_lines.append(f"Backend: {response.metadata.backend_used if response.metadata else 'Unknown'}")
        output_lines.append("")
        
        # Results
        for i, result in enumerate(response.results, 1):
            output_lines.append(f"{i}. {result.title}")
            output_lines.append(f"   URL: {result.url}")
            
            if result.description:
                output_lines.append(f"   Description: {result.description}")
            
            if result.rich_snippet:
                output_lines.append(f"   Rich Snippet: {result.rich_snippet[:200]}...")
            
            if result.rag_reasoning:
                output_lines.append(f"   RAG Reasoning: {result.rag_reasoning[:150]}...")
            
            if result.key_insights:
                insights_text = ", ".join(result.key_insights[:2])
                output_lines.append(f"   Key Insights: {insights_text}")
            
            if result.result_type:
                output_lines.append(f"   Type: {result.result_type}")
            
            output_lines.append("")
        
        # Metadata
        if response.metadata:
            output_lines.append("📊 Search Metadata:")
            output_lines.append(f"   Total Results: {response.metadata.total_results}")
            output_lines.append(f"   Query Reformulations: {response.metadata.query_reformulations}")
            output_lines.append(f"   RAG Iterations: {response.metadata.rag_iterations}")
            output_lines.append(f"   Cache Hits: {response.metadata.cache_hits}")
            output_lines.append(f"   Search Time: {response.metadata.search_time_seconds:.2f}s")
            output_lines.append(f"   HTTP/2 Enabled: {response.metadata.http2_enabled}")
            output_lines.append(f"   Structured Results: {response.metadata.structured_results_enabled}")
        
        # Reasoning trace (limited)
        if response.reasoning_trace and len(response.reasoning_trace) > 0:
            output_lines.append("")
            output_lines.append("🧠 Reasoning Trace (last 10 entries):")
            for trace in response.reasoning_trace[-10:]:
                output_lines.append(f"   • {trace}")
        
        return "\n".join(output_lines)
    
    async def close(self):
        """Close all backend connections."""
        for backend in self._backends.values():
            await backend.close()
    
    def __del__(self):
        """Cleanup when tool is destroyed."""
        if self._backends:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except:
                pass