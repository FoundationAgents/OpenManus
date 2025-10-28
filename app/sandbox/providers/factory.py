"""
Factory helpers for creating sandbox providers based on configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import SandboxSettings, config
from app.utils.logger import logger

from .base import SandboxProvider

if TYPE_CHECKING:
    from app.config import SandboxSettings


def _normalize_provider_name(name: str | None) -> str:
    if not name:
        return "daytona"
    return name.strip().lower()


def create_sandbox_provider() -> SandboxProvider:
    """
    Instantiate a sandbox provider according to configuration.

    Returns:
        SandboxProvider: Concrete sandbox provider instance.

    Raises:
        ValueError: If no matching provider is found.
    """

    sandbox_settings: SandboxSettings = config.sandbox or SandboxSettings()
    provider_name = _normalize_provider_name(getattr(sandbox_settings, "provider", None))

    logger.debug(f"Creating sandbox provider: {provider_name}")

    if provider_name == "daytona":
        from .daytona_provider import DaytonaSandboxProvider

        return DaytonaSandboxProvider(config, sandbox_settings)
    if provider_name == "agentbay":
        from .agentbay_provider import AgentBaySandboxProvider

        return AgentBaySandboxProvider(config, sandbox_settings)

    raise ValueError(f"Unsupported sandbox provider: {provider_name}")
