"""Regression tests for the tool schema defaults published by the MCP server.

A tool's JSON schema declares a default for every optional parameter
(``web_search``: ``num_results: 5``, ``lang: "en"``, ``country: "us"``,
``fetch_content: false``). The generated signature becomes the argument model of
the registered MCP tool, so dropping those defaults makes clients send ``None``
instead of the documented value.
"""

import inspect
from pathlib import Path

import pytest


# ``app.config`` needs config/config.toml (with a daytona section) to import; create
# a throw-away one so the suite runs on a fresh checkout without a local config.
_CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.toml"
if not _CONFIG.exists():
    _CONFIG.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n',
        encoding="utf-8",
    )

from app.mcp.server import MCPServer  # noqa: E402
from app.tool.base import BaseTool  # noqa: E402
from app.tool.web_search import WebSearch  # noqa: E402


class _SchemaDefaultsTool(BaseTool):
    name: str = "schema_defaults"
    description: str = "tool with falsy default values"
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "force": {"type": "boolean", "default": False},
            "limit": {"type": "integer", "default": 0},
            "label": {"type": "string", "default": "all"},
            "note": {"type": "string"},
        },
        "required": ["path"],
    }

    async def execute(self, **kwargs):
        return "ok"


def _signature_defaults(server: MCPServer, tool: BaseTool) -> dict:
    signature = server._build_signature(tool.to_param()["function"])
    return {
        name: parameter.default
        for name, parameter in signature.parameters.items()
        if parameter.default is not inspect.Parameter.empty
    }


def test_signature_keeps_declared_defaults():
    server = MCPServer()

    defaults = _signature_defaults(server, WebSearch())

    assert defaults == {
        "num_results": 5,
        "lang": "en",
        "country": "us",
        "fetch_content": False,
    }


def test_signature_keeps_falsy_defaults():
    server = MCPServer()

    defaults = _signature_defaults(server, _SchemaDefaultsTool())

    assert defaults == {"force": False, "limit": 0, "label": "all", "note": None}


@pytest.mark.parametrize("tool_factory", [WebSearch, _SchemaDefaultsTool])
def test_registered_tool_publishes_schema_defaults(tool_factory):
    server = MCPServer()
    tool = tool_factory()
    server.register_tool(tool)

    tool_manager = getattr(server.server, "_tool_manager", None)
    if tool_manager is None:  # pragma: no cover - depends on the MCP release
        pytest.skip("installed MCP release does not expose the tool manager")

    properties = tool_manager._tools[tool.name].parameters["properties"]
    declared = tool.to_param()["function"]["parameters"]
    for name, details in declared["properties"].items():
        if "default" in details:
            assert properties[name]["default"] == details["default"]
        if name in declared.get("required", []):
            assert "default" not in properties[name]
