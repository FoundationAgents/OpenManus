import threading
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


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
    api_type: str = Field(..., description="Azure, Openai, or Ollama")
    api_version: str = Field(..., description="Azure Openai version if AzureOpenai")


class ProxySettings(BaseModel):
    server: str = Field(None, description="Proxy server address")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")


class SearchSettings(BaseModel):
    engine: str = Field(default="Google", description="Search engine the llm to use")
    fallback_engines: List[str] = Field(
        default_factory=lambda: ["DuckDuckGo", "Baidu"],
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
    max_observe: int = Field(10000, description="Maximum number of tokens to observe for browser agent")
    max_steps: int = Field(50, description="Maximum number of steps for browser agent execution")


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


class ManusSettings(BaseModel):
    """Configuration for the manus execution"""
    max_observe: int = Field(10000, description="Maximum number of tokens to observe")
    max_steps: int = Field(50, description="Maximum number of steps for manus execution")


class ReactSettings(BaseModel):
    """Configuration for the react agent execution"""
    max_steps: int = Field(10, description="Maximum number of steps for react agent execution")


class SWESettings(BaseModel):
    """Configuration for the SWE agent execution"""
    max_steps: int = Field(20, description="Maximum number of steps for SWE agent execution")


class PlanningSettings(BaseModel):
    """Configuration for the Planning agent execution"""
    max_steps: int = Field(20, description="Maximum number of steps for Planning agent execution")


class MCPSettings(BaseModel):
    """Configuration for the MCP agent execution"""
    max_steps: int = Field(20, description="Maximum number of steps for MCP agent execution")


class ToolCallSettings(BaseModel):
    """Configuration for the toolcall agent execution"""
    max_observe: Optional[Union[int, bool]] = Field(10000, description="Maximum number of tokens to observe for toolcall agents")
    max_steps: Optional[int] = Field(50, description="Maximum number of steps for toolcall agent execution")


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings]
    sandbox: Optional[SandboxSettings] = Field(
        None, description="Sandbox configuration"
    )
    browser_config: Optional[BrowserSettings] = Field(
        None, description="Browser configuration"
    )
    search_config: Optional[SearchSettings] = Field(
        None, description="Search configuration"
    )
    manus: Optional[ManusSettings] = Field(
        None, description="Manus configuration"
    )
    toolcall: Optional[ToolCallSettings] = Field(
        None, description="ToolCall agent configuration"
    )
    react: Optional[ReactSettings] = Field(
        None, description="React agent configuration"
    )
    swe: Optional[SWESettings] = Field(
        None, description="SWE agent configuration"
    )
    planning: Optional[PlanningSettings] = Field(
        None, description="Planning agent configuration"
    )
    mcp: Optional[MCPSettings] = Field(
        None, description="MCP agent configuration"
    )

    class Config:
        arbitrary_types_allowed = True


