
"""
AgentBay SDK Browser Proxy Example

This example demonstrates how to use proxy functionality with AgentBay SDK. 
AgentBay supports two types of proxies:

1. Custom Proxy:
   - Uses user-provided proxy servers
   - Supports HTTP/HTTPS/SOCKS proxies
   - Optionally provides username and password for authentication

2. Wuying Proxy:
   - Uses Alibaba Cloud Wuying proxy service
   - Supports two strategies:
     * restricted: Uses fixed proxy nodes
     * polling: Rotates through proxy pool nodes

This example demonstrates:
- Creating a browser session with proxy configuration
- Using Playwright to connect to AI Browser instance via CDP protocol
- Verifying the proxy's public IP address
"""

import os
import asyncio

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption, BrowserProxy

from playwright.async_api import async_playwright

async def main():
    """Main function demonstrating browser proxy functionality."""
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    print("Initializing AgentBay client...")
    agent_bay = AgentBay(api_key=api_key)

    print("Creating new session...")
    params = CreateSessionParams(
        image_id="browser_latest",  # Use latest browser image
    )
    session_result = agent_bay.create(params)

    if session_result.success:
        session = session_result.session
        print(f"Session created successfully, Session ID: {session.session_id}")

        # ==================== Proxy Configuration Examples ====================
        
        # Example 1: Custom Proxy Configuration
        # Suitable for users who have their own proxy servers
        # browser_proxy = BrowserProxy(
        #     proxy_type="custom",           # Proxy type: custom
        #     server="http://127.0.0.1:9090", # Proxy server address (required)
        #     username="username",           # Proxy username (optional)
        #     password="password"            # Proxy password (optional)
        # )

        # Example 2: Wuying Proxy - Polling Strategy
        # Rotates through proxy pool nodes, suitable for scenarios requiring frequent IP switching
        browser_proxy = BrowserProxy(
            proxy_type="wuying",    # Proxy type: wuying proxy
            strategy="polling",     # Strategy: polling
            pollsize=2             # Proxy pool size: 2 nodes
        )

        # Example 3: Wuying Proxy - Restricted Strategy
        # Uses fixed proxy nodes, suitable for scenarios requiring stable IP
        # browser_proxy = BrowserProxy(
        #     proxy_type="wuying",    # Proxy type: wuying proxy
        #     strategy="restricted"   # Strategy: restricted (fixed nodes)
        # )

        # Create browser options with proxy configuration, now only support one proxy
        browser_option = BrowserOption(
            proxies=[browser_proxy]
        )

        # Initialize browser instance
        if await session.browser.initialize_async(browser_option):
            # Get browser CDP connection endpoint
            endpoint_url = session.browser.get_endpoint_url()
            print(f"Browser CDP endpoint: {endpoint_url}")

            # Use Playwright to connect to remote browser instance
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                context = browser.contexts[0]  # Get default browser context
                page = await context.new_page()  # Create new page

                # ==================== Verify Proxy IP ====================
                print("\n--- Starting proxy public IP check ---")
                await page.goto("https://httpbin.org/ip")  # Visit IP checking service

                try:
                    # Parse JSON response from page content
                    response = await page.evaluate("() => JSON.parse(document.body.textContent)")
                    public_ip = response.get("origin", "").strip()
                    print(f"Proxy public IP: {public_ip}")
                except Exception as e:
                    print(f"Failed to get proxy public IP: {e}")
                    public_ip = None
                print("--- Proxy IP check completed ---\n")
                
                # Wait 3 seconds to observe results
                await page.wait_for_timeout(3000)
                await browser.close()
        else:
            print("Browser initialization failed")

        # Clean up session resources
        print("Cleaning up session...")
        agent_bay.delete(session)
        print("Session cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
