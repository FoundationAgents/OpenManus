"""
示例：会议室快速查询
打开 Alimeeting
自然语言查询“下周三 朝阳科技园C3 六楼 10:00-12:00”的可用会议室，并关闭弹窗
重点：变量注入（用户名/密码）、模糊指令、弹窗处理
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
        if not await session.browser.initialize_async(BrowserOption()):
            print("Browser init failed")
            return
        agent = session.browser.agent
        await agent.navigate_async("https://meeting.alibaba-inc.com/")
        await agent.act_async(
            ActOptions(
                action="帮我登陆",
                variables={"用户名": "xxxx", "密码": "123456"},
            )
        )
        await agent.act_async(
            ActOptions(
                action="帮我找下下周三朝阳科技园C3六楼10点到12点有没有可用的会议室，如果有弹窗，帮我关掉",
            )
        )
        await asyncio.sleep(2)
    finally:
        try:
            await session.browser.agent.close_async()
        except Exception:
            pass
        agent_bay.delete(session)


if __name__ == "__main__":
    asyncio.run(main())
