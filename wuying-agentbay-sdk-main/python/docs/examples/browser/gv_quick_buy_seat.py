"""
示例：GV 影院 Quick Buy + 选座
打开 gv.com.sg
通过 Quick Buy 选择影院/日期/场次，进入选座并选择单个座位
重点：复杂流程的自然语言分步动作；保持只选一个座位
"""
import os, asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ActOptions

async def main():
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY not set"); return
    agentbay = AgentBay(api_key=api_key)
    session = agentbay.create(CreateSessionParams(image_id="browser_latest")).session
    try:
        if not await session.browser.initialize_async(BrowserOption()):
            print("Browser init failed"); 
            return
        agent = session.browser.agent
        await agent.navigate_async("https://www.gv.com.sg/")

        await agent.act_async(action_input=ActOptions(
            action='点击 "Quick Buy" 按钮', dom_settle_timeout_ms=3000
        ))
        await agent.act_async(action_input=ActOptions(
            action="在 Quick-Buy 面板中选择任意影院、任意影片，日期选择 2025-08-12", dom_settle_timeout_ms=4000
        ))
        await agent.act_async(action_input=ActOptions(
            action='点击 "Go" 进入选座页面', dom_settle_timeout_ms=4000
        ))
        await agent.act_async(action_input=ActOptions(
            action='点击 "12:55 PM" 的场次', dom_settle_timeout_ms=4000
        ))
        await agent.act_async(action_input=ActOptions(
            action="选择任意可用座位，确保只选择一个，如有两座被选中则取消多余的",
            dom_settle_timeout_ms=5000
        ))
        await asyncio.sleep(3)
    finally:
        try: await session.browser.agent.close_async()
        except Exception: pass
        agentbay.delete(session)

if __name__ == "__main__":
    asyncio.run(main())