"""Regression test for `Manus.connect_mcp_server` tool registration."""

from pathlib import Path
from types import SimpleNamespace

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.agent.manus import Manus
    from app.tool.mcp import MCPClients, MCPClientTool
    from app.tool.terminate import Terminate
    from app.tool.tool_collection import ToolCollection
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


async def fake_connect_stdio(
    self, command, args, server_id="", tool_name_prefix=True, env=None
):
    """Mimic MCPClients.connect_stdio, including its server_id fallback."""
    resolved_server_id = server_id or command
    tool = MCPClientTool(
        name="browser_exec",
        description="Execute browser code",
        parameters={"type": "object"},
        server_id=resolved_server_id,
        original_name="browser_exec",
    )
    self.sessions[resolved_server_id] = SimpleNamespace()
    self.tool_map[tool.name] = tool
    self.tools = tuple(self.tool_map.values())
    self.server_instructions[resolved_server_id] = "use browser_exec"


@pytest.mark.asyncio
async def test_connect_without_server_id_registers_the_server_tools(monkeypatch):
    """Omitting server_id must not silently drop the new tools."""
    monkeypatch.setattr(MCPClients, "connect_stdio", fake_connect_stdio)

    agent = Manus.model_construct(llm=None)
    agent.available_tools = ToolCollection(Terminate())
    agent.connected_servers = {}
    agent.mcp_instruction_servers = set()

    await agent.connect_mcp_server("uvx", use_stdio=True, stdio_args=["browser-use"])

    assert [tool.name for tool in agent.mcp_clients.tools] == ["browser_exec"]
    assert "browser_exec" in agent.available_tools.tool_map
    assert agent.connected_servers == {"uvx": "uvx"}
