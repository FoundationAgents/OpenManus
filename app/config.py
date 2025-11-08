import json
import threading
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: Optional[str] = Field(None, description="API key (optional for some providers)")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    max_input_tokens: Optional[int] = Field(
        None,
        description="Maximum input tokens to use across all requests (None for unlimited)",
    )
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field("openai", description="API type: openai, azure, aws, ollama, or custom")
    api_version: Optional[str] = Field(None, description="Azure Openai version if AzureOpenai")
    requires_api_key: bool = Field(True, description="Whether this provider requires an API key")
    supports_tools: bool = Field(True, description="Whether this provider supports tool calling")
    supports_vision: bool = Field(False, description="Whether this provider supports vision input")


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


class RunflowSettings(BaseModel):
    use_data_analysis_agent: bool = Field(
        default=False, description="Enable data analysis agent in run flow"
    )
    default_mode: str = Field(
        default="agent_flow", description="Default mode: chat or agent_flow"
    )
    enable_ade_mode: bool = Field(
        default=True, description="Enable ADE (Agentic Development Environment) mode"
    )
    enable_multi_agent: bool = Field(
        default=True, description="Enable multi-agent environment"
    )
    enable_user_interaction: bool = Field(
        default=True, description="Enable real-time user interaction"
    )
    max_concurrent_agents: int = Field(
        default=20, description="Maximum concurrent agents"
    )
    agent_timeout: int = Field(
        default=3600, description="Agent timeout in seconds"
    )


class AgentPoolSettings(BaseModel):
    """Configuration for agent pools"""
    
    architect: int = Field(default=2, description="Number of architect agents")
    developer: int = Field(default=8, description="Number of developer agents")
    tester: int = Field(default=4, description="Number of tester agents")
    devops: int = Field(default=3, description="Number of DevOps agents")
    security: int = Field(default=3, description="Number of security agents")
    product_manager: int = Field(default=2, description="Number of product manager agents")
    ui_ux_designer: int = Field(default=3, description="Number of UI/UX designer agents")
    data_analyst: int = Field(default=2, description="Number of data analyst agents")
    documentation: int = Field(default=2, description="Number of documentation agents")
    performance: int = Field(default=2, description="Number of performance agents")
    code_reviewer: int = Field(default=4, description="Number of code reviewer agents")
    researcher: int = Field(default=2, description="Number of researcher agents")


class BlackboardSettings(BaseModel):
    """Configuration for blackboard communication system"""
    
    max_message_history: int = Field(
        default=10000, description="Maximum message history size"
    )
    message_retention_seconds: int = Field(
        default=86400, description="Message retention time in seconds"
    )
    enable_thought_broadcasting: bool = Field(
        default=True, description="Enable broadcasting agent thoughts"
    )
    enable_real_time_coordination: bool = Field(
        default=True, description="Enable real-time agent coordination"
    )


class InteractionSettings(BaseModel):
    """Configuration for user interaction"""
    
    enable_real_time_thoughts: bool = Field(
        default=True, description="Enable real-time thought display"
    )
    enable_user_guidance: bool = Field(
        default=True, description="Enable user guidance during execution"
    )
    enable_execution_control: bool = Field(
        default=True, description="Enable execution pause/resume/cancel"
    )
    thought_update_interval: float = Field(
        default=2.0, description="Thought update interval in seconds"
    )
    max_thought_history: int = Field(
        default=1000, description="Maximum thought history per agent"
    )


class ProjectManagementSettings(BaseModel):
    """Configuration for project management"""
    
    enable_roadmap_generation: bool = Field(
        default=True, description="Enable automatic roadmap generation"
    )
    enable_milestone_tracking: bool = Field(
        default=True, description="Enable milestone tracking"
    )
    enable_risk_assessment: bool = Field(
        default=True, description="Enable risk assessment"
    )
    enable_resource_optimization: bool = Field(
        default=True, description="Enable resource optimization"
    )
    max_project_duration_hours: int = Field(
        default=168, description="Maximum project duration in hours (1 week)"
    )


