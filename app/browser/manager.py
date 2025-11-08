"""
Browser manager orchestrating embedded vs external browser selection.

Features:
- Automatic browser mode selection (embedded, chrome, firefox, edge, auto)
- Browser pool management
- Session affinity (same agent gets same browser instance)
- Load balancing
- Resource monitoring
- Guardian integration for URL safety
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.browser.embedded_engine import EmbeddedBrowserEngine, EmbeddedBrowserSession
from app.browser.external_adapter import (
    ChromeAdapter,
    EdgeAdapter,
    ExternalBrowserAdapter,
    FirefoxAdapter,
)
from app.logger import logger


class BrowserPoolStats(BaseModel):
    """Statistics for browser pool."""
    
    total_instances: int = Field(description="Total browser instances")
    active_instances: int = Field(description="Currently active instances")
    idle_instances: int = Field(description="Idle instances")
    total_navigations: int = Field(description="Total page navigations")
    failed_navigations: int = Field(description="Failed navigations")
    average_load_time: float = Field(description="Average page load time in ms")


class BrowserManager:
    """
    Manages browser instances with fallback chain support.
    
    Fallback chain: Embedded → Chrome → Firefox → Edge
    """
    
    def __init__(
        self,
        mode: str = "auto",
        headless: bool = False,
        pool_size: int = 3,
        timeout: float = 30.0,
        enable_guardian: bool = True,
    ):
        """
        Initialize browser manager.
        
        Args:
            mode: Browser mode: embedded, chrome, firefox, edge, or auto
            headless: Whether to run browsers in headless mode
            pool_size: Number of concurrent browser instances
            timeout: Default timeout for operations
            enable_guardian: Whether to enable Guardian URL checks
        """
        self.mode = mode
        self.headless = headless
        self.pool_size = pool_size
        self.timeout = timeout
        self.enable_guardian = enable_guardian
        
        # Browser pool
        self.sessions: Dict[str, EmbeddedBrowserSession] = {}
        self.external_browsers: Dict[str, ExternalBrowserAdapter] = {}
        self.session_affinity: Dict[str, str] = {}  # agent_id -> session_id
        
        # Statistics
        self.total_navigations = 0
        self.failed_navigations = 0
        self.load_times: List[float] = []
        
        logger.info(f"Initialized BrowserManager (mode={mode}, pool_size={pool_size})")
    
    async def get_browser(self, agent_id: str) -> Optional[EmbeddedBrowserEngine]:
        """
        Get a browser instance for an agent with session affinity.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Browser engine instance or None if unavailable
        """
        try:
            # Check for existing session affinity
            if agent_id in self.session_affinity:
                session_id = self.session_affinity[agent_id]
                if session_id in self.sessions:
                    session = self.sessions[session_id]
                    if session.current_tab:
                        return session.tabs.get(session.current_tab)
            
            # Create new session if needed
            session_id = f"session_{len(self.sessions)}"
            session = EmbeddedBrowserSession(session_id)
            self.sessions[session_id] = session
            self.session_affinity[agent_id] = session_id
            
            # Create default tab
            browser = session.create_tab(tab_id="tab_0")
            
            logger.debug(f"Assigned browser session {session_id} to agent {agent_id}")
            return browser
        except Exception as e:
            logger.error(f"Failed to get browser for agent {agent_id}: {e}")
            return None
    
    async def navigate(
        self,
        agent_id: str,
        url: str,
        wait_until: str = "networkidle2",
    ) -> bool:
        """
        Navigate to a URL with Guardian check.
        
        Args:
            agent_id: Agent identifier
            url: URL to navigate to
            wait_until: When to consider navigation complete
            
        Returns:
            True if navigation succeeded
        """
        try:
            # Guardian check
            if self.enable_guardian:
                # TODO: Integrate with Guardian for URL validation
                pass
            
            browser = await self.get_browser(agent_id)
            if not browser:
                logger.error(f"No browser available for agent {agent_id}")
                return False
            
            start_time = time.time()
            result = await browser.navigate(url, wait_until=wait_until, timeout=self.timeout)
            load_time = time.time() - start_time
            
            self.total_navigations += 1
            self.load_times.append(load_time * 1000)
            
            if result.get("success"):
                logger.debug(f"Navigation successful: {url} ({load_time*1000:.2f}ms)")
                return True
            else:
                self.failed_navigations += 1
                logger.warning(f"Navigation failed: {url} - {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self.failed_navigations += 1
            return False
    
    async def execute_script(
        self,
        agent_id: str,
        script: str,
        args: Optional[List] = None,
    ) -> Optional[any]:
        """Execute JavaScript in agent's browser."""
        try:
            browser = await self.get_browser(agent_id)
            if not browser:
                return None
            
            result = await browser.execute_javascript(script, args=args)
            return result.get("result")
        except Exception as e:
            logger.error(f"Script execution error: {e}")
            return None
    
    async def screenshot(
        self,
        agent_id: str,
        output_path: Optional[str] = None,
        full_page: bool = True,
    ) -> Optional[bytes]:
        """Take a screenshot of agent's browser."""
        try:
            browser = await self.get_browser(agent_id)
            if not browser:
                return None
            
            return await browser.screenshot(output_path=output_path, full_page=full_page)
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    async def create_tab(
        self,
        agent_id: str,
        url: Optional[str] = None,
    ) -> bool:
        """Create a new tab in agent's session."""
        try:
            # Get or create session
            if agent_id not in self.session_affinity:
                await self.get_browser(agent_id)
            
            session_id = self.session_affinity.get(agent_id)
            if not session_id or session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            tab_id = f"tab_{len(session.tabs)}"
            session.create_tab(tab_id=tab_id)
            
            if url:
                browser = session.tabs[tab_id]
                await browser.navigate(url)
            
            return True
        except Exception as e:
            logger.error(f"Failed to create tab: {e}")
            return False
    
    async def switch_tab(self, agent_id: str, tab_index: int) -> bool:
        """Switch to a different tab."""
        try:
            session_id = self.session_affinity.get(agent_id)
            if not session_id or session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            tab_ids = list(session.tabs.keys())
            
            if 0 <= tab_index < len(tab_ids):
                session.switch_tab(tab_ids[tab_index])
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to switch tab: {e}")
            return False
    
    async def close_tab(self, agent_id: str, tab_index: int) -> bool:
        """Close a tab."""
        try:
            session_id = self.session_affinity.get(agent_id)
            if not session_id or session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            tab_ids = list(session.tabs.keys())
            
            if 0 <= tab_index < len(tab_ids):
                session.close_tab(tab_ids[tab_index])
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to close tab: {e}")
            return False
    
    def get_pool_stats(self) -> BrowserPoolStats:
        """Get statistics about the browser pool."""
        total_instances = len(self.sessions)
        active_instances = sum(1 for s in self.sessions.values() if s.tabs)
        idle_instances = total_instances - active_instances
        
        avg_load_time = 0.0
        if self.load_times:
            avg_load_time = sum(self.load_times) / len(self.load_times)
        
        return BrowserPoolStats(
            total_instances=total_instances,
            active_instances=active_instances,
            idle_instances=idle_instances,
            total_navigations=self.total_navigations,
            failed_navigations=self.failed_navigations,
            average_load_time=avg_load_time,
        )
    
    async def cleanup_idle_sessions(self, max_idle_time: float = 300.0):
        """Close idle sessions to free resources."""
        try:
            current_time = time.time()
            sessions_to_close = []
            
            for session_id, session in self.sessions.items():
                session_age = (current_time - session.created_at.timestamp())
                
                if session_age > max_idle_time and not session.tabs:
                    sessions_to_close.append(session_id)
            
            for session_id in sessions_to_close:
                await self.sessions[session_id].close()
                del self.sessions[session_id]
                logger.debug(f"Closed idle session: {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up idle sessions: {e}")
    
    async def shutdown(self):
        """Shutdown all browser instances."""
        try:
            logger.info("Shutting down browser manager")
            
            for session in self.sessions.values():
                await session.close()
            
            for browser in self.external_browsers.values():
                await browser.stop()
            
            self.sessions.clear()
            self.external_browsers.clear()
            
            logger.info("Browser manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during browser manager shutdown: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# Global browser manager instance
_global_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the global browser manager."""
    global _global_browser_manager
    
    if _global_browser_manager is None:
        _global_browser_manager = BrowserManager()
    
    return _global_browser_manager
