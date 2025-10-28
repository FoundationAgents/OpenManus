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
                # Step 1: Connect to the browser
                browser = await p.chromium.connect_over_cdp(endpoint_url)

                # Step 2: Open the website
                page = await browser.new_page()
                await page.goto("https://www.aliyun.com")
                print("page.title() =", await page.title())

                await page.wait_for_timeout(3000)

                # Step 3: Search for the keyword
                try:
                    search_input = await page.wait_for_selector("//input[contains(@class, 'search-input')]", timeout=10000)
                    await search_input.click()
                    await search_input.fill("Agentbay帮助文档")
                    await page.keyboard.press("Enter")
                    print("Search completed")
                except Exception as e:
                    print(f"Search failed: {e}")
                    await browser.close()
                    return

                await page.wait_for_timeout(3000)

                # Step 4: Get the search results
                try:
                    await page.wait_for_selector("//a[contains(@class, 'search-result-title')]", timeout=10000)
                    search_results = await page.locator("//a[contains(@class, 'search-result-title')]").all()
                    print(f"Found {len(search_results)} search results")
                except Exception as e:
                    print(f"Failed to get search results: {e}")
                    await browser.close()
                    return

                await page.wait_for_timeout(3000)

                # Step 5: Click the search result
                agentbay_link = None
                for result in search_results:
                    try:
                        text = await result.text_content()
                        print("result =", text)
                        if "无影AgentBay" in text or "AgentBay" in text:
                            agentbay_link = result
                            break
                    except Exception as e:
                        print(f"Error reading result text: {e}")
                        continue

                if not agentbay_link:
                    print("AgentBay link not found in search results")
                    await browser.close()
                    return

                await page.wait_for_timeout(3000)

                # Step 6: Click the helper button
                try:
                    async with page.context.expect_page() as new_page_info:
                        await agentbay_link.click()
                        new_page = await new_page_info.value
                        await new_page.wait_for_load_state("domcontentloaded")
                        print("New page loaded, current URL:", new_page.url)

                        # Wait a bit for the page to fully render
                        await new_page.wait_for_timeout(5000)

                        # Try multiple selectors for the documentation link
                        selectors_to_try = [
                            "a[href*='agentbay-document-index']",
                            "a[href*='document']",
                            "a[href*='帮助']",
                            "a[href*='文档']",
                            "//a[contains(text(), '文档')]",
                            "//a[contains(text(), '帮助')]",
                            "//a[contains(text(), 'AgentBay')]"
                        ]

                        helper_link = None
                        for selector in selectors_to_try:
                            try:
                                print(f"Trying selector: {selector}")
                                await new_page.wait_for_selector(selector, timeout=5000)
                                helper_link = new_page.locator(selector).first
                                link_text = await helper_link.text_content()
                                print(f"Found link with text: {link_text}")
                                break
                            except Exception as e:
                                print(f"Selector {selector} failed: {e}")
                                continue

                        if helper_link:
                            print("helper_link =", await helper_link.text_content())
                            await helper_link.click()
                            print("Successfully clicked the documentation link")
                        else:
                            print("Could not find documentation link, listing all links on the page:")
                            # List all links for debugging
                            all_links = await new_page.locator("a").all()
                            for i, link in enumerate(all_links[:10]):  # Show first 10 links
                                try:
                                    href = await link.get_attribute("href")
                                    text = await link.text_content()
                                    print(f"Link {i+1}: href='{href}', text='{text}'")
                                except:
                                    continue

                except Exception as e:
                    print(f"Error in new page handling: {e}")

                await page.wait_for_timeout(10000)

                await browser.close()
        else:
            print("Failed to initialize browser")

if __name__ == "__main__":
    asyncio.run(main())
