#!/usr/bin/env python3
"""
Integration test for browser context functionality.
This test verifies that browser context (cookies, localStorage, etc.) can be persisted
across sessions using the same ContextId.
"""

import asyncio
import os
import time
import unittest
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.browser.browser import BrowserOption
from playwright.async_api import async_playwright


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")
    return api_key


class TestBrowserContextIntegration(unittest.TestCase):
    """Integration tests for browser context persistence functionality."""

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.first_session_cookies: list = []
        self.first_session_cookie_dict: dict = {}

    @classmethod
    def setUpClass(cls):
        # Skip if no API key is available or in CI environment
        api_key = os.environ.get("AGENTBAY_API_KEY")
        if not api_key or os.environ.get("CI"):
            raise unittest.SkipTest(
                "Skipping integration test: No API key available or running in CI"
            )

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(api_key)

        # Create a unique context name for this test
        cls.context_name = f"test-browser-context-{int(time.time())}"

        # Create a context
        context_result = cls.agent_bay.context.get(cls.context_name, True)
        if not context_result.success or not context_result.context:
            raise unittest.SkipTest("Failed to create context")

        cls.context = context_result.context
        print(f"Created context: {cls.context.name} (ID: {cls.context.id})")

    @classmethod
    def tearDownClass(cls):
        # Clean up context
        if hasattr(cls, "context"):
            try:
                cls.agent_bay.context.delete(cls.context)
                print(f"Context deleted: {cls.context.id}")
            except Exception as e:
                print(f"Warning: Failed to delete context: {e}")

    def test_browser_context_cookie_persistence(self):
        """Test that manually set cookies persist across sessions with the same browser context."""
        # Test data
        test_url = "https://www.aliyun.com"
        test_domain = "aliyun.com"

        # Helper function to add one hour to current time
        def add_hour():
            return int(time.time()) + 3600  # 1 hour from now

        test_cookies = [
            {
                "name": "myCookie",
                "value": "cookieValue",
                "domain": test_domain,
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "expires": add_hour()
            },
            {
                "name": "test_cookie_2",
                "value": "test_value_2",
                "domain": test_domain,
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "expires": add_hour()
            }
        ]

        # Step 1 & 2: Create ContextId and create session with BrowserContext
        print(f"Step 1-2: Creating session with browser context ID: {self.context.id}")
        browser_context = BrowserContext(self.context.id, auto_upload=True)
        params = CreateSessionParams(
            image_id="browser_latest",
            browser_context=browser_context
        )

        session_result = self.agent_bay.create(params)
        self.assertTrue(session_result.success, "Failed to create first session")
        self.assertIsNotNone(session_result.session, "Session should not be None")

        session1 = session_result.session
        assert session1 is not None  # Type narrowing for linter
        print(f"First session created with ID: {session1.session_id}")

        # Step 3: Get browser object through initialize_async and get_endpoint_url
        async def first_session_operations():
            print("Step 3: Initializing browser and getting browser object...")

            # Initialize browser
            init_success = await session1.browser.initialize_async(BrowserOption())
            self.assertTrue(init_success, "Failed to initialize browser")
            print("Browser initialized successfully")

            # Get endpoint URL
            endpoint_url = session1.browser.get_endpoint_url()
            self.assertIsNotNone(endpoint_url, "Endpoint URL should not be None")
            print(f"Browser endpoint URL: {endpoint_url}")

            # Step 4: Connect with playwright, open aliyun.com and then add test cookies
            print("Step 4: Opening aliyun.com and then adding test cookies...")
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                self.assertIsNotNone(browser, "Failed to connect to browser")
                cdp_session = await browser.new_browser_cdp_session()

                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()

                # Navigate to test URL first
                await page.goto(test_url)
                print(f"Navigated to {test_url}")

                # Wait a bit for the page to load
                await page.wait_for_timeout(3000)

                # Add test cookies after navigating to the page
                await context.add_cookies(test_cookies)  # type: ignore
                print(f"Added {len(test_cookies)} test cookies after navigating to {test_url}")

                # Read cookies to verify they were set correctly
                cookies = await context.cookies()
                cookie_dict = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies}

                print(f"Cookies found in first session: {list(cookie_dict.keys())}")
                print(f"Total cookies count: {len(cookies)}")

                # Store cookies for comparison in second session
                self.first_session_cookies = cookies
                self.first_session_cookie_dict = cookie_dict

                await cdp_session.send('Browser.close')
                print("First session browser operations completed")

                # Wait for browser to save cookies to file
                print("Waiting for browser to save cookies to file...")
                await asyncio.sleep(2)
                print("Wait completed")

        # Run first session operations
        asyncio.run(first_session_operations())

        # Step 5: Release session with syncContext=True
        print("Step 5: Releasing first session with syncContext=True...")
        delete_result = self.agent_bay.delete(session1, sync_context=True)
        self.assertTrue(delete_result.success, "Failed to delete first session")
        print(f"First session deleted successfully (RequestID: {delete_result.request_id})")

        # Wait for context sync to complete
        time.sleep(3)

        # Step 6: Create second session with same ContextId
        print(f"Step 6: Creating second session with same context ID: {self.context.id}")
        session_result2 = self.agent_bay.create(params)
        self.assertTrue(session_result2.success, "Failed to create second session")
        self.assertIsNotNone(session_result2.session, "Second session should not be None")

        session2 = session_result2.session
        assert session2 is not None  # Type narrowing for linter
        print(f"Second session created with ID: {session2.session_id}")

        # Step 7: Get browser object and check if test cookies exist without opening any page
        async def second_session_operations():
            print("Step 7: Getting browser object and checking test cookie persistence without opening any page...")

            # Initialize browser
            init_success = await session2.browser.initialize_async(BrowserOption())
            self.assertTrue(init_success, "Failed to initialize browser in second session")
            print("Second session browser initialized successfully")

            # Get endpoint URL
            endpoint_url = session2.browser.get_endpoint_url()
            self.assertIsNotNone(endpoint_url, "Endpoint URL should not be None")
            print(f"Second session browser endpoint URL: {endpoint_url}")



            # Connect with playwright and read cookies directly from context without opening any page
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                self.assertIsNotNone(browser, "Failed to connect to browser in second session")

                context = browser.contexts[0] if browser.contexts else await browser.new_context()

                # Read cookies directly from context without opening any page
                cookies = await context.cookies()
                cookie_dict = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies}

                print(f"Cookies found in second session (without opening page): {list(cookie_dict.keys())}")
                print(f"Total cookies count in second session: {len(cookies)}")

                # Check if our test cookies exist in the second session
                expected_cookie_names = {"myCookie", "test_cookie_2"}
                found_cookie_names = set(cookie_dict.keys())

                print(f"Expected test cookies: {expected_cookie_names}")
                print(f"Found cookies: {found_cookie_names}")

                # Check if all expected test cookies are present
                missing_cookies = expected_cookie_names - found_cookie_names
                if missing_cookies:
                    self.fail(f"Missing expected test cookies in second session: {missing_cookies}")

                # Check if test cookie values match what we set
                for cookie_name in expected_cookie_names:
                    if cookie_name in cookie_dict:
                        expected_value = next(cookie["value"] for cookie in test_cookies if cookie["name"] == cookie_name)
                        actual_value = cookie_dict[cookie_name]
                        self.assertEqual(expected_value, actual_value,
                                       f"Test cookie '{cookie_name}' value should match. Expected: {expected_value}, Actual: {actual_value}")
                        print(f"✓ Test cookie '{cookie_name}' value matches: {actual_value}")

                print(f"SUCCESS: All {len(expected_cookie_names)} test cookies persisted correctly!")
                print(f"Test cookies found: {list(expected_cookie_names)}")


                await context.close()
                print("Second session browser operations completed")

        # Run second session operations
        asyncio.run(second_session_operations())

        print("Browser context manual cookie persistence test completed successfully!")


if __name__ == "__main__":
    unittest.main()
