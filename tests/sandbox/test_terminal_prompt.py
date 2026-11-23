import socket
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.sandbox.core.terminal import DockerSession
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("chunks", [[b""], [b"Welcome\n", b""]])
async def test_session_creation_reports_eof_before_the_shell_prompt(chunks):
    transport = Mock(spec=socket.socket)
    transport.recv.side_effect = chunks + [
        AssertionError("The closed socket must not be read again")
    ]
    api = Mock()
    api.exec_create.return_value = {"Id": "test-exec"}
    api.exec_start.return_value = SimpleNamespace(_sock=transport)

    with patch("app.sandbox.core.terminal.APIClient", return_value=api):
        session = DockerSession("test-container")

    with pytest.raises(RuntimeError, match="closed.*prompt"):
        await session.create("/workspace", {})


@pytest.mark.asyncio
async def test_session_creation_accepts_a_prompt_split_across_reads():
    transport = Mock(spec=socket.socket)
    transport.recv.side_effect = [b"Welcome\n$", b" "]
    api = Mock()
    api.exec_create.return_value = {"Id": "test-exec"}
    api.exec_start.return_value = SimpleNamespace(_sock=transport)

    with patch("app.sandbox.core.terminal.APIClient", return_value=api):
        session = DockerSession("test-container")

    await session.create("/workspace", {})
    assert session.exec_id == "test-exec"
