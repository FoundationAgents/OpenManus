import logging
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://www.vanta.com/")

    instruction = "click the buy now button if it is available"
    observations = await agent.observe(instruction=instruction)

    success = len(observations) == 0

    if success:
        logger.info(
            "✅ Validation Passed: Agent correctly found 0 elements for the instruction."
        )
    else:
        error_msg = f"Validation Failed: Expected 0 elements, but Agent found {len(observations)}."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    return {"_success": True}