class QualityAssuranceSettings(BaseModel):
    """Configuration for quality assurance"""
    
    enable_automated_testing: bool = Field(
        default=True, description="Enable automated testing"
    )
    enable_code_review: bool = Field(
        default=True, description="Enable automated code review"
    )
    enable_security_scanning: bool = Field(
        default=True, description="Enable security scanning"
    )
    enable_performance_analysis: bool = Field(
        default=True, description="Enable performance analysis"
    )
    min_test_coverage: float = Field(
        default=80.0, description="Minimum test coverage percentage"
    )
    min_code_quality_score: float = Field(
        default=7.0, description="Minimum code quality score (0-10)"
    )


class DeploymentSettings(BaseModel):
    """Configuration for deployment"""
    
    enable_automated_deployment: bool = Field(
        default=True, description="Enable automated deployment"
    )
    enable_infrastructure_as_code: bool = Field(
        default=True, description="Enable infrastructure as code"
    )
    enable_monitoring: bool = Field(
        default=True, description="Enable deployment monitoring"
    )
    enable_backup: bool = Field(
        default=True, description="Enable backup strategies"
    )
    deployment_environments: List[str] = Field(
        default_factory=lambda: ["development", "staging", "production"],
        description="Deployment environments"
    )


class MonitoringSettings(BaseModel):
    """Configuration for monitoring and metrics"""
    
    enable_performance_monitoring: bool = Field(
        default=True, description="Enable performance monitoring"
    )
    enable_agent_monitoring: bool = Field(
        default=True, description="Enable agent activity monitoring"
    )
    enable_project_monitoring: bool = Field(
        default=True, description="Enable project progress monitoring"
    )
    metrics_retention_days: int = Field(
        default=30, description="Metrics retention period in days"
    )
    alert_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {"error_rate": 0.05, "response_time": 5.0},
        description="Alert thresholds for monitoring"
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


class DaytonaSettings(BaseModel):
    daytona_api_key: Optional[str] = Field(None, description="Daytona API key (optional)")
    daytona_server_url: Optional[str] = Field(
        "https://app.daytona.io/api", description=""
    )
    daytona_target: Optional[str] = Field("us", description="enum ['eu', 'us']")
    sandbox_image_name: Optional[str] = Field("whitezxj/sandbox:0.1.0", description="")
    sandbox_entrypoint: Optional[str] = Field(
        "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
        description="",
    )
    # sandbox_id: Optional[str] = Field(
    #     None, description="ID of the daytona sandbox to use, if any"
    # )
    VNC_password: Optional[str] = Field(
        "123456", description="VNC password for the vnc service in sandbox"
    )


class LocalServiceSettings(BaseModel):
    """Configuration for local service execution (replacing Daytona)"""
    
    use_local_service: bool = Field(True, description="Use local service instead of Daytona")
    workspace_directory: str = Field("./workspace", description="Local workspace directory")
    python_executable: str = Field("python3", description="Python executable path")
    max_concurrent_processes: int = Field(5, description="Maximum concurrent processes")
    process_timeout: int = Field(300, description="Process timeout in seconds")
    enable_network: bool = Field(True, description="Enable network access")
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["python", "pip", "git", "npm", "node", "bash", "cmd", "powershell"],
        description="Allowed commands for execution"
    )


class EditorSettings(BaseModel):
    """Configuration for code editor"""
    
    enable_editor: bool = Field(True, description="Enable code editor")
    default_language: str = Field("python", description="Default language for new files")
    default_theme: str = Field("default", description="Default editor theme")
    auto_save: bool = Field(True, description="Auto-save files")
    auto_save_interval: int = Field(60, description="Auto-save interval in seconds")
    line_numbers: bool = Field(True, description="Show line numbers")
    syntax_highlighting: bool = Field(True, description="Enable syntax highlighting")
    tab_size: int = Field(4, description="Tab size in spaces")
    use_spaces: bool = Field(True, description="Use spaces instead of tabs")
    font_size: int = Field(10, description="Editor font size")
    font_family: str = Field("Courier New", description="Editor font family")
    languages_config_dir: str = Field("config/languages", description="Directory for language definitions")


