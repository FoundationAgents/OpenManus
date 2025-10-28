import logging
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://tucowsdomains.com/abuse-form/phishing/")

    logger.info("Observing for the main header of the page...")
    observations = await agent.observe(
        instruction="find the main header of the page",
    )

    if not observations:
        return {"_success": False, "error": "Observe returned no elements."}

    try:
        page = await agent.get_current_page()
    except AttributeError:
        error_msg = "Agent is missing the 'get_playwright_page' method required for this test's validation."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    possible_locators = [
        "#primary > div.singlePage > section > div > div > article > div > iframe",
        "#primary > div.heroBanner > section > div > h1",
    ]

    candidate_handles = []
    for selector in possible_locators:
        try:
            handle = await page.locator(selector).element_handle(timeout=5000)
            if handle:
                candidate_handles.append({"selector": selector, "handle": handle})
        except Exception:
            logger.warning(f"Ground truth selector not found: {selector}")

    found_match = False
    matched_locator = None

    for observation in observations:
        try:
            observation_handle = await page.locator(
                observation.selector
            ).element_handle(timeout=5000)
            if not observation_handle:
                continue

            for candidate in candidate_handles:
                is_same = await observation_handle.evaluate(
                    " (node, otherNode) => node === otherNode ", candidate["handle"]
                )
                if is_same:
                    found_match = True
                    matched_locator = candidate["selector"]
                    break
        except Exception as e:
            logger.warning(
                f"Could not validate observation with selector '{observation.selector}': {e}"
            )

        if found_match:
            break

    if found_match:
        logger.info(
            f"✅ Validation passed: Agent's observation matched ground truth locator '{matched_locator}'."
        )
    else:
        logger.error(
            "Validation failed: None of the agent's observations matched the expected elements."
        )

    return {"_success": found_match, "matched_locator": matched_locator}
