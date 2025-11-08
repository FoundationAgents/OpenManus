"""Tests for BrowserRAGHelper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.browser.rag_helper import (
    BrowserRAGHelper,
    PageSummary,
    SemanticElement,
    ContentUnderstanding,
)


@pytest.fixture
def rag_helper():
    """Create a RAG helper instance."""
    helper = BrowserRAGHelper(
        llm=MagicMock(),
        cache_dir="./cache/test_rag",
    )
    return helper


@pytest.fixture
def mock_page_content():
    """Mock page content."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Welcome to Test Page</h1>
        <form>
            <input type="email" id="email" placeholder="Email">
            <input type="password" id="password" placeholder="Password">
            <button type="submit">Login</button>
        </form>
        <div class="content">
            <p>This is the main content of the page.</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_page_text():
    """Mock page text content."""
    return """
    Welcome to Test Page
    
    This is the main content of the page.
    
    Please enter your email and password to login.
    """


class TestBrowserRAGHelper:
    """Tests for BrowserRAGHelper."""
    
    def test_initialization(self, rag_helper):
        """Test RAG helper initialization."""
        assert rag_helper is not None
        assert rag_helper.semantic_depth in ["minimal", "normal", "detailed"]
        assert rag_helper.cache_ttl > 0
    
    def test_cache_initialization(self, rag_helper):
        """Test cache database initialization."""
        cache_db = rag_helper.cache_dir / "browser_rag_cache.db"
        assert cache_db.exists()
    
    def test_get_cache_key(self, rag_helper):
        """Test cache key generation."""
        key1 = rag_helper._get_cache_key("https://example.com", "query1")
        key2 = rag_helper._get_cache_key("https://example.com", "query1")
        key3 = rag_helper._get_cache_key("https://example.com", "query2")
        
        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32  # MD5 hash
    
    def test_cache_response_retrieval(self, rag_helper):
        """Test caching and retrieving responses."""
        url = "https://example.com"
        query = "test query"
        response = {"key": "value"}
        reasoning = "test reasoning"
        
        # Cache response
        rag_helper._cache_response(url, query, response, reasoning)
        
        # Retrieve cached response
        cached = rag_helper._get_cached_response(url, query)
        
        assert cached is not None
        assert cached["cached"] is True
        assert cached["response"] == response
    
    @pytest.mark.asyncio
    async def test_understand_page(self, rag_helper, mock_page_content, mock_page_text):
        """Test page understanding."""
        with patch.object(rag_helper.llm, "ask", new_callable=AsyncMock) as mock_ask:
            # Mock LLM response
            mock_ask.return_value = """{
                "main_content": "Test page with login form",
                "key_sections": ["Header", "Login Form", "Content"],
                "page_type": "login",
                "noise_elements": ["ads", "footer"],
                "interactive_elements": []
            }"""
            
            summary = await rag_helper.understand_page(
                "https://example.com",
                mock_page_content,
                "Test Page",
            )
            
            assert isinstance(summary, PageSummary)
            assert summary.url == "https://example.com"
            assert summary.title == "Test Page"
            assert summary.page_type == "login"
            assert len(summary.key_sections) > 0
    
    @pytest.mark.asyncio
    async def test_find_element_by_description(self, rag_helper, mock_page_content):
        """Test finding element by semantic description."""
        with patch.object(rag_helper.llm, "ask", new_callable=AsyncMock) as mock_ask:
            # Mock LLM response
            mock_ask.return_value = """{
                "xpath": "//button[@type='submit']",
                "element_type": "button",
                "text": "Login",
                "purpose": "Submit login form",
                "suggested_interaction": "click"
            }"""
            
            element = await rag_helper.find_element_by_description(
                mock_page_content,
                "the login button",
            )
            
            assert element is not None
            assert isinstance(element, SemanticElement)
            assert element.element_type == "button"
            assert element.text == "Login"
            assert "login" in element.purpose.lower()
    
    @pytest.mark.asyncio
    async def test_answer_question_about_page(
        self,
        rag_helper,
        mock_page_text,
    ):
        """Test answering questions about page."""
        with patch.object(rag_helper.llm, "ask", new_callable=AsyncMock) as mock_ask:
            # Mock LLM response
            mock_ask.return_value = """{
                "answer": "The page has a login form",
                "supporting_evidence": "The form contains email and password fields",
                "confidence": 0.95,
                "reasoning_trace": "I analyzed the page structure..."
            }"""
            
            understanding = await rag_helper.answer_question_about_page(
                "https://example.com",
                mock_page_text,
                "What is on this page?",
            )
            
            assert isinstance(understanding, ContentUnderstanding)
            assert "login" in understanding.answer.lower()
            assert understanding.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_suggest_interactions(self, rag_helper, mock_page_content):
        """Test suggesting interactions."""
        with patch.object(rag_helper.llm, "ask", new_callable=AsyncMock) as mock_ask:
            # Mock LLM response
            mock_ask.return_value = """[
                {
                    "xpath": "//input[@id='email']",
                    "element_type": "input",
                    "text": "Email",
                    "purpose": "Email input field",
                    "suggested_interaction": "fill"
                },
                {
                    "xpath": "//input[@id='password']",
                    "element_type": "input",
                    "text": "Password",
                    "purpose": "Password input field",
                    "suggested_interaction": "fill"
                }
            ]"""
            
            suggestions = await rag_helper.suggest_interactions(
                mock_page_content,
                "Login to the website",
            )
            
            assert len(suggestions) > 0
            assert all(isinstance(s, SemanticElement) for s in suggestions)
    
    def test_clear_cache(self, rag_helper):
        """Test cache clearing."""
        # Add some entries
        rag_helper._cache_response("url1", "query1", {"data": "test"}, "reasoning")
        
        # Clear cache
        rag_helper.clear_cache(older_than_seconds=0)
        
        # Verify cleared
        cached = rag_helper._get_cached_response("url1", "query1")
        # Should be None since we cleared everything
        assert cached is None or not cached.get("cached", False)
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, rag_helper, mock_page_text):
        """Test cache hit for questions."""
        url = "https://example.com"
        question = "What is this page about?"
        
        # First call - should use LLM
        with patch.object(rag_helper.llm, "ask", new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = """{
                "answer": "This is a test page",
                "supporting_evidence": "Based on the content",
                "confidence": 0.9,
                "reasoning_trace": "Analysis"
            }"""
            
            result1 = await rag_helper.answer_question_about_page(
                url,
                mock_page_text,
                question,
            )
        
        # Second call - should use cache
        result2 = await rag_helper.answer_question_about_page(
            url,
            mock_page_text,
            question,
        )
        
        # Both should have same answer
        assert result1.answer == result2.answer