class UISettings(BaseModel):
    """Configuration for user interface"""
    
    enable_gui: bool = Field(True, description="Enable PyQt6 GUI")
    enable_webui: bool = Field(True, description="Enable web UI on localhost")
    webui_port: int = Field(8080, description="Port for web UI")
    webui_host: str = Field("localhost", description="Host for web UI")
    theme: str = Field("dark", description="UI theme: light, dark, or auto")
    window_width: int = Field(1200, description="Default window width")
    window_height: int = Field(800, description="Default window height")
    auto_save: bool = Field(True, description="Auto-save conversations")


class VectorStoreSettings(BaseModel):
    """Configuration for vector store (embeddings)"""
    
    vector_store_type: str = Field("faiss", description="Type of vector store: faiss or milvus")
    vector_dimension: int = Field(1536, description="Dimension of embeddings")
    index_type: str = Field("IVFFlat", description="FAISS index type")
    nprobe: int = Field(10, description="FAISS nprobe parameter")
    use_gpu: bool = Field(False, description="Use GPU for FAISS operations")
    persistence_path: str = Field("data/vectors", description="Path to persist vector store")


class EmbeddingSettings(BaseModel):
    """Configuration for embedding generation"""
    
    provider: str = Field("anthropic", description="Embedding provider: anthropic or openai")
    model: str = Field("claude-3-5-sonnet-20241022", description="Embedding model name")
    fallback_provider: str = Field("openai", description="Fallback provider if primary fails")
    fallback_model: str = Field("text-embedding-3-small", description="Fallback embedding model")
    batch_size: int = Field(10, description="Batch size for embedding requests")
    rate_limit_rpm: int = Field(3000, description="Requests per minute rate limit")
    cache_embeddings: bool = Field(True, description="Cache embeddings in memory")
    cache_max_size: int = Field(10000, description="Maximum cached embeddings")


