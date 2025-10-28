import logging
import re
from pydantic import BaseModel, Field
from typing import Dict, Any
from mcp_server.page_agent import PageAgent


class RecipeDetails(BaseModel):
    title: str = Field(..., description="Title of the recipe")
    total_ratings: int | None


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto("https://www.allrecipes.com/")
    await agent.act('Type "chocolate chip cookies" in the search bar')
    await agent.act("press enter")

    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    extracted_data: RecipeDetails = await agent.extract(
        instruction="Extract the title of the first recipe and the total number of ratings it has received.",
        schema=RecipeDetails,
        use_text_extract=use_text_extract,
    )

    if not extracted_data:
        error_msg = "Extraction failed: could not extract any recipe details."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    logger.info(f"Successfully extracted data: {extracted_data.model_dump_json()}")

    expected_title = "Best Chocolate Chip Cookies"
    expected_ratings = 19164

    if extracted_data.total_ratings is None:
        extracted_ratings_int = -1
    else:
        if isinstance(extracted_data.total_ratings, int):
            extracted_ratings_int = extracted_data.total_ratings
        else:
            cleaned_ratings_str = re.sub(
                r"[^\d]", "", str(extracted_data.total_ratings)
            )
            try:
                extracted_ratings_int = int(cleaned_ratings_str)
            except ValueError:
                extracted_ratings_int = -1

    is_ratings_within_range = (
        expected_ratings - 1000 <= extracted_ratings_int <= expected_ratings + 1000
    )
    is_title_match = extracted_data.title == expected_title

    if is_title_match and is_ratings_within_range:
        success_msg = "✅ Validation Passed: Extracted title and ratings are correct."
        logger.info(success_msg)
        return {
            "_success": True,
            "data": {
                "title": extracted_data.title,
                "total_ratings": extracted_ratings_int,
            },
        }
    else:
        errors = []
        if not is_title_match:
            errors.append(
                f"Title mismatch. Expected: '{expected_title}', Got: '{extracted_data.title}'"
            )
        if not is_ratings_within_range:
            errors.append(
                f"Ratings out of range. Expected: ~{expected_ratings}, Got: {extracted_ratings_int}"
            )

        error_summary = "Validation Failed: " + " | ".join(errors)
        logger.error(error_summary)

        return {
            "_success": False,
            "error": error_summary,
            "details": {
                "expected_title": expected_title,
                "actual_title": extracted_data.title,
                "expected_ratings_range": f"{expected_ratings - 1000} - {expected_ratings + 1000}",
                "actual_ratings": extracted_ratings_int,
            },
        }
