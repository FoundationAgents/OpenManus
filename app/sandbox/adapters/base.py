"""Base adapter interface for sandbox backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class SandboxStatus(Enum):
    """Sandbox status enumeration."""

    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class SandboxInfo:
    """Information about a sandbox instance."""

    id: str
    status: SandboxStatus
    image: str
    created_at: str
    urls: Dict[str, str] = None  # e.g. {"vnc": "http://...", "web": "http://..."}
    metadata: Dict[str, Any] = None


@dataclass
class ExecutionResult:
    """Result of command execution in sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    execution_time: float


class BaseSandboxAdapter(ABC):
    """Base interface for sandbox adapters."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._active_sandboxes: Dict[str, SandboxInfo] = {}

    @abstractmethod
    async def create_sandbox(self, **kwargs) -> str:
        """Create a new sandbox instance.

        Args:
            **kwargs: Backend-specific creation parameters

        Returns:
            str: Sandbox ID
        """
        pass

    @abstractmethod
    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo:
        """Get information about a sandbox."""
        pass

    @abstractmethod
    async def execute_command(
        self, sandbox_id: str, command: str, **kwargs
    ) -> ExecutionResult:
        """Execute command in sandbox."""
        pass

    @abstractmethod
    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        """Write file to sandbox."""
        pass

    @abstractmethod
    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read file from sandbox."""
        pass

    @abstractmethod
    async def list_files(self, sandbox_id: str, path: str = "/") -> List[str]:
        """List files in sandbox directory."""
        pass

    @abstractmethod
    async def start_sandbox(self, sandbox_id: str) -> None:
        """Start a stopped sandbox."""
        pass

    @abstractmethod
    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop a running sandbox."""
        pass

    @abstractmethod
    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Completely destroy a sandbox."""
        pass

    async def list_sandboxes(self) -> List[SandboxInfo]:
        """List all active sandboxes."""
        return list(self._active_sandboxes.values())

    async def cleanup_all(self) -> None:
        """Clean up all active sandboxes."""
        sandbox_ids = list(self._active_sandboxes.keys())
        for sandbox_id in sandbox_ids:
            try:
                await self.destroy_sandbox(sandbox_id)
            except Exception as e:
                print(f"Error cleaning up sandbox {sandbox_id}: {e}")

    def _update_sandbox_info(self, sandbox_id: str, info: SandboxInfo) -> None:
        """Update internal sandbox info cache."""
        self._active_sandboxes[sandbox_id] = info

    def _remove_sandbox_info(self, sandbox_id: str) -> None:
        """Remove sandbox from internal cache."""
        self._active_sandboxes.pop(sandbox_id, None)
