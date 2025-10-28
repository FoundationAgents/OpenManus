"""
Example demonstrating AIBrowser capabilites with AgentBay SDK.
This example shows how to use AIBrowser to visit aliyun.com, including:
- Create AIBrowser session
- Use playwright to connect to AIBrowser instance through CDP protocol
- Utilize playwright to visit aliyun.com
"""

import os
import time
import asyncio

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption

from playwright.async_api import async_playwright

async def main():
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

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                page = await browser.new_page()
                await page.goto("https://www.aliyun.com")
                print("page.title() =", await page.title())

                await page.wait_for_timeout(5000)

                # Modify page font to Microsoft YaHei
                await page.evaluate("""
                    document.body.style.fontFamily = 'Microsoft YaHei';
                """)

                await page.wait_for_timeout(5000)

                # Scale page content to 200%
                await page.evaluate("""
                    document.body.style.transform = 'scale(2)';
                    document.body.style.transformOrigin = 'top left';
                """)

                await page.wait_for_timeout(10000)
                await browser.close()
        agent_bay.delete(session)

if __name__ == "__main__":
    asyncio.run(main())