class Config:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            return example_path
        raise FileNotFoundError("No configuration file found in config directory")

    def _load_config(self) -> dict:
        config_path = self._get_config_path()
        with config_path.open("rb") as f:
            return tomllib.load(f)

    def _load_initial_config(self):
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})
        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": base_llm.get("model"),
            "base_url": base_llm.get("base_url"),
            "api_key": base_llm.get("api_key"),
            "max_tokens": base_llm.get("max_tokens", 4096),
            "max_input_tokens": base_llm.get("max_input_tokens"),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", ""),
            "api_version": base_llm.get("api_version", ""),
        }

        # handle browser config.
        browser_config = raw_config.get("browser", {})
        browser_settings = None

        if browser_config:
            # handle proxy settings.
            proxy_config = browser_config.get("proxy", {})
            proxy_settings = None

            if proxy_config and proxy_config.get("server"):
                proxy_settings = ProxySettings(
                    **{
                        k: v
                        for k, v in proxy_config.items()
                        if k in ["server", "username", "password"] and v
                    }
                )

            # filter valid browser config parameters.
            valid_browser_params = {
                k: v
                for k, v in browser_config.items()
                if k in BrowserSettings.__annotations__ and v is not None
            }

            # if there is proxy settings, add it to the parameters.
            if proxy_settings:
                valid_browser_params["proxy"] = proxy_settings

            # only create BrowserSettings when there are valid parameters.
            if valid_browser_params:
                browser_settings = BrowserSettings(**valid_browser_params)

        search_config = raw_config.get("search", {})
        search_settings = None
        if search_config:
            search_settings = SearchSettings(**search_config)

        sandbox_config = raw_config.get("sandbox", {})
        if sandbox_config:
            sandbox_settings = SandboxSettings(**sandbox_config)
        else:
            sandbox_settings = SandboxSettings()

        # Add manus configuration handling
        manus_config = raw_config.get("manus", {})
        manus_settings = None
        if manus_config:
            manus_settings = ManusSettings(**manus_config)

        # Add toolcall configuration handling
        toolcall_config = raw_config.get("toolcall", {})
        toolcall_settings = None
        if toolcall_config:
            # Handle None values explicitly for toolcall config
            processed_config = {}
            for key, value in toolcall_config.items():
                # Convert string 'None' or empty string to Python None
                if value == '' or value is None:
                    processed_config[key] = None
                else:
                    processed_config[key] = value
            toolcall_settings = ToolCallSettings(**processed_config)

        # Add react configuration handling
        react_config = raw_config.get("react", {})
        react_settings = None
        if react_config:
            react_settings = ReactSettings(**react_config)

        # Add SWE configuration handling
        swe_config = raw_config.get("swe", {})
        swe_settings = None
        if swe_config:
            swe_settings = SWESettings(**swe_config)

        # Add Planning configuration handling
        planning_config = raw_config.get("planning", {})
        planning_settings = None
        if planning_config:
            planning_settings = PlanningSettings(**planning_config)

        # Add MCP configuration handling
        mcp_config = raw_config.get("mcp", {})
        mcp_settings = None
        if mcp_config:
            mcp_settings = MCPSettings(**mcp_config)

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            },
            "sandbox": sandbox_settings,
            "browser_config": browser_settings,
            "search_config": search_settings,
            "manus": manus_settings,
            "toolcall": toolcall_settings,
            "react": react_settings,
            "swe": swe_settings,
            "planning": planning_settings,
            "mcp": mcp_settings,
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    @property
    def sandbox(self) -> SandboxSettings:
        return self._config.sandbox

    @property
    def browser_config(self) -> Optional[BrowserSettings]:
        return self._config.browser_config

    @property
    def browser(self) -> BrowserSettings:
        """Get the browser configuration settings (shorthand for browser_config)"""
        if self._config.browser_config is None:
            return BrowserSettings()
        return self._config.browser_config

    @property
    def search_config(self) -> Optional[SearchSettings]:
        return self._config.search_config

    @property
    def manus(self) -> Optional[ManusSettings]:
        return self._config.manus

    @property
    def toolcall(self) -> Optional[ToolCallSettings]:
        """Get the toolcall configuration settings"""
        return self._config.toolcall

    @property
    def react(self) -> ReactSettings:
        """Get the react configuration settings"""
        if self._config.react is None:
            return ReactSettings()
        return self._config.react

    @property
    def swe(self) -> SWESettings:
        """Get the SWE configuration settings"""
        if self._config.swe is None:
            return SWESettings()
        return self._config.swe

    @property
    def planning(self) -> PlanningSettings:
        """Get the Planning configuration settings"""
        if self._config.planning is None:
            return PlanningSettings()
        return self._config.planning

    @property
    def mcp(self) -> MCPSettings:
        """Get the MCP configuration settings"""
        if self._config.mcp is None:
            return MCPSettings()
        return self._config.mcp

    @property
    def workspace_root(self) -> Path:
        """Get the workspace root directory"""
        return WORKSPACE_ROOT

    @property
    def root_path(self) -> Path:
        """Get the root path of the application"""
        return PROJECT_ROOT


config = Config()
