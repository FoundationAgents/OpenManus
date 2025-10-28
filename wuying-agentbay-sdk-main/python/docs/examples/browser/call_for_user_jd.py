"""
Example demonstrating wuying-call-for-user message handling with AgentBay SDK.

This example shows how to handle the 'wuying-call-for-user' message that can be received
during browser automation sessions. The wuying-call-for-user message is triggered when:

1. The browser encounters a situation that requires human intervention
2. Authentication challenges that cannot be automatically resolved
3. Complex verification processes that need user input
4. Security measures that require manual verification

When you receive a 'wuying-call-for-user' message, the recommended handling flow is:

1. Parse the console message to identify the message type
2. When 'wuying-call-for-user' is detected, open the session resource URL in a browser
3. Allow the user to interact with the browser to complete the required action
4. Wait for the user to complete the interaction (typically 20-30 seconds)
5. Continue with the automation flow

This example demonstrates:
- Creating an AgentBay session with browser capabilities
- Connecting to the browser via CDP protocol using Playwright
- Setting up console message listeners to detect wuying-call-for-user messages
- Opening the session resource URL for user interaction
- Implementing a wait mechanism for user completion
- Taking screenshots for debugging purposes
"""

import os
import time
import asyncio
import base64
import json

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption

from playwright.async_api import async_playwright

from agentbay.browser.browser import (
    Browser,
    BrowserOption,
    BrowserViewport,
    BrowserScreen,
    BrowserFingerprint,
    BrowserProxy
)

async def main():
    """
    Main function demonstrating wuying-call-for-user message handling.
    This function sets up a browser session and navigates to JD.com to trigger
    scenarios that might require user intervention.
    """
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    # Initialize AgentBay client
    print("Initializing AgentBay client...")
    agent_bay = AgentBay(api_key=api_key)

    # Create a session
    print("Creating a new session...")
    params = CreateSessionParams(
        image_id="browser_latest",  # Specify the image ID
    )
    session_result = agent_bay.create(params)

    if session_result.success:
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")
        if await session.browser.initialize_async(BrowserOption()):
            print("Browser initialized successfully")
            endpoint_url = session.browser.get_endpoint_url()
            print("endpoint_url =", endpoint_url)
            result = session.info()
            info = result.data
            print(f"session resource url is {info.resource_url}")

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                page = await browser.new_page()
                print("🌐 Navigating to jd site...")
                url = "https://www.jd.com/"
                await page.goto(url)

                # Listen for console messages
                def handle_console(msg):
                    print(f"🔍 Received console message: {msg.text}")
                    
                    # Parse JSON message
                    try:
                        message_data = json.loads(msg.text)
                        message_type = message_data.get('type', '')
                        print(f"📋 Parsed message type: {message_type}")
                    except (json.JSONDecodeError, AttributeError):
                        # If not JSON, treat as plain text
                        message_type = msg.text
                        print(f"📋 Plain text message: {message_type}")
                    # message_type = msg.text

                    if message_type == "wuying-call-for-user":
                        print("📞 Received wuying-call-for-user message")
                        print(f"session resource url is {info.resource_url}")
                        # You can skip this message or use chrome to open url for user hanle
                        # Following sample code shows how to use chrome open url
                        import subprocess
                        import webbrowser
                        print("🌐 Opening browser with session resource URL...")
                        webbrowser.open(info.resource_url)
                        # wait user to interact with the browser
                        print("⏳ Starting 20 second wait for user interaction...")
                        # Use time.sleep to block for 20 seconds for user interaction, also you can check user input
                        time.sleep(20)

                page.on("console", handle_console)

                await asyncio.sleep(5)
                print("click login")
                await page.click('.link-login')
                await asyncio.sleep(25)
                
                print("Test completed")
                
                # Keep browser open for a while to observe results
                await asyncio.sleep(5)

                # Take screenshot and print base64, can be pasted directly into Chrome address bar
                try:
                    screenshot_bytes = await page.screenshot(full_page=False)
                    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    print("page_screenshot_base64 = data:image/png;base64,", b64)
                except Exception as e:
                    print("screenshot failed:", e)
                
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
