"""Regression tests for MCP tool name sanitization."""

import re
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.types import ListToolsResult, Tool


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool.mcp import MCPClients
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


VALID_TOOL_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class FakeSession(ClientSession):
    """Serves a fixed tool list."""

    def __init__(self, tool_names):
        self.tool_names = tool_names

    async def initialize(self):
        class Initialization:
            instructions = ""

        return Initialization()

    async def list_tools(self):
        return ListToolsResult(
            tools=[
                Tool(
                    name=name,
                    description=f"{name} tool",
                    inputSchema={"type": "object"},
                )
                for name in self.tool_names
            ]
        )


async def _connect(tool_names, server_id: str = "weather", prefix: bool = True):
    clients = MCPClients()
    clients.sessions[server_id] = FakeSession(tool_names)
    await clients._initialize_and_list_tools(server_id, tool_name_prefix=prefix)
    return clients


@pytest.mark.asyncio
async def test_replaced_characters_do_not_collapse_tools_together():
    clients = await _connect(["查询天气", "发送邮件"])

    names = list(clients.tool_map)
    assert len(names) == 2
    assert len(set(names)) == 2
    assert all(VALID_TOOL_NAME.match(name) for name in names)
    assert {tool.original_name for tool in clients.tool_map.values()} == {
        "查询天气",
        "发送邮件",
    }


@pytest.mark.asyncio
async def test_tool_name_is_never_empty():
    clients = await _connect(["天气预报"], prefix=False)

    names = list(clients.tool_map)
    assert len(names) == 1
    assert names[0]
    assert VALID_TOOL_NAME.match(names[0])


@pytest.mark.asyncio
async def test_truncated_names_stay_unique():
    prefix = "a" * 60
    clients = await _connect([f"{prefix}_first", f"{prefix}_second"])

    names = list(clients.tool_map)
    assert len(names) == 2
    assert all(len(name) <= 64 for name in names)
    assert len(set(names)) == 2
