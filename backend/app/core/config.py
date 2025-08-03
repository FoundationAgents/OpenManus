"""
OpenManus Backend Configuration Management
"""

import os
from typing import List

from pydantic import BaseModel, Field


class BackendConfig(BaseModel):
    """Backend configuration class"""

    # Service configuration
    host: str = Field(default="0.0.0.0", description="Service listening address")
    port: int = Field(default=8000, description="Service port")

    # Session configuration
    max_sessions: int = Field(default=100, description="Maximum concurrent sessions")
    session_timeout: int = Field(default=3600, description="Session timeout (seconds)")

    # Task configuration
    default_max_steps: int = Field(
        default=20, description="Default maximum execution steps"
    )
    default_max_observe: int = Field(
        default=10000, description="Default maximum observation length"
    )

    # CORS configuration
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")

    # Security configuration
    enable_rate_limit: bool = Field(
        default=False, description="Whether to enable rate limiting"
    )
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests count"
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit time window (seconds)"
    )


def get_config() -> BackendConfig:
    """Get configuration instance"""
    return BackendConfig(
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        max_sessions=int(os.getenv("BACKEND_MAX_SESSIONS", "100")),
        session_timeout=int(os.getenv("BACKEND_SESSION_TIMEOUT", "3600")),
        default_max_steps=int(os.getenv("BACKEND_DEFAULT_MAX_STEPS", "20")),
        default_max_observe=int(os.getenv("BACKEND_DEFAULT_MAX_OBSERVE", "10000")),
        cors_origins=os.getenv("BACKEND_CORS_ORIGINS", "*").split(","),
        enable_rate_limit=os.getenv("BACKEND_ENABLE_RATE_LIMIT", "false").lower()
        == "true",
        rate_limit_requests=int(os.getenv("BACKEND_RATE_LIMIT_REQUESTS", "100")),
        rate_limit_window=int(os.getenv("BACKEND_RATE_LIMIT_WINDOW", "60")),
    )


# Global configuration instance
config = get_config()
