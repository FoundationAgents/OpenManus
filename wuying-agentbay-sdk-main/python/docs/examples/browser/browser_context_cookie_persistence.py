#!/usr/bin/env python3
"""
Browser Context Cookie Persistence Example

This example demonstrates how to use Browser Context to persist cookies
across multiple sessions. It shows the complete workflow of:
1. Creating a session with Browser Context
2. Setting cookies in the browser
3. Deleting the session with context synchronization
4. Creating a new session with the same Browser Context
5. Verifying that cookies persist across sessions
"""

import asyncio
import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.browser.browser import BrowserOption
from playwright.async_api import async_playwright

def main():
    """Demonstrate browser context cookie persistence."""
    # Get API key from environment
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    # Initialize AgentBay client
    agent_bay = AgentBay(api_key)
    print("AgentBay client initialized")

    # Create a unique context name for this demo
    context_name = f"browser-cookie-demo-{int(time.time())}"

    try:
        # Step 1: Create or get a persistent context for browser data
        print(f"Step 1: Creating context '{context_name}'...")
        context_result = agent_bay.context.get(context_name, create=True)

        if not context_result.success or not context_result.context:
            print(f"Failed to create context: {context_result.error_message}")
            return

        context = context_result.context
        print(f"Context created with ID: {context.id}")

        # Step 2: Create first session with Browser Context
        print("Step 2: Creating first session with Browser Context...")
        browser_context = BrowserContext(context.id, auto_upload=True)
        params = CreateSessionParams(
            image_id="imgc-wucyOiPmeV2Z753lq",  # Browser image ID
            browser_context=browser_context
        )

        session_result = agent_bay.create(params)
        if not session_result.success or not session_result.session:
            print(f"Failed to create first session: {session_result.error_message}")
            return

        session1 = session_result.session
        print(f"First session created with ID: {session1.session_id}")


        # Test data
        test_url = "https://www.aliyun.com"
        test_domain = "aliyun.com"

        # Define test cookies
        test_cookies = [
            {
                "name": "demo_cookie_1",
                "value": "demo_value_1",
                "domain": test_domain,
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "expires": int(time.time()) + 3600  # 1 hour from now
            },
            {
                "name": "demo_cookie_2",
                "value": "demo_value_2",
                "domain": test_domain,
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "expires": int(time.time()) + 3600  # 1 hour from now
            }
        ]


        # Step 3: Initialize browser and set cookies
        print("Step 3: Initializing browser and setting test cookies...")
        async def first_session_operations():
            # Initialize browser
            init_success = await session1.browser.initialize_async(BrowserOption())
            if not init_success:
                print("Failed to initialize browser")
                return

            print("Browser initialized successfully")

            # Get endpoint URL
            endpoint_url = session1.browser.get_endpoint_url()
            if not endpoint_url:
                print("Failed to get browser endpoint URL")
                return

            print(f"Browser endpoint URL: {endpoint_url}")
            # Connect with Playwright and set cookies
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                cdp_session = await browser.new_browser_cdp_session()
                context_p = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context_p.new_page()

                # Navigate to test URL first (required before setting cookies)
                await page.goto(test_url)
                print(f"Navigated to {test_url}")
                await page.wait_for_timeout(2000)

                # Add test cookies
                await context_p.add_cookies(test_cookies)  # type: ignore
                print(f"Added {len(test_cookies)} test cookies")

                # Verify cookies were set
                cookies = await context_p.cookies()
                cookie_dict = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies}
                print(f"Total cookies in first session: {len(cookies)}")
                # Check our test cookies
                for test_cookie in test_cookies:
                    cookie_name = test_cookie["name"]
                    if cookie_name in cookie_dict:
                        print(f"✓ Test cookie '{cookie_name}' set successfully: {cookie_dict[cookie_name]}")
                    else:
                        print(f"✗ Test cookie '{cookie_name}' not found")

                await cdp_session.send('Browser.close')
                print("First session browser operations completed")

                # Wait for browser to save cookies to file
                print("Waiting for browser to save cookies to file...")
                await asyncio.sleep(2)
                print("Wait completed")

                await browser.close()
                print("First session browser operations completed")
        # Run first session operations
        asyncio.run(first_session_operations())
        # Step 4: Delete first session with context synchronization
        print("Step 4: Deleting first session with context synchronization...")
        delete_result = agent_bay.delete(session1, sync_context=True)

        if not delete_result.success:
            print(f"Failed to delete first session: {delete_result.error_message}")
            return

        print(f"First session deleted successfully (RequestID: {delete_result.request_id})")

        # Wait for context sync to complete
        print("Waiting for context synchronization to complete...")
        time.sleep(3)

        # Step 5: Create second session with same Browser Context
        print("Step 5: Creating second session with same Browser Context...")
        session_result2 = agent_bay.create(params)

        if not session_result2.success or not session_result2.session:
            print(f"Failed to create second session: {session_result2.error_message}")
            return

        session2 = session_result2.session
        print(f"Second session created with ID: {session2.session_id}")

        # Step 6: Verify cookie persistence
        print("Step 6: Verifying cookie persistence in second session...")

        async def second_session_operations():

            # Initialize browser in second session
            init_success2 = await session2.browser.initialize_async(BrowserOption())
            if not init_success2:
                print("Failed to initialize browser in second session")
                return

            print("Second session browser initialized successfully")

            # Get endpoint URL for second session
            endpoint_url2 = session2.browser.get_endpoint_url()
            if not endpoint_url2:
                print("Failed to get browser endpoint URL for second session")
                return

            print(f"Second session browser endpoint URL: {endpoint_url2}")

            # Check cookies in second session
            async with async_playwright() as p:
                browser2 = await p.chromium.connect_over_cdp(endpoint_url2)
                context2 = browser2.contexts[0] if browser2.contexts else await browser2.new_context()

                # Read cookies directly from context (without opening any page)
                cookies2 = await context2.cookies()
                cookie_dict2 = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies2}

                print(f"Total cookies in second session: {len(cookies2)}")

                # Check if our test cookies persisted
                expected_cookie_names = {"demo_cookie_1", "demo_cookie_2"}
                found_cookie_names = set(cookie_dict2.keys())

                print("Checking test cookie persistence...")
                missing_cookies = expected_cookie_names - found_cookie_names

                if missing_cookies:
                    print(f"✗ Missing test cookies: {missing_cookies}")
                    print("Cookie persistence test FAILED")
                else:
                    # Verify cookie values
                    all_values_match = True
                    for test_cookie in test_cookies:
                        cookie_name = test_cookie["name"]
                        expected_value = test_cookie["value"]
                        actual_value = cookie_dict2.get(cookie_name, "")

                        if expected_value == actual_value:
                            print(f"✓ Cookie '{cookie_name}' persisted correctly: {actual_value}")
                        else:
                            print(f"✗ Cookie '{cookie_name}' value mismatch. Expected: {expected_value}, Actual: {actual_value}")
                            all_values_match = False

                    if all_values_match:
                        print("🎉 Cookie persistence test PASSED! All cookies persisted correctly across sessions.")
                    else:
                        print("Cookie persistence test FAILED due to value mismatches")

                await browser2.close()
                print("Second session browser operations completed")
        asyncio.run(second_session_operations())
        # Step 7: Clean up second session
        print("Step 7: Cleaning up second session...")
        delete_result2 = agent_bay.delete(session2)

        if delete_result2.success:
            print(f"Second session deleted successfully (RequestID: {delete_result2.request_id})")
        else:
            print(f"Failed to delete second session: {delete_result2.error_message}")

    except Exception as e:
        print(f"Error during demo: {e}")

    finally:
        # Clean up context
        async def clear_context():
            try:
                agent_bay.context.delete(context)
                print(f"Context '{context_name}' deleted")
            except Exception as e:
                print(f"Warning: Failed to delete context: {e}")
        asyncio.run(clear_context())
    print("\nBrowser Context Cookie Persistence Demo completed!")


if __name__ == "__main__":
    main()
