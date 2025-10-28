import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from mcp_server.page_agent import PageAgent


class Listing(BaseModel):
    price: str = Field(..., description="The price of the listing, e.g., '$3,500'")
    address: str = Field(..., description="The full address of the listing")


class ApartmentListings(BaseModel):
    listings: List[Listing]


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    logger.info("Navigating to apartments.com with extended timeout...")
    await agent.goto(
        "https://www.apartments.com/san-francisco-ca/2-bedrooms/"
    )
    logger.info("Page navigation completed.")

    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    instruction = (
        "Extract all the apartment listings with their prices and their addresses."
    )

    extracted_data: ApartmentListings = await agent.extract(
        instruction=instruction,
        schema=ApartmentListings,
        use_text_extract=use_text_extract,
    )

    if not extracted_data or not extracted_data.listings:
        error_msg = "Extraction failed: The process returned no listings."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    listings = extracted_data.listings
    logger.info(f"Successfully extracted {len(listings)} apartment listings.")

    expected_min_length = 20
    if len(listings) < expected_min_length:
        error_msg = (
            f"Validation failed: Incorrect number of listings extracted. "
            f"Expected at least {expected_min_length}, but got {len(listings)}."
        )
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    first_listing = listings[0]
    if not first_listing.price.startswith("$") or not first_listing.address:
        error_msg = f"Validation failed: First listing format is incorrect. Got: {first_listing.dict()}"
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    logger.info("✅ Validation passed for extract_apartments.")
    return {"_success": True}
