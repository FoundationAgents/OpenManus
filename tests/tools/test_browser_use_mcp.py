import subprocess
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
    monkeypatch.setattr(manus_module.shutil, "which", lambda command: None)
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


@pytest.mark.asyncio
async def test_manus_enables_installed_cua_driver_by_default(monkeypatch):
    calls = []

    async def record_connection(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setenv("OPENMANUS_DISABLE_BROWSER_USE", "1")
    monkeypatch.delenv("OPENMANUS_DISABLE_CUA_DRIVER", raising=False)
    monkeypatch.setattr(
        manus_module.shutil,
        "which",
        lambda command: (
            "/usr/local/bin/cua-driver" if command == "cua-driver" else None
        ),
    )
    monkeypatch.setattr(
        manus_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=(
                '{"mcp_invocation":{"command":"/opt/cua-driver",'
                '"args":["mcp","--socket","/tmp/cua.sock"]}}'
            ),
        ),
    )
    monkeypatch.setattr(manus_module.config.mcp_config, "servers", {})
    monkeypatch.setattr(manus_module.Manus, "connect_mcp_server", record_connection)

    await manus_module.Manus.model_construct().initialize_mcp_servers()

    assert calls == [
        (
            ("/opt/cua-driver", "cua_driver"),
            {
                "use_stdio": True,
                "stdio_args": ["mcp", "--socket", "/tmp/cua.sock"],
                "tool_name_prefix": False,
            },
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("servers", "disabled"),
    [
        ({}, "1"),
        ({"cua_driver": object()}, "0"),
    ],
)
async def test_manus_does_not_duplicate_or_force_cua_driver(
    monkeypatch, servers, disabled
):
    calls = []

    async def record_connection(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setenv("OPENMANUS_DISABLE_BROWSER_USE", "1")
    monkeypatch.setenv("OPENMANUS_DISABLE_CUA_DRIVER", disabled)
    monkeypatch.setattr(
        manus_module.shutil, "which", lambda command: "/usr/local/bin/cua-driver"
    )
    monkeypatch.setattr(manus_module.config.mcp_config, "servers", servers)
    monkeypatch.setattr(manus_module.Manus, "connect_mcp_server", record_connection)

    await manus_module.Manus.model_construct().initialize_mcp_servers()

    assert calls == []


def test_cua_driver_manifest_failure_uses_compatible_mcp_command(monkeypatch):
    monkeypatch.setattr(
        manus_module.shutil, "which", lambda command: "/usr/local/bin/cua-driver"
    )

    def fail_manifest(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], timeout=5)

    monkeypatch.setattr(manus_module.subprocess, "run", fail_manifest)

    assert manus_module._cua_driver_mcp_invocation() == (
        "/usr/local/bin/cua-driver",
        ["mcp"],
    )
