"""
示例：使用PageUse Agent的AgentBay接口访问阿里云并搜索“AgentBay帮助文档”
打开 https://www.aliyun.com
搜索“AgentBay帮助文档”，点击第一条搜索结果并进入“帮助文档”，滚动到页面底部
重点：全程使用 BrowserAgent API
"""

import os
import asyncio

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ActOptions

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
                agent = session.browser.agent

                await agent.navigate_async("https://www.aliyun.com")

                await agent.act_async(
                    ActOptions(action="搜索框输入'AgentBay帮助文档'并回车")
                )
                await agent.act_async(ActOptions(action="点击搜索结果中的第一项"))
                await agent.act_async(ActOptions(action="点击'帮助文档'"))
                await agent.act_async(ActOptions(action="滚动页面到底部"))

                await asyncio.sleep(5)
                await browser.close()
        else:
            print("Failed to initialize browser")
        agent_bay.delete(session)


if __name__ == "__main__":
    asyncio.run(main())
