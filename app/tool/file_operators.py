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

    async def create_directory(self, path: PathLike) -> None:
        """Creates a new directory at the given path."""
        ...

    async def rename(self, src: PathLike, dst: PathLike) -> None:
        """Renames/moves 'src' to 'dst' without overwriting if 'dst' already exists."""
        ...

    async def delete(self, path: PathLike) -> None:
        """Deletes the file or empty directory if `path` is a file."""
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
        """Writes content to a file. If the directory does not exist, it will be created."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
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

    async def create_directory(self, path: PathLike) -> None:
        """
        Creates a new directory at the given path.
        Raises an error if the directory already exists.
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=False)
        except Exception as e:
            raise ToolError(f"Failed to create directory {path}: {str(e)}") from None

    async def rename(self, src: PathLike, dst: PathLike) -> None:
        """
        Renames/moves 'src' to 'dst' without overwriting if 'dst' already exists.
        Raises error if the destination already exists.
        """
        source = Path(src)
        destination = Path(dst)

        # Check that source exists
        if not source.exists():
            raise ToolError(f"Cannot rename '{src}': source does not exist.")

        # Check that destination does NOT exist
        if destination.exists():
            raise ToolError(
                f"Cannot rename '{src}' to '{dst}': destination already exists."
            )

        try:
            source.rename(destination)
        except Exception as e:
            raise ToolError(f"Failed to rename '{src}' to '{dst}': {str(e)}") from None

    async def delete(self, path: PathLike) -> None:
        """
        Deletes the file if `path` is a file.
        Deletes the directory ONLY if it is empty.
        The name must match exactly (p.name == Path(path).name).
        """
        p = Path(path)

        # 1) Check if it exists.
        if not p.exists():
            raise ToolError(f"Cannot delete '{path}': does not exist.")

        # 2) Verify that the name matches exactly (no extra resolution).
        if p.name != Path(path).name:
            raise ToolError(f"Name mismatch: '{p.name}' != '{Path(path).name}'")

        try:
            # 3) If it's a directory, check if it is empty.
            if p.is_dir():
                contents = list(p.iterdir())
                if contents:
                    raise ToolError(f"Directory '{path}' is not empty. Cannot delete.")
                p.rmdir()
            else:
                # Assume it's a file.
                p.unlink()
        except Exception as e:
            raise ToolError(f"Failed to delete '{path}': {str(e)}") from None


class SandboxFileOperator(FileOperator):
    """File operations implementation for sandbox environment."""

    def __init__(self):
        self.sandbox_client = SANDBOX_CLIENT

    async def _ensure_sandbox_initialized(self):
        """Ensure sandbox is initialized."""
        if not self.sandbox_client.sandbox:
            await self.sandbox_client.create(config=SandboxSettings())

    async def read_file(self, path: PathLike) -> str:
        """Read content from a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            return await self.sandbox_client.read_file(str(path))
        except Exception as e:
            raise ToolError(f"Failed to read {path} in sandbox: {str(e)}") from None

    async def write_file(self, path: PathLike, content: str) -> None:
        """Write content to a file in sandbox."""
        await self._ensure_sandbox_initialized()
        try:
            await self.sandbox_client.write_file(str(path), content)
        except Exception as e:
            raise ToolError(f"Failed to write to {path} in sandbox: {str(e)}") from None

    async def is_directory(self, path: PathLike) -> bool:
        """Check if path points to a directory in sandbox."""
        await self._ensure_sandbox_initialized()
        result = await self.sandbox_client.run_command(
            f"test -d {path} && echo 'true' || echo 'false'"
        )
        return result.strip() == "true"

    async def exists(self, path: PathLike) -> bool:
        """Check if path exists in sandbox."""
        await self._ensure_sandbox_initialized()
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

    async def create_directory(self, path: PathLike) -> None:
        """
        Creates a new directory at the given path in the sandbox.
        Fails if the directory (or any file) already exists at that path,
        mirroring the local operator's behavior with exist_ok=False.
        """
        await self._ensure_sandbox_initialized()

        # 1) Check if there's already something at 'path'
        exists_cmd = f"test -e {path} && echo 'true' || echo 'false'"
        result = await self.sandbox_client.run_command(exists_cmd)
        if result.strip() == "true":
            # Something exists => fail
            raise ToolError(
                f"Cannot create directory {path}: it already exists in sandbox."
            )

        # 2) Actually create the directory ('-p' here -> create parents).
        mkdir_cmd = f"mkdir -p {path}"
        try:
            await self.sandbox_client.run_command(mkdir_cmd)
        except Exception as e:
            raise ToolError(
                f"Failed to create directory {path} in sandbox: {str(e)}"
            ) from None

    async def rename(self, src: PathLike, dst: PathLike) -> None:
        """
        Renames/moves 'src' to 'dst' within the sandbox, without overwriting if 'dst' exists.
        Raises ToolError if the destination already exists.
        """
        await self._ensure_sandbox_initialized()

        # 1) Check if source exists
        src_exists_cmd = f"test -e {src} && echo 'true' || echo 'false'"
        src_exists_out = await self.sandbox_client.run_command(src_exists_cmd)
        if src_exists_out.strip() != "true":
            raise ToolError(f"Cannot rename '{src}': source does not exist in sandbox.")

        # 2) Check if destination already exists
        dst_exists_cmd = f"test -e {dst} && echo 'true' || echo 'false'"
        dst_exists_out = await self.sandbox_client.run_command(dst_exists_cmd)
        if dst_exists_out.strip() == "true":
            raise ToolError(
                f"Cannot rename '{src}' to '{dst}' in sandbox: destination already exists."
            )

        # 3) Do the move
        mv_cmd = f"mv {src} {dst}"
        try:
            await self.sandbox_client.run_command(mv_cmd)
        except Exception as e:
            raise ToolError(
                f"Failed to rename '{src}' to '{dst}' in sandbox: {str(e)}"
            ) from None

    async def delete(self, path: PathLike) -> None:
        """
        Deletes the file if it is not a directory.
        Deletes the directory ONLY if it is empty.
        The name must match exactly (p.name == Path(path).name).
        """
        await self._ensure_sandbox_initialized()

        # 1) Check if it exists.
        exists_cmd = f"test -e {path} && echo 'true' || echo 'false'"
        result = await self.sandbox_client.run_command(exists_cmd)
        if result.strip() != "true":
            raise ToolError(f"Cannot delete '{path}': does not exist in sandbox.")

        # 2) Verify the exact name (via 'basename' in shell) to match Path(path).name
        basename_cmd = f"basename {path}"
        base_name = (await self.sandbox_client.run_command(basename_cmd)).strip()
        if base_name != Path(path).name:
            raise ToolError(
                f"Name mismatch in sandbox: '{base_name}' != '{Path(path).name}'"
            )

        # 3) Determine if it's a directory or a file.
        isdir_cmd = f"test -d {path} && echo 'true' || echo 'false'"
        is_dir = (await self.sandbox_client.run_command(isdir_cmd)).strip() == "true"

        if is_dir:
            # Check if directory is empty.
            ls_cmd = f"ls -A {path}"
            ls_out = await self.sandbox_client.run_command(ls_cmd)
            if ls_out.strip():
                # Not empty.
                raise ToolError(
                    f"Directory '{path}' in sandbox is not empty. Cannot delete."
                )

            # It's empty, so we can remove it with rmdir.
            rm_cmd = f"rmdir {path}"
        else:
            # It's a file.
            rm_cmd = f"rm {path}"

        # Execute final removal command.
        try:
            await self.sandbox_client.run_command(rm_cmd)
        except Exception as e:
            raise ToolError(f"Failed to delete '{path}' in sandbox: {str(e)}") from None
