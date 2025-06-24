from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol, Any # Add Any

from app.config import SandboxSettings
from app.logger import logger
from app.sandbox.core.sandbox import DockerSandbox


class SandboxFileOperations(Protocol):
    """Protocol for sandbox file operations."""

    async def copy_from(self, container_path: str, local_path: str) -> None:
        """Copies file from container to local.

        Args:
            container_path: File path in container.
            local_path: Local destination path.
        """
        ...

    async def copy_to(self, local_path: str, container_path: str) -> None:
        """Copies file from local to container.

        Args:
            local_path: Local source file path.
            container_path: Destination path in container.
        """
        ...

    async def read_file(self, path: str) -> str:
        """Reads file content from container.

        Args:
            path: File path in container.

        Returns:
            str: File content.
        """
        ...

    async def write_file(self, path: str, content: str) -> None:
        """Writes content to file in container.

        Args:
            path: File path in container.
            content: Content to write.
        """
        ...


class BaseSandboxClient(ABC):
    """Base sandbox client interface."""

    @abstractmethod
    async def create(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
    ) -> None:
        """Creates sandbox."""

    @abstractmethod
    async def run_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Executes command."""

    @abstractmethod
    async def copy_from(self, container_path: str, local_path: str) -> None:
        """Copies file from container."""

    @abstractmethod
    async def copy_to(self, local_path: str, container_path: str) -> None:
        """Copies file to container."""

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Reads file."""

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """Writes file."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleans up resources."""


class LocalSandboxClient(BaseSandboxClient):
    """Local sandbox client implementation."""

    def __init__(self):
        """Initializes local sandbox client."""
        self.sandbox: Optional[DockerSandbox] = None

    async def create(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
    ) -> None:
        """Creates a sandbox.

        Args:
            config: Sandbox configuration.
            volume_bindings: Volume mappings.

        Raises:
            RuntimeError: If sandbox creation fails.
        """
        self.sandbox = DockerSandbox(config, volume_bindings)
        await self.sandbox.create()

    async def run_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Runs command in sandbox.

        Args:
            command: Command to execute.
            timeout: Execution timeout in seconds.

        Returns:
            A dictionary containing "exit_code", "stdout", and "stderr".

        Raises:
            RuntimeError: If sandbox not initialized or command execution fails.
            SandboxTimeoutError: If the command times out.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        # This will now return the dictionary {"exit_code": ..., "stdout": ..., "stderr": ...}
        # Exceptions like SandboxTimeoutError or RuntimeError (for other exec failures)
        # will be propagated from self.sandbox.run_command
        return await self.sandbox.run_command(command, timeout)

    async def copy_from(self, container_path: str, local_path: str) -> None:
        """Copies file from container to local.

        Args:
            container_path: File path in container.
            local_path: Local destination path.

        Raises:
            RuntimeError: If sandbox not initialized.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        await self.sandbox.copy_from(container_path, local_path)

    async def copy_to(self, local_path: str, container_path: str) -> None:
        """Copies file from local to container.

        Args:
            local_path: Local source file path.
            container_path: Destination path in container.

        Raises:
            RuntimeError: If sandbox not initialized.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        await self.sandbox.copy_to(local_path, container_path)

    async def read_file(self, path: str) -> str:
        """Reads file from container.

        Args:
            path: File path in container.

        Returns:
            File content.

        Raises:
            RuntimeError: If sandbox not initialized.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        return await self.sandbox.read_file(path)

    async def write_file(self, path: str, content: str) -> None:
        """Writes file to container.

        Args:
            path: File path in container.
            content: File content.

        Raises:
            RuntimeError: If sandbox not initialized.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        await self.sandbox.write_file(path, content)

    async def cleanup(self) -> None:
        """Cleans up resources."""
        logger.info("LocalSandboxClient.cleanup: Starting...")
        if self.sandbox:
            logger.info("LocalSandboxClient.cleanup: About to call self.sandbox.cleanup()")
            await self.sandbox.cleanup()
            logger.info("LocalSandboxClient.cleanup: self.sandbox.cleanup() completed.")
            self.sandbox = None
            logger.info("LocalSandboxClient.cleanup: self.sandbox set to None.")
        logger.info("LocalSandboxClient.cleanup: Finished.")


def create_sandbox_client() -> LocalSandboxClient:
    """Creates a sandbox client.

    Returns:
        LocalSandboxClient: Sandbox client instance.
    """
    return LocalSandboxClient()


SANDBOX_CLIENT = create_sandbox_client()
