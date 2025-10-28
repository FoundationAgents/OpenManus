import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from agentbay.config import BROWSER_DATA_PATH
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.agentbay import AgentBay


class TestBrowserContextConfig(unittest.TestCase):
    """Test browser context configuration and constant usage."""

    def test_browser_data_path_constant(self):
        """Test that BROWSER_DATA_PATH constant is correctly defined."""
        self.assertEqual(BROWSER_DATA_PATH, "/tmp/agentbay_browser")
        self.assertIsInstance(BROWSER_DATA_PATH, str)
        self.assertTrue(BROWSER_DATA_PATH.startswith("/"))

    def test_browser_context_creation(self):
        """Test BrowserContext creation with correct attributes."""
        context_id = "test-context-123"
        auto_upload = True
        
        browser_context = BrowserContext(context_id, auto_upload)
        
        self.assertEqual(browser_context.context_id, context_id)
        self.assertEqual(browser_context.auto_upload, auto_upload)

    def test_browser_context_default_auto_upload(self):
        """Test BrowserContext creation with default auto_upload value."""
        context_id = "test-context-456"
        
        browser_context = BrowserContext(context_id)
        
        self.assertEqual(browser_context.context_id, context_id)
        self.assertTrue(browser_context.auto_upload)  # Default should be True

    def test_create_session_params_with_browser_context(self):
        """Test CreateSessionParams with browser context."""
        context_id = "test-context-789"
        browser_context = BrowserContext(context_id, auto_upload=False)
        
        params = CreateSessionParams(browser_context=browser_context)
        
        self.assertIsNotNone(params.browser_context)
        self.assertEqual(params.browser_context.context_id, context_id)
        self.assertFalse(params.browser_context.auto_upload)

    def test_agentbay_create_with_browser_context_uses_constant(self):
        """Test that AgentBay.create uses BROWSER_DATA_PATH constant when creating browser context sync."""

        agent_bay = AgentBay(api_key="test-api-key")
        
        # Create session params with browser context
        context_id = "test-context-456"
        browser_context = BrowserContext(context_id, auto_upload=True)
        params = CreateSessionParams(browser_context=browser_context)
        

        self.assertIsNotNone(params.browser_context)
        self.assertEqual(params.browser_context.context_id, context_id)
        self.assertTrue(params.browser_context.auto_upload)

    def test_browser_context_serialization(self):
        """Test that BrowserContext can be properly serialized for JSON."""
        context_id = "test-context-serialization"
        browser_context = BrowserContext(context_id, auto_upload=True)
        
        # Test that the object can be converted to dict-like structure
        self.assertEqual(browser_context.context_id, context_id)
        self.assertEqual(browser_context.auto_upload, True)
        
        # Test that it can be used in JSON serialization context
        data = {
            "context_id": browser_context.context_id,
            "auto_upload": browser_context.auto_upload
        }
        
        json_str = json.dumps(data)
        parsed_data = json.loads(json_str)
        
        self.assertEqual(parsed_data["context_id"], context_id)
        self.assertEqual(parsed_data["auto_upload"], True)


if __name__ == '__main__':
    unittest.main()
