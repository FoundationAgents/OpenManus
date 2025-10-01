"""Unified client that works with any sandbox backend."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from .base import BaseSandboxAdapter, ExecutionResult, SandboxInfo
from .factory import SandboxFactory


class UnifiedSandboxClient:
    """Unified client for any sandbox backend."""

    def __init__(
        self, backend: Optional[str] = None, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize unified sandbox client.

        Args:
            backend: Specific backend to use, or None for auto-detection
            config: Backend-specific configuration
        """
        if backend:
            self.adapter: BaseSandboxAdapter = SandboxFactory.create_adapter(
                backend, config
            )
            self.backend_name = backend
        else:
            self.adapter: BaseSandboxAdapter = SandboxFactory.create_best_available(
                config
            )
            self.backend_name = SandboxFactory.auto_detect_backend(config)

        self.active_sandboxes: Dict[str, str] = {}

    @property
    def backend(self) -> str:
        """Get the current backend name."""
        return self.backend_name

    async def create_sandbox(self, **kwargs) -> str:
        """Create new sandbox.

        Args:
            **kwargs: Backend-specific creation parameters

        Returns:
            str: Sandbox ID
        """
        sandbox_id = await self.adapter.create_sandbox(**kwargs)
        self.active_sandboxes[sandbox_id] = sandbox_id
        return sandbox_id

    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo:
        """Get sandbox information.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            SandboxInfo: Sandbox information
        """
        return await self.adapter.get_sandbox_info(sandbox_id)

    async def execute(self, sandbox_id: str, command: str, **kwargs) -> ExecutionResult:
        """Execute command in sandbox.

        Args:
            sandbox_id: Sandbox identifier
            command: Command to execute
            **kwargs: Execution options (timeout, etc.)

        Returns:
            ExecutionResult: Command execution result
        """
        return await self.adapter.execute_command(sandbox_id, command, **kwargs)

    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        """Write file to sandbox.

        Args:
            sandbox_id: Sandbox identifier
            path: File path in sandbox
            content: File content
        """
        await self.adapter.write_file(sandbox_id, path, content)

    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read file from sandbox.

        Args:
            sandbox_id: Sandbox identifier
            path: File path in sandbox

        Returns:
            str: File content
        """
        return await self.adapter.read_file(sandbox_id, path)

    async def list_files(self, sandbox_id: str, path: str = "/") -> List[str]:
        """List files in sandbox directory.

        Args:
            sandbox_id: Sandbox identifier
            path: Directory path to list

        Returns:
            List[str]: List of file/directory names
        """
        return await self.adapter.list_files(sandbox_id, path)

    async def start_sandbox(self, sandbox_id: str) -> None:
        """Start a stopped sandbox.

        Args:
            sandbox_id: Sandbox identifier
        """
        await self.adapter.start_sandbox(sandbox_id)

    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop a running sandbox.

        Args:
            sandbox_id: Sandbox identifier
        """
        await self.adapter.stop_sandbox(sandbox_id)

    async def cleanup_sandbox(self, sandbox_id: str) -> None:
        """Clean up specific sandbox.

        Args:
            sandbox_id: Sandbox identifier
        """
        if sandbox_id in self.active_sandboxes:
            await self.adapter.destroy_sandbox(sandbox_id)
            del self.active_sandboxes[sandbox_id]

    async def cleanup_all(self) -> None:
        """Clean up all active sandboxes."""
        sandbox_ids = list(self.active_sandboxes.keys())

        # Clean up in parallel for efficiency
        cleanup_tasks = [self.cleanup_sandbox(sandbox_id) for sandbox_id in sandbox_ids]

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def list_sandboxes(self) -> List[SandboxInfo]:
        """List all active sandboxes.

        Returns:
            List[SandboxInfo]: List of sandbox information
        """
        return await self.adapter.list_sandboxes()

    @asynccontextmanager
    async def sandbox_context(self, **kwargs):
        """Context manager for automatic sandbox cleanup.

        Example:
            async with client.sandbox_context() as sandbox_id:
                result = await client.execute(sandbox_id, "echo 'Hello'")
                print(result.stdout)
            # Sandbox automatically cleaned up

        Args:
            **kwargs: Arguments passed to create_sandbox

        Yields:
            str: Sandbox ID
        """
        sandbox_id = await self.create_sandbox(**kwargs)
        try:
            yield sandbox_id
        finally:
            await self.cleanup_sandbox(sandbox_id)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup_all()

    def __repr__(self) -> str:
        """String representation."""
        return f"UnifiedSandboxClient(backend='{self.backend_name}', active_sandboxes={len(self.active_sandboxes)})"
