import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import BaseModel, Field
from typing import List, Optional

from agentbay.browser.browser import (
    Browser,
    BrowserOption,
    BrowserViewport,
    BrowserScreen,
    BrowserFingerprint,
    BrowserProxy
)
from agentbay.browser.browser_agent import (
    BrowserAgent, 
    ActOptions, 
    ActResult, 
    ObserveOptions, 
    ObserveResult, 
    ExtractOptions, 
    BrowserError
)


class TestSchema(BaseModel):
    title: str = Field(..., description="Page title")
    content: Optional[str] = Field(None, description="Page content")


class TestBrowser(unittest.TestCase):
    def setUp(self):
        """Set up test browser."""
        self.mock_session = MagicMock()
        # Configure async mock for init_browser_async
        self.mock_session.get_client().init_browser_async = AsyncMock()
        self.mock_session.get_client().init_browser_async.return_value = MagicMock()
        self.mock_session.get_client().init_browser_async.return_value.to_map.return_value = {
            "body": {"Data": {"Port": 9333}}
        }
        self.browser = Browser(self.mock_session)
        self.browser.agent = MagicMock()

    def test_initialize(self):
        """Test initialize method."""
        self.assertTrue(self.browser.initialize(BrowserOption()))

    def test_initialize_async(self):
        """Test initialize_async method."""
        result = asyncio.run(self.browser.initialize_async(BrowserOption()))
        self.assertTrue(result)

    def test_is_initialized(self):
        """Test is_initialized method."""
        self.assertFalse(self.browser.is_initialized())

    def test_get_endpoint_url(self):
        """Test get_endpoint_url method."""
        self.browser.initialize(BrowserOption())
        self.assertIsNotNone(self.browser.get_endpoint_url())

    def test_get_option(self):
        """Test get_option method."""
        # Create a proxy for testing
        test_proxy = BrowserProxy(
            proxy_type="wuying",
            strategy="polling",
            pollsize=15
        )
        
        browser_option = BrowserOption(
            use_stealth=True,
            user_agent="User-Agent(By Mock)",
            viewport=BrowserViewport(width=1920, height=1080),
            screen=BrowserScreen(width=1920, height=1080),
            fingerprint=BrowserFingerprint(
                devices=["desktop"],
                operating_systems=["windows", "macos"],
                locales=["zh-CN"],
            ),
            solve_captchas=True,
            proxies=[test_proxy]
        )
        self.browser.initialize(browser_option)
        option = self.browser.get_option()
        self.assertIsNotNone(option)
        self.assertEqual(option.use_stealth, True)
        self.assertEqual(option.user_agent, "User-Agent(By Mock)")
        self.assertEqual(option.viewport.width, 1920)
        self.assertEqual(option.viewport.height, 1080)
        self.assertEqual(option.screen.width, 1920)
        self.assertEqual(option.screen.height, 1080)
        self.assertEqual(option.fingerprint.devices, ["desktop"])
        self.assertEqual(option.fingerprint.operating_systems, ["windows", "macos"])
        self.assertEqual(option.fingerprint.locales, ["zh-CN"])
        self.assertEqual(option.solve_captchas, True)
        
        # Test proxy options
        self.assertIsNotNone(option.proxies)
        self.assertEqual(len(option.proxies), 1)
        proxy = option.proxies[0]
        self.assertEqual(proxy.type, "wuying")
        self.assertEqual(proxy.strategy, "polling")
        self.assertEqual(proxy.pollsize, 15)

    def test_browser_proxy_options(self):
        """Test different types of browser proxy configurations."""
        
        # Test custom proxy
        custom_proxy = BrowserProxy(
            proxy_type="custom",
            server="http://proxy.example.com:8080",
            username="testuser",
            password="testpass"
        )
        
        custom_option = BrowserOption(proxies=[custom_proxy])
        self.browser.initialize(custom_option)
        option = self.browser.get_option()
        
        self.assertIsNotNone(option.proxies)
        self.assertEqual(len(option.proxies), 1)
        proxy = option.proxies[0]
        self.assertEqual(proxy.type, "custom")
        self.assertEqual(proxy.server, "http://proxy.example.com:8080")
        self.assertEqual(proxy.username, "testuser")
        self.assertEqual(proxy.password, "testpass")
        
        # Test wuying restricted proxy
        restricted_proxy = BrowserProxy(
            proxy_type="wuying",
            strategy="restricted"
        )
        
        restricted_option = BrowserOption(proxies=[restricted_proxy])
        # Create new browser instance for clean state
        restricted_browser = Browser(self.mock_session)
        restricted_browser.initialize(restricted_option)
        restricted_option_result = restricted_browser.get_option()
        
        self.assertIsNotNone(restricted_option_result.proxies)
        self.assertEqual(len(restricted_option_result.proxies), 1)
        restricted_proxy_result = restricted_option_result.proxies[0]
        self.assertEqual(restricted_proxy_result.type, "wuying")
        self.assertEqual(restricted_proxy_result.strategy, "restricted")
        
        # Test proxy serialization/deserialization
        proxy_map = custom_proxy.to_map()
        self.assertEqual(proxy_map["type"], "custom")
        self.assertEqual(proxy_map["server"], "http://proxy.example.com:8080")
        self.assertEqual(proxy_map["username"], "testuser")
        self.assertEqual(proxy_map["password"], "testpass")
        
        # Test from_map
        restored_proxy = BrowserProxy.from_map(proxy_map)
        self.assertEqual(restored_proxy.type, "custom")
        self.assertEqual(restored_proxy.server, "http://proxy.example.com:8080")
        self.assertEqual(restored_proxy.username, "testuser")
        self.assertEqual(restored_proxy.password, "testpass")

    def test_proxy_validation(self):
        """Test proxy validation logic."""
        
        # Test multiple proxies should fail
        proxy1 = BrowserProxy(proxy_type="custom", server="http://proxy1.com")
        proxy2 = BrowserProxy(proxy_type="custom", server="http://proxy2.com")
        
        with self.assertRaises(ValueError) as context:
            BrowserOption(proxies=[proxy1, proxy2])
        self.assertIn("proxies list length must be limited to 1", str(context.exception))
        
        # Test invalid proxy type should fail
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="invalid")
        self.assertIn("proxy_type must be custom or wuying", str(context.exception))
        
        # Test custom proxy without server should fail
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="custom")
        self.assertIn("server is required for custom proxy type", str(context.exception))
        
        # Test wuying proxy without strategy should fail
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="wuying")
        self.assertIn("strategy is required for wuying proxy type", str(context.exception))
        
        # Test wuying proxy with invalid strategy should fail
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="wuying", strategy="invalid")
        self.assertIn("strategy must be restricted or polling for wuying proxy type", str(context.exception))
        
        # Test polling strategy with invalid pollsize should fail
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="wuying", strategy="polling", pollsize=0)
        self.assertIn("pollsize must be greater than 0 for polling strategy", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            BrowserProxy(proxy_type="wuying", strategy="polling", pollsize=-1)
        self.assertIn("pollsize must be greater than 0 for polling strategy", str(context.exception))

    def test_act(self):
        """Test act method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.act(ActOptions(action="Click search button"), page)

    def test_observe(self):
        """Test observe method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.observe(ObserveOptions(instruction="Find the search button"), page)

    def test_extract(self):
        """Test extract method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.extract(ExtractOptions(instruction="Extract the title", schema=TestSchema), page)

    def test_act_async(self):
        """Test act_async method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.act_async(ActOptions(action="Click search button"), page)

    def test_observe_async(self):
        """Test observe_async method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.observe_async(ObserveOptions(instruction="Find the search button"), page)

    def test_extract_async(self):
        """Test extract_async method."""
        page = MagicMock()
        self.browser.initialize(BrowserOption())
        self.browser.agent.extract_async(ExtractOptions(instruction="Extract the title", schema=TestSchema), page)

if __name__ == '__main__':
    unittest.main()
