"""Tests for embedded browser engine."""

import asyncio
import pytest
from pathlib import Path

from app.browser.embedded_engine import (
    EmbeddedBrowserEngine,
    EmbeddedBrowserSession,
    PerformanceMetrics,
)


@pytest.fixture
def browser_engine():
    """Create a browser engine instance for testing."""
    return EmbeddedBrowserEngine(
        headless=True,
        cache_dir="./cache/test_browser",
    )


@pytest.fixture
def browser_session():
    """Create a browser session for testing."""
    session = EmbeddedBrowserSession("test_session")
    yield session
    # Close synchronously for fixtures
    import asyncio
    try:
        asyncio.run(session.close())
    except:
        pass


class TestEmbeddedBrowserEngine:
    """Tests for embedded browser engine."""
    
    def test_initialization(self, browser_engine):
        """Test browser engine initialization."""
        assert browser_engine is not None
        assert browser_engine.headless is True
        assert browser_engine.cache_dir.exists()
    
    def test_cache_initialization(self, browser_engine):
        """Test cache database initialization."""
        cache_db = browser_engine.cache_dir / "browser_content_cache.db"
        assert cache_db.exists()
    
    @pytest.mark.asyncio
    async def test_navigate(self, browser_engine):
        """Test page navigation."""
        result = await browser_engine.navigate(
            "https://example.com",
            timeout=5.0,
        )
        
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert browser_engine.current_url == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_execute_javascript(self, browser_engine):
        """Test JavaScript execution."""
        result = await browser_engine.execute_javascript(
            "return 1 + 1"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_page_content(self, browser_engine):
        """Test getting page HTML content."""
        await browser_engine.navigate("https://example.com")
        content = await browser_engine.get_page_content()
        
        assert isinstance(content, str)
    
    @pytest.mark.asyncio
    async def test_get_page_text(self, browser_engine):
        """Test extracting page text."""
        await browser_engine.navigate("https://example.com")
        text = await browser_engine.get_page_text()
        
        assert isinstance(text, str)
    
    @pytest.mark.asyncio
    async def test_screenshot(self, browser_engine):
        """Test screenshot capture."""
        screenshot = await browser_engine.screenshot()
        
        assert screenshot is not None
        assert isinstance(screenshot, bytes)
        assert screenshot.startswith(b"\x89PNG")
    
    @pytest.mark.asyncio
    async def test_screenshot_with_path(self, browser_engine, tmp_path):
        """Test screenshot with file saving."""
        output_path = tmp_path / "screenshot.png"
        screenshot = await browser_engine.screenshot(output_path=str(output_path))
        
        assert screenshot is not None
        assert output_path.exists()
    
    @pytest.mark.asyncio
    async def test_get_cookies(self, browser_engine):
        """Test getting cookies."""
        cookies = await browser_engine.get_cookies()
        
        assert isinstance(cookies, dict)
    
    @pytest.mark.asyncio
    async def test_set_cookies(self, browser_engine):
        """Test setting cookies."""
        test_cookies = {"session": "abc123", "user": "testuser"}
        success = await browser_engine.set_cookies(test_cookies)
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_click_element(self, browser_engine):
        """Test element clicking."""
        success = await browser_engine.click_element(".some-button")
        
        assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_fill_form(self, browser_engine):
        """Test form filling."""
        success = await browser_engine.fill_form("#email", "test@example.com")
        
        assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_scroll(self, browser_engine):
        """Test page scrolling."""
        success = await browser_engine.scroll("down", 300)
        assert success is True
        
        success = await browser_engine.scroll("up", 300)
        assert success is True
        
        success = await browser_engine.scroll("top")
        assert success is True
        
        success = await browser_engine.scroll("bottom")
        assert success is True
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, browser_engine):
        """Test waiting for element."""
        # Should timeout since we're not on a real page
        result = await browser_engine.wait_for_selector(".nonexistent", timeout=1.0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_dom_snapshot(self, browser_engine):
        """Test getting DOM snapshot."""
        dom_tree = await browser_engine.get_dom_snapshot()
        
        assert isinstance(dom_tree, dict)
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, browser_engine):
        """Test getting performance metrics."""
        await browser_engine.navigate("https://example.com")
        metrics = await browser_engine.get_performance_metrics()
        
        assert metrics is not None
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.load_time > 0


class TestEmbeddedBrowserSession:
    """Tests for browser session management."""
    
    @pytest.mark.asyncio
    async def test_session_creation(self, browser_session):
        """Test session creation."""
        assert browser_session is not None
        assert browser_session.session_id == "test_session"
        assert len(browser_session.tabs) == 0
    
    @pytest.mark.asyncio
    async def test_create_tab(self, browser_session):
        """Test creating a tab."""
        engine = browser_session.create_tab()
        
        assert engine is not None
        assert len(browser_session.tabs) == 1
        assert browser_session.current_tab is not None
    
    @pytest.mark.asyncio
    async def test_create_multiple_tabs(self, browser_session):
        """Test creating multiple tabs."""
        engine1 = browser_session.create_tab(tab_id="tab_1")
        engine2 = browser_session.create_tab(tab_id="tab_2")
        
        assert len(browser_session.tabs) == 2
        assert "tab_1" in browser_session.tabs
        assert "tab_2" in browser_session.tabs
    
    @pytest.mark.asyncio
    async def test_switch_tab(self, browser_session):
        """Test switching tabs."""
        browser_session.create_tab(tab_id="tab_1")
        browser_session.create_tab(tab_id="tab_2")
        
        engine = browser_session.switch_tab("tab_2")
        assert engine is not None
        assert browser_session.current_tab == "tab_2"
    
    @pytest.mark.asyncio
    async def test_switch_tab_nonexistent(self, browser_session):
        """Test switching to nonexistent tab."""
        browser_session.create_tab(tab_id="tab_1")
        
        engine = browser_session.switch_tab("nonexistent")
        assert engine is None
    
    @pytest.mark.asyncio
    async def test_close_tab(self, browser_session):
        """Test closing a tab."""
        browser_session.create_tab(tab_id="tab_1")
        browser_session.create_tab(tab_id="tab_2")
        
        success = browser_session.close_tab("tab_1")
        assert success is True
        assert len(browser_session.tabs) == 1
        assert "tab_1" not in browser_session.tabs
    
    @pytest.mark.asyncio
    async def test_close_nonexistent_tab(self, browser_session):
        """Test closing nonexistent tab."""
        success = browser_session.close_tab("nonexistent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, browser_session):
        """Test session cleanup."""
        browser_session.create_tab()
        assert len(browser_session.tabs) == 1
        
        await browser_session.close()
        assert len(browser_session.tabs) == 0
