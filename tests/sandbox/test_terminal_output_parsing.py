"""Regression tests for DockerSession command output parsing.

The interactive session echoes the command line, the command output, the exit
code and the shell prompt over the same socket, so the parser has to drop the
echo and the exit status while keeping every line that the command produced.
These tests feed a recorded byte stream to a fake socket, so no Docker daemon
is required.
"""

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
    from app.sandbox.core import terminal as terminal_module
    from app.sandbox.core.terminal import DockerSession
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _FakeSocket:
    """Minimal stand-in for the exec socket returned by docker."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def recv(self, size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""

    def shutdown(self, *args) -> None:  # pragma: no cover - not used by execute()
        pass

    def close(self) -> None:  # pragma: no cover - not used by execute()
        pass


@pytest.fixture
def make_session(monkeypatch):
    """Build a DockerSession whose socket replays the given chunks."""

    monkeypatch.setattr(terminal_module, "APIClient", lambda *a, **k: SimpleNamespace())

    def _make(chunks):
        session = DockerSession("test-container")
        session.socket = _FakeSocket(chunks)
        return session

    return _make


@pytest.mark.asyncio
async def test_numeric_output_is_preserved(make_session):
    """A command whose output is a number must not lose that line."""
    # tty echo of the command, output "42", exit code "0", prompt
    session = make_session([b"wc -l data.txt\r\n42\r\n0\r\n$ "])

    output = await session.execute("wc -l data.txt")

    assert output == "42"


@pytest.mark.asyncio
async def test_multiple_numeric_lines_are_preserved(make_session):
    session = make_session([b"seq 1 3\r\n1\r\n2\r\n3\r\n0\r\n$ "])

    output = await session.execute("seq 1 3")

    assert output == "1\n2\n3"


@pytest.mark.asyncio
async def test_text_output_is_unchanged(make_session):
    session = make_session([b"echo hi\r\na\r\nb\r\n0\r\n$ "])

    output = await session.execute("echo hi")

    assert output == "a\nb"
