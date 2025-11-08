import asyncio
from typing import Any, Dict, List, Optional

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.modern_web_search import ModernWebSearch, ModernSearchResponse, ModernSearchResult
from app.tool.search import (
    WebSearchEngine,
)
from app.tool.search.base import SearchItem


class SearchResult(ModernSearchResult):
    """Legacy search result class for backward compatibility."""
    
    def __init__(self, **data):
        # Convert legacy field names to modern ones
        if "raw_content" in data and data["raw_content"]:
            # Keep raw_content as is
            pass
        super().__init__(**data)


class SearchMetadata:
    """Legacy metadata class for backward compatibility."""
    
    def __init__(self, total_results: int, language: str, country: str, **kwargs):
        self.total_results = total_results
        self.language = language
        self.country = country
        
        # Add any additional metadata
        for key, value in kwargs.items():
            setattr(self, key, value)


class SearchResponse:
    """Legacy search response class for backward compatibility."""
    
    def __init__(self, **data):
        # Set required fields with defaults
        self.query = data.get("query", "")
        self.original_query = data.get("original_query", data.get("query", ""))
        self.results = data.get("results", [])
        self.error = data.get("error", None)
        self.status = data.get("status", "success" if not data.get("error") else "error")
        self.output = data.get("output", None)
        self.metadata = data.get("metadata", None)
        
        # Convert to legacy format
        if self.results:
            # Convert ModernSearchResult to SearchResult if needed
            legacy_results = []
            for result in self.results:
                if isinstance(result, ModernSearchResult):
                    # Convert to legacy SearchResult
                    legacy_data = result.dict()
                    legacy_result = SearchResult(**legacy_data)
                    legacy_results.append(legacy_result)
                else:
                    legacy_results.append(result)
            self.results = legacy_results
        
        # Generate legacy output format
        if not self.error and self.results:
            self.output = self._generate_legacy_output()
    
    def _generate_legacy_output(self) -> str:
        """Generate output in legacy format."""
        result_text = [f"Search results for '{self.query}':"]

        for i, result in enumerate(self.results, 1):
            # Add title with position number
            title = result.title.strip() or "No title"
            result_text.append(f"\n{i}. {title}")

            # Add URL with proper indentation
            result_text.append(f"   URL: {result.url}")

            # Add description if available
            if hasattr(result, 'description') and result.description and result.description.strip():
                result_text.append(f"   Description: {result.description}")

            # Add content preview if available
            if hasattr(result, 'raw_content') and result.raw_content:
                content_preview = result.raw_content[:1000].replace("\n", " ").strip()
                if len(result.raw_content) > 1000:
                    content_preview += "..."
                result_text.append(f"   Content: {content_preview}")

        # Add metadata at the bottom if available
        if hasattr(self, 'metadata') and self.metadata:
            result_text.extend([
                f"\nMetadata:",
                f"- Total results: {self.metadata.total_results}",
                f"- Language: {self.metadata.language}",
                f"- Country: {self.metadata.country}",
            ])

        return "\n".join(result_text)


class WebContentFetcher:
    """Legacy web content fetcher for backward compatibility."""
    
    @staticmethod
    async def fetch_content(url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch and extract the main content from a webpage.
        
        This is a legacy wrapper around the modern content fetching.
        """
        try:
            # Use the modern web search's content fetching
            modern_search = ModernWebSearch()
            
            # Create a dummy result and fetch content
            dummy_result = ModernSearchResult(
                position=1,
                url=url,
                title="Content Fetch",
                description="Fetching content"
            )
            
            fetched_result = await modern_search._fetch_single_content(dummy_result)
            return fetched_result.raw_content
            
        except Exception as e:
            logger.warning(f"Error fetching content from {url}: {e}")
            return None


class WebSearch(BaseTool):
    """
    Legacy Web search tool with modern backend support.
    
    This tool provides backward compatibility while using the modern
    HTTP/2-enabled search backends and RAG helper.
    """
    
    name: str = "web_search"
    description: str = """Search the web for real-time information using modern search backends.
    
    This tool now uses HTTP/2-enabled backends (SerpAPI, Brave, DuckDuckGo, Google)
    with optional LLM-based semantic refinement and structured results parsing.
    
    Legacy behavior is maintained for backward compatibility.
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
                "description": "(optional) Number of results to return. Default is 5.",
                "default": 5,
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
            "fetch_content": {
                "type": "boolean",
                "description": "(optional) Fetch full content from result pages. Default: false.",
                "default": False,
            },
        },
        "required": ["query"],
    }
    
    def __init__(self):
        super().__init__()
        self._modern_search = ModernWebSearch()
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
        lang: Optional[str] = None,
        country: Optional[str] = None,
        fetch_content: bool = False,
    ) -> SearchResponse:
        """
        Execute web search using modern backend but return legacy format.
        
        Args:
            query: The search query
            num_results: Number of results to return
            lang: Language code
            country: Country code
            fetch_content: Whether to fetch full content
            
        Returns:
            Legacy SearchResponse with modern results
        """
        try:
            # Use modern search backend
            modern_response = await self._modern_search.execute(
                query=query,
                num_results=num_results,
                lang=lang,
                country=country,
                enable_rag=getattr(config.search_config, "search_rag_enabled", True),
                fetch_content=fetch_content,
            )
            
            # Convert to legacy format
            legacy_results = []
            for modern_result in modern_response.results:
                # Convert to legacy SearchResult
                legacy_result = SearchResult(
                    position=modern_result.position,
                    url=modern_result.url,
                    title=modern_result.title,
                    description=modern_result.description,
                    source=modern_result.source,
                    raw_content=modern_result.raw_content,
                )
                legacy_results.append(legacy_result)
            
            # Create legacy metadata
            legacy_metadata = SearchMetadata(
                total_results=len(legacy_results),
                language=lang or getattr(config.search_config, "lang", "en"),
                country=country or getattr(config.search_config, "country", "us"),
                backend_used=modern_response.metadata.backend_used if modern_response.metadata else "unknown",
                query_reformulations=modern_response.metadata.query_reformulations if modern_response.metadata else 0,
                rag_iterations=modern_response.metadata.rag_iterations if modern_response.metadata else 0,
            )
            
            # Return legacy response
            return SearchResponse(
                query=modern_response.query,
                original_query=modern_response.original_query,
                results=legacy_results,
                metadata=legacy_metadata,
                error=modern_response.error,
                output=modern_response.output,
            )
            
        except Exception as e:
            logger.error(f"Legacy web search failed: {e}")
            return SearchResponse(
                query=query,
                original_query=query,
                error=f"Search failed: {str(e)}",
                results=[],
            )


if __name__ == "__main__":
    web_search = WebSearch()
    search_response = asyncio.run(
        web_search.execute(
            query="Python programming", 
            fetch_content=True, 
            num_results=3
        )
    )
    print(search_response.to_tool_result())
