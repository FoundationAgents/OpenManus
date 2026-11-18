"""Regression test for the sandbox browser state reported to the agent.

``SandboxBrowserTool.get_current_state`` renders the state that
``_execute_browser_action`` stored, which is plain JSON coming back from the
sandbox automation service (``json.loads(response.result)``).  The renderer
used to treat that JSON as an object: ``tab.model_dump()`` raised
``AttributeError`` for dict tabs (so the agent got no browser state at all) and
``getattr(state, "pixels_above", 0)`` always reported ``0``.

The Daytona SDK is optional (it is not part of ``requirements.txt``), so the
test installs a stand-in for it before importing the sandbox tool.
"""

import importlib
import json
import sys
import types
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
    from app.config import config  # noqa: F401  (loads config/config.toml)
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _StandIn:
    """Accepts any construction arguments and any attribute access."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _StandIn


class _TabModel:
    """Minimal stand-in for the browser library's tab model object."""

    def __init__(self, **data):
        self._data = data

    def model_dump(self):
        return dict(self._data)


def _import_sandbox_browser_tool(monkeypatch):
    # Always shadow the optional Daytona SDK so the test behaves the same in
    # environments that do not install it (it is not in requirements.txt).
    stub = types.ModuleType("daytona")
    stub.__getattr__ = lambda attribute: _StandIn
    monkeypatch.setitem(sys.modules, "daytona", stub)
    monkeypatch.delitem(
        sys.modules, "app.tool.sandbox.sb_browser_tool", raising=False
    )
    return importlib.import_module("app.tool.sandbox.sb_browser_tool")


def _tool_with_state(module, state):
    tool = module.SandboxBrowserTool()
    tool.browser_message = module.ThreadMessage(
        type="browser_state", content=state, is_llm_message=False
    )
    return tool


@pytest.mark.asyncio
async def test_json_browser_state_is_reported_to_the_agent(monkeypatch):
    module = _import_sandbox_browser_tool(monkeypatch)
    state = {
        "url": "https://example.com/form",
        "title": "Example form",
        "tabs": [{"id": 0, "url": "https://example.com/form"}],
        "pixels_above": 120,
        "pixels_below": 340,
        "screenshot_base64": "iVBORw0KGgo=",
    }

    result = await _tool_with_state(module, state).get_current_state()

    assert result.error is None, result.error
    reported = json.loads(result.output)
    assert reported["url"] == "https://example.com/form"
    assert reported["title"] == "Example form"
    assert reported["tabs"] == [{"id": 0, "url": "https://example.com/form"}]
    assert reported["pixels_above"] == 120
    assert reported["pixels_below"] == 340
    assert result.base64_image == "iVBORw0KGgo="


@pytest.mark.asyncio
async def test_model_tab_objects_are_still_dumped(monkeypatch):
    module = _import_sandbox_browser_tool(monkeypatch)
    state = {
        "url": "https://example.com/",
        "title": "Example",
        "tabs": [_TabModel(id=1, url="https://example.com/")],
    }

    result = await _tool_with_state(module, state).get_current_state()

    assert result.error is None, result.error
    assert json.loads(result.output)["tabs"] == [
        {"id": 1, "url": "https://example.com/"}
    ]
