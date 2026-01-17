"""Sandbox factory for creating appropriate adapter instances."""

import os
from typing import Any, Dict, Optional

from .base import BaseSandboxAdapter
from .docker_adapter import DockerSandboxAdapter
from .e2b_adapter import E2BSandboxAdapter
from .gitpod_adapter import GitPodSandboxAdapter


class SandboxFactory:
    """Factory for creating sandbox adapters."""

    # Registry of available adapters
    _adapters = {
        "docker": DockerSandboxAdapter,
        "gitpod": GitPodSandboxAdapter,
        "e2b": E2BSandboxAdapter,
    }

    @classmethod
    def register_adapter(cls, name: str, adapter_class: type) -> None:
        """Register a new adapter type.

        Args:
            name: Adapter identifier
            adapter_class: Adapter class that inherits from BaseSandboxAdapter
        """
        if not issubclass(adapter_class, BaseSandboxAdapter):
            raise ValueError(f"Adapter class must inherit from BaseSandboxAdapter")

        cls._adapters[name] = adapter_class

    @classmethod
    def get_available_adapters(cls) -> list:
        """Get list of available adapter names."""
        return list(cls._adapters.keys())

    @classmethod
    def create_adapter(
        cls, backend: str = "docker", config: Optional[Dict[str, Any]] = None
    ) -> BaseSandboxAdapter:
        """Create sandbox adapter based on backend type.

        Args:
            backend: Backend type ('docker', 'gitpod', 'e2b')
            config: Backend-specific configuration dictionary

        Returns:
            Configured sandbox adapter

        Raises:
            ValueError: If backend is not supported
            ImportError: If required dependencies are missing
        """
        backend = backend.lower()

        if backend not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(
                f"Unsupported sandbox backend: {backend}. "
                f"Available backends: {available}"
            )

        adapter_class = cls._adapters[backend]

        try:
            return adapter_class(config)
        except ImportError as e:
            raise ImportError(
                f"Failed to create {backend} adapter: {e}. "
                f"Make sure required dependencies are installed."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize {backend} adapter: {e}")

    @classmethod
    def create_from_env(
        cls, config: Optional[Dict[str, Any]] = None
    ) -> BaseSandboxAdapter:
        """Create adapter based on environment variables.

        Environment variables:
            SANDBOX_BACKEND: Backend type (default: docker)
            E2B_API_KEY: E2B API key (for e2b backend)
            GITPOD_TOKEN: GitPod API token (for gitpod backend)
            GITPOD_URL: GitPod server URL (for gitpod backend)

        Args:
            config: Additional configuration to merge with environment

        Returns:
            Configured sandbox adapter
        """
        backend = os.getenv("SANDBOX_BACKEND", "docker").lower()

        # Build config from environment variables
        env_config = {}

        # Common environment variables
        if os.getenv("SANDBOX_IMAGE"):
            env_config["image"] = os.getenv("SANDBOX_IMAGE")

        # E2B specific
        if backend == "e2b":
            if os.getenv("E2B_API_KEY"):
                env_config["api_key"] = os.getenv("E2B_API_KEY")
            if os.getenv("E2B_TEMPLATE"):
                env_config["template"] = os.getenv("E2B_TEMPLATE")

        # GitPod specific
        elif backend == "gitpod":
            if os.getenv("GITPOD_TOKEN"):
                env_config["gitpod_token"] = os.getenv("GITPOD_TOKEN")
            if os.getenv("GITPOD_URL"):
                env_config["gitpod_url"] = os.getenv("GITPOD_URL")

        # Merge with provided config
        final_config = {**env_config, **(config or {})}

        return cls.create_adapter(backend, final_config)

    @classmethod
    def auto_detect_backend(cls, config: Optional[Dict[str, Any]] = None) -> str:
        """Auto-detect the best available backend based on configuration and environment.

        Priority:
        1. Explicit SANDBOX_BACKEND environment variable
        2. Available API keys/tokens in environment
        3. Docker (default fallback)

        Returns:
            Best available backend name
        """
        # Check explicit backend setting
        if os.getenv("SANDBOX_BACKEND"):
            return os.getenv("SANDBOX_BACKEND").lower()

        # Check configuration
        if config:
            if config.get("backend"):
                return config["backend"].lower()

        # Auto-detect based on available credentials
        if os.getenv("E2B_API_KEY"):
            return "e2b"

        if os.getenv("GITPOD_TOKEN"):
            return "gitpod"

        # Default to docker
        return "docker"

    @classmethod
    def create_best_available(
        cls, config: Optional[Dict[str, Any]] = None
    ) -> BaseSandboxAdapter:
        """Create the best available adapter based on auto-detection.

        Args:
            config: Optional configuration dictionary

        Returns:
            Best available configured sandbox adapter
        """
        backend = cls.auto_detect_backend(config)
        return cls.create_from_env(config)
