import logging
from pydantic import BaseModel
from typing import List, Dict, Any
from mcp_server.page_agent import PageAgent


class Batch(BaseModel):
    batch: int
    companies: List[str]


class CompanyList(BaseModel):
    batches: List[Batch]


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto(
        "https://browserbase.github.io/stagehand-eval-sites/sites/aigrant/"
    )

    instruction = (
        "Extract all companies that received the AI grant and group them with their "
        "batch numbers as an array of objects. Each object should contain the "
        "batch number and its corresponding company names."
    )

    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    extracted_data = await agent.extract(
        instruction=instruction,
        schema=CompanyList,
        use_text_extract=use_text_extract,
    )

    batches = extracted_data.batches
    expected_length = 4
    expected_companies = [
        {
            "batch": 1,
            "companies": 26,
        },
        {
            "batch": 2,
            "companies": 30,
        },
        {
            "batch": 3,
            "companies": 19,
        },
        {
            "batch": 4,
            "companies": 16,
        },
    ]

    if len(batches) != expected_length:
        error_msg = f"Incorrect number of companies. Expected {expected_length}, got {len(batches)}"
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    for index in range(len(expected_companies)):
        extracted_item = batches[index]
        expected_item = expected_companies[index]
        if (
            extracted_item.batch != expected_item["batch"]
            or len(extracted_item.companies) != expected_item["companies"]
        ):
            error_msg = f"First item mismatch. Expected {expected_item}, got {extracted_item.dict()}"
            logger.error(error_msg)
            return {"_success": False, "error": error_msg}

    return {"_success": True}
