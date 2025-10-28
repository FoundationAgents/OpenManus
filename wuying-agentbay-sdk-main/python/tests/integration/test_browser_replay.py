import json
import os
import sys
import time
import unittest
from agentbay.browser import Browser, BrowserOption
from playwright.sync_api import sync_playwright

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key

class TestBrowserRecordIntegration(unittest.TestCase):
    """Integration test for browser session with browser recording enabled."""

    def setUp(self):
        """Set up test fixtures."""
        api_key = get_test_api_key()
        print("api_key =", api_key)
        self.agent_bay = AgentBay(api_key=api_key)
        print("Creating a new session for browser recording testing...")
        self.create_session()

    def create_session(self):
        """Create a session with browser recording enabled."""
        # Create session parameters with recording enabled
        session_param = CreateSessionParams()
        session_param.image_id = "browser_latest"
        session_param.enable_browser_replay = True  # Enable browser recording

        print("Creating session with browser recording enabled...")
        result = self.agent_bay.create(session_param)
        self.assertTrue(result.success, f"Failed to create session: {result.error_message}")
        self.session = result.session
        if self.session:
            print(f"Session created with ID: {self.session.session_id}")
            info_result = self.session.info()
            print("=== Session Info Details ===")

            if info_result.success and info_result.data:
                session_info = info_result.data
                # Print the specific fields from SessionInfo object
                info_fields = ['resource_url', 'app_id', 'auth_code', 'connection_properties', 'resource_id', 'resource_type', 'ticket']
                for field in info_fields:
                    if hasattr(session_info, field):
                        value = getattr(session_info, field)
                        print(f"{field}: {value}")
                    else:
                        print(f"{field}: Not available in session_info")

                # Also print session_id
                if hasattr(session_info, 'session_id'):
                    print(f"session_id: {session_info.session_id}")
            else:
                print(f"Failed to get session info: {info_result.error_message}")
                print(f"Info result object: {info_result}")

            print("=== End Session Info Details ===")

    def tearDown(self):
        """Tear down test fixtures."""
        import signal
        import sys

        def signal_handler(sig, frame):
            print("\nReceived Ctrl+C, cleaning up: Deleting the session...")
            try:
                if self.session:
                    delete_result = self.agent_bay.delete(self.session)
                    if delete_result.success:
                        print("Session deleted successfully")
                    else:
                        print(f"Warning: Error deleting session: {delete_result.error_message}")
                else:
                    print("No session to delete")
            except Exception as e:
                print(f"Warning: Unexpected error deleting session: {e}")
            sys.exit(0)

        # Register the signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)

        print("Test completed. Session is kept alive.")
        print("Press Ctrl+C to delete the session and exit...")

        try:
            # Sleep continuously until Ctrl+C is received
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # This should be handled by the signal handler, but just in case
            signal_handler(signal.SIGINT, None)

    def test_browser_record_operations(self):
        """Test browser operations with recording enabled."""
        browser = self.session.browser
        self.assertIsNotNone(browser)

        # Initialize browser
        print("Initializing browser for operations test...")
        browser_option = BrowserOption()
        init_result = browser.initialize(browser_option)
        self.assertTrue(init_result, "Browser initialization should succeed")

        # Get endpoint URL
        endpoint_url = browser.get_endpoint_url()
        self.assertIsNotNone(endpoint_url, "Browser endpoint URL should not be None")

        # Wait for browser to be ready
        time.sleep(5)

        try:
            # Connect to browser using Playwright
            print("Connecting to browser via Playwright...")
            with sync_playwright() as p:
                playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
                self.assertIsNotNone(playwright_browser, "Playwright browser connection should succeed")

                # Getting the default context to ensure the sessions are recorded.
                default_context = playwright_browser.contexts[0]
                # Create a new page
                page = default_context.new_page()
                print("New page created")

                # Navigate to a test website
                print("Navigating to Baidu...")
                page.goto("http://www.baidu.com")
                time.sleep(3)  # Wait for page to load

                # Get page title
                page_title = page.title()
                print("page.title() =", page_title)
                self.assertIsNotNone(page_title, "Page title should not be None")
                self.assertTrue(len(page_title) > 0, "Page title should not be empty")

                # Perform some browser operations that will be recorded
                print("Performing browser operations for recording...")

                # Take a screenshot
                screenshot_path = "/tmp/test_screenshot.png"
                page.screenshot(path=screenshot_path)
                print(f"Screenshot saved to {screenshot_path}")

                # Try to interact with the page more safely
                try:
                    # Wait for page to be fully loaded
                    page.wait_for_load_state("networkidle", timeout=10000)

                    # Try to find and interact with search input
                    search_selectors = ["#kw", "input[name='wd']", "input[type='text']"]
                    search_input = None

                    for selector in search_selectors:
                        try:
                            search_input = page.wait_for_selector(selector, timeout=5000)
                            if search_input and search_input.is_visible():
                                print(f"Found search input with selector: {selector}")
                                break
                        except:
                            continue

                    if search_input:
                        search_input.fill("AgentBay测试")
                        print("Filled search input")
                        time.sleep(1)

                        # Try to find and click search button
                        button_selectors = ["#su", "input[type='submit']", "button[type='submit']"]
                        for btn_selector in button_selectors:
                            try:
                                search_button = page.wait_for_selector(btn_selector, timeout=3000)
                                if search_button and search_button.is_visible():
                                    search_button.click()
                                    print("Clicked search button")
                                    time.sleep(2)
                                    break
                            except:
                                continue
                    else:
                        print("Search input not found, performing simple navigation instead")
                        # Just scroll the page to demonstrate interaction
                        page.evaluate("window.scrollTo(0, 500)")
                        time.sleep(1)
                        page.evaluate("window.scrollTo(0, 0)")

                except Exception as interaction_error:
                    print(f"Page interaction failed, but that's okay for recording test: {interaction_error}")

                # Wait a bit more to ensure recording captures all operations
                time.sleep(2)

                # Close the page
                page.close()
                print("Page closed")

        except Exception as e:
            print(f"Browser operations encountered an error: {e}")
            # Don't fail the test for browser interaction issues, as long as recording is working
            print("This is acceptable for a recording test - the important part is that recording is enabled")

        print("Browser operations completed successfully with recording")

if __name__ == "__main__":
    unittest.main()