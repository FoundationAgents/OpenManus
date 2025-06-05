import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    max_input_tokens: Optional[int] = Field(
        None,
        description="Maximum input tokens to use across all requests (None for unlimited)",
    )
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field(default="", description="Azure, Openai, or Ollama")
    api_version: str = Field(default="", description="Azure Openai version if AzureOpenai")


class ProxySettings(BaseModel):
    server: str = Field(None, description="Proxy server address")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")


class SearchSettings(BaseModel):
    engine: str = Field(default="Google", description="Search engine the llm to use")
    fallback_engines: List[str] = Field(
        default_factory=lambda: ["DuckDuckGo", "Baidu", "Bing"],
        description="Fallback search engines to try if the primary engine fails",
    )
    retry_delay: int = Field(
        default=60,
        description="Seconds to wait before retrying all engines again after they all fail",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of times to retry all engines when all fail",
    )
    lang: str = Field(
        default="en",
        description="Language code for search results (e.g., en, zh, fr)",
    )
    country: str = Field(
        default="us",
        description="Country code for search results (e.g., us, cn, uk)",
    )


class BrowserSettings(BaseModel):
    headless: bool = Field(False, description="Whether to run browser in headless mode")
    disable_security: bool = Field(
        True, description="Disable browser security features"
    )
    extra_chromium_args: List[str] = Field(
        default_factory=list, description="Extra arguments to pass to the browser"
    )
    chrome_instance_path: Optional[str] = Field(
        None, description="Path to a Chrome instance to use"
    )
    wss_url: Optional[str] = Field(
        None, description="Connect to a browser instance via WebSocket"
    )
    cdp_url: Optional[str] = Field(
        None, description="Connect to a browser instance via CDP"
    )
    proxy: Optional[ProxySettings] = Field(
        None, description="Proxy settings for the browser"
    )
    max_content_length: int = Field(
        2000, description="Maximum length for content retrieval operations"
    )

    @field_validator("proxy", mode="before")
    @classmethod
    def validate_proxy(cls, v: Optional[Dict[str, Any]]) -> Optional[ProxySettings]:
        if not v:
            return None
        if not isinstance(v, dict):
            return v
        if not v.get("server"):
            return None
        return ProxySettings(
            **{k: v[k] for k in ["server", "username", "password"] if k in v and v[k]}
        )


class SandboxSettings(BaseModel):
    """Configuration for the execution sandbox"""

    use_sandbox: bool = Field(False, description="Whether to use the sandbox")
    image: str = Field("python:3.12-slim", description="Base image")
    work_dir: str = Field("/workspace", description="Container working directory")
    memory_limit: str = Field("512m", description="Memory limit")
    cpu_limit: float = Field(1.0, description="CPU limit")
    timeout: int = Field(300, description="Default command timeout (seconds)")
    network_enabled: bool = Field(
        False, description="Whether network access is allowed"
    )


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server"""

    type: str = Field(..., description="Server connection type (sse or stdio)")
    url: Optional[str] = Field(None, description="Server URL for SSE connections")
    command: Optional[str] = Field(None, description="Command for stdio connections")
    args: List[str] = Field(
        default_factory=list, description="Arguments for stdio command"
    )


class MCPSettings(BaseModel):
    """Configuration for MCP (Model Context Protocol)"""

    server_reference: str = Field(
        "app.mcp.server", description="Module reference for the MCP server"
    )
    servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="MCP server configurations"
    )

    @classmethod
    def load_server_config(cls) -> Dict[str, MCPServerConfig]:
        """Load MCP server configuration from JSON file"""
        config_path = PROJECT_ROOT / "config" / "mcp.json"

        try:
            config_file = config_path if config_path.exists() else None
            if not config_file:
                return {}

            with config_file.open() as f:
                data = json.load(f)
                servers = {}

                for server_id, server_config in data.get("mcpServers", {}).items():
                    servers[server_id] = MCPServerConfig(
                        type=server_config["type"],
                        url=server_config.get("url"),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                    )
                return servers
        except Exception as e:
            raise ValueError(f"Failed to load MCP server config: {e}")


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=PROJECT_ROOT / "config" / "config.toml",
        extra="ignore",
    )

    llm: Dict[str, LLMSettings] = Field(default_factory=dict)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    browser_config: BrowserSettings = Field(default_factory=BrowserSettings, alias="browser")
    search_config: SearchSettings = Field(default_factory=SearchSettings, alias="search")
    mcp_config: MCPSettings = Field(default_factory=lambda: MCPSettings(servers=MCPSettings.load_server_config()),
                                    alias="mcp")
    workspace_root: str = str(WORKSPACE_ROOT)
    root_path: str = str(PROJECT_ROOT)

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)

    @model_validator(mode="before")
    @classmethod
    def process_llm_config(cls, values: dict) -> dict:
        if "llm" in values:
            llm_config = values["llm"]
            if isinstance(llm_config, dict):
                # Process base LLM configuration
                base_config = {k: v for k, v in llm_config.items() if not isinstance(v, dict)}
                if base_config:
                    values["llm"] = {"default": base_config}

                # Process additional LLM configurations (e.g., vision)
                for key, value in llm_config.items():
                    if isinstance(value, dict):
                        if "llm" not in values:
                            values["llm"] = {}
                        values["llm"][key] = value
        return values

    @model_validator(mode="after")
    def validate_llm_config(self) -> "Config":
        if not self.llm:
            raise ValueError("At least one LLM configuration must be provided")
        if "default" not in self.llm:
            raise ValueError("A default LLM configuration must be provided")
        return self


@lru_cache
def get_config() -> Config:
    """Get the global configuration singleton"""
    return Config()


config = get_config()
