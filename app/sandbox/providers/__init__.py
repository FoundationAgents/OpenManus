"""
Sandbox provider abstractions and factory for switching between different backends.
"""

from .base import (
    BrowserService,
    ComputerService,
    FileService,
    MobileService,
    SandboxMetadata,
    SandboxProvider,
    ShellCommandResult,
    ShellService,
    VisionService,
)
from .factory import create_sandbox_provider


__all__ = [
    "SandboxMetadata",
    "SandboxProvider",
    "ShellCommandResult",
    "ShellService",
    "FileService",
    "BrowserService",
    "VisionService",
    "ComputerService",
    "MobileService",
    "create_sandbox_provider",
]
