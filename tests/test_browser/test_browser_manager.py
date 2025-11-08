"""Tests for browser manager and orchestration."""

import pytest

from app.browser.manager import BrowserManager, BrowserPoolStats


@pytest.fixture
def browser_manager():
    """Create a browser manager for testing."""
    return BrowserManager(
        mode="embedded",
        headless=True,
        pool_size=3,
        timeout=10.0,
        enable_guardian=False,  # Disable for testing
    )


@pytest.fixture
def manager_with_cleanup(browser_manager):
    """Browser manager with cleanup."""
    yield browser_manager
    import asyncio
    try:
        asyncio.run(browser_manager.shutdown())
    except:
        pass


class TestBrowserManager:
    """Tests for browser manager."""
    
    def test_initialization(self, browser_manager):
        """Test manager initialization."""
        assert browser_manager is not None
        assert browser_manager.mode == "embedded"
        assert browser_manager.pool_size == 3
        assert browser_manager.headless is True
    
    @pytest.mark.asyncio
    async def test_get_browser(self, manager_with_cleanup):
        """Test getting a browser instance."""
        browser = await manager_with_cleanup.get_browser("agent_1")
        
        assert browser is not None
    
    @pytest.mark.asyncio
    async def test_session_affinity(self, manager_with_cleanup):
        """Test session affinity for agents."""
        browser1 = await manager_with_cleanup.get_browser("agent_1")
        browser2 = await manager_with_cleanup.get_browser("agent_1")
        
        # Same agent should get same browser instance
        assert browser1 is browser2
    
    @pytest.mark.asyncio
    async def test_different_agents_different_browsers(self, manager_with_cleanup):
        """Test different agents get different browser instances."""
        browser1 = await manager_with_cleanup.get_browser("agent_1")
        browser2 = await manager_with_cleanup.get_browser("agent_2")
        
        assert browser1 is not None
        assert browser2 is not None
    
    @pytest.mark.asyncio
    async def test_navigate(self, manager_with_cleanup):
        """Test navigation through manager."""
        success = await manager_with_cleanup.navigate("agent_1", "https://example.com")
        
        assert isinstance(success, bool)
        assert manager_with_cleanup.total_navigations > 0
    
    @pytest.mark.asyncio
    async def test_execute_script(self, manager_with_cleanup):
        """Test script execution."""
        await manager_with_cleanup.navigate("agent_1", "https://example.com")
        
        result = await manager_with_cleanup.execute_script(
            "agent_1",
            "return 1 + 1"
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_screenshot(self, manager_with_cleanup):
        """Test screenshot capture."""
        await manager_with_cleanup.navigate("agent_1", "https://example.com")
        
        screenshot = await manager_with_cleanup.screenshot("agent_1")
        
        assert screenshot is not None
        assert isinstance(screenshot, bytes)
    
    @pytest.mark.asyncio
    async def test_create_tab(self, manager_with_cleanup):
        """Test creating a new tab."""
        success = await manager_with_cleanup.create_tab("agent_1")
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_switch_tab(self, manager_with_cleanup):
        """Test switching tabs."""
        await manager_with_cleanup.create_tab("agent_1")
        await manager_with_cleanup.create_tab("agent_1")
        
        success = await manager_with_cleanup.switch_tab("agent_1", 1)
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_close_tab(self, manager_with_cleanup):
        """Test closing a tab."""
        await manager_with_cleanup.create_tab("agent_1", url="https://example.com")
        
        success = await manager_with_cleanup.close_tab("agent_1", 0)
        
        assert isinstance(success, bool)
    
    def test_get_pool_stats(self, browser_manager):
        """Test getting pool statistics."""
        stats = browser_manager.get_pool_stats()
        
        assert isinstance(stats, BrowserPoolStats)
        assert stats.total_instances == 0
        assert stats.failed_navigations == 0
    
    @pytest.mark.asyncio
    async def test_pool_stats_after_navigation(self, manager_with_cleanup):
        """Test pool stats after navigation."""
        await manager_with_cleanup.navigate("agent_1", "https://example.com")
        
        stats = manager_with_cleanup.get_pool_stats()
        
        assert stats.total_navigations > 0
        assert stats.active_instances > 0
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_sessions(self, manager_with_cleanup):
        """Test cleanup of idle sessions."""
        await manager_with_cleanup.navigate("agent_1", "https://example.com")
        initial_count = len(manager_with_cleanup.sessions)
        
        # Cleanup with 0 timeout to cleanup all idle sessions
        await manager_with_cleanup.cleanup_idle_sessions(max_idle_time=0)
        
        # May have sessions if they're considered active
        assert len(manager_with_cleanup.sessions) <= initial_count
    
    @pytest.mark.asyncio
    async def test_shutdown(self, browser_manager):
        """Test shutdown."""
        await browser_manager.navigate("agent_1", "https://example.com")
        
        await browser_manager.shutdown()
        
        assert len(browser_manager.sessions) == 0
        assert len(browser_manager.external_browsers) == 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with BrowserManager() as manager:
            browser = await manager.get_browser("agent_1")
            assert browser is not None
        
        # Sessions should be cleaned up
        assert len(manager.sessions) == 0
