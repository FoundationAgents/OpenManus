import pytest
import pytest_asyncio

from app.sandbox.core.sandbox import DockerSandbox, SandboxSettings


@pytest.fixture(scope="module")
def sandbox_config():
    """Creates sandbox configuration for testing."""
    return SandboxSettings(
        image="python:3.12-slim",
        work_dir="/workspace",
        memory_limit="1g",
        cpu_limit=0.5,
        network_enabled=True,
    )


@pytest_asyncio.fixture(scope="module")
async def sandbox(sandbox_config):
    """Creates and manages a test sandbox instance."""
    sandbox = DockerSandbox(sandbox_config)
    await sandbox.create()
    try:
        yield sandbox
    finally:
        await sandbox.cleanup()


@pytest.mark.asyncio
async def test_sandbox_working_directory(sandbox):
    """Tests sandbox working directory configuration."""
    result = await sandbox.terminal.run_command("pwd")
    assert result.strip() == "/workspace"


@pytest.mark.asyncio
async def test_sandbox_file_operations(sandbox):
    """Tests sandbox file read/write operations."""
    # Test file writing
    test_content = "Hello from sandbox!"
    await sandbox.write_file("/workspace/test.txt", test_content)

    # Test file reading
    content = await sandbox.read_file("/workspace/test.txt")
    assert content.strip() == test_content


@pytest.mark.asyncio
async def test_sandbox_python_execution(sandbox):
    """Tests Python code execution in sandbox."""
    # Write test file
    await sandbox.write_file("/workspace/test.txt", "Hello from file!")

    # Write Python script
    python_code = """
print("Hello from Python!")
with open('/workspace/test.txt') as f:
    print(f.read())
"""
    await sandbox.write_file("/workspace/test.py", python_code)

    # Execute script and verify output
    result = await sandbox.terminal.run_command("python3 /workspace/test.py")
    assert "Hello from Python!" in result
    assert "Hello from file!" in result


@pytest.mark.asyncio
async def test_sandbox_file_persistence(sandbox):
    """Tests file persistence in sandbox."""
    # Create multiple files
    files = {
        "file1.txt": "Content 1",
        "file2.txt": "Content 2",
        "nested/file3.txt": "Content 3",
    }

    # Write files
    for path, content in files.items():
        await sandbox.write_file(f"/workspace/{path}", content)

    # Verify file contents
    for path, expected_content in files.items():
        content = await sandbox.read_file(f"/workspace/{path}")
        assert content.strip() == expected_content


@pytest.mark.asyncio
async def test_sandbox_python_environment(sandbox):
    """Tests Python environment configuration."""
    # Test Python version
    result = await sandbox.terminal.run_command("python3 --version")
    assert "Python 3.10" in result

    # Test basic module imports
    python_code = """
import sys
import os
import json
print("Python is working!")
"""
    await sandbox.write_file("/workspace/env_test.py", python_code)
    result = await sandbox.terminal.run_command("python3 /workspace/env_test.py")
    assert "Python is working!" in result


@pytest.mark.asyncio
async def test_sandbox_network_access(sandbox):
    """Tests sandbox network access."""
    if not sandbox.config.network_enabled:
        pytest.skip("Network access is disabled")

    # Test network connectivity
    await sandbox.terminal.run_command("apt update && apt install curl -y")
    result = await sandbox.terminal.run_command("curl -I https://www.example.com")
    assert "HTTP/2 200" in result


@pytest.mark.asyncio
async def test_sandbox_cleanup(sandbox_config):
    """Tests sandbox cleanup process."""
    sandbox = DockerSandbox(sandbox_config)
    await sandbox.create()

    # Create test files
    await sandbox.write_file("/workspace/test.txt", "test")
    container_id = sandbox.terminal.container.id
    # Perform cleanup
    await sandbox.cleanup()

    # Verify container has been removed
    import docker

    client = docker.from_env()
    containers = client.containers.list(all=True)
    assert not any(c.id == container_id for c in containers)


@pytest.mark.asyncio
async def test_sandbox_error_handling():
    """Tests error handling with invalid configuration."""
    # Test invalid configuration
    invalid_config = SandboxSettings(image="nonexistent:latest", work_dir="/invalid")

    sandbox = DockerSandbox(invalid_config)
    with pytest.raises(Exception):
        await sandbox.create()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
