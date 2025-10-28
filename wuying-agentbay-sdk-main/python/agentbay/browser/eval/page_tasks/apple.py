import logging
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://www.apple.com/iphone-16-pro/")

    actions = [
        "click on the buy button",
        "select the Pro Max model",
        "select the natural titanium color",
        "select the 256GB storage option",
        "click on the 'select a smartphone' trade-in option",
        "select the iPhone 13 mini model from the dropdown",
        "select the iPhone 13 mini is in good condition",
    ]

    for action in actions:
        await agent.act(action)

    logger.info("Verifying success message visibility...")
    try:
        page = await agent.get_current_page()
        success_message_locator = page.locator(
            'text="Good News. Your iPhone 13 mini qualifies for credit."'
        )
        await success_message_locator.wait_for(state="visible", timeout=10000)
        is_visible = True

    except Exception as e:
        logger.error(f"Error during final validation: {e}")
        return {"_success": False, "error": str(e)}

    if is_visible:
        logger.info("✅ Validation passed: Trade-in success message is visible.")
    else:
        logger.error(
            "Validation failed: Trade-in success message was not found or not visible."
        )

    return {"_success": is_visible}
