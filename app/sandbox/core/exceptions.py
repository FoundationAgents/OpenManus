"""Exception classes for the sandbox system.

This module defines custom exceptions used throughout the sandbox system to
handle various error conditions in a structured way.
"""


class SandboxError(Exception):
    """Base exception for sandbox-related errors."""


class SandboxTimeoutError(SandboxError):
    """Exception raised when a sandbox operation times out."""


class SandboxResourceError(SandboxError):
    """Exception raised for resource-related errors."""
