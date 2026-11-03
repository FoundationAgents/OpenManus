import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import ClientSession
from mcp.types import ImageContent, ListToolsResult, TextContent, Tool


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.agent import manus as manus_module
    from app.agent.toolcall import ToolCallAgent
    from app.schema import Function, ToolCall
    from app.tool.base import BaseTool, ToolResult
    from app.tool.mcp import MCPClients, MCPClientTool
    from app.tool.tool_collection import ToolCollection
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class FakeSession(ClientSession):
    def __init__(self, *, instructions="", content=None):
        self.instructions = instructions
        self.content = content or []

    async def initialize(self):
        return SimpleNamespace(instructions=self.instructions)

    async def list_tools(self):
        return ListToolsResult(
            tools=[
                Tool(
                    name="browser_exec",
                    description="Execute Browser Use CLI 3.0 code",
                    inputSchema={"type": "object"},
                ),
                Tool(
                    name="browser_screenshot",
                    description="Capture the current page",
                    inputSchema={"type": "object"},
                ),
            ]
        )

    async def call_tool(self, name, arguments):
        return SimpleNamespace(content=self.content)


class ImageTool(BaseTool):
    name: str = "image_tool"
    description: str = "Return an image"
    parameters: dict = {"type": "object"}

    async def execute(self, **kwargs):
        return ToolResult(output="image ready", base64_image="cG5n")


@pytest.mark.asyncio
async def test_mcp_preserves_server_instructions_and_native_tool_names():
    clients = MCPClients()
    clients.sessions["browser_use"] = FakeSession(instructions="canonical skill")

    await clients._initialize_and_list_tools("browser_use", tool_name_prefix=False)

    assert clients.server_instructions["browser_use"] == "canonical skill"
    assert set(clients.tool_map) == {"browser_exec", "browser_screenshot"}


@pytest.mark.asyncio
async def test_mcp_forwards_text_and_screenshot_content():
    session = FakeSession(
        content=[
            TextContent(type="text", text="done"),
            ImageContent(type="image", data="cG5n", mimeType="image/png"),
        ]
    )
    tool = MCPClientTool(
        name="browser_screenshot",
        description="Capture the current page",
        parameters={"type": "object"},
        session=session,
        server_id="browser_use",
        original_name="browser_screenshot",
    )

    result = await tool.execute()

    assert result.output == "done"
    assert result.base64_image == "cG5n"


@pytest.mark.asyncio
async def test_tool_images_follow_the_tool_result_as_user_messages():
    agent = ToolCallAgent(available_tools=ToolCollection(ImageTool()))
    agent.tool_calls = [
        ToolCall(
            id="call_1",
            function=Function(name="image_tool", arguments="{}"),
        )
    ]

    await agent.act()

    tool_message, image_message = agent.memory.messages
    assert getattr(tool_message.role, "value", tool_message.role) == "tool"
    assert tool_message.base64_image is None
    assert getattr(image_message.role, "value", image_message.role) == "user"
    assert image_message.base64_image == "cG5n"


@pytest.mark.asyncio
async def test_manus_enables_cli_mcp_by_default(monkeypatch):
    calls = []

    async def record_connection(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.delenv("OPENMANUS_DISABLE_BROWSER_USE", raising=False)
    monkeypatch.setenv("BROWSER_USE_API_KEY", "bu_test")
    monkeypatch.setenv("BU_CDP_URL", "http://127.0.0.1:9237")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-forwarded")
    monkeypatch.setattr(manus_module.config.mcp_config, "servers", {})
    monkeypatch.setattr(manus_module.Manus, "connect_mcp_server", record_connection)

    await manus_module.Manus.model_construct().initialize_mcp_servers()

    assert calls == [
        (
            ("uvx", "browser_use"),
            {
                "use_stdio": True,
                "stdio_args": ["browser-use", "--cli-mcp"],
                "tool_name_prefix": False,
                "stdio_env": {
                    "BROWSER_USE_API_KEY": "bu_test",
                    "BU_CDP_URL": "http://127.0.0.1:9237",
                },
            },
        )
    ]


@pytest.fixture
def description_server(tmp_path):
    server = tmp_path / "description_server.py"
    server.write_text(
        """import asyncio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server = Server("description-metadata")
schema = {"type": "object", "properties": {}, "additionalProperties": False}

@server.list_tools()
async def list_tools():
    return [
        Tool(name="described", description="A fixed description.", inputSchema=schema),
        Tool(name="undescribed", inputSchema=schema),
        Tool(name="empty_description", description="", inputSchema=schema),
    ]

@server.call_tool()
async def call_tool(name, arguments):
    return [TextContent(type="text", text=f"{name}:ok")]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

asyncio.run(main())
""",
        encoding="utf-8",
    )
    return server


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name_prefix", [False, True])
async def test_mcp_connects_with_optional_descriptions(
    description_server, tool_name_prefix
):
    clients = MCPClients()
    descriptions = {
        "described": "A fixed description.",
        "undescribed": "",
        "empty_description": "",
    }
    try:
        await clients.connect_stdio(
            command=sys.executable,
            args=[str(description_server)],
            server_id="metadata",
            tool_name_prefix=tool_name_prefix,
        )
        remote = await clients.list_tools()
        assert {tool.name: tool.description for tool in remote.tools} == {
            **descriptions,
            "undescribed": None,
        }
        params = clients.to_params()
        assert len(params) == len(descriptions)
        for param, (original_name, description) in zip(params, descriptions.items()):
            name = (
                f"mcp_metadata_{original_name}" if tool_name_prefix else original_name
            )
            assert param == {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            }
            result = await clients.execute(name=name, tool_input={})
            assert result.error is None
            assert result.output == f"{original_name}:ok"
    finally:
        await clients.disconnect("metadata")
    assert not clients.sessions
    assert not clients.exit_stacks
    assert not clients.tools
    assert not clients.tool_map
