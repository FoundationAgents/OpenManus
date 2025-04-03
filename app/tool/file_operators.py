"""File operation interfaces and implementations for local and sandbox environments."""

import asyncio
from pathlib import Path
from typing import Optional, Protocol, Tuple, Union, runtime_checkable

from app.config import SandboxSettings
from app.exceptions import ToolError
from app.sandbox.client import SANDBOX_CLIENT

PathLike = Union[str, Path]


@runtime_checkable
class FileOperator(Protocol):
    """Interface for file operations in different environments."""

    base_path: Path

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
    base_path: Path = None  # Will be set by StrReplaceEditor

    def _resolve_path(self, path: PathLike) -> Path:
        """Resolve path relative to base_path."""
        if self.base_path is None:
            raise ToolError(
                "base_path is not set. Please set base_path before using LocalFileOperator."
            )

        path = Path(path)
        # Convert Windows-style path to POSIX-style
        path_str = str(path).replace("\\", "/")

        if path_str.startswith("/workspace"):
            # For sandbox paths, use the full path as is
            resolved = Path(path_str)
        else:
            # For all other paths, join with base_path
            resolved = self.base_path / path_str

        # Ensure the directory exists
        resolved.parent.mkdir(parents=True, exist_ok=True)

        return resolved

    async def read_file(self, path: PathLike) -> str:
        """Read content from a local file."""
        try:
            resolved_path = self._resolve_path(path)
            return resolved_path.read_text(encoding=self.encoding)
        except Exception as e:
            raise ToolError(f"Failed to read {path}: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a local file."""
        try:
            resolved_path = self._resolve_path(path)
            resolved_path.write_text(content, encoding=self.encoding)
        except Exception as e:
            raise ToolError(f"Failed to write to {path}: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory."""
        resolved_path = self._resolve_path(path)
        return resolved_path.is_dir()

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists."""
        resolved_path = self._resolve_path(path)
        return resolved_path.exists()

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

    base_path: Path = Path("/workspace")

    def __init__(self):
        self.sandbox_client = SANDBOX_CLIENT

    def _resolve_path(self, path: PathLike) -> str:
        """Resolve path relative to base_path."""
        path = str(path)
        if path.startswith("/workspace"):
            return path  # Sandbox already uses /workspace as base
        return str(self.base_path / path)

    async def _ensure_sandbox_initialized(self):
        """Ensure sandbox is initialized."""
        if not self.sandbox_client.sandbox:
            await self.sandbox_client.create(config=SandboxSettings())

    async def read_file(self, path: PathLike) -> str:
        """Read content from a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            resolved_path = self._resolve_path(path)
            return await self.sandbox_client.read_file(resolved_path)
        except Exception as e:
            raise ToolError(f"Failed to read {path} in sandbox: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            resolved_path = self._resolve_path(path)
            await self.sandbox_client.write_file(resolved_path, content)
        except Exception as e:
            raise ToolError(f"Failed to write to {path} in sandbox: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory in sandbox."""
        await self._ensure_sandbox_initialized()
        resolved_path = self._resolve_path(path)
        result = await self.sandbox_client.run_command(
            f"test -d {resolved_path} && echo 'true' || echo 'false'"
        )
        return result.strip() == "true"

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists in sandbox."""
        await self._ensure_sandbox_initialized()
        resolved_path = self._resolve_path(path)
        result = await self.sandbox_client.run_command(
            f"test -e {resolved_path} && echo 'true' || echo 'false'"
        )
        return result.strip() == "true"

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
