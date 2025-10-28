import logging
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://browserbase.github.io/stagehand-eval-sites/sites/google/")

    await agent.act('type "OpenAI" into the search bar')
    await agent.act("click the search button")

    page = await agent.get_current_page()
    expectedUrl = "https://browserbase.github.io/stagehand-eval-sites/sites/google/openai.html"
    success = page.url.startswith(expectedUrl)

    return {"_success": success, "final_url": page.url}
