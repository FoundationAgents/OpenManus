"""Tests for path quoting in the sandbox file operator's shell checks."""
import shlex
from pathlib import Path

import pytest

_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool.file_operators import SandboxFileOperator
finally:
    if _CREATED_TEST_CONFIG and _CONFIG_PATH.exists():
        _CONFIG_PATH.unlink()


class FakeClient:
    """Records the shell command instead of running it in a sandbox."""

    sandbox = object()

    def __init__(self):
        self.commands = []

    async def create(self, config=None):
        return None

    async def run_command(self, command, timeout=None):
        self.commands.append(command)
        return "false"


@pytest.mark.asyncio
async def test_exists_quotes_a_path_containing_spaces():
    operator = SandboxFileOperator()
    operator.sandbox_client = FakeClient()

    await operator.exists("my dir/file.txt")

    command = operator.sandbox_client.commands[-1]
    assert shlex.split(command)[:3] == ["test", "-e", "my dir/file.txt"]


@pytest.mark.asyncio
async def test_is_directory_quotes_shell_metacharacters():
    operator = SandboxFileOperator()
    operator.sandbox_client = FakeClient()

    await operator.is_directory("a; echo injected")

    command = operator.sandbox_client.commands[-1]
    tokens = shlex.split(command)
    assert tokens[:3] == ["test", "-d", "a; echo injected"]
    assert "injected" not in " ".join(tokens[3:]).replace("echo 'true'", "")
