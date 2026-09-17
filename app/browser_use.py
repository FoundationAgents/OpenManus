import os
from typing import Dict, Optional

from app.config import BrowserSettings


BROWSER_USE_SERVER_ID = "browser_use"
BROWSER_USE_COMMAND = "uvx"
BROWSER_USE_ARGS = ["browser-use", "--cli-mcp"]
BROWSER_USE_ENV_VARS = (
    "BROWSER_USE_API_KEY",
    "BROWSER_USE_CLOUD_API_URL",
    "BU_BROWSER_ID",
    "BU_CDP_URL",
    "BU_CDP_WS",
    "BU_NAME",
)


def browser_use_disabled() -> bool:
    return os.getenv("OPENMANUS_DISABLE_BROWSER_USE", "").lower() in {
        "1",
        "true",
        "yes",
    }


def browser_use_env(settings: Optional[BrowserSettings] = None) -> Dict[str, str]:
    """Build the environment passed to the Browser Use MCP subprocess.

    Explicit environment variables take precedence over values from the
    application browser configuration, which keeps secrets and deployment
    overrides outside config.toml.
    """
    environment = {
        name: value
        for name in BROWSER_USE_ENV_VARS
        if (value := os.getenv(name))
    }
    if settings:
        environment.setdefault("BU_CDP_URL", settings.cdp_url or "")
        environment.setdefault("BU_CDP_WS", settings.wss_url or "")
    return {name: value for name, value in environment.items() if value}
