import json
import threading
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class SpecializedPoolConfig(BaseModel):
    """Configuration for a specialized agent pool"""
    
    pool_id: str = Field(..., description="Unique pool identifier")
    name: str = Field(..., description="Pool name")
    description: Optional[str] = Field(None, description="Pool description")
    size: int = Field(default=5, description="Number of agents in the pool")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities")
    priority: int = Field(default=100, description="Pool priority for task assignment (higher = more likely to receive tasks)")
    roles: List[str] = Field(default_factory=list, description="Agent roles in this pool")
    max_queue_size: int = Field(default=100, description="Maximum task queue size")
    timeout_seconds: int = Field(default=300, description="Task timeout in seconds")
    enabled: bool = Field(default=True, description="Whether the pool is enabled")


class PoolManagerSettings(BaseModel):
    """Configuration for the agent pool manager"""
    
    enable_pool_manager: bool = Field(default=True, description="Enable the pool manager")
    pools: List[SpecializedPoolConfig] = Field(default_factory=list, description="Pool configurations")
    max_concurrent_tasks: int = Field(default=50, description="Maximum concurrent tasks across all pools")
    load_balancer_strategy: str = Field(default="round_robin", description="Load balancing strategy: round_robin, least_loaded, priority_based")
    rebalance_interval_seconds: int = Field(default=30, description="How often to rebalance tasks")
    metrics_retention_days: int = Field(default=7, description="How long to retain metrics in database")
    enable_auto_scaling: bool = Field(default=False, description="Enable automatic pool scaling based on load")
    min_pool_size: int = Field(default=1, description="Minimum pool size for auto-scaling")
    max_pool_size: int = Field(default=20, description="Maximum pool size for auto-scaling")


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


class ACLTemplateRule(BaseModel):
    """Default ACL rule template definition."""
    
    path: str = Field(..., description="Path scope (supports environment variables and wildcards)")
    operations: List[str] = Field(
        default_factory=lambda: ["read"],
        description="Operations governed by this rule"
    )
    effect: str = Field(
        "allow",
        pattern="^(allow|deny)$",
        description="Whether the rule allows or denies the operations"
    )
    priority: int = Field(100, description="Rule evaluation priority (lower values take precedence)")
    description: Optional[str] = Field(None, description="Optional human readable description")


class ACLRoleTemplate(BaseModel):
    """ACL template definition applied to agents with a given role."""
    
    inherits: List[str] = Field(
        default_factory=list,
        description="Parent role templates that this role inherits"
    )
    rules: List[ACLTemplateRule] = Field(
        default_factory=list,
        description="ACL rules applied to the role"
    )


class ACLSettings(BaseModel):
    """Configuration for Access Control Layer"""
    
    enable_acl: bool = Field(True, description="Enable access control")
    default_permission: str = Field("read", description="Default permission level (comma separated operations)")
    admin_roles: List[str] = Field(
        default_factory=lambda: ["admin", "superuser"], 
        description="Roles with administrative access"
    )
    permission_cache_ttl: int = Field(
        300, description="Permission cache TTL in seconds"
    )
    audit_access: bool = Field(True, description="Audit all access attempts")
    max_failed_attempts: int = Field(5, description="Max failed login attempts")
    lockout_duration: int = Field(900, description="Account lockout duration in seconds")
    default_role_templates: Dict[str, ACLRoleTemplate] = Field(
        default_factory=dict,
        description="Default ACL templates loaded for each agent role"
    )
    default_agent_pools: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Default pool memberships assigned per role"
    )


class GuardianSettings(BaseModel):
    """Configuration for Guardian security monitoring"""
    
    enable_guardian: bool = Field(True, description="Enable Guardian security system")
    threat_detection: bool = Field(True, description="Enable automatic threat detection")
    anomaly_threshold: float = Field(0.8, description="Anomaly detection threshold")
    scan_interval: int = Field(60, description="Security scan interval in seconds")
    alert_channels: List[str] = Field(
        default_factory=lambda: ["log", "ui"], 
        description="Alert notification channels"
    )
    quarantine_suspicious: bool = Field(True, description="Quarantine suspicious activities")
    security_rules_file: str = Field("config/security_rules.json", description="Security rules file")


