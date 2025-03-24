import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from app.config import SandboxSettings
from app.sandbox.client import LocalSandboxClient, create_sandbox_client


@pytest_asyncio.fixture(scope="function")
async def local_client() -> AsyncGenerator[LocalSandboxClient, None]:
    """Creates a local sandbox client for testing."""
    client = create_sandbox_client()
    try:
        yield client
    finally:
        await client.cleanup()


@pytest.fixture(scope="function")
def temp_dir() -> Path:
    """Creates a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.mark.asyncio
async def test_sandbox_creation(local_client: LocalSandboxClient):
    """Tests sandbox creation with specific configuration."""
    config = SandboxSettings(
        image="python:3.12-slim",
        work_dir="/workspace",
        memory_limit="512m",
        cpu_limit=0.5,
    )

    await local_client.create(config)
    result = await local_client.run_command("python3 --version")
    assert "Python 3.10" in result


@pytest.mark.asyncio
async def test_local_command_execution(local_client: LocalSandboxClient):
    """Tests command execution in local sandbox."""
    await local_client.create()

    result = await local_client.run_command("echo 'test'")
    assert result.strip() == "test"

    with pytest.raises(Exception):
        await local_client.run_command("sleep 10", timeout=1)


@pytest.mark.asyncio
async def test_local_file_operations(local_client: LocalSandboxClient, temp_dir: Path):
    """Tests file operations in local sandbox."""
    await local_client.create()

    # Test write and read operations
    test_content = "Hello, World!"
    await local_client.write_file("/workspace/test.txt", test_content)
    content = await local_client.read_file("/workspace/test.txt")
    assert content.strip() == test_content

    # Test copying file to container
    src_file = temp_dir / "src.txt"
    src_file.write_text("Copy to container")
    await local_client.copy_to(str(src_file), "/workspace/copied.txt")
    content = await local_client.read_file("/workspace/copied.txt")
    assert content.strip() == "Copy to container"

    # Test copying file from container
    dst_file = temp_dir / "dst.txt"
    await local_client.copy_from("/workspace/test.txt", str(dst_file))
    assert dst_file.read_text().strip() == test_content


@pytest.mark.asyncio
async def test_local_volume_binding(local_client: LocalSandboxClient, temp_dir: Path):
    """Tests volume binding in local sandbox."""
    bind_path = str(temp_dir)
    volume_bindings = {bind_path: "/data"}

    await local_client.create(volume_bindings=volume_bindings)

    test_file = temp_dir / "test.txt"
    test_file.write_text("Volume test")

    content = await local_client.read_file("/data/test.txt")
    assert "Volume test" in content


@pytest.mark.asyncio
async def test_local_error_handling(local_client: LocalSandboxClient):
    """Tests error handling in local sandbox."""
    await local_client.create()

    with pytest.raises(Exception) as exc:
        await local_client.read_file("/nonexistent.txt")
    assert "not found" in str(exc.value).lower()

    with pytest.raises(Exception) as exc:
        await local_client.copy_from("/nonexistent.txt", "local.txt")
    assert "not found" in str(exc.value).lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
