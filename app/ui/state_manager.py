"""
Central State Management for the application.

Provides a single source of truth for application state with reactive updates.
All state changes flow through the state manager and notify interested subscribers.
"""

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Set

from app.ui.message_bus import get_message_bus, EventTypes

logger = logging.getLogger(__name__)


@dataclass
class ComponentState:
    """State for a single component."""
    name: str
    loaded: bool = False
    enabled: bool = True
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProjectState:
    """State for the current project."""
    name: str = ""
    path: Optional[Path] = None
    opened_at: Optional[datetime] = None
    recent_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """State for the current session."""
    active_agents: List[str] = field(default_factory=list)
    conversations: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    current_task: Optional[str] = None
    workspace_path: Optional[Path] = None


@dataclass
class UserPreferences:
    """User preferences and settings."""
    theme: str = "light"
    font_size: int = 12
    font_family: str = "Courier New"
    auto_save: bool = True
    show_line_numbers: bool = True
    enable_syntax_highlighting: bool = True
    panel_layout: Dict[str, Any] = field(default_factory=dict)
    keyboard_shortcuts: Dict[str, str] = field(default_factory=dict)
    enabled_components: Set[str] = field(default_factory=set)


@dataclass
class StateSnapshot:
    """A snapshot of application state for undo/redo."""
    timestamp: datetime
    components: Dict[str, ComponentState]
    project: ProjectState
    session: SessionState
    preferences: UserPreferences
    description: str = ""


