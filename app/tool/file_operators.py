"""File operation interfaces and implementations for local and sandbox environments."""

import asyncio
from pathlib import Path
from typing import Optional, Protocol, Tuple, Union, runtime_checkable

# Ensure these are imported only once and correctly
from app.config import SandboxSettings, config # Ensure 'config' is imported
from app.exceptions import ToolError
from app.sandbox.client import SANDBOX_CLIENT
from app.logger import logger # Ensure logger is imported

PathLike = Union[str, Path]


@runtime_checkable
class FileOperator(Protocol):
    """Interface for file operations in different environments."""

    async def read_file(self, path: PathLike) -> str:
        """Read content from a file."""
        ...

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a file."""
        ...

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory."""
        ...

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists."""
        ...

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Run a shell command and return (return_code, stdout, stderr)."""
        ...

    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Translate a host path to its equivalent in the sandbox if applicable."""
        raise NotImplementedError


class LocalFileOperator(FileOperator):
    """File operations implementation for local filesystem."""

    encoding: str = "utf-8"

    async def read_file(self, path: PathLike) -> str:
        """Read content from a local file."""
        try:
            content = Path(path).read_text(encoding=self.encoding)
            return content
        except Exception as e:
            raise ToolError(f"Failed to read {path}: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a local file."""
        try:
            Path(path).write_text(content, encoding=self.encoding)
        except Exception as e:
            raise ToolError(f"Failed to write to {path}: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory."""
        result = Path(path).is_dir()
        return result

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists."""
        result = Path(path).exists()
        return result

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Run a shell command locally."""
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                process.returncode or 0,
                stdout.decode(),
                stderr.decode(),
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass # Process already terminated
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds"
            ) from exc
        
    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Local operator does not translate to sandbox paths, returns original."""
        return str(host_path)


class SandboxFileOperator(FileOperator):
    """File operations implementation for sandbox environment."""

    SANDBOX_WORKSPACE_PATH = "/workspace" # Standard sandbox workspace

    def __init__(self):
        self.sandbox_client = SANDBOX_CLIENT
        self.host_workspace_root = Path(config.workspace_root).resolve()

    def _translate_to_sandbox_path(self, host_path: PathLike) -> str:
        """Translate an absolute host path to its corresponding sandbox path."""
        resolved_host_path = Path(host_path).resolve()
        try:
            relative_path = resolved_host_path.relative_to(self.host_workspace_root)
        except ValueError as e:
            raise ToolError(
                f"Path '{host_path}' is not within the configured host workspace "
                f"'{self.host_workspace_root}'. Cannot translate to sandbox path."
            ) from e
        sandbox_path = Path(self.SANDBOX_WORKSPACE_PATH) / relative_path
        return str(sandbox_path)

    async def get_sandbox_path(self, host_path: PathLike) -> str:
        """Public method to get the translated sandbox path."""
        translated_path = self._translate_to_sandbox_path(host_path)
        return translated_path

    async def _ensure_sandbox_initialized(self):
        """Ensure sandbox is initialized."""
        if not self.sandbox_client.sandbox:
            await self.sandbox_client.create(config=SandboxSettings())

    async def read_file(self, path: PathLike) -> str:
        """Read content from a file in sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        try:
            content = await self.sandbox_client.read_file(sandbox_path)
            return content
        except Exception as e:
            raise ToolError(f"Failed to read {sandbox_path} in sandbox: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a file in sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        try:
            await self.sandbox_client.write_file(sandbox_path, content)
        except Exception as e:
            raise ToolError(f"Failed to write to {sandbox_path} in sandbox: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory in sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        cmd_str = f"test -d {sandbox_path} && echo 'true' || echo 'false'"
        result_str = await self.sandbox_client.run_command(cmd_str)
        result_bool = result_str.strip().lower() == "true" # Ensure lowercase comparison
        return result_bool

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists in sandbox."""
        await self._ensure_sandbox_initialized()
        sandbox_path = self._translate_to_sandbox_path(path)
        cmd_str = f"test -e {sandbox_path} && echo 'true' || echo 'false'"
        result_str = await self.sandbox_client.run_command(cmd_str)
        result_bool = result_str.strip().lower() == "true" # Ensure lowercase comparison
        return result_bool

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Run a command in sandbox environment."""
        await self._ensure_sandbox_initialized()
        try:
            stdout = await self.sandbox_client.run_command(
                cmd, timeout=int(timeout) if timeout else None
            )
            return (
                0,
                stdout,
                "", 
            )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds in sandbox"
            ) from exc
        except Exception as exc:
            return 1, "", f"Error executing command in sandbox: {str(exc)}"
