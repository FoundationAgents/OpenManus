import logging
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://browserbase.github.io/stagehand-eval-sites/sites/amazon/")
    observations1 = await agent.observe(
        instruction="Find and click the 'Add to Cart' button",
    )

    if not observations1:
        return {
            "_success": False,
            "error": "Step 1 Failed: Could not find 'Add to Cart' button.",
        }

    await agent.act(observations1[0])

    observations2 = await agent.observe(
        instruction="Find and click the 'Proceed to checkout' button",
    )

    if not observations2:
        return {
            "_success": False,
            "error": "Step 2 Failed: Could not find 'Proceed to checkout' button.",
        }

    logger.info("Found 'Proceed to checkout' button. Executing action...")
    await agent.act(observations2[0])

    page = await agent.get_current_page()
    expected_url_prefix = (
        "https://browserbase.github.io/stagehand-eval-sites/sites/amazon/sign-in.html"
    )

    if page.url.startswith(expected_url_prefix):
        logger.info("✅ Validation passed: Reached the expected sign-in page.")
        return {"_success": True}
    else:
        error_msg = f"Validation failed: Final URL mismatch. Expected prefix: '{expected_url_prefix}', Got: '{page.url}'"
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}