class StateManager:
    """
    Central state manager for the application.
    
    Features:
    - Single source of truth for app state
    - Reactive updates via message bus
    - Undo/redo history
    - State persistence
    - Thread-safe operations
    - State snapshots for debugging
    
    Example:
        # Get state
        state = state_manager.get_component_state("code_editor")
        
        # Update state
        state_manager.update_component_state("code_editor", loaded=True)
        
        # Subscribe to changes
        state_manager.on_state_change("components", lambda s: print(s))
    """
    
    def __init__(self, max_history: int = 50):
        """
        Initialize the state manager.
        
        Args:
            max_history: Maximum number of history entries to keep
        """
        self._components: Dict[str, ComponentState] = {}
        self._project = ProjectState()
        self._session = SessionState()
        self._preferences = UserPreferences()
        
        self._history: List[StateSnapshot] = []
        self._history_index = -1
        self._max_history = max_history
        
        self._lock = RLock()
        self._message_bus = get_message_bus()
        self._change_listeners: Dict[str, List[Callable]] = {}
        
        logger.info("State manager initialized")
    
    # Component state management
    
    def register_component(self, name: str, dependencies: Optional[List[str]] = None) -> None:
        """
        Register a new component.
        
        Args:
            name: Component name
            dependencies: List of dependency component names
        """
        with self._lock:
            if name not in self._components:
                self._components[name] = ComponentState(
                    name=name,
                    dependencies=dependencies or []
                )
                logger.info(f"Registered component: {name}")
                self._notify_change("components")
    
    def update_component_state(self, name: str, **kwargs) -> None:
        """
        Update component state.
        
        Args:
            name: Component name
            **kwargs: State fields to update
        """
        with self._lock:
            if name not in self._components:
                self.register_component(name)
            
            component = self._components[name]
            for key, value in kwargs.items():
                if hasattr(component, key):
                    setattr(component, key, value)
            
            component.last_updated = datetime.now()
            
            logger.debug(f"Updated component state: {name}")
            self._notify_change("components")
            
            # Publish component events
            if kwargs.get("loaded"):
                self._message_bus.publish(EventTypes.COMPONENT_LOADED, {"name": name})
            if kwargs.get("error"):
                self._message_bus.publish(EventTypes.COMPONENT_FAILED, {
                    "name": name,
                    "error": kwargs["error"]
                })
    
    def get_component_state(self, name: str) -> Optional[ComponentState]:
        """
        Get component state.
        
        Args:
            name: Component name
            
        Returns:
            ComponentState or None if not found
        """
        with self._lock:
            return deepcopy(self._components.get(name))
    
    def get_all_components(self) -> Dict[str, ComponentState]:
        """
        Get all component states.
        
        Returns:
            Dictionary of component states
        """
        with self._lock:
            return deepcopy(self._components)
    
    def is_component_ready(self, name: str) -> bool:
        """
        Check if a component is ready (loaded and no errors).
        
        Args:
            name: Component name
            
        Returns:
            True if component is ready
        """
        state = self.get_component_state(name)
        return state is not None and state.loaded and state.error is None
    
    def check_dependencies(self, name: str) -> tuple[bool, List[str]]:
        """
        Check if all dependencies for a component are ready.
        
        Args:
            name: Component name
            
        Returns:
            Tuple of (all_ready, missing_dependencies)
        """
        state = self.get_component_state(name)
        if not state:
            return False, [name]
        
        missing = []
        for dep in state.dependencies:
            if not self.is_component_ready(dep):
                missing.append(dep)
        
        return len(missing) == 0, missing
    
    # Project state management
    
    def set_project(self, name: str, path: Optional[Path] = None, **metadata) -> None:
        """
        Set the current project.
        
        Args:
            name: Project name
            path: Project path
            **metadata: Additional project metadata
        """
        with self._lock:
            self._project = ProjectState(
                name=name,
                path=path,
                opened_at=datetime.now(),
                metadata=metadata
            )
            
            logger.info(f"Project opened: {name}")
            self._notify_change("project")
            self._message_bus.publish(EventTypes.PROJECT_OPENED, {"name": name, "path": str(path)})
    
    def get_project(self) -> ProjectState:
        """Get current project state."""
        with self._lock:
            return deepcopy(self._project)
    
    def add_recent_file(self, file_path: str) -> None:
        """
        Add a file to recent files list.
        
        Args:
            file_path: Path to the file
        """
        with self._lock:
            if file_path in self._project.recent_files:
                self._project.recent_files.remove(file_path)
            
            self._project.recent_files.insert(0, file_path)
            
            # Keep only last 10
            self._project.recent_files = self._project.recent_files[:10]
            
            self._notify_change("project")
    
    # Session state management
    
    def update_session(self, **kwargs) -> None:
        """
        Update session state.
        
        Args:
            **kwargs: Session fields to update
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._session, key):
                    setattr(self._session, key, value)
            
            self._notify_change("session")
    
    def get_session(self) -> SessionState:
        """Get current session state."""
        with self._lock:
            return deepcopy(self._session)
    
    # User preferences management
    
    def update_preferences(self, **kwargs) -> None:
        """
        Update user preferences.
        
        Args:
            **kwargs: Preference fields to update
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._preferences, key):
                    setattr(self._preferences, key, value)
            
            logger.info(f"Preferences updated: {list(kwargs.keys())}")
            self._notify_change("preferences")
            self._message_bus.publish(EventTypes.SETTINGS_CHANGED, kwargs)
            
            # Special handling for theme changes
            if "theme" in kwargs:
                self._message_bus.publish(EventTypes.THEME_CHANGED, {"theme": kwargs["theme"]})
    
    def get_preferences(self) -> UserPreferences:
        """Get user preferences."""
        with self._lock:
            return deepcopy(self._preferences)
    
    # History and undo/redo
    
    def create_snapshot(self, description: str = "") -> None:
        """
        Create a snapshot of current state for undo/redo.
        
        Args:
            description: Description of the state change
        """
        with self._lock:
            # Remove any snapshots after current index
            if self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
            
            snapshot = StateSnapshot(
                timestamp=datetime.now(),
                components=deepcopy(self._components),
                project=deepcopy(self._project),
                session=deepcopy(self._session),
                preferences=deepcopy(self._preferences),
                description=description
            )
            
            self._history.append(snapshot)
            self._history_index = len(self._history) - 1
            
            # Trim history if needed
            if len(self._history) > self._max_history:
                self._history.pop(0)
                self._history_index -= 1
            
            logger.debug(f"State snapshot created: {description}")
    
    def undo(self) -> bool:
        """
        Undo to previous state.
        
        Returns:
            True if undo was successful
        """
        with self._lock:
            if self._history_index > 0:
                self._history_index -= 1
                self._restore_snapshot(self._history[self._history_index])
                logger.info("State undone")
                return True
            return False
    
    def redo(self) -> bool:
        """
        Redo to next state.
        
        Returns:
            True if redo was successful
        """
        with self._lock:
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self._restore_snapshot(self._history[self._history_index])
                logger.info("State redone")
                return True
            return False
    
    def _restore_snapshot(self, snapshot: StateSnapshot) -> None:
        """Restore state from a snapshot."""
        self._components = deepcopy(snapshot.components)
        self._project = deepcopy(snapshot.project)
        self._session = deepcopy(snapshot.session)
        self._preferences = deepcopy(snapshot.preferences)
        
        self._notify_change("all")
    
    # State persistence
    
    def save_state(self, file_path: Path) -> None:
        """
        Save state to file.
        
        Args:
            file_path: Path to save state to
        """
        with self._lock:
            state_dict = {
                "components": {name: asdict(comp) for name, comp in self._components.items()},
                "project": asdict(self._project),
                "session": asdict(self._session),
                "preferences": asdict(self._preferences)
            }
            
            # Convert non-serializable types
            def convert(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Path):
                    return str(obj)
                elif isinstance(obj, set):
                    return list(obj)
                return obj
            
            def deep_convert(obj):
                if isinstance(obj, dict):
                    return {k: deep_convert(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [deep_convert(item) for item in obj]
                else:
                    return convert(obj)
            
            state_dict = deep_convert(state_dict)
            
            with open(file_path, 'w') as f:
                json.dump(state_dict, f, indent=2)
            
            logger.info(f"State saved to {file_path}")
    
    def load_state(self, file_path: Path) -> None:
        """
        Load state from file.
        
        Args:
            file_path: Path to load state from
        """
        with open(file_path, 'r') as f:
            state_dict = json.load(f)
        
        # TODO: Reconstruct state from dict
        # This is a simplified version
        with self._lock:
            if "preferences" in state_dict:
                prefs = state_dict["preferences"]
                for key, value in prefs.items():
                    if hasattr(self._preferences, key):
                        if key == "enabled_components":
                            value = set(value)
                        setattr(self._preferences, key, value)
        
        logger.info(f"State loaded from {file_path}")
        self._notify_change("all")
    
    # Change notifications
    
    def on_state_change(self, state_type: str, handler: Callable[[Any], None]) -> None:
        """
        Subscribe to state changes.
        
        Args:
            state_type: Type of state to watch ("components", "project", "session", "preferences", "all")
            handler: Callback function
        """
        with self._lock:
            if state_type not in self._change_listeners:
                self._change_listeners[state_type] = []
            
            if handler not in self._change_listeners[state_type]:
                self._change_listeners[state_type].append(handler)
                logger.debug(f"Subscribed to {state_type} state changes")
    
    def _notify_change(self, state_type: str) -> None:
        """Notify listeners of state changes."""
        handlers = []
        
        with self._lock:
            handlers.extend(self._change_listeners.get(state_type, []))
            handlers.extend(self._change_listeners.get("all", []))
        
        # Get current state
        state_data = None
        if state_type == "components":
            state_data = self.get_all_components()
        elif state_type == "project":
            state_data = self.get_project()
        elif state_type == "session":
            state_data = self.get_session()
        elif state_type == "preferences":
            state_data = self.get_preferences()
        
        # Notify handlers
        for handler in handlers:
            try:
                handler(state_data)
            except Exception as e:
                logger.error(f"Error in state change handler: {e}", exc_info=True)


# Global state manager instance
_state_manager: Optional[StateManager] = None
_state_manager_lock = RLock()


def get_state_manager() -> StateManager:
    """
    Get the global state manager instance (singleton).
    
    Returns:
        Global StateManager instance
    """
    global _state_manager
    
    if _state_manager is None:
        with _state_manager_lock:
            if _state_manager is None:
                _state_manager = StateManager()
    
    return _state_manager