class GuardianValidationSettings(BaseModel):
    """Configuration for Guardian validation and command approval"""
    
    enable_command_validation: bool = Field(True, description="Enable command validation")
    auto_approval_threshold: float = Field(70.0, description="Auto-approval risk score threshold (0-100)")
    approval_timeout: int = Field(300, description="User approval timeout in seconds")
    policies_file: str = Field("config/security/guardian.json", description="Guardian policies file")
    audit_db_path: str = Field("./data/guardian.db", description="Path to Guardian audit database")
    require_user_approval: bool = Field(True, description="Require user approval for risky commands")
    log_all_commands: bool = Field(True, description="Log all command validations")
    enable_sandbox_validation: bool = Field(True, description="Enable validation in sandbox")
    block_dangerous_patterns: bool = Field(True, description="Block dangerous patterns automatically")


class VersioningSettings(BaseModel):
    """Configuration for version control and management"""
    
    enable_versioning: bool = Field(True, description="Enable version management")
    max_versions_per_file: int = Field(100, description="Maximum versions to keep per file")
    auto_snapshot: bool = Field(True, description="Enable automatic snapshots")
    snapshot_interval: int = Field(3600, description="Snapshot interval in seconds")
    compression: bool = Field(True, description="Compress version data")
    storage_backend: str = Field("sqlite", description="Storage backend: sqlite, postgresql, mysql")
    retention_days: int = Field(90, description="Version retention period in days")


class BackupSettings(BaseModel):
    """Configuration for backup management"""
    
    enable_backups: bool = Field(True, description="Enable backup system")
    backup_interval: int = Field(86400, description="Backup interval in seconds (24 hours)")
    max_backups: int = Field(30, description="Maximum number of backups to keep")
    compression: bool = Field(True, description="Compress backup files")
    encryption: bool = Field(False, description="Encrypt backup files")
    backup_locations: List[str] = Field(
        default_factory=lambda: ["./backups"], 
        description="Backup storage locations"
    )
    include_workspace: bool = Field(True, description="Include workspace in backups")
    include_config: bool = Field(True, description="Include configuration in backups")
    include_database: bool = Field(True, description="Include database in backups")


class KnowledgeGraphSettings(BaseModel):
    """Configuration for knowledge graph management"""
    
    enable_knowledge_graph: bool = Field(True, description="Enable knowledge graph")
    vector_db_type: str = Field("faiss", description="Vector database: faiss, milvus, chroma")
    embedding_model: str = Field("text-embedding-ada-002", description="Embedding model")
    max_nodes: int = Field(10000, description="Maximum nodes in graph")
    max_relationships: int = Field(50000, description="Maximum relationships")
    auto_update: bool = Field(True, description="Auto-update graph from interactions")
    similarity_threshold: float = Field(0.7, description="Similarity threshold for connections")
    persist_to_disk: bool = Field(True, description="Persist graph to disk")
    graph_storage_path: str = Field("./data/knowledge_graph", description="Graph storage path")


class ResourceCatalogSettings(BaseModel):
    """Configuration for system resource catalog"""
    
    enable_catalog: bool = Field(True, description="Enable system resource catalog")
    auto_refresh_on_startup: bool = Field(
        True, description="Run discovery when the system starts"
    )
    debounce_seconds: int = Field(
        300, description="Minimum seconds between discovery refresh runs"
    )
    enable_watchers: bool = Field(
        True, description="Enable filesystem polling for cache invalidation"
    )
    watch_paths: List[str] = Field(
        default_factory=list,
        description="Paths to monitor for resource availability changes",
    )
    watch_interval_seconds: int = Field(
        900, description="Polling interval for watcher checks in seconds"
    )
    known_install_paths: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Known installation roots per locator identifier",
    )


class NetworkSettings(BaseModel):
    """Configuration for network management"""
    
    enable_networking: bool = Field(True, description="Enable networking features")
    max_connections: int = Field(100, description="Maximum concurrent connections")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    retry_attempts: int = Field(3, description="Max retry attempts for failed connections")
    bandwidth_limit: Optional[int] = Field(None, description="Bandwidth limit in bytes/s")
    enable_proxy: bool = Field(False, description="Enable proxy support")
    proxy_url: Optional[str] = Field(None, description="Proxy server URL")
    enable_ssl_verification: bool = Field(True, description="Enable SSL certificate verification")
    trusted_certificates: List[str] = Field(
        default_factory=list, description="Trusted certificate paths"
    )


