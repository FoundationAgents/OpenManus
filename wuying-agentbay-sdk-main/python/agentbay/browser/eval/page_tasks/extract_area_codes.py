import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from mcp_server.page_agent import PageAgent

class Center(BaseModel):
    name: str = Field(
        ..., description="The name of the Primary Center (city/town)."
    )
    code: str = Field(..., description="The area code for the Primary Center.")


class Zone(BaseModel):
    name: str = Field(..., description="The name of the Zone.")
    center: List[Center]


class AreaCodeData(BaseModel):
    zone: List[Zone]

EXPECTED_DATA = {
    "zone": [
        {
            "name": "Lagos Zone",
            "center": [
                {"name": "Lagos", "code": "01"}
            ]
        },
        {
            "name": "North West Zone",
            "center": [
                {"name": "Sokoto", "code": "060"},
                {"name": "Kafanchan", "code": "061"},
                {"name": "Kaduna", "code": "062"},
                {"name": "Gusau", "code": "063"},
                {"name": "Kano", "code": "064"},
                {"name": "Katsina", "code": "065"},
                {"name": "Birnin-Kebbi", "code": "068"},
                {"name": "Zaria", "code": "069"},
                {"name": "Hadejia", "code": "078"}
            ]
        },
        {
            "name": "Central Zone",
            "center": [
                {"name": "Abuja", "code": "09"},
                {"name": "Ilorin", "code": "031"},
                {"name": "Makurdi", "code": "044"},
                {"name": "Lokoja", "code": "058"},
                {"name": "Minna", "code": "066"},
                {"name": "Kontagora", "code": "067"},
                {"name": "New Bussa", "code": "033"}
            ]
        },
        {
            "name": "North-East Zone",
            "center": [
                {"name": "Wukari", "code": "041"},
                {"name": "Lafia", "code": "047"},
                {"name": "Azare", "code": "071"},
                {"name": "Gombe", "code": "072"},
                {"name": "Jos", "code": "073"},
                {"name": "Yola", "code": "075"},
                {"name": "Maiduguri", "code": "076"},
                {"name": "Bauchi", "code": "077"},
                {"name": "Jalingo", "code": "079"}
            ]
        },
        {
            "name": "South-West Zone",
            "center": [
                {"name": "Ibadan", "code": "02"},
                {"name": "Ado-Ekiti", "code": "030"},
                {"name": "Akure", "code": "034"},
                {"name": "Oshogbo", "code": "035"},
                {"name": "Ile-Ife", "code": "036"},
                {"name": "Ijebu-Ode", "code": "037"},
                {"name": "Oyo", "code": "038"},
                {"name": "Abeokuta", "code": "039"},
                {"name": "Ikare", "code": "050"},
                {"name": "Owo", "code": "051"},
                {"name": "Benin", "code": "053"},
                {"name": "Warri", "code": "052"},
                {"name": "Sapele", "code": "054"},
                {"name": "Agbor", "code": "055"},
                {"name": "Asaba", "code": "056"},
                {"name": "Auchi", "code": "057"},
                {"name": "Okitipupa", "code": "059"}
            ]
        },
        {
            "name": "South-East",
            "center": [
                {"name": "Enugu", "code": "042"},
                {"name": "Abakaliki", "code": "043"},
                {"name": "Ogoja", "code": "045"},
                {"name": "Onitsha", "code": "046"},
                {"name": "Awka", "code": "048"},
                {"name": "Aba", "code": "082"},
                {"name": "Owerri", "code": "083"},
                {"name": "Port-Harcourt", "code": "084"},
                {"name": "Uyo", "code": "085"},
                {"name": "Ahoada", "code": "086"},
                {"name": "Calabar", "code": "087"},
                {"name": "Umuahia", "code": "088"},
                {"name": "Yenagoa", "code": "089"}
            ]
        }
    ]
}

def validate_zone_centers(extracted_centers: List[Dict], expected_centers: List[Dict], zone_name: str) -> tuple[bool, str]:
    """
    Validate all the centers in a zone
    """
    # Convert to dictionary for fast lookup
    extracted_dict = {(center["name"], center["code"]): center for center in extracted_centers}
    expected_dict = {(center["name"], center["code"]): center for center in expected_centers}

    # Check for missing items
    missing_items = set(expected_dict.keys()) - set(extracted_dict.keys())
    if missing_items:
        return False, f"Zone '{zone_name}' missing zone centers: {missing_items}"

    # Check for extra items
    extra_items = set(extracted_dict.keys()) - set(expected_dict.keys())
    if extra_items:
        return False, f"Zone '{zone_name}' have additional zone centers: {extra_items}"

    return True, ""

def validate_extracted_data(extracted_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that the extracted data matches expectations
    """
    if not extracted_data or "zone" not in extracted_data:
        return False, "Extracted data is empty or does not contain 'zone' field"

    extracted_zones = extracted_data["zone"]
    expected_zones = EXPECTED_DATA["zone"]

    # Convert to dictionary for lookup
    extracted_zone_dict = {zone["name"]: zone for zone in extracted_zones}
    expected_zone_dict = {zone["name"]: zone for zone in expected_zones}

    # Check zone count
    if len(extracted_zones) != len(expected_zones):
        return False, f"Zone count mismatch: expected {len(expected_zones)} zones, got {len(extracted_zones)} zones"

    # Check for missing zones
    missing_zones = set(expected_zone_dict.keys()) - set(extracted_zone_dict.keys())
    if missing_zones:
        return False, f"Missing zones: {missing_zones}"

    # Check for extra zones
    extra_zones = set(extracted_zone_dict.keys()) - set(expected_zone_dict.keys())
    if extra_zones:
        return False, f"Additional zones found: {extra_zones}"

    # Validate centers in each zone
    for zone_name, expected_zone in expected_zone_dict.items():
        if zone_name not in extracted_zone_dict:
            return False, f"Missing zone: {zone_name}"

        extracted_zone = extracted_zone_dict[zone_name]
        if "center" not in extracted_zone:
            return False, f"Zone '{zone_name}' is missing 'center' field"

        success, error_msg = validate_zone_centers(
            extracted_zone["center"],
            expected_zone["center"],
            zone_name
        )
        if not success:
            return False, error_msg

    return True, "Validation passed"


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    await agent.goto(
        "https://browserbase.github.io/stagehand-eval-sites/sites/ncc-area-codes/"
    )

    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    instruction = (
        "Extract ALL the Primary Center names and their corresponding Area Code, "
        "and the name of their corresponding Zone."
    )

    extracted_data: AreaCodeData = await agent.extract(
        instruction=instruction,
        schema=AreaCodeData,
        use_text_extract=use_text_extract,
    )
    success, error_msg = validate_extracted_data(extracted_data.model_dump())

    if not success:
        logger.error(f"Validation Failed: {error_msg}")
        return {"_success": False, "error": error_msg}

    logger.info("✅ Validation passed for extract_area_codes.")
    return {"_success": True}