"""
Base abstractions for sandbox providers and the services they expose.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence


@dataclass
class SandboxMetadata:
    """Lightweight metadata describing the active sandbox session."""

    provider: str
    links: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShellCommandResult:
    """Result returned by shell service operations."""

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    session_name: Optional[str] = None
    completed: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShellService(ABC):
    """Abstract shell command execution service."""

    @abstractmethod
    async def execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = False,
        session: Optional[str] = None,
    ) -> ShellCommandResult:
        """Execute a command inside the sandbox."""

    async def check(self, session: str) -> ShellCommandResult:
        """Retrieve output for a long-running session."""
        raise NotImplementedError("check is not supported by this provider")

    async def terminate(self, session: str) -> ShellCommandResult:
        """Terminate a running session."""
        raise NotImplementedError("terminate is not supported by this provider")

    async def list_sessions(self) -> Sequence[str]:
        """List existing shell sessions."""
        raise NotImplementedError("list_sessions is not supported by this provider")


class FileService(ABC):
    """Abstract file management service."""

    @abstractmethod
    async def read(self, path: str) -> str:
        """Read file contents."""

    @abstractmethod
    async def write(self, path: str, content: str, *, overwrite: bool = True) -> None:
        """Write file contents."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file or directory."""

    @abstractmethod
    async def list(self, path: str) -> Sequence[Dict[str, Any]]:
        """List entries under a directory."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check whether a path exists."""


class BrowserService(ABC):
    """Abstract browser automation service."""

    async def initialize(self) -> None:
        """Initialize browser resources."""

    async def cleanup(self) -> None:
        """Release browser resources."""

    @abstractmethod
    async def perform_action(
        self, action: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a browser action and return structured response."""

    async def current_state(self) -> Dict[str, Any]:
        """Return current browser state snapshot."""
        raise NotImplementedError("current_state is not supported by this provider")


class VisionService(ABC):
    """Abstract vision service for reading images inside sandbox."""

    @abstractmethod
    async def read_image(self, path: str) -> Dict[str, Any]:
        """Read and encode an image file located inside sandbox."""


class ComputerService(ABC):
    """Abstract computer automation service for desktop interactions."""

    async def move_mouse(self, x: int, y: int) -> None:
        """Move mouse cursor to the given coordinates."""
        raise NotImplementedError("move_mouse is not supported by this provider")

    async def click_mouse(self, x: int, y: int, *, button: str, count: int = 1) -> None:
        """Click mouse at the given coordinates."""
        raise NotImplementedError("click_mouse is not supported by this provider")

    async def drag_mouse(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        *,
        button: str = "left",
    ) -> None:
        """Drag mouse from one coordinate to another."""
        raise NotImplementedError("drag_mouse is not supported by this provider")

    async def scroll(self, x: int, y: int, *, amount: int) -> None:
        """Scroll at the given coordinates. Positive amount scrolls up, negative scrolls down."""
        raise NotImplementedError("scroll is not supported by this provider")

    async def input_text(self, text: str) -> None:
        """Type text into the active element."""
        raise NotImplementedError("input_text is not supported by this provider")

    async def press_keys(self, keys: Sequence[str], *, hold: bool = False) -> None:
        """Press one or more keys simultaneously."""
        raise NotImplementedError("press_keys is not supported by this provider")

    async def release_keys(self, keys: Sequence[str]) -> None:
        """Release previously held keys."""
        raise NotImplementedError("release_keys is not supported by this provider")

    async def get_cursor_position(self) -> Dict[str, int]:
        """Return current cursor position."""
        raise NotImplementedError(
            "get_cursor_position is not supported by this provider"
        )

    async def get_screen_size(self) -> Dict[str, Any]:
        """Return screen size metadata."""
        raise NotImplementedError("get_screen_size is not supported by this provider")

    async def screenshot(self) -> Dict[str, Any]:
        """Capture a screenshot and return metadata (e.g., url/base64)."""
        raise NotImplementedError("screenshot is not supported by this provider")

    def supports_mouse_hold(self) -> bool:
        """Return True when provider can distinguish mouse down/up operations."""
        return False


class MobileService(ABC):
    """Abstract mobile automation service."""

    async def tap(self, x: int, y: int) -> None:
        raise NotImplementedError("tap is not supported by this provider")

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> None:
        raise NotImplementedError("swipe is not supported by this provider")

    async def input_text(self, text: str) -> None:
        raise NotImplementedError("input_text is not supported by this provider")

    async def send_key(self, key_code: int) -> None:
        raise NotImplementedError("send_key is not supported by this provider")

    async def screenshot(self) -> Dict[str, Any]:
        raise NotImplementedError("screenshot is not supported by this provider")

    async def get_clickable_ui_elements(self, timeout_ms: int = 2000) -> Dict[str, Any]:
        raise NotImplementedError(
            "get_clickable_ui_elements is not supported by this provider"
        )


class SandboxProvider(ABC):
    """Base class for sandbox providers."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare sandbox session resources."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Release sandbox session resources."""

    @abstractmethod
    def metadata(self) -> SandboxMetadata:
        """Return metadata describing the active sandbox."""

    @abstractmethod
    def shell_service(self) -> ShellService:
        """Return shell service instance."""

    @abstractmethod
    def file_service(self) -> FileService:
        """Return file service instance."""

    def browser_service(self) -> Optional[BrowserService]:
        """Return browser service instance if available."""
        return None

    def vision_service(self) -> Optional[VisionService]:
        """Return vision service instance if available."""
        return None

    def computer_service(self) -> Optional[ComputerService]:
        """Return computer automation service if available."""
        return None

    def mobile_service(self) -> Optional[MobileService]:
        """Return mobile automation service if available."""
        return None
