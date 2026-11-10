"""Schema building for every response type must terminate."""

import asyncio
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple, Union

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
    from app.tool.create_chat_completion import CreateChatCompletion
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _Order(BaseModel):
    item: str
    quantity: int


def _parameters(response_type) -> dict:
    return CreateChatCompletion(response_type=response_type).parameters


@pytest.mark.parametrize(
    "response_type",
    [Literal["yes", "no"], Set[int], Tuple[int, str], frozenset[str]],
)
def test_unmapped_generic_builds_a_plain_response_schema(response_type):
    """Literal/Set/Tuple used to recurse until RecursionError."""
    parameters = _parameters(response_type)

    assert parameters["type"] == "object"
    assert list(parameters["properties"]) == ["response"]
    assert parameters["properties"]["response"]["type"] == "string"
    assert parameters["required"] == ["response"]


@pytest.mark.parametrize(
    ("response_type", "expected"),
    [(str, "string"), (int, "integer"), (float, "number"), (bool, "boolean")],
)
def test_primitive_types_keep_their_json_type(response_type, expected):
    parameters = _parameters(response_type)

    assert parameters["properties"]["response"]["type"] == expected


def test_list_type_keeps_its_item_schema():
    parameters = _parameters(List[int])

    assert parameters["properties"]["response"]["type"] == "array"
    assert parameters["properties"]["response"]["items"]["type"] == "integer"


def test_dict_type_keeps_its_value_schema():
    parameters = _parameters(Dict[str, int])

    assert parameters["properties"]["response"]["type"] == "object"
    assert (
        parameters["properties"]["response"]["additionalProperties"]["type"]
        == "integer"
    )


def test_union_and_optional_types_use_any_of():
    for response_type in (Union[int, str], Optional[int]):
        parameters = _parameters(response_type)

        assert len(parameters["properties"]["response"]["anyOf"]) == 2


def test_pydantic_response_type_reuses_the_model_schema():
    parameters = _parameters(_Order)

    assert set(parameters["properties"]) == {"item", "quantity"}
    assert parameters["required"] == ["item", "quantity"]


def test_execute_still_converts_the_response():
    tool = CreateChatCompletion(response_type=int)

    assert asyncio.run(tool.execute(**{"response": "7"})) == 7
