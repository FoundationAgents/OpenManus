import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from docker.utils import split_command


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.sandbox.core.terminal import AsyncDockerizedTerminal, DockerSession
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["project", "project files", "project '$HOME"])
async def test_session_enters_the_literal_working_directory(tmp_path, name):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash is required to exercise the Docker startup shell command")
    directory = tmp_path / name
    directory.mkdir()
    (directory / "startup-marker").write_text("ready")
    api = Mock()
    api.exec_create.return_value = {"Id": "test-exec"}
    api.exec_start.return_value = SimpleNamespace(_sock=Mock())
    with patch("app.sandbox.core.terminal.APIClient", return_value=api):
        session = DockerSession("test-container")
    session._read_until_prompt = AsyncMock(return_value="$ ")

    await session.create(directory.as_posix(), {})

    startup = api.exec_create.call_args.args[1]
    assert startup[:2] == ["bash", "-c"]
    # Execute the actual cd prefix without launching the interactive shell.
    cd_command = startup[2].split(" && ", 1)[0]
    result = subprocess.run(
        [bash, "-c", cd_command + " && test -f startup-marker"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "directory", ["/workspace", "/workspace/project files", "/workspace/project '$HOME"]
)
async def test_workdir_creation_passes_one_literal_path_to_docker(directory):
    with patch("app.sandbox.core.terminal.docker.from_env"):
        terminal = AsyncDockerizedTerminal("test-container", working_dir=directory)
    terminal._exec_simple = AsyncMock(return_value=(0, ""))

    await terminal._ensure_workdir()

    # Docker SDK uses split_command on string commands before exec_create.
    command = terminal._exec_simple.call_args.args[0]
    assert split_command(command) == ["mkdir", "-p", directory]
