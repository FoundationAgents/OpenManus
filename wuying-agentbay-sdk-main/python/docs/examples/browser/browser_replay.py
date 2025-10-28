#!/usr/bin/env python3
"""
Browser Replay Example

This example demonstrates how to:
1. Create a browser session with browser replay enabled
2. Perform browser operations that will be captured
3. Access the replay video files
4. Clean up the session

The browser replay will capture all browser interactions and save them for internal processing
"""

import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser import BrowserOption
from playwright.sync_api import sync_playwright


def main():
    # Initialize AgentBay client
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Please set AGENTBAY_API_KEY environment variable")
        return

    agent_bay = AgentBay(api_key=api_key)

    try:
        # Create a browser session with browser replay enabled
        print("🎬 Creating browser session with browser replay...")
        session_params = CreateSessionParams(
            image_id="browser_latest",
            enable_browser_replay=True,  # Enable browser replay
            labels={
                "example": "browser_replay",
                "session_type": "browser",
                "replay": "enabled"
            }
        )

        result = agent_bay.create(session_params)
        if not result.success:
            print(f"❌ Failed to create session: {result.error_message}")
            return

        session = result.session
        print(f"✅ Session created: {session.session_id}")
        print(f"📹 Browser replay enabled: {session.enableBrowserReplay}")

        # Initialize browser
        print("\n🌐 Initializing browser...")
        browser = session.browser
        browser_option = BrowserOption()

        if not browser.initialize(browser_option):
            print("❌ Failed to initialize browser")
            return

        endpoint_url = browser.get_endpoint_url()
        print(f"🔗 Browser endpoint: {endpoint_url}")

        # Wait for browser to be ready
        time.sleep(5)

        # Perform browser operations that will be captured
        print("\n🎥 Starting browser operations for replay...")

        with sync_playwright() as p:
            playwright_browser = p.chromium.connect_over_cdp(endpoint_url)

            # Test multiple websites and operations
            test_scenarios = [
                {
                    "name": "Baidu Search",
                    "url": "https://www.baidu.com",
                    "actions": lambda page: perform_baidu_search(page)
                },
                {
                    "name": "Google Search",
                    "url": "https://www.google.com",
                    "actions": lambda page: perform_google_search(page)
                },
                {
                    "name": "AgentBay Documentation",
                    "url": "https://help.aliyun.com/zh/agentbay/",
                    "actions": lambda page: browse_documentation(page)
                }
            ]

            for i, scenario in enumerate(test_scenarios, 1):
                print(f"\n📋 Scenario {i}: {scenario['name']}")

                default_context = playwright_browser.contexts[0]
                # Create a new page
                page = default_context.new_page()

                try:
                    # Navigate to the website
                    print(f"🔄 Navigating to {scenario['url']}")
                    page.goto(scenario['url'], timeout=30000, wait_until="domcontentloaded")
                    time.sleep(2)

                    # Get page title
                    title = page.title()
                    print(f"📄 Page title: {title}")

                    # Take a screenshot
                    screenshot_path = f"/tmp/replay_screenshot_{i}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot saved: {screenshot_path}")

                    # Perform specific actions for this scenario
                    scenario['actions'](page)

                    # Wait to ensure the actions are captured
                    time.sleep(3)

                except Exception as e:
                    print(f"⚠️  Warning: Failed to complete scenario {scenario['name']}: {e}")

                finally:
                    page.close()
                    time.sleep(1)

            # Close the browser
            playwright_browser.close()

        print(f"\n🎬 Browser replay completed!")
        print("📁 Replay files are automatically generated and stored by the system")
        print("🎥 These files are used for internal processing and analysis")

    except Exception as e:
        print(f"❌ Error during browser replay demo: {e}")

    finally:
        # Clean up: delete the session
        print(f"\n🧹 Cleaning up session {session.session_id}...")
        try:
            delete_result = agent_bay.delete(session)
            if delete_result.success:
                print("✅ Session deleted successfully")
            else:
                print(f"⚠️  Warning: Failed to delete session: {delete_result.error_message}")
        except Exception as e:
            print(f"⚠️  Warning: Error during cleanup: {e}")


def perform_baidu_search(page):
    """Perform a search on Baidu"""
    try:
        # Find search input and enter search term
        search_input = page.query_selector("#kw")
        if search_input:
            search_term = "AgentBay cloud automation"
            search_input.fill(search_term)
            print(f"🔍 Searching for: {search_term}")
            time.sleep(1)

            # Click search button
            search_button = page.query_selector("#su")
            if search_button:
                search_button.click()
                print("🔄 Search submitted")
                time.sleep(3)  # Wait for results
    except Exception as e:
        print(f"⚠️  Search failed: {e}")


def perform_google_search(page):
    """Perform a search on Google"""
    try:
        # Find search input and enter search term
        search_input = page.query_selector("input[name='q']")
        if search_input:
            search_term = "AgentBay browser recording"
            search_input.fill(search_term)
            print(f"🔍 Searching for: {search_term}")
            time.sleep(1)

            # Press Enter to search
            search_input.press("Enter")
            print("🔄 Search submitted")
            time.sleep(3)  # Wait for results
    except Exception as e:
        print(f"⚠️  Search failed: {e}")


def browse_documentation(page):
    """Browse documentation site"""
    try:
        # Wait for page to load
        time.sleep(2)

        # Try to find and click on a link
        links = page.query_selector_all("a")
        if links and len(links) > 0:
            # Click on the first few links to demonstrate navigation
            for i, link in enumerate(links[:3]):
                try:
                    link_text = link.text_content()
                    if link_text and len(link_text.strip()) > 0:
                        print(f"🔗 Clicking link: {link_text[:50]}...")
                        link.click()
                        time.sleep(2)
                        break
                except:
                    continue
    except Exception as e:
        print(f"⚠️  Documentation browsing failed: {e}")


if __name__ == "__main__":
    print("🎬 AgentBay Browser Replay Demo")
    print("=" * 50)
    main()