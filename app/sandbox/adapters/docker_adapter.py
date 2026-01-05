"""Docker-based sandbox adapter (using existing OpenManus Docker implementation)."""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...config import SandboxSettings
from ..core.manager import SandboxManager
from ..core.sandbox import DockerSandbox
from .base import BaseSandboxAdapter, ExecutionResult, SandboxInfo, SandboxStatus


class DockerSandboxAdapter(BaseSandboxAdapter):
    """Local Docker sandbox adapter using existing OpenManus implementation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Convert config dict to SandboxSettings if needed
        if isinstance(config, dict):
            sandbox_config = SandboxSettings(**config)
        else:
            sandbox_config = config or SandboxSettings()

        self.sandbox_config = sandbox_config
        self.manager = SandboxManager(
            max_sandboxes=100, idle_timeout=3600, cleanup_interval=300
        )
        self._docker_sandboxes: Dict[str, DockerSandbox] = {}

    async def create_sandbox(self, **kwargs) -> str:
        """Create Docker sandbox using existing implementation."""
        try:
            # Create sandbox using existing manager
            sandbox_id = await self.manager.create_sandbox(
                config=self.sandbox_config,
                volume_bindings=kwargs.get("volume_bindings"),
            )

            # Get the actual sandbox instance
            docker_sandbox = await self.manager.get_sandbox(sandbox_id)
            self._docker_sandboxes[sandbox_id] = docker_sandbox

            # Create sandbox info
            info = SandboxInfo(
                id=sandbox_id,
                status=SandboxStatus.RUNNING,
                image=self.sandbox_config.image,
                created_at=datetime.now().isoformat(),
                urls={},  # Docker doesn't expose external URLs by default
                metadata={
                    "backend": "docker",
                    "work_dir": self.sandbox_config.work_dir,
                    "memory_limit": self.sandbox_config.memory_limit,
                    "cpu_limit": self.sandbox_config.cpu_limit,
                },
            )

            self._update_sandbox_info(sandbox_id, info)
            return sandbox_id

        except Exception as e:
            raise RuntimeError(f"Failed to create Docker sandbox: {e}")

    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo:
        """Get Docker sandbox information."""
        if sandbox_id in self._active_sandboxes:
            return self._active_sandboxes[sandbox_id]
        else:
            raise ValueError(f"Sandbox {sandbox_id} not found")

    async def execute_command(
        self, sandbox_id: str, command: str, **kwargs
    ) -> ExecutionResult:
        """Execute command in Docker sandbox."""
        sandbox = self._docker_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        timeout = kwargs.get("timeout", self.sandbox_config.timeout)

        try:
            start_time = time.time()

            # Use existing DockerSandbox run_command method
            output = await sandbox.run_command(command, timeout=timeout)

            execution_time = time.time() - start_time

            return ExecutionResult(
                stdout=output,
                stderr="",  # DockerSandbox doesn't separate stderr
                exit_code=0,  # Assume success if no exception
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                stdout="", stderr=str(e), exit_code=1, execution_time=execution_time
            )

    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        """Write file to Docker sandbox."""
        sandbox = self._docker_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        await sandbox.write_file(path, content)

    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read file from Docker sandbox."""
        sandbox = self._docker_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        return await sandbox.read_file(path)

    async def list_files(self, sandbox_id: str, path: str = "/") -> List[str]:
        """List files in Docker sandbox directory."""
        result = await self.execute_command(sandbox_id, f"ls -la {path}", timeout=30)

        if result.exit_code != 0:
            raise FileNotFoundError(f"Directory {path} not found or not accessible")

        # Parse ls output to get file names
        lines = result.stdout.strip().split("\n")
        files = []
        for line in lines[1:]:  # Skip first line (total)
            if line.strip():
                parts = line.split()
                if len(parts) >= 9:
                    filename = " ".join(parts[8:])  # Handle filenames with spaces
                    if filename not in [".", ".."]:  # Skip . and ..
                        files.append(filename)

        return files

    async def start_sandbox(self, sandbox_id: str) -> None:
        """Start a stopped Docker sandbox."""
        # Docker containers are created in running state
        # This is a no-op for the existing implementation
        info = await self.get_sandbox_info(sandbox_id)
        info.status = SandboxStatus.RUNNING
        self._update_sandbox_info(sandbox_id, info)

    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop a running Docker sandbox."""
        sandbox = self._docker_sandboxes.get(sandbox_id)
        if sandbox:
            # The existing implementation doesn't have stop/start
            # We'll update the status only
            info = await self.get_sandbox_info(sandbox_id)
            info.status = SandboxStatus.STOPPED
            self._update_sandbox_info(sandbox_id, info)

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Completely destroy Docker sandbox."""
        try:
            # Clean up Docker sandbox using existing implementation
            if sandbox_id in self._docker_sandboxes:
                sandbox = self._docker_sandboxes[sandbox_id]
                await sandbox.cleanup()
                del self._docker_sandboxes[sandbox_id]

            # Remove from manager (use delete_sandbox, not remove_sandbox)
            await self.manager.delete_sandbox(sandbox_id)

            # Update status
            if sandbox_id in self._active_sandboxes:
                info = self._active_sandboxes[sandbox_id]
                info.status = SandboxStatus.DESTROYED
                self._remove_sandbox_info(sandbox_id)

        except Exception as e:
            raise RuntimeError(f"Failed to destroy Docker sandbox {sandbox_id}: {e}")
            raise RuntimeError(f"Failed to destroy Docker sandbox {sandbox_id}: {e}")
