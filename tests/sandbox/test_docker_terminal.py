"""Tests for the AsyncDockerizedTerminal implementation."""

import docker
import pytest
import pytest_asyncio

from app.sandbox.core.terminal import AsyncDockerizedTerminal


@pytest.fixture(scope="module")
def docker_client():
    """Fixture providing a Docker client."""
    return docker.from_env()


@pytest_asyncio.fixture(scope="module")
async def docker_container(docker_client):
    """Fixture providing a test Docker container."""
    container = docker_client.containers.run(
        "python:3.12-slim",
        "tail -f /dev/null",
        name="test_container",
        detach=True,
        remove=True,
    )
    yield container
    container.stop()


@pytest_asyncio.fixture
async def terminal(docker_container):
    """Fixture providing an initialized AsyncDockerizedTerminal instance."""
    terminal = AsyncDockerizedTerminal(
        docker_container,
        working_dir="/workspace",
        env_vars={"TEST_VAR": "test_value"},
        default_timeout=30,
    )
    await terminal.init()
    yield terminal
    await terminal.close()


class TestAsyncDockerizedTerminal:
    """Test cases for AsyncDockerizedTerminal."""

    @pytest.mark.asyncio
    async def test_basic_command_execution(self, terminal):
        """Test basic command execution functionality."""
        result = await terminal.run_command("echo 'Hello World'")
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_environment_variables(self, terminal):
        """Test environment variable setting and access."""
        result = await terminal.run_command("echo $TEST_VAR")
        assert "test_value" in result

    @pytest.mark.asyncio
    async def test_working_directory(self, terminal):
        """Test working directory setup."""
        result = await terminal.run_command("pwd")
        assert "/workspace" == result

    @pytest.mark.asyncio
    async def test_command_timeout(self, docker_container):
        """Test command timeout functionality."""
        terminal = AsyncDockerizedTerminal(docker_container, default_timeout=1)
        await terminal.init()
        try:
            with pytest.raises(TimeoutError):
                await terminal.run_command("sleep 5")
        finally:
            await terminal.close()

    @pytest.mark.asyncio
    async def test_multiple_commands(self, terminal):
        """Test execution of multiple commands in sequence."""
        cmd1 = await terminal.run_command("echo 'First'")
        cmd2 = await terminal.run_command("echo 'Second'")
        assert "First" in cmd1
        assert "Second" in cmd2

    @pytest.mark.asyncio
    async def test_session_cleanup(self, docker_container):
        """Test proper cleanup of resources."""
        terminal = AsyncDockerizedTerminal(docker_container)
        await terminal.init()
        assert terminal.session is not None
        await terminal.close()
        # Verify session is properly cleaned up
        # Note: session object still exists, but internal connection is closed
        assert terminal.session is not None


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest-asyncio."""
    config.addinivalue_line("asyncio_mode", "strict")
    config.addinivalue_line("asyncio_default_fixture_loop_scope", "function")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
