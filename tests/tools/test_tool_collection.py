from pathlib import Path

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool import BaseTool, ToolCollection
    from app.tool.base import ToolResult
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Return the configured message."
    parameters: dict = {"type": "object", "properties": {}}
    message: str

    async def execute(self, **kwargs):
        return ToolResult(output=self.message)


@pytest.mark.asyncio
@pytest.mark.parametrize("registration", ["constructor", "add_tools"])
async def test_duplicate_tool_names_keep_the_first_registration(registration):
    first = EchoTool(message="first")
    duplicate = EchoTool(message="duplicate")
    other = EchoTool(name="other", message="other")

    if registration == "constructor":
        collection = ToolCollection(first, duplicate, other)
    else:
        collection = ToolCollection().add_tools(first, duplicate, other)

    assert [tool["function"]["name"] for tool in collection.to_params()] == [
        "echo",
        "other",
    ]
    assert collection.get_tool("echo") is first
    assert (await collection.execute(name="echo", tool_input={})).output == "first"
    assert [result.output for result in await collection.execute_all()] == [
        "first",
        "other",
    ]