class ResilienceSettings(BaseModel):
    """Configuration for resilience and fault tolerance"""
    
    enable_resilience: bool = Field(True, description="Enable resilience features")
    circuit_breaker_threshold: int = Field(5, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: int = Field(60, description="Circuit breaker timeout in seconds")
    retry_base_delay: float = Field(1.0, description="Base delay for retries in seconds")
    retry_max_delay: float = Field(60.0, description="Maximum delay for retries")
    retry_jitter: bool = Field(True, description="Add jitter to retry delays")
    bulkhead_limit: int = Field(10, description="Bulkhead pattern limit")
    timeout_threshold: float = Field(30.0, description="Operation timeout threshold")
    health_check_interval: int = Field(30, description="Health check interval in seconds")
class ResilienceSettings(BaseModel):
    """Configuration for agent resilience and health monitoring"""
    
    # Health monitoring settings
    health_check_interval: float = Field(
        default=30.0, description="Health check interval in seconds"
    )
    heartbeat_timeout: float = Field(
        default=120.0, description="Heartbeat timeout in seconds"
    )
    inactivity_threshold: float = Field(
        default=300.0, description="Inactivity threshold in seconds"
    )
    
    # Failure detection thresholds
    max_consecutive_errors: int = Field(
        default=3, description="Maximum consecutive errors before replacement"
    )
    max_error_rate: float = Field(
        default=0.3, description="Maximum error rate (0.0 to 1.0)"
    )
    max_latency: float = Field(
        default=10.0, description="Maximum average latency in seconds"
    )
    min_health_score: float = Field(
        default=0.3, description="Minimum health score before replacement"
    )
    
    # Replacement settings
    enable_auto_replacement: bool = Field(
        default=True, description="Enable automatic agent replacement"
    )
    replacement_delay: float = Field(
        default=5.0, description="Delay before replacement in seconds"
    )
    max_replacements_per_hour: int = Field(
        default=5, description="Maximum replacements per hour per role"
    )
    
    # Context transfer settings
    context_retention_tasks: int = Field(
        default=10, description="Number of recent tasks to retain"
    )
    context_retention_messages: int = Field(
        default=50, description="Number of recent messages to retain"
    )
    context_retention_time: float = Field(
        default=3600.0, description="Context retention time in seconds"
    )
    
    # Recovery settings
    enable_recovery_attempts: bool = Field(
        default=True, description="Enable recovery attempts before replacement"
    )
    max_recovery_attempts: int = Field(
        default=2, description="Maximum recovery attempts"
    )
    recovery_timeout: float = Field(
        default=60.0, description="Recovery attempt timeout"
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


class BackupSettings(BaseModel):
    """Configuration for backup system"""
    
    enable_backups: bool = Field(True, description="Enable backup system")
    backup_frequency: str = Field("daily", description="Backup frequency: hourly, daily, weekly")
    backup_time: str = Field("02:00", description="Time for daily backups (HH:MM)")
    retention_days: int = Field(90, description="Number of days to retain backups")
    archive_threshold_days: int = Field(30, description="Days before archiving old backups")
    keep_minimum_count: int = Field(10, description="Minimum number of recent backups to keep")
    auto_backup_enabled: bool = Field(True, description="Enable automatic scheduled backups")
    include_versions: bool = Field(True, description="Include version history in backups")
    include_workflows: bool = Field(False, description="Include workflow snapshots in backups")
    compression_level: int = Field(6, description="Compression level (0-9)")
    archive_path: str = Field("data/archives", description="Path for archived backups")
    backup_path: str = Field("data/backups", description="Path for active backups")
    cloud_backup_enabled: bool = Field(False, description="Enable cloud backup")
    cloud_provider: Optional[str] = Field(None, description="Cloud provider: s3, azure, gcs")
    cloud_bucket: Optional[str] = Field(None, description="Cloud bucket/container name")
    cloud_access_key: Optional[str] = Field(None, description="Cloud access key")
    cloud_secret_key: Optional[str] = Field(None, description="Cloud secret key")
    cloud_region: Optional[str] = Field(None, description="Cloud region")


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


class NetworkSettings(BaseModel):
    """Configuration for network toolkit"""
    
    # HTTP Client
    enable_http_cache: bool = Field(True, description="Enable HTTP response caching")
    http_cache_max_size: int = Field(1000, description="Maximum cache entries")
    http_cache_max_memory_mb: int = Field(100, description="Maximum cache memory in MB")
    http_cache_default_ttl: int = Field(3600, description="Default cache TTL in seconds")
    http_cache_persist: bool = Field(False, description="Enable cache persistence")
    http_timeout: float = Field(30.0, description="HTTP request timeout in seconds")
    http_max_retries: int = Field(3, description="Maximum HTTP retry attempts")
    http_verify_ssl: bool = Field(True, description="Verify SSL certificates")
    
    # Rate Limiting
    enable_rate_limiting: bool = Field(True, description="Enable rate limiting")
    rate_limit_per_second: float = Field(10.0, description="Requests per second limit")
    rate_limit_burst: int = Field(20, description="Burst size for rate limiting")
    
    # WebSocket
    websocket_heartbeat_interval: float = Field(30.0, description="WebSocket heartbeat interval")
    websocket_ping_interval: float = Field(20.0, description="WebSocket ping interval")
    websocket_max_reconnect: int = Field(5, description="Max WebSocket reconnect attempts")
    
    # Diagnostics
    enable_diagnostics: bool = Field(True, description="Enable network diagnostics")
    ping_count: int = Field(4, description="Default ping packet count")
    traceroute_max_hops: int = Field(30, description="Maximum traceroute hops")
    
    # API Manager
    api_profiles_dir: str = Field("config/api_profiles", description="API profiles storage directory")
class VersioningSettings(BaseModel):
    """Configuration for versioning engine"""
    
    enable_versioning: bool = Field(True, description="Enable file versioning")
    database_path: str = Field("workspace/.versions/versions.db", description="SQLite database path")
    storage_path: str = Field("workspace/.versions/storage", description="Content storage directory")
    auto_version: bool = Field(True, description="Automatically create versions on file saves")
    retention_days: int = Field(30, description="Default retention period for versions in days")
    max_storage_mb: int = Field(1024, description="Maximum storage size in MB")
    cleanup_interval_hours: int = Field(24, description="Cleanup interval in hours")
    track_file_patterns: List[str] = Field(
        default_factory=lambda: ["**/*.py", "**/*.js", "**/*.ts", "**/*.go", "**/*.rs", "**/*.sql", "**/*.sh", "**/*.md"],
        description="File patterns to track for versioning"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["**/.git/**", "**/node_modules/**", "**/__pycache__/**", "**/.pytest_cache/**"],
        description="File patterns to exclude from versioning"
    )
    enable_snapshots: bool = Field(True, description="Enable snapshot functionality")
    max_snapshots: int = Field(100, description="Maximum number of snapshots to keep")
    enable_guardian_checks: bool = Field(True, description="Enable Guardian checks on rollback operations")


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

    # Legacy settings for backward compatibility
    server_reference: str = Field(
        "app.mcp.modular_server", description="Module reference for the MCP server"
    )
    servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="Legacy MCP server configurations"
    )
    
    # New bridge configuration
    default_transport: str = Field("stdio", description="Default transport: stdio or sse")
    enable_fallback: bool = Field(True, description="Enable stdio fallback when tools not supported")
    
    # Fallback detection settings
    fallback_detection: Dict[str, Any] = Field(
        default_factory=lambda: {
            "checkSupportsTools": True,
            "checkApiType": True,
            "unsupportedApiTypes": ["ollama", "custom"]
        },
        description="Settings for detecting when to use fallback"
    )
    
    # Internal server configurations
    internal_servers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Internal MCP server configurations"
    )
    
    # External server configurations  
    external_servers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="External MCP server configurations"
    )
    
    # Connection pool settings
    connection_pool: Dict[str, Any] = Field(
        default_factory=lambda: {
            "maxConnections": 10,
            "connectionTimeout": 30,
            "retryAttempts": 3,
            "retryDelay": 1.0
        },
        description="Connection pool settings"
    )
    
    # Logging settings
    logging: Dict[str, Any] = Field(
        default_factory=lambda: {
            "level": "INFO",
            "logToolCalls": True,
            "logFallbacks": True
        },
        description="Logging configuration"
    )

    @classmethod
    def load_server_config(cls) -> Dict[str, MCPServerConfig]:
        """Load MCP server configuration from JSON file (legacy support)"""
        config_path = PROJECT_ROOT / "config" / "mcp.json"

        try:
            config_file = config_path if config_path.exists() else None
            if not config_file:
                return {}

            with config_file.open() as f:
                data = json.load(f)
                servers = {}

                # Load legacy mcpServers
                for server_id, server_config in data.get("mcpServers", {}).items():
                    servers[server_id] = MCPServerConfig(
                        type=server_config["type"],
                        url=server_config.get("url"),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                    )
                
                # Load internal servers
                for server_id, server_config in data.get("internalServers", {}).items():
                    servers[server_id] = MCPServerConfig(
                        type=server_config["type"],
                        url=server_config.get("url"),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                    )
                
                # Load external servers
                for server_id, server_config in data.get("externalServers", {}).items():
                    servers[server_id] = MCPServerConfig(
                        type=server_config["type"],
                        url=server_config.get("url"),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                    )
                
                return servers
        except Exception as e:
            raise ValueError(f"Failed to load MCP server config: {e}")
    
    @classmethod
    def load_bridge_config(cls) -> Dict[str, Any]:
        """Load complete bridge configuration from JSON file"""
        config_path = PROJECT_ROOT / "config" / "mcp.json"

        try:
            config_file = config_path if config_path.exists() else None
            if not config_file:
                return {}

            with config_file.open() as f:
                data = json.load(f)
                return data
        except Exception as e:
            raise ValueError(f"Failed to load MCP bridge config: {e}")


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
    backup_config: Optional[BackupSettings] = Field(
        None, description="Backup configuration"
    )
    editor_config: Optional[EditorSettings] = Field(
        None, description="Code editor configuration"
    )
    versioning_config: Optional[VersioningSettings] = Field(
        None, description="Versioning engine configuration"
    )
    ui_config: Optional[UISettings] = Field(
        None, description="UI configuration"
    )
    agent_pools_config: Optional[AgentPoolSettings] = Field(
        None, description="Agent pool configuration"
    )
    pool_manager_config: Optional[PoolManagerSettings] = Field(
        None, description="Pool manager configuration"
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
    network_config: Optional[NetworkSettings] = Field(
        None, description="Network toolkit configuration"
    )
    acl_config: Optional[ACLSettings] = Field(
        None, description="Access control layer configuration"
    )
    guardian_config: Optional[GuardianSettings] = Field(
        None, description="Guardian security monitoring configuration"
    )
    guardian_validation_config: Optional[GuardianValidationSettings] = Field(
        None, description="Guardian validation and command approval configuration"
    )
    backup_config: Optional[BackupSettings] = Field(
        None, description="Backup configuration"
    )
    resilience_config: Optional[ResilienceSettings] = Field(
        None, description="Agent resilience configuration"
    )
    resource_catalog_config: Optional[ResourceCatalogSettings] = Field(
        None, description="System resource catalog configuration"
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
    network_config: Optional[NetworkSettings] = Field(
        None, description="Network configuration"
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

        backup_config = raw_config.get("backup", {})
        if backup_config:
            backup_settings = BackupSettings(**backup_config)
        else:
            backup_settings = BackupSettings()

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
            
            # Load bridge configuration from JSON if not in TOML
            if "internal_servers" not in mcp_config:
                bridge_config = MCPSettings.load_bridge_config()
                mcp_config.update(bridge_config)
            
            mcp_settings = MCPSettings(**mcp_config)
        else:
            # Load from JSON only
            bridge_config = MCPSettings.load_bridge_config()
            if bridge_config:
                bridge_config["servers"] = MCPSettings.load_server_config()
                mcp_settings = MCPSettings(**bridge_config)
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

        pool_manager_config = raw_config.get("pool_manager", {})
        if pool_manager_config:
            pool_manager_settings = PoolManagerSettings(**pool_manager_config)
        else:
            pool_manager_settings = PoolManagerSettings()

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

        resource_catalog_config = raw_config.get("resource_catalog", {})
        if resource_catalog_config:
            resource_catalog_settings = ResourceCatalogSettings(**resource_catalog_config)
        else:
            resource_catalog_settings = ResourceCatalogSettings()

        # Load new system integration configurations
        acl_config = raw_config.get("acl", {})
        if acl_config:
            acl_settings = ACLSettings(**acl_config)
        else:
            acl_settings = ACLSettings()

        guardian_config = raw_config.get("guardian", {})
        if guardian_config:
            guardian_settings = GuardianSettings(**guardian_config)
        else:
            guardian_settings = GuardianSettings()

        guardian_validation_config = raw_config.get("guardian_validation", {})
        if guardian_validation_config:
            guardian_validation_settings = GuardianValidationSettings(**guardian_validation_config)
        else:
            guardian_validation_settings = GuardianValidationSettings()

        versioning_config = raw_config.get("versioning", {})
        if versioning_config:
            versioning_settings = VersioningSettings(**versioning_config)
        else:
            versioning_settings = VersioningSettings()

        backup_config = raw_config.get("backup", {})
        if backup_config:
            backup_settings = BackupSettings(**backup_config)
        else:
            backup_settings = BackupSettings()
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

        network_config = raw_config.get("network", {})
        if network_config:
            network_settings = NetworkSettings(**network_config)
        else:
            network_settings = NetworkSettings()

        resilience_config = raw_config.get("resilience", {})
        if resilience_config:
            resilience_settings = ResilienceSettings(**resilience_config)
        else:
            resilience_settings = ResilienceSettings()

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
            "backup_config": backup_settings,
            "editor_config": editor_settings,
            "versioning_config": versioning_settings,
            "ui_config": ui_settings,
            "agent_pools_config": agent_pools_settings,
            "pool_manager_config": pool_manager_settings,
            "blackboard_config": blackboard_settings,
            "interaction_config": interaction_settings,
            "project_management_config": project_management_settings,
            "quality_assurance_config": quality_assurance_settings,
            "deployment_config": deployment_settings,
            "monitoring_config": monitoring_settings,
            "acl_config": acl_settings,
            "guardian_config": guardian_settings,
            "guardian_validation_config": guardian_validation_settings,
            "versioning_config": versioning_settings,
            "backup_config": backup_settings,
            "knowledge_graph_config": knowledge_graph_settings,
            "network_config": network_settings,
            "resilience_config": resilience_settings,
            "vector_store_config": vector_store_settings,
            "embedding_config": embedding_settings,
            "resource_catalog_config": resource_catalog_settings,
            "vector_store_config": vector_store_settings,
            "embedding_config": embedding_settings,
            "knowledge_graph_config": knowledge_graph_settings,
            "resilience_config": resilience_settings,
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
    def backup(self) -> BackupSettings:
        """Get the backup configuration"""
        return self._config.backup_config

    @property
    def editor(self) -> EditorSettings:
        """Get the editor configuration"""
        return self._config.editor_config

    @property
    def versioning(self) -> VersioningSettings:
        """Get the versioning configuration"""
        return self._config.versioning_config

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
    def network(self) -> NetworkSettings:
        """Get the network configuration"""
        return self._config.network_config

    @property
    def acl(self) -> ACLSettings:
        """Get the ACL configuration"""
        return self._config.acl_config

    @property
    def guardian(self) -> GuardianSettings:
        """Get the Guardian configuration"""
        return self._config.guardian_config

    @property
    def guardian_validation(self) -> GuardianValidationSettings:
        """Get the Guardian validation configuration"""
        return self._config.guardian_validation_config

    @property
    def versioning(self) -> VersioningSettings:
        """Get the versioning configuration"""
        return self._config.versioning_config

    @property
    def pool_manager(self) -> PoolManagerSettings:
        """Get the pool manager configuration"""
        return self._config.pool_manager_config

    @property
    def resource_catalog(self) -> ResourceCatalogSettings:
        """Get the system resource catalog configuration"""
        return self._config.resource_catalog_config

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

    @property
    def resilience(self) -> ResilienceSettings:
        """Get the resilience configuration"""
        return self._config.resilience_config


config = Config()
