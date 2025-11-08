"""
Component Registry
Centralized registry for all system components with metadata and dependencies.
"""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class ComponentType(Enum):
    """Type of component."""
    CORE = "core"
    UI = "ui"
    TOOL = "tool"
    MEMORY = "memory"
    EXECUTION = "execution"
    NETWORK = "network"
    SECURITY = "security"
    STORAGE = "storage"
    INTEGRATION = "integration"


class ComponentStatus(Enum):
    """Status of component."""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ComponentMetadata:
    """Metadata for a system component."""
    name: str
    component_type: ComponentType
    dependencies: List[str] = field(default_factory=list)
    optional: bool = True
    resource_requirement_mb: int = 0
    load_priority: int = 10
    gui_panel: Optional[str] = None
    module_path: Optional[str] = None
    condition: Optional[Callable[[], bool]] = None
    description: str = ""
    status: ComponentStatus = ComponentStatus.NOT_LOADED
    instance: Any = None
    error: Optional[Exception] = None
    load_time_ms: float = 0.0


class ComponentRegistry:
    """
    Central registry for all system components.
    Manages component metadata, dependencies, and loading state.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._components: Dict[str, ComponentMetadata] = {}
        self._initialize_registry()
    
    def _initialize_registry(self):
        """Initialize the component registry with all system components."""
        components = [
            # CORE (always required)
            ComponentMetadata(
                name="config",
                component_type=ComponentType.CORE,
                dependencies=[],
                optional=False,
                resource_requirement_mb=1,
                load_priority=1,
                module_path="app.config",
                description="Configuration system"
            ),
            ComponentMetadata(
                name="logger",
                component_type=ComponentType.CORE,
                dependencies=[],
                optional=False,
                resource_requirement_mb=1,
                load_priority=1,
                module_path="app.logger",
                description="Logging system"
            ),
            ComponentMetadata(
                name="database",
                component_type=ComponentType.STORAGE,
                dependencies=["config", "logger"],
                optional=False,
                resource_requirement_mb=10,
                load_priority=2,
                module_path="app.database",
                description="Database layer"
            ),
            
            # ESSENTIAL UI (load early)
            ComponentMetadata(
                name="code_editor",
                component_type=ComponentType.UI,
                dependencies=["config"],
                optional=False,
                resource_requirement_mb=20,
                load_priority=3,
                gui_panel="CodeEditorPanel",
                module_path="app.ui.panels",
                description="Code editor with syntax highlighting"
            ),
            ComponentMetadata(
                name="command_log",
                component_type=ComponentType.UI,
                dependencies=["logger"],
                optional=False,
                resource_requirement_mb=5,
                load_priority=3,
                gui_panel="CommandLogPanel",
                module_path="app.ui.panels",
                description="Command log panel"
            ),
            
            # AGENTS (high priority)
            ComponentMetadata(
                name="agent_control",
                component_type=ComponentType.UI,
                dependencies=["config", "database"],
                optional=False,
                resource_requirement_mb=30,
                load_priority=4,
                gui_panel="AgentControlPanel",
                module_path="app.ui.panels",
                description="Agent control panel"
            ),
            ComponentMetadata(
                name="agent_monitor",
                component_type=ComponentType.UI,
                dependencies=["agent_control"],
                optional=False,
                resource_requirement_mb=10,
                load_priority=4,
                gui_panel="AgentMonitorPanel",
                module_path="app.ui.panels",
                description="Agent monitoring panel"
            ),
            
            # OPTIONAL COMPONENTS (load on-demand)
            ComponentMetadata(
                name="knowledge_graph",
                component_type=ComponentType.MEMORY,
                dependencies=["database"],
                optional=True,
                resource_requirement_mb=100,
                load_priority=7,
                gui_panel="KnowledgeGraphPanel",
                module_path="app.knowledge_graph",
                condition=lambda: True,  # Load if user has project
                description="Knowledge graph with FAISS"
            ),
            ComponentMetadata(
                name="web_search",
                component_type=ComponentType.TOOL,
                dependencies=["network"],
                optional=True,
                resource_requirement_mb=10,
                load_priority=8,
                module_path="app.tool.modern_web_search",
                condition=lambda: True,  # Load if agent uses web search
                description="Modern web search with RAG"
            ),
            ComponentMetadata(
                name="sandbox",
                component_type=ComponentType.EXECUTION,
                dependencies=["guardian"],
                optional=True,
                resource_requirement_mb=500,
                load_priority=8,
                gui_panel="ConsolePanel",
                module_path="app.sandbox",
                condition=lambda: True,  # Load if agent runs code
                description="Sandbox execution environment"
            ),
            ComponentMetadata(
                name="browser",
                component_type=ComponentType.TOOL,
                dependencies=["network", "guardian"],
                optional=True,
                resource_requirement_mb=500,
                load_priority=9,
                module_path="app.tool.browser",
                condition=lambda: False,  # Load only when explicitly needed
                description="Browser automation with Playwright"
            ),
            ComponentMetadata(
                name="network",
                component_type=ComponentType.NETWORK,
                dependencies=["config", "guardian"],
                optional=True,
                resource_requirement_mb=20,
                load_priority=5,
                module_path="app.network",
                description="Network toolkit with HTTP/WebSocket"
            ),
            ComponentMetadata(
                name="guardian",
                component_type=ComponentType.SECURITY,
                dependencies=["config", "logger"],
                optional=False,
                resource_requirement_mb=5,
                load_priority=2,
                gui_panel="SecurityMonitorPanel",
                module_path="app.guardian",
                description="Security and policy enforcement"
            ),
            ComponentMetadata(
                name="workflow",
                component_type=ComponentType.UI,
                dependencies=["agent_control"],
                optional=True,
                resource_requirement_mb=15,
                load_priority=6,
                gui_panel="WorkflowVisualizerPanel",
                module_path="app.ui.panels",
                description="Workflow visualization"
            ),
            ComponentMetadata(
                name="backup",
                component_type=ComponentType.STORAGE,
                dependencies=["config", "database"],
                optional=True,
                resource_requirement_mb=50,
                load_priority=7,
                gui_panel="BackupPanel",
                module_path="app.backup",
                condition=lambda: False,  # Load only when user opens project
                description="Backup and versioning system"
            ),
            ComponentMetadata(
                name="versioning",
                component_type=ComponentType.STORAGE,
                dependencies=["database"],
                optional=True,
                resource_requirement_mb=20,
                load_priority=7,
                module_path="app.versioning",
                condition=lambda: False,  # Load only when user opens project
                description="Version control integration"
            ),
            ComponentMetadata(
                name="resource_catalog",
                component_type=ComponentType.UI,
                dependencies=["database"],
                optional=True,
                resource_requirement_mb=10,
                load_priority=7,
                gui_panel="ResourceCatalogPanel",
                module_path="app.ui.panels",
                description="Resource catalog panel"
            ),
            ComponentMetadata(
                name="mcp_bridge",
                component_type=ComponentType.INTEGRATION,
                dependencies=["config", "guardian"],
                optional=True,
                resource_requirement_mb=30,
                load_priority=6,
                module_path="app.mcp",
                description="Model Context Protocol bridge"
            ),
        ]
        
        for component in components:
            self._components[component.name] = component
    
    def register_component(self, metadata: ComponentMetadata):
        """Register a new component."""
        with self._lock:
            self._components[metadata.name] = metadata
    
    def get_component(self, name: str) -> Optional[ComponentMetadata]:
        """Get component metadata by name."""
        with self._lock:
            return self._components.get(name)
    
    def get_all_components(self) -> List[ComponentMetadata]:
        """Get all registered components."""
        with self._lock:
            return list(self._components.values())
    
    def get_components_by_type(self, component_type: ComponentType) -> List[ComponentMetadata]:
        """Get all components of a specific type."""
        with self._lock:
            return [c for c in self._components.values() if c.component_type == component_type]
    
    def get_required_components(self) -> List[ComponentMetadata]:
        """Get all required (non-optional) components."""
        with self._lock:
            return [c for c in self._components.values() if not c.optional]
    
    def get_optional_components(self) -> List[ComponentMetadata]:
        """Get all optional components."""
        with self._lock:
            return [c for c in self._components.values() if c.optional]
    
    def get_components_by_priority(self) -> List[ComponentMetadata]:
        """Get all components sorted by load priority."""
        with self._lock:
            return sorted(self._components.values(), key=lambda c: c.load_priority)
    
    def get_dependencies(self, name: str) -> List[str]:
        """Get dependencies for a component."""
        component = self.get_component(name)
        if component:
            return component.dependencies
        return []
    
    def get_dependency_chain(self, name: str) -> List[str]:
        """Get full dependency chain for a component (including transitive dependencies)."""
        visited: Set[str] = set()
        chain: List[str] = []
        
        def _collect_deps(comp_name: str):
            if comp_name in visited:
                return
            visited.add(comp_name)
            
            component = self.get_component(comp_name)
            if not component:
                return
            
            for dep in component.dependencies:
                _collect_deps(dep)
            
            chain.append(comp_name)
        
        _collect_deps(name)
        return chain
    
    def update_status(self, name: str, status: ComponentStatus, instance: Any = None, error: Exception = None):
        """Update component status."""
        with self._lock:
            component = self._components.get(name)
            if component:
                component.status = status
                if instance is not None:
                    component.instance = instance
                if error is not None:
                    component.error = error
    
    def set_load_time(self, name: str, load_time_ms: float):
        """Set component load time."""
        with self._lock:
            component = self._components.get(name)
            if component:
                component.load_time_ms = load_time_ms
    
    def is_loaded(self, name: str) -> bool:
        """Check if component is loaded."""
        component = self.get_component(name)
        return component is not None and component.status == ComponentStatus.LOADED
    
    def can_load(self, name: str) -> bool:
        """Check if component can be loaded (all dependencies satisfied)."""
        component = self.get_component(name)
        if not component:
            return False
        
        for dep in component.dependencies:
            if not self.is_loaded(dep):
                return False
        
        # Check condition if specified
        if component.condition and not component.condition():
            return False
        
        return True
    
    def get_loadable_components(self) -> List[ComponentMetadata]:
        """Get all components that can be loaded now."""
        with self._lock:
            return [
                c for c in self._components.values()
                if c.status == ComponentStatus.NOT_LOADED and self.can_load(c.name)
            ]
    
    def get_total_resource_requirement(self, component_names: List[str]) -> int:
        """Calculate total resource requirement for components."""
        total = 0
        for name in component_names:
            component = self.get_component(name)
            if component:
                total += component.resource_requirement_mb
        return total


# Global singleton
_registry = None
_registry_lock = threading.Lock()


def get_component_registry() -> ComponentRegistry:
    """Get the global component registry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ComponentRegistry()
    return _registry
