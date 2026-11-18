"""Regression test for the A2A protocol entry point.

``protocol/a2a/app/main.py`` is the documented way to start the A2A server
(``python -m protocol.a2a.app.main``).  It used to import the browser skill
description from ``app.tool.browser_use_tool``, a module that no longer exists
once browsing moved to the Browser Use CLI MCP server, so the whole entry point
died with ``ModuleNotFoundError`` before it could start.

The a2a SDK is optional (see ``protocol/a2a/app/README.md``), therefore the test
installs tiny stand-ins for the third-party packages and only then imports the
entry point, exactly the way a user starts it.
"""

import importlib
import importlib.util
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


_OPTIONAL_MODULES = (
    "httpx",
    "dotenv",
    "a2a",
    "a2a.server",
    "a2a.server.agent_execution",
    "a2a.server.apps",
    "a2a.server.events",
    "a2a.server.request_handlers",
    "a2a.server.tasks",
    "a2a.types",
    "a2a.utils",
    "a2a.utils.errors",
)


def _is_importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _missing_optional_modules() -> list:
    """Optional modules that have to be stubbed, resolved before stubbing."""
    missing = []
    top_level_available = {}
    for name in _OPTIONAL_MODULES:
        top_level = name.split(".")[0]
        if top_level not in top_level_available:
            top_level_available[top_level] = _is_importable(top_level)
        # Never shadow a package that really is installed (``httpx`` is also a
        # transitive dependency of the required ``openai`` package).
        if top_level_available[top_level] and _is_importable(name):
            continue
        missing.append(name)
    return missing


def _import_entry_point(monkeypatch):
    """Import ``protocol.a2a.app.main`` with the optional SDK stubbed out."""
    for name in _missing_optional_modules():
        module = types.ModuleType(name)
        module.__getattr__ = lambda attribute: _StandIn
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.delitem(sys.modules, "protocol.a2a.app.main", raising=False)
    return importlib.import_module("protocol.a2a.app.main")


def test_entry_point_imports_and_describes_the_browser_skill(monkeypatch):
    entry_point = _import_entry_point(monkeypatch)

    assert callable(entry_point.main)
    assert callable(entry_point.run_server)
    assert isinstance(entry_point._BROWSER_DESCRIPTION, str)
    assert "browser" in entry_point._BROWSER_DESCRIPTION.lower()


@pytest.mark.asyncio
async def test_entry_point_builds_the_agent_card(monkeypatch):
    entry_point = _import_entry_point(monkeypatch)

    application = await entry_point.main()

    assert application is not None
