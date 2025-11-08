"""
Tests for modern web search implementation.

These tests verify the HTTP/2-enabled search backends, RAG helper,
and structured results parsing functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import config
from app.rag.search_rag_helper import SearchRAGHelper, QueryReformulation, ResultRanking
from app.tool.modern_web_search import ModernWebSearch, ModernSearchResult, ModernSearchMetadata, ModernSearchResponse
from app.tool.search.backends import (
    BraveSearchBackend,
    DuckDuckGoBackend,
    GoogleCustomSearchBackend,
    SerpApiBackend,
)
from app.tool.search.backends.base import StructuredSearchResult


class TestModernSearchBackends:
    """Test modern search backends."""
    
    @pytest.fixture
    def backend_config(self):
        """Common backend configuration."""
        return {
            "enable_http2": True,
            "enable_connection_pooling": True,
            "max_connections_per_backend": 10,
            "enable_request_compression": True,
            "enable_response_compression": True,
            "enable_structured_results": True,
            "enable_user_agent_rotation": True,
            "user_agents": ["test-agent"],
            "search_timeout": 30.0,
            "verify_ssl": True,
        }
    
    @pytest.mark.asyncio
    async def test_serpapi_backend_initialization(self, backend_config):
        """Test SerpApi backend initialization."""
        backend = SerpApiBackend(backend_config)
        assert backend.name == "serpapi"
        assert backend.config == backend_config
        await backend.close()
    
    @pytest.mark.asyncio
    async def test_brave_backend_initialization(self, backend_config):
        """Test Brave Search backend initialization."""
        backend = BraveSearchBackend(backend_config)
        assert backend.name == "bravesearch"
        assert backend.config == backend_config
        await backend.close()
    
    @pytest.mark.asyncio
    async def test_duckduckgo_backend_initialization(self, backend_config):
        """Test DuckDuckGo backend initialization."""
        backend = DuckDuckGoBackend(backend_config)
        assert backend.name == "duckduckgo"
        assert backend.config == backend_config
        await backend.close()
    
    @pytest.mark.asyncio
    async def test_google_backend_initialization(self, backend_config):
        """Test Google Custom Search backend initialization."""
        backend = GoogleCustomSearchBackend(backend_config)
        assert backend.name == "googlecustomsearch"
        assert backend.config == backend_config
        await backend.close()
    
    @pytest.mark.asyncio
    async def test_http2_client_creation(self, backend_config):
        """Test HTTP/2 client creation."""
        backend = SerpApiBackend(backend_config)
        client = backend.client
        
        # Verify HTTP/2 is enabled
        assert client._http2 == True
        
        # Verify limits are set
        assert client._limits.max_keepalive_connections == 10
        assert client._limits.max_connections == 20
        
        await backend.close()
    
    @pytest.mark.asyncio
    async def test_user_agent_rotation(self, backend_config):
        """Test User-Agent rotation."""
        backend = SerpApiBackend(backend_config)
        
        # Get first user agent
        ua1 = backend._get_user_agent()
        
        # Get second user agent (should be same since only one in list)
        ua2 = backend._get_user_agent()
        
        assert ua1 == ua2
        assert ua1 == "test-agent"
        
        await backend.close()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_serpapi_search_success(self, mock_get, backend_config):
        """Test successful SerpApi search."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic_results": [
                {
                    "title": "Test Result",
                    "link": "https://example.com",
                    "snippet": "Test description",
                    "position": 1
                }
            ]
        }
        mock_get.return_value = mock_response
        
        backend = SerpApiBackend({**backend_config, "serpapi_key": "test_key"})
        backend._client = MagicMock()
        backend._make_request = AsyncMock(return_value=mock_response)
        
        results = await backend.search("test query", num_results=5)
        
        assert len(results) == 1
        assert results[0].title == "Test Result"
        assert results[0].url == "https://example.com"
        assert results[0].description == "Test description"
        assert results[0].position == 1
        
        await backend.close()


