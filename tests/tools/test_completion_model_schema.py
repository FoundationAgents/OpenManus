from pathlib import Path

import pytest
from pydantic import BaseModel


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool import CreateChatCompletion
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class Address(BaseModel):
    city: str


class Profile(BaseModel):
    address: Address
    delivery_note: str = ""


class OptionalProfile(BaseModel):
    nickname: str = "guest"


@pytest.mark.asyncio
async def test_model_completion_schema_keeps_nested_reference_definitions():
    tool = CreateChatCompletion(response_type=Profile)
    schema = tool.to_param()["function"]["parameters"]
    reference = schema["properties"]["address"]["$ref"]
    definition = schema
    for part in reference.removeprefix("#/").split("/"):
        definition = definition[part]

    assert definition["required"] == ["city"]
    assert definition["properties"]["city"]["type"] == "string"
    result = await tool.execute(address={"city": "Paris"})
    assert isinstance(result, Profile)
    assert result.address.city == "Paris"


@pytest.mark.asyncio
async def test_model_completion_schema_does_not_require_an_absent_response_field():
    tool = CreateChatCompletion(response_type=OptionalProfile)
    schema = tool.to_param()["function"]["parameters"]

    assert schema.get("required", []) == []
    result = await tool.execute()
    assert isinstance(result, OptionalProfile)
    assert result.nickname == "guest"
