"""
Sandbox Adapters Module

Provides adapters for different sandbox backends:
- Local Docker (default)
- GitPod Self-Hosted
- E2B Open Source
- Firecracker VMs
"""

from .base import BaseSandboxAdapter
from .docker_adapter import DockerSandboxAdapter
from .e2b_adapter import E2BSandboxAdapter
from .factory import SandboxFactory
from .gitpod_adapter import GitPodSandboxAdapter

__all__ = [
    "BaseSandboxAdapter",
    "DockerSandboxAdapter",
    "GitPodSandboxAdapter",
    "E2BSandboxAdapter",
    "SandboxFactory",
]
