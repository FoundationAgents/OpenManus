"""
Progressive UI Loading System.

Renders the GUI immediately with skeleton/placeholders, then loads components
in the background to prevent UI freezing.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from threading import Thread

try:
    from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

from app.ui.component_discovery import get_component_discovery
from app.ui.state_manager import get_state_manager
from app.ui.message_bus import get_message_bus, EventTypes

logger = logging.getLogger(__name__)


@dataclass
class LoadTask:
    """A task to load a component."""
    name: str
    display_name: str
    loader: Callable[[], Any]
    priority: int = 5
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class LoadingPlaceholder(QWidget):
    """Placeholder widget shown while component is loading."""
    
    def __init__(self, component_name: str, display_name: str, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.display_name = display_name
        self.init_ui()
    
    def init_ui(self):
        """Initialize the placeholder UI."""
        layout = QVBoxLayout()
        
        # Component name
        label = QLabel(f"<h3>{self.display_name}</h3>")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Loading message
        loading_label = QLabel("Loading...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        layout.addStretch()
        self.setLayout(layout)


class ProgressiveLoader(QObject):
    """
    Manages progressive loading of UI components.
    
    Features:
    - Shows skeleton UI immediately
    - Loads components in background
    - Shows loading placeholders
    - Fills in content as ready
    - Respects dependencies
    - Priority-based loading
    
    Signals:
        component_loaded: Emitted when a component is loaded
        all_loaded: Emitted when all components are loaded
        load_progress: Emitted with progress updates
    """
    
    component_loaded = pyqtSignal(str, object)  # component_name, component_instance
    all_loaded = pyqtSignal()
    load_progress = pyqtSignal(int, int, str)  # current, total, component_name
    
    def __init__(self):
        super().__init__()
        self.discovery = get_component_discovery()
        self.state_manager = get_state_manager()
        self.message_bus = get_message_bus()
        
        self._load_tasks: List[LoadTask] = []
        self._loaded_count = 0
        self._total_count = 0
        self._is_loading = False
        
        logger.info("Progressive loader initialized")
    
    def add_load_task(
        self,
        name: str,
        display_name: str,
        loader: Callable[[], Any],
        priority: int = 5,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """
        Add a component load task.
        
        Args:
            name: Component identifier
            display_name: Display name for the component
            loader: Function that loads and returns the component
            priority: Load priority (lower = higher priority)
            dependencies: List of component names that must load first
        """
        task = LoadTask(
            name=name,
            display_name=display_name,
            loader=loader,
            priority=priority,
            dependencies=dependencies or []
        )
        self._load_tasks.append(task)
        logger.debug(f"Added load task: {name} (priority: {priority})")
    
    def create_placeholder(self, component_name: str, display_name: str) -> QWidget:
        """
        Create a placeholder widget for a component.
        
        Args:
            component_name: Component identifier
            display_name: Display name for the component
            
        Returns:
            Placeholder widget
        """
        if PYQT6_AVAILABLE:
            return LoadingPlaceholder(component_name, display_name)
        else:
            # Return a dummy widget if PyQt6 not available
            class DummyWidget:
                def __init__(self):
                    pass
            return DummyWidget()
    
    def start_loading(self) -> None:
        """Start loading all components progressively."""
        if self._is_loading:
            logger.warning("Loading already in progress")
            return
        
        self._is_loading = True
        self._loaded_count = 0
        self._total_count = len(self._load_tasks)
        
        logger.info(f"Starting progressive loading of {self._total_count} components")
        
        # Sort tasks by priority
        self._load_tasks.sort(key=lambda t: t.priority)
        
        # Start loading in background thread
        thread = Thread(target=self._load_components_thread, daemon=True)
        thread.start()
    
    def _load_components_thread(self) -> None:
        """Background thread for loading components."""
        loaded_components = set()
        
        for task in self._load_tasks:
            # Check dependencies
            dependencies_met = all(dep in loaded_components for dep in task.dependencies)
            
            if not dependencies_met:
                missing = [dep for dep in task.dependencies if dep not in loaded_components]
                logger.warning(f"Skipping {task.name} - missing dependencies: {missing}")
                self.state_manager.update_component_state(
                    task.name,
                    loaded=False,
                    error=f"Missing dependencies: {', '.join(missing)}"
                )
                self._loaded_count += 1
                continue
            
            # Load the component
            try:
                logger.info(f"Loading component: {task.name}")
                start_time = time.time()
                
                component = task.loader()
                
                load_time = time.time() - start_time
                
                if component is not None:
                    loaded_components.add(task.name)
                    self.state_manager.update_component_state(
                        task.name,
                        loaded=True,
                        error=None
                    )
                    
                    # Emit signal on main thread
                    self.component_loaded.emit(task.name, component)
                    
                    logger.info(f"Component loaded: {task.name} ({load_time:.2f}s)")
                else:
                    logger.error(f"Component failed to load: {task.name}")
                    self.state_manager.update_component_state(
                        task.name,
                        loaded=False,
                        error="Loader returned None"
                    )
                
            except Exception as e:
                logger.error(f"Error loading component {task.name}: {e}", exc_info=True)
                self.state_manager.update_component_state(
                    task.name,
                    loaded=False,
                    error=str(e)
                )
            
            self._loaded_count += 1
            self.load_progress.emit(self._loaded_count, self._total_count, task.name)
        
        self._is_loading = False
        self.all_loaded.emit()
        logger.info("All components loaded")
    
    def load_components_from_discovery(self) -> None:
        """
        Load all components discovered by ComponentDiscovery.
        """
        components = self.discovery.discover_components()
        
        for comp_info in components:
            if comp_info.available:
                self.add_load_task(
                    name=comp_info.name,
                    display_name=comp_info.display_name,
                    loader=lambda name=comp_info.name: self.discovery.load_component(name),
                    priority=5,
                    dependencies=comp_info.dependencies
                )
        
        logger.info(f"Queued {len(self._load_tasks)} components for loading")
    
    def is_loading(self) -> bool:
        """Check if loading is in progress."""
        return self._is_loading
    
    def get_progress(self) -> tuple[int, int]:
        """
        Get loading progress.
        
        Returns:
            Tuple of (loaded_count, total_count)
        """
        return self._loaded_count, self._total_count


class SkeletonUI(QWidget):
    """
    Skeleton UI shown immediately while components load.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the skeleton UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h1>OpenManus IDE</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Loading message
        message = QLabel("Initializing components...")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_progress(self, current: int, total: int, component_name: str):
        """Update progress display."""
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(current)
        
        if hasattr(self, "message"):
            self.findChild(QLabel, "message").setText(
                f"Loading {component_name}... ({current}/{total})"
            )


def load_ui_progressively(window, components_to_load: Optional[List[str]] = None) -> ProgressiveLoader:
    """
    Helper function to load UI components progressively.
    
    Args:
        window: Main window instance
        components_to_load: Optional list of component names to load (None = all available)
        
    Returns:
        ProgressiveLoader instance
    """
    loader = ProgressiveLoader()
    
    if components_to_load is None:
        # Load all available components
        loader.load_components_from_discovery()
    else:
        # Load specific components
        discovery = get_component_discovery()
        for comp_name in components_to_load:
            comp_info = discovery.get_component_info(comp_name)
            if comp_info and comp_info.available:
                loader.add_load_task(
                    name=comp_info.name,
                    display_name=comp_info.display_name,
                    loader=lambda name=comp_info.name: discovery.load_component(name),
                    dependencies=comp_info.dependencies
                )
    
    return loader