class KnowledgeGraphSettings(BaseModel):
    """Configuration for knowledge graph"""
    
    enable_knowledge_graph: bool = Field(True, description="Enable knowledge graph")
    storage_path: str = Field("data/knowledge_graph", description="Path for graph storage")
    db_type: str = Field("sqlite", description="Database type: sqlite or postgresql")
    persistence_enabled: bool = Field(True, description="Enable graph persistence")
    max_nodes: Optional[int] = Field(None, description="Maximum nodes in graph (None for unlimited)")
    enable_versioning: bool = Field(True, description="Enable version tracking for nodes")
    auto_vacuum: bool = Field(True, description="Enable SQLite auto-vacuum")
    vacuum_interval_seconds: int = Field(3600, description="Auto-vacuum interval in seconds")


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
    mcp_config: Optional[MCPSettings] = Field(None, description="MCP configuration")
    run_flow_config: Optional[RunflowSettings] = Field(
        None, description="Run flow configuration"
    )
    daytona_config: Optional[DaytonaSettings] = Field(
        None, description="Daytona configuration"
    )
    local_service_config: Optional[LocalServiceSettings] = Field(
        None, description="Local service configuration"
    )
    editor_config: Optional[EditorSettings] = Field(
        None, description="Code editor configuration"
    )
    ui_config: Optional[UISettings] = Field(
        None, description="UI configuration"
    )
    agent_pools_config: Optional[AgentPoolSettings] = Field(
        None, description="Agent pool configuration"
    )
    blackboard_config: Optional[BlackboardSettings] = Field(
        None, description="Blackboard configuration"
    )
    interaction_config: Optional[InteractionSettings] = Field(
        None, description="User interaction configuration"
    )
    project_management_config: Optional[ProjectManagementSettings] = Field(
        None, description="Project management configuration"
    )
    quality_assurance_config: Optional[QualityAssuranceSettings] = Field(
        None, description="Quality assurance configuration"
    )
    deployment_config: Optional[DeploymentSettings] = Field(
        None, description="Deployment configuration"
    )
    monitoring_config: Optional[MonitoringSettings] = Field(
        None, description="Monitoring configuration"
    )
    vector_store_config: Optional[VectorStoreSettings] = Field(
        None, description="Vector store configuration"
    )
    embedding_config: Optional[EmbeddingSettings] = Field(
        None, description="Embedding generation configuration"
    )
    knowledge_graph_config: Optional[KnowledgeGraphSettings] = Field(
        None, description="Knowledge graph configuration"
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
        daytona_config = raw_config.get("daytona", {})
        if daytona_config:
            try:
                daytona_settings = DaytonaSettings(**daytona_config)
            except Exception as e:
                logger.warning(f"Failed to load Daytona settings: {e}")
                daytona_settings = DaytonaSettings()
        else:
            daytona_settings = DaytonaSettings()

        local_service_config = raw_config.get("local_service", {})
        if local_service_config:
            local_service_settings = LocalServiceSettings(**local_service_config)
        else:
            local_service_settings = LocalServiceSettings()

        editor_config = raw_config.get("editor", {})
        if editor_config:
            editor_settings = EditorSettings(**editor_config)
        else:
            editor_settings = EditorSettings()

        ui_config = raw_config.get("ui", {})
        if ui_config:
            ui_settings = UISettings(**ui_config)
        else:
            ui_settings = UISettings()

        mcp_config = raw_config.get("mcp", {})
        mcp_settings = None
        if mcp_config:
            # Load server configurations from JSON
            mcp_config["servers"] = MCPSettings.load_server_config()
            mcp_settings = MCPSettings(**mcp_config)
        else:
            mcp_settings = MCPSettings(servers=MCPSettings.load_server_config())

        run_flow_config = raw_config.get("runflow")
        if run_flow_config:
            run_flow_settings = RunflowSettings(**run_flow_config)
        else:
            run_flow_settings = RunflowSettings()

        # Load new multi-agent configuration sections
        agent_pools_config = raw_config.get("agent_pools", {})
        if agent_pools_config:
            agent_pools_settings = AgentPoolSettings(**agent_pools_config)
        else:
            agent_pools_settings = AgentPoolSettings()

        blackboard_config = raw_config.get("blackboard", {})
        if blackboard_config:
            blackboard_settings = BlackboardSettings(**blackboard_config)
        else:
            blackboard_settings = BlackboardSettings()

        interaction_config = raw_config.get("interaction", {})
        if interaction_config:
            interaction_settings = InteractionSettings(**interaction_config)
        else:
            interaction_settings = InteractionSettings()

        project_management_config = raw_config.get("project_management", {})
        if project_management_config:
            project_management_settings = ProjectManagementSettings(**project_management_config)
        else:
            project_management_settings = ProjectManagementSettings()

        quality_assurance_config = raw_config.get("quality_assurance", {})
        if quality_assurance_config:
            quality_assurance_settings = QualityAssuranceSettings(**quality_assurance_config)
        else:
            quality_assurance_settings = QualityAssuranceSettings()

        deployment_config = raw_config.get("deployment", {})
        if deployment_config:
            deployment_settings = DeploymentSettings(**deployment_config)
        else:
            deployment_settings = DeploymentSettings()

        monitoring_config = raw_config.get("monitoring", {})
        if monitoring_config:
            monitoring_settings = MonitoringSettings(**monitoring_config)
        else:
            monitoring_settings = MonitoringSettings()

        vector_store_config = raw_config.get("vector_store", {})
        if vector_store_config:
            vector_store_settings = VectorStoreSettings(**vector_store_config)
        else:
            vector_store_settings = VectorStoreSettings()

        embedding_config = raw_config.get("embedding", {})
        if embedding_config:
            embedding_settings = EmbeddingSettings(**embedding_config)
        else:
            embedding_settings = EmbeddingSettings()

        knowledge_graph_config = raw_config.get("knowledge_graph", {})
        if knowledge_graph_config:
            knowledge_graph_settings = KnowledgeGraphSettings(**knowledge_graph_config)
        else:
            knowledge_graph_settings = KnowledgeGraphSettings()

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
            "mcp_config": mcp_settings,
            "run_flow_config": run_flow_settings,
            "daytona_config": daytona_settings,
            "local_service_config": local_service_settings,
            "editor_config": editor_settings,
            "ui_config": ui_settings,
            "agent_pools_config": agent_pools_settings,
            "blackboard_config": blackboard_settings,
            "interaction_config": interaction_settings,
            "project_management_config": project_management_settings,
            "quality_assurance_config": quality_assurance_settings,
            "deployment_config": deployment_settings,
            "monitoring_config": monitoring_settings,
            "vector_store_config": vector_store_settings,
            "embedding_config": embedding_settings,
            "knowledge_graph_config": knowledge_graph_settings,
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    @property
    def sandbox(self) -> SandboxSettings:
        return self._config.sandbox

    @property
    def daytona(self) -> DaytonaSettings:
        return self._config.daytona_config

    @property
    def browser_config(self) -> Optional[BrowserSettings]:
        return self._config.browser_config

    @property
    def search_config(self) -> Optional[SearchSettings]:
        return self._config.search_config

    @property
    def mcp_config(self) -> MCPSettings:
        """Get the MCP configuration"""
        return self._config.mcp_config

    @property
    def run_flow_config(self) -> RunflowSettings:
        """Get the Run Flow configuration"""
        return self._config.run_flow_config

    @property
    def workspace_root(self) -> Path:
        """Get the workspace root directory"""
        return WORKSPACE_ROOT

    @property
    def root_path(self) -> Path:
        """Get the root path of the application"""
        return PROJECT_ROOT

    @property
    def local_service(self) -> LocalServiceSettings:
        """Get the local service configuration"""
        return self._config.local_service_config

    @property
    def editor(self) -> EditorSettings:
        """Get the editor configuration"""
        return self._config.editor_config

    @property
    def ui(self) -> UISettings:
        """Get the UI configuration"""
        return self._config.ui_config

    @property
    def agent_pools(self) -> AgentPoolSettings:
        """Get the agent pools configuration"""
        return self._config.agent_pools_config

    @property
    def blackboard(self) -> BlackboardSettings:
        """Get the blackboard configuration"""
        return self._config.blackboard_config

    @property
    def interaction(self) -> InteractionSettings:
        """Get the interaction configuration"""
        return self._config.interaction_config

    @property
    def project_management(self) -> ProjectManagementSettings:
        """Get the project management configuration"""
        return self._config.project_management_config

    @property
    def quality_assurance(self) -> QualityAssuranceSettings:
        """Get the quality assurance configuration"""
        return self._config.quality_assurance_config

    @property
    def deployment(self) -> DeploymentSettings:
        """Get the deployment configuration"""
        return self._config.deployment_config

    @property
    def monitoring(self) -> MonitoringSettings:
        """Get the monitoring configuration"""
        return self._config.monitoring_config

    @property
    def vector_store(self) -> VectorStoreSettings:
        """Get the vector store configuration"""
        return self._config.vector_store_config

    @property
    def embedding(self) -> EmbeddingSettings:
        """Get the embedding generation configuration"""
        return self._config.embedding_config

    @property
    def knowledge_graph(self) -> KnowledgeGraphSettings:
        """Get the knowledge graph configuration"""
        return self._config.knowledge_graph_config


config = Config()