class TestSearchRAGHelper:
    """Test RAG helper functionality."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        llm = MagicMock()
        llm.generate_response = AsyncMock()
        return llm
    
    @pytest.fixture
    def rag_helper(self, mock_llm):
        """RAG helper with mock LLM."""
        return SearchRAGHelper(mock_llm)
    
    def test_rag_helper_initialization(self, mock_llm):
        """Test RAG helper initialization."""
        helper = SearchRAGHelper(mock_llm)
        assert helper.llm == mock_llm
        assert helper.max_iterations > 0
        assert helper.context_window > 0
        assert 0 <= helper.similarity_threshold <= 1
    
    @pytest.mark.asyncio
    async def test_query_reformulation_parsing(self, rag_helper):
        """Test query reformulation JSON parsing."""
        mock_response = json.dumps({
            "reformulated_query": "improved query",
            "reformulation_reasoning": "made it more specific",
            "expansion_terms": ["term1", "term2"],
            "disambiguation_context": "context for clarification"
        })
        
        rag_helper.llm.generate_response.return_value = mock_response
        
        reformulation = await rag_helper._reformulate_query(
            "original query", 
            [], 
            ["needs more specificity"]
        )
        
        assert reformulation.original_query == "original query"
        assert reformulation.reformulated_query == "improved query"
        assert reformulation.reformulation_reasoning == "made it more specific"
        assert reformulation.expansion_terms == ["term1", "term2"]
        assert reformulation.disambiguation_context == "context for clarification"
    
    @pytest.mark.asyncio
    async def test_result_ranking(self, rag_helper):
        """Test result ranking functionality."""
        # Create test results
        results = [
            StructuredSearchResult(
                position=1, url="https://example1.com", title="Result 1",
                description="Description 1", source="test"
            ),
            StructuredSearchResult(
                position=2, url="https://example2.com", title="Result 2",
                description="Description 2", source="test"
            ),
        ]
        
        # Mock ranking response
        mock_response = json.dumps([
            {
                "result_index": 0,
                "relevance_score": 0.9,
                "ranking_reasoning": "Highly relevant",
                "key_insights": ["insight 1"],
                "relevance_to_query": "Directly answers the question"
            },
            {
                "result_index": 1,
                "relevance_score": 0.7,
                "ranking_reasoning": "Somewhat relevant",
                "key_insights": ["insight 2"],
                "relevance_to_query": "Related but not direct"
            }
        ])
        
        rag_helper.llm.generate_response.return_value = mock_response
        
        ranked_results, rankings = await rag_helper._rank_results("test query", results, [])
        
        assert len(ranked_results) == 2
        assert len(rankings) == 2
        assert rankings[0].relevance_score == 0.9
        assert rankings[1].relevance_score == 0.7
    
    def test_result_deduplication(self, rag_helper):
        """Test result deduplication."""
        results = [
            StructuredSearchResult(
                position=1, url="https://example.com", title="Result 1",
                description="Description 1", source="test"
            ),
            StructuredSearchResult(
                position=2, url="https://example.com/", title="Result 2",
                description="Description 2", source="test"
            ),
            StructuredSearchResult(
                position=3, url="https://example.com/page", title="Result 3",
                description="Description 3", source="test"
            ),
        ]
        
        unique_results = rag_helper._deduplicate_results(results)
        
        # Should remove duplicates (same URL after normalization)
        assert len(unique_results) == 2
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, rag_helper):
        """Test cache get/set operations."""
        # Create a mock result
        from app.rag.search_rag_helper import SearchRAGResult
        mock_result = SearchRAGResult(
            query="test query",
            original_results=[],
            ranked_results=[],
            reformulations=[],
            rankings=[],
            reasoning_trace=["test"],
            iteration_count=1,
            cache_hits=0,
            search_metadata={}
        )
        
        # Test caching
        await rag_helper._cache_result("test query", mock_result)
        
        # Test retrieval
        cached_result = await rag_helper._get_cached_result("test query")
        assert cached_result is not None
        assert cached_result.query == "test query"
        assert cached_result.cache_hits == 2  # Original + retrieval


class TestModernWebSearch:
    """Test modern web search tool."""
    
    @pytest.fixture
    def modern_search(self):
        """Modern web search instance."""
        return ModernWebSearch()
    
    def test_modern_search_initialization(self, modern_search):
        """Test modern search initialization."""
        assert modern_search.name == "web_search"
        assert "serpapi" in modern_search._backends
        assert "brave" in modern_search._backends
        assert "duckduckgo" in modern_search._backends
        assert "google" in modern_search._backends
    
    @pytest.mark.asyncio
    async def test_backend_validation(self, modern_search):
        """Test backend validation."""
        response = await modern_search.execute(
            query="test",
            backend="invalid_backend"
        )
        
        assert response.error is not None
        assert "invalid_backend" in response.error
        assert "Available:" in response.error
    
    @pytest.mark.asyncio
    @patch('app.tool.search.backends.serpapi_backend.SerpApiBackend.search')
    async def test_search_with_rag_disabled(self, mock_search, modern_search):
        """Test search without RAG helper."""
        # Mock successful search
        mock_search.return_value = [
            StructuredSearchResult(
                position=1, url="https://example.com", title="Test",
                description="Test description", source="serpapi"
            )
        ]
        
        response = await modern_search.execute(
            query="test",
            enable_rag=False,
            num_results=5
        )
        
        assert response.status == "success"
        assert len(response.results) == 1
        assert response.results[0].title == "Test"
        assert response.metadata is not None
        assert response.metadata.rag_iterations == 1
        assert response.metadata.query_reformulations == 0
    
    @pytest.mark.asyncio
    async def test_content_fetching(self, modern_search):
        """Test content fetching functionality."""
        # Create a mock result
        result = ModernSearchResult(
            position=1, url="https://example.com", title="Test",
            description="Test description", source="test"
        )
        
        # Mock HTTP response
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body><h1>Test Content</h1><p>Test paragraph</p></body></html>"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            fetched_result = await modern_search._fetch_single_content(result)
            
            assert fetched_result.raw_content is not None
            assert "Test Content" in fetched_result.raw_content
            assert "Test paragraph" in fetched_result.raw_content
    
    def test_output_formatting(self, modern_search):
        """Test output formatting."""
        # Create mock response
        from app.tool.modern_web_search import ModernSearchMetadata
        metadata = ModernSearchMetadata(
            total_results=5,
            backend_used="serpapi",
            query_reformulations=2,
            rag_iterations=3,
            cache_hits=1,
            search_time_seconds=1.5,
            http2_enabled=True,
            structured_results_enabled=True
        )
        
        response = ModernSearchResponse(
            status="success",
            query="test query",
            original_query="test",
            results=[],
            metadata=metadata,
            reasoning_trace=["step 1", "step 2"]
        )
        
        output = modern_search._format_output(response)
        
        assert "Modern Web Search Results" in output
        assert "Query: test query" in output
        assert "Backend: serpapi" in output
        assert "Total Results: 5" in output
        assert "Query Reformulations: 2" in output
        assert "RAG Iterations: 3" in output
        assert "HTTP/2 Enabled: True" in output


class TestBackwardCompatibility:
    """Test backward compatibility with legacy web search."""
    
    @pytest.mark.asyncio
    async def test_legacy_search_response_format(self):
        """Test that legacy SearchResponse format is maintained."""
        from app.tool.web_search import SearchResponse, SearchResult
        
        # Create modern results
        modern_results = [
            ModernSearchResult(
                position=1, url="https://example.com", title="Test",
                description="Test description", source="test"
            )
        ]
        
        # Convert to legacy format
        response = SearchResponse(
            status="success",
            query="test",
            results=modern_results
        )
        
        # Verify legacy format
        assert len(response.results) == 1
        assert isinstance(response.results[0], SearchResult)
        assert response.results[0].title == "Test"
        assert response.results[0].url == "https://example.com"
        assert response.output is not None
        assert "Search results for 'test'" in response.output


if __name__ == "__main__":
    # Run a quick smoke test
    async def smoke_test():
        print("Running smoke test for modern web search...")
        
        # Test backend initialization
        config = {
            "enable_http2": True,
            "search_timeout": 30.0,
            "user_agents": ["test-agent"],
        }
        
        backend = SerpApiBackend(config)
        print(f"✓ SerpApi backend initialized: {backend.name}")
        
        # Test RAG helper
        helper = SearchRAGHelper()
        print(f"✓ RAG helper initialized")
        
        # Test modern search
        search = ModernWebSearch()
        print(f"✓ Modern web search initialized with {len(search._backends)} backends")
        
        print("Smoke test passed!")
    
    asyncio.run(smoke_test())