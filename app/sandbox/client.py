import os
import sys
import shutil
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol

from app.config import SandboxSettings, PROJECT_ROOT
from app.sandbox.core.sandbox import DockerSandbox
from app.logger import logger

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


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
    async def run_command(self, command: str, timeout: Optional[int] = None) -> str:
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


class LocalShellSession:
    """An interactive shell session running locally on the host, emulating container bash."""

    def __init__(self, cwd: str, env_vars: Optional[Dict[str, str]] = None, timeout: float = 120.0):
        self.cwd = cwd
        self.env_vars = env_vars or {}
        self._started = False
        self._timed_out = False
        self._sentinel = "<<exit>>"
        self._timeout = timeout

    async def start(self):
        if self._started:
            return

        # Find available shell
        shell_cmd = "bash"
        if not shutil.which(shell_cmd):
            shell_cmd = "sh"

        env = os.environ.copy()
        env.update(self.env_vars)
        env["PYTHONUNBUFFERED"] = "1"
        env["TERM"] = "dumb"

        kwargs = {
            "shell": True,
            "bufsize": 0,
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.STDOUT,  # Merge stderr into stdout for terminal emulation
            "cwd": self.cwd,
            "env": env,
        }
        if sys.version_info >= (3, 11):
            kwargs["process_group"] = 0
        elif hasattr(os, "setsid"):
            # Note: preexec_fn is not thread-safe and can lead to deadlocks in multi-threaded programs.
            # It is only used here as a best-effort process grouping fallback for legacy Python versions.
            kwargs["preexec_fn"] = os.setsid

        self._process = await asyncio.create_subprocess_shell(
            shell_cmd,
            **kwargs
        )
        self._started = True

    def stop(self):
        if not self._started:
            return
        if self._process.returncode is not None:
            return
        try:
            self._process.terminate()
        except Exception:
            pass

    async def run(self, command: str, timeout: Optional[int] = None) -> str:
        if not self._started:
            raise RuntimeError("Session has not started.")
        if self._process.returncode is not None:
            raise RuntimeError(f"Shell has exited with returncode {self._process.returncode}")
        if self._timed_out:
            raise RuntimeError("Shell session timed out previously and must be restarted.")

        # Timeout handling
        exec_timeout = timeout or self._timeout

        # Send command and print a sentinel
        self._process.stdin.write(
            command.encode() + f"\necho -n '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # Read output until the sentinel is found using the standard readuntil API
        try:
            if sys.version_info >= (3, 11):
                async with asyncio.timeout(exec_timeout):
                    data = await self._process.stdout.readuntil(self._sentinel.encode())
            else:
                data = await asyncio.wait_for(self._process.stdout.readuntil(self._sentinel.encode()), exec_timeout)
            output = data[:-len(self._sentinel)].decode("utf-8", errors="replace")
        except (asyncio.TimeoutError, TimeoutError):
            self._timed_out = True
            raise TimeoutError(f"Command execution timed out after {exec_timeout} seconds") from None

        if output.endswith("\n"):
            output = output[:-1]
        if output.endswith("\r"):
            output = output[:-1]

        return output


class LocalSubprocessSandboxClient(BaseSandboxClient):
    """Local subprocess-based sandbox client implementation to support environments without Docker (e.g. Android/Termux)."""

    def __init__(self):
        self.sandbox_dir: Optional[str] = None
        self.session: Optional[LocalShellSession] = None
        self.config: Optional[SandboxSettings] = None

    async def create(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
    ) -> None:
        self.config = config or SandboxSettings()
        self.sandbox_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "workspace", "sandbox"))
        os.makedirs(self.sandbox_dir, exist_ok=True)
        
        # Initialize terminal/shell session
        self.session = LocalShellSession(
            self.sandbox_dir, 
            env_vars={"PYTHONUNBUFFERED": "1"}, 
            timeout=float(self.config.timeout)
        )
        await self.session.start()

    def _safe_resolve_path(self, path: str) -> str:
        normalized_rel_path = os.path.normpath(path)
        if os.path.isabs(normalized_rel_path):
            drive, path_without_drive = os.path.splitdrive(normalized_rel_path)
            normalized_rel_path = path_without_drive.lstrip(os.path.sep)

        resolved = os.path.abspath(os.path.join(self.sandbox_dir, normalized_rel_path))
        sandbox_dir_abs = os.path.abspath(self.sandbox_dir)
        if not resolved.startswith(sandbox_dir_abs):
            raise ValueError(f"Path traversal attempt detected: {path}")
        return resolved

    def _copy_dir_or_file(self, src: str, dst: str) -> None:
        if os.path.isdir(src):
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    # Note: dirs_exist_ok is supported in Python 3.8+ (OpenManus requires Python 3.12+)
                    shutil.copytree(src, os.path.join(dst, os.path.basename(src)), dirs_exist_ok=True)
                else:
                    raise RuntimeError(f"Cannot copy directory to a file: {dst}")
            else:
                shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    async def run_command(self, command: str, timeout: Optional[int] = None) -> str:
        if not self.session:
            raise RuntimeError("Sandbox not initialized")
        return await self.session.run(command, timeout)

    async def copy_from(self, container_path: str, local_path: str) -> None:
        src_path = self._safe_resolve_path(container_path)
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file not found: {container_path}")
        parent_dir = os.path.dirname(local_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self._copy_dir_or_file(src_path, local_path)

    async def copy_to(self, local_path: str, container_path: str) -> None:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Source file not found: {local_path}")
        dst_path = self._safe_resolve_path(container_path)
        parent_dir = os.path.dirname(dst_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self._copy_dir_or_file(local_path, dst_path)

    async def read_file(self, path: str) -> str:
        resolved = self._safe_resolve_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {path}")
        if HAS_AIOFILES:
            async with aiofiles.open(resolved, mode="r", encoding="utf-8", errors="replace") as f:
                return await f.read()
        else:
            with open(resolved, mode="r", encoding="utf-8", errors="replace") as f:
                return f.read()

    async def write_file(self, path: str, content: str) -> None:
        resolved = self._safe_resolve_path(path)
        parent_dir = os.path.dirname(resolved)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if HAS_AIOFILES:
            async with aiofiles.open(resolved, mode="w", encoding="utf-8") as f:
                await f.write(content)
        else:
            with open(resolved, mode="w", encoding="utf-8") as f:
                f.write(content)

    async def cleanup(self) -> None:
        if self.session:
            self.session.stop()
            self.session = None


class LocalSandboxClient(BaseSandboxClient):
    """Local sandbox client implementation with automatic local subprocess fallback when Docker is unavailable."""

    def __init__(self):
        """Initializes local sandbox client."""
        self.sandbox: Optional[BaseSandboxClient] = None

    async def create(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
    ) -> None:
        """Creates a sandbox with Docker or local subprocess fallback.

        Args:
            config: Sandbox configuration.
            volume_bindings: Volume mappings.

        Raises:
            RuntimeError: If sandbox creation fails.
        """
        try:
            import docker
            client = docker.from_env()
            try:
                client.ping()
            finally:
                client.close()
            self.sandbox = DockerSandbox(config, volume_bindings)
            await self.sandbox.create()
            logger.info("Initialized Docker sandbox client successfully.")
        except Exception as e:
            logger.warning(
                f"Docker sandbox client creation failed (e.g. running on Android/Termux without root/Docker): {e}. "
                "Falling back to Local Subprocess Sandbox Client. Note: Local Subprocess Sandbox provides "
                "directory-level isolation within 'workspace/sandbox' but does not isolate processes, memory, "
                "or network. Use caution when running untrusted tasks."
            )
            self.sandbox = LocalSubprocessSandboxClient()
            await self.sandbox.create(config, volume_bindings)

    async def run_command(self, command: str, timeout: Optional[int] = None) -> str:
        """Runs command in sandbox.

        Args:
            command: Command to execute.
            timeout: Execution timeout in seconds.

        Returns:
            Command output.

        Raises:
            RuntimeError: If sandbox not initialized.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
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
        if self.sandbox:
            await self.sandbox.cleanup()
            self.sandbox = None


def create_sandbox_client() -> LocalSandboxClient:
    """Creates a sandbox client.

    Returns:
        LocalSandboxClient: Sandbox client instance.
    """
    return LocalSandboxClient()


SANDBOX_CLIENT = create_sandbox_client()
