"""File operation interfaces and implementations for local and sandbox environments."""

import asyncio
from pathlib import Path
from typing import Optional, Protocol, Tuple, Union, runtime_checkable

from app.config import SandboxSettings
from app.exceptions import ToolError
from app.sandbox.client import SANDBOX_CLIENT
from app.task_context import get_current_sandbox


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


class LocalFileOperator(FileOperator):
    """File operations implementation for local filesystem."""

    encoding: str = "utf-8"

    async def read_file(self, path: PathLike) -> str:
        """Read content from a local file."""
        try:
            return Path(path).read_text(encoding=self.encoding)
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
        return Path(path).is_dir()

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists."""
        return Path(path).exists()

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
                pass
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds"
            ) from exc


class SandboxFileOperator(FileOperator):
    """File operations implementation for sandbox environment."""

    def __init__(self):
        self.sandbox_client = SANDBOX_CLIENT

    async def _ensure_sandbox_initialized(self):
        """Ensure sandbox is initialized."""
        if get_current_sandbox() is not None:
            return
        if not self.sandbox_client.sandbox:
            await self.sandbox_client.create(config=SandboxSettings())

    async def read_file(self, path: PathLike) -> str:
        """Read content from a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            current_sandbox = get_current_sandbox()
            if current_sandbox is not None:
                return await current_sandbox.read_file(str(path))
            return await self.sandbox_client.read_file(str(path))
        except Exception as e:
            raise ToolError(f"Failed to read {path} in sandbox: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            current_sandbox = get_current_sandbox()
            if current_sandbox is not None:
                await current_sandbox.write_file(str(path), content)
                return
            await self.sandbox_client.write_file(str(path), content)
        except Exception as e:
            raise ToolError(f"Failed to write to {path} in sandbox: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory in sandbox."""
        await self._ensure_sandbox_initialized()
        current_sandbox = get_current_sandbox()
        if current_sandbox is not None:
            return await current_sandbox.is_directory(str(path))
        result = await self.sandbox_client.run_command(
            f"test -d {path} && echo 'true' || echo 'false'"
        )
        return result.strip() == "true"

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists in sandbox."""
        await self._ensure_sandbox_initialized()
        current_sandbox = get_current_sandbox()
        if current_sandbox is not None:
            return await current_sandbox.exists(str(path))
        result = await self.sandbox_client.run_command(
            f"test -e {path} && echo 'true' || echo 'false'"
        )
        return result.strip() == "true"

    async def run_command(
        self, cmd: str, timeout: Optional[float] = 120.0
    ) -> Tuple[int, str, str]:
        """Run a command in sandbox environment."""
        await self._ensure_sandbox_initialized()
        try:
            current_sandbox = get_current_sandbox()
            if current_sandbox is not None:
                return_code, stdout, stderr = await current_sandbox.run(
                    cmd, timeout=int(timeout) if timeout else None
                )
                return return_code, stdout, stderr
            stdout = await self.sandbox_client.run_command(
                cmd, timeout=int(timeout) if timeout else None
            )
            return (
                0,  # Always return 0 since we don't have explicit return code from sandbox
                stdout,
                "",  # No stderr capture in the current sandbox implementation
            )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds in sandbox"
            ) from exc
        except Exception as exc:
            return 1, "", f"Error executing command in sandbox: {str(exc)}"
