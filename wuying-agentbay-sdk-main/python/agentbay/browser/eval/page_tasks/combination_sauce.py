import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from mcp_server.page_agent import PageAgent


class LoginCredentials(BaseModel):
    usernames: List[str] = Field(..., description="The list of accepted usernames.")
    password: str = Field(..., description="The password for all users.")


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://www.saucedemo.com/")

    logger.info("Extracting login credentials...")
    extract_method = config.get("extract_method", "textExtract")
    use_text_extract = extract_method == "textExtract"

    credentials: LoginCredentials = await agent.extract(
        instruction="extract the accepted usernames and the password for login",
        schema=LoginCredentials,
        use_text_extract=use_text_extract,
    )
    if not credentials or not credentials.password:
        return {
            "_success": False,
            "error": "Step 1 Failed: Could not extract credentials.",
        }

    await agent.act("enter username 'standard_user'")
    await agent.act(f"enter password {credentials.password}")
    await agent.act("click on 'login'")

    logger.info("Observing for 'add to cart' buttons on the inventory page...")
    observations = await agent.observe(
        instruction="find all the 'add to cart' buttons",
    )

    page = await agent.get_current_page()

    usernames_check = len(credentials.usernames) == 6
    url_check = page.url == "https://www.saucedemo.com/inventory.html"
    observations_check = len(observations) == 6

    if not usernames_check:
        return {
            "_success": False,
            "error": f"Username validation failed. Expected 6, got {len(credentials.usernames)}.",
        }
    if not url_check:
        return {
            "_success": False,
            "error": f"URL validation failed. Expected inventory page, got {page.url}.",
        }
    if not observations_check:
        return {
            "_success": False,
            "error": f"Observation validation failed. Expected 6 buttons, found {len(observations)}.",
        }

    logger.info("✅ Validation passed for all steps in combination_sauce.")
    return {"_success": True}
