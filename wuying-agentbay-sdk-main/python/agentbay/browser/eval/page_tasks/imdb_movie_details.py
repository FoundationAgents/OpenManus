import logging
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from mcp_server.page_agent import PageAgent


class CountryRatings(BaseModel):
    countries: List[str] = Field(
        ...,
        description="A list of countries with the most ratings, ordered from highest to lowest.",
    )


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://www.imdb.com/title/tt0111161/")
    await agent.act("click on the movie ratings")
    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    extracted_data: CountryRatings = await agent.extract(
        instruction="Extract the list of countries with the most ratings.",
        schema=CountryRatings,
        use_text_extract=use_text_extract,
    )

    if not extracted_data or not extracted_data.countries:
        error_msg = "Extraction failed: could not extract any country data."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    logger.info(f"Successfully extracted countries: {extracted_data.countries}")

    expected_countries = [
        "United States",
        "United Kingdom",
        "Turkey",
        "India",
        "Germany",
    ]

    if len(extracted_data.countries) < len(expected_countries):
        error_msg = f"Validation Failed: Expected at least {len(expected_countries)} countries, but got {len(extracted_data.countries)}."
        logger.error(error_msg)
        return {
            "_success": False,
            "error": error_msg,
            "details": {
                "expected_min_count": len(expected_countries),
                "actual_count": len(extracted_data.countries),
                "extracted_list": extracted_data.countries,
            },
        }

    extracted_set = set(extracted_data.countries)
    missing_countries = [
        country for country in expected_countries if country not in extracted_set
    ]

    if not missing_countries:
        success_msg = "✅ Validation Passed: All expected countries were found in the extracted list."
        logger.info(success_msg)
        return {
            "_success": True,
            "data": {"countries": extracted_data.countries},
        }
    else:
        error_summary = f"Validation Failed: The following expected countries were missing: {', '.join(missing_countries)}"
        logger.error(error_summary)

        return {
            "_success": False,
            "error": "Extracted countries do not match expected countries.",
            "details": {
                "missing_countries": missing_countries,
                "extracted_list": extracted_data.countries,
                "expected_list": expected_countries,
            },
        }
