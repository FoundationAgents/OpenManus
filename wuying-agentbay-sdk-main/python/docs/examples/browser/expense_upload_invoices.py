"""
示例：内网报销自动化（上传发票）
登录工作台，进入报销单
依次上传多张 PDF 电子发票，并保存与提交
重点：变量注入（用户名/密码）、文件上传、多步流程
"""

import os, asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ActOptions


async def main():
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY not set")
        return

    agent_bay = AgentBay(api_key=api_key)
    session = agent_bay.create(CreateSessionParams(image_id="browser_latest")).session

    try:
        ok = await session.browser.initialize_async(BrowserOption())
        if not ok:
            print("Browser init failed")
            return

        agent = session.browser.agent

        await agent.navigate_async("https://work.aliyun-inc.com/")
        await agent.act_async(
            ActOptions(
                action="帮我登陆",
                variables={"用户名": "xxx", "密码": "123456"},
            )
        )
        await agent.act_async(ActOptions(action="点击报销链接或按钮"))
        await agent.act_async(ActOptions(action="在报销单列表中点击第一个项目"))

        invoices = [
            "/Users/user/Desktop/20250711114033.pdf",
            "/Users/user/Desktop/20250711114034.pdf",
            "/Users/user/Desktop/20250711114035.pdf",
        ]
        for path in invoices:
            await agent.act_async(
                ActOptions(action="在快速新增费用列表中选择'差旅-餐费'")
            )
            await agent.act_async(ActOptions(action="点击'上传电子发票'按钮"))
            await agent.act_async(ActOptions(action=f"上传位于 '{path}' 的文件"))
            await agent.act_async(ActOptions(action="点击'保存'按钮"))

        await agent.act_async(ActOptions(action="点击提交报销单"))
        await asyncio.sleep(3)
    finally:
        try:
            await session.browser.agent.close_async()
        except Exception:
            pass
        agent_bay.delete(session)


if __name__ == "__main__":
    asyncio.run(main())
