"""Regression test: a timed out bash session must stay recoverable.

``Bash.execute()`` implements a ``restart`` switch that starts a fresh shell,
and ``_BashSession.run()`` refuses every command once a session timed out. The
tool schema is the only interface a model sees, so it has to advertise that
switch; otherwise a single timeout permanently disables the bash tool.
"""

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
    from app.exceptions import ToolError
    from app.tool import bash as bash_module
    from app.tool.bash import Bash
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _FakeSession:
    """Stand-in for ``_BashSession`` that records lifecycle calls."""

    def __init__(self):
        self.started = False
        self.stopped = False
        self.timed_out = False

    async def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    async def run(self, command):
        if self.timed_out:
            raise ToolError(
                "timed out: bash has not returned in 120.0 seconds and must be restarted"
            )
        return f"ran: {command}"


def _advertised_parameters() -> dict:
    """The parameter schema exactly as the model receives it."""
    return Bash().to_param()["function"]["parameters"]["properties"]


def test_schema_advertises_restart():
    """The model can only recover a timed out session if the schema says so."""
    restart = _advertised_parameters().get("restart")

    assert restart is not None, "bash tool cannot recover from a timed out session"
    assert restart["type"] == "boolean"


@pytest.mark.asyncio
async def test_timed_out_session_is_recoverable_through_the_tool_schema(monkeypatch):
    monkeypatch.setattr(bash_module, "_BashSession", _FakeSession)

    tool = Bash()
    stale_session = _FakeSession()
    stale_session.timed_out = True
    tool._session = stale_session

    with pytest.raises(ToolError):
        await tool.execute(command="echo hi")

    # Only the arguments advertised by the schema are available to the model.
    restart_arguments = {
        name: True for name in _advertised_parameters() if name == "restart"
    }
    result = await tool.execute(command="echo hi", **restart_arguments)

    assert result.system == "tool has been restarted."
    assert stale_session.stopped is True
    assert tool._session is not stale_session
    assert tool._session.started is True
