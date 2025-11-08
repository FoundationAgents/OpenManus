"""
Component Visibility Controller
Manage visibility and state of GUI components based on loading status.
"""

import threading
from typing import Callable, Dict, List, Optional

from app.core.component_registry import ComponentStatus, get_component_registry
from app.logger import logger

try:
    from PyQt6.QtWidgets import QDockWidget, QWidget, QLabel, QVBoxLayout, QProgressBar
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDockWidget = object
    QWidget = object
    QObject = object
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()


class LoadingIndicatorWidget(QWidget):
    """Widget to show loading progress for a component."""
    
    def __init__(self, component_name: str, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Title
        self.title_label = QLabel(f"Loading {self.component_name}...")
        layout.addWidget(self.title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_progress(self, progress: float):
        """Set progress percentage."""
        if progress < 0:
            # Error state
            self.progress_bar.setValue(0)
            self.status_label.setText("Failed to load")
            self.title_label.setText(f"Failed: {self.component_name}")
        else:
            self.progress_bar.setValue(int(progress))
            if progress >= 100:
                self.status_label.setText("Ready!")
            else:
                self.status_label.setText(f"Loading... {progress:.0f}%")


class NotLoadedWidget(QWidget):
    """Widget to show when a component is not loaded."""
    
    def __init__(self, component_name: str, on_load_click: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.on_load_click = on_load_click
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel(f"{self.component_name}\nNot Loaded")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        if self.on_load_click and PYQT6_AVAILABLE:
            from PyQt6.QtWidgets import QPushButton
            load_btn = QPushButton("Load Component")
            load_btn.clicked.connect(self._handle_load_click)
            layout.addWidget(load_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _handle_load_click(self):
        """Handle load button click."""
        if self.on_load_click:
            self.on_load_click(self.component_name)


class ComponentVisibilityController(QObject):
    """
    Controller for managing visibility and state of GUI components.
    Shows/hides components based on their loading status.
    """
    
    # Signals
    component_shown = pyqtSignal(str)
    component_hidden = pyqtSignal(str)
    component_loading = pyqtSignal(str, float)
    
    def __init__(self):
        if PYQT6_AVAILABLE:
            super().__init__()
        self.registry = get_component_registry()
        self._lock = threading.RLock()
        self._dock_widgets: Dict[str, QDockWidget] = {}
        self._original_widgets: Dict[str, QWidget] = {}
        self._loading_widgets: Dict[str, LoadingIndicatorWidget] = {}
        self._not_loaded_widgets: Dict[str, NotLoadedWidget] = {}
        self._on_load_callbacks: Dict[str, Callable] = {}
    
    def register_dock(
        self,
        component_name: str,
        dock_widget: QDockWidget,
        on_load: Optional[Callable[[str], None]] = None
    ):
        """
        Register a dock widget for a component.
        
        Args:
            component_name: Name of the component
            dock_widget: The dock widget to manage
            on_load: Callback to trigger component loading
        """
        with self._lock:
            self._dock_widgets[component_name] = dock_widget
            self._original_widgets[component_name] = dock_widget.widget()
            
            if on_load:
                self._on_load_callbacks[component_name] = on_load
            
            # Update visibility based on current status
            self.update_component_visibility(component_name)
    
    def update_component_visibility(self, component_name: str):
        """Update visibility of a component based on its loading status."""
        if not PYQT6_AVAILABLE:
            return
        
        component = self.registry.get_component(component_name)
        if not component:
            return
        
        dock = self._dock_widgets.get(component_name)
        if not dock:
            return
        
        with self._lock:
            if component.status == ComponentStatus.NOT_LOADED:
                self._show_not_loaded(component_name, dock)
            elif component.status == ComponentStatus.LOADING:
                self._show_loading(component_name, dock)
            elif component.status == ComponentStatus.LOADED:
                self._show_loaded(component_name, dock)
            elif component.status == ComponentStatus.FAILED:
                self._show_failed(component_name, dock)
            elif component.status == ComponentStatus.DISABLED:
                self._hide_component(component_name, dock)
    
    def _show_not_loaded(self, component_name: str, dock: QDockWidget):
        """Show 'not loaded' state for a component."""
        if component_name not in self._not_loaded_widgets:
            on_load = self._on_load_callbacks.get(component_name)
            self._not_loaded_widgets[component_name] = NotLoadedWidget(
                component_name,
                on_load
            )
        
        dock.setWidget(self._not_loaded_widgets[component_name])
        dock.setVisible(False)  # Hide until user clicks load or it's auto-loaded
        
        logger.debug(f"Component '{component_name}' shown as not loaded (hidden)")
    
    def _show_loading(self, component_name: str, dock: QDockWidget):
        """Show loading state for a component."""
        if component_name not in self._loading_widgets:
            self._loading_widgets[component_name] = LoadingIndicatorWidget(component_name)
        
        dock.setWidget(self._loading_widgets[component_name])
        dock.setVisible(True)
        
        logger.debug(f"Component '{component_name}' shown as loading")
        self.component_loading.emit(component_name, 0.0)
    
    def _show_loaded(self, component_name: str, dock: QDockWidget):
        """Show loaded state for a component."""
        original_widget = self._original_widgets.get(component_name)
        if original_widget:
            dock.setWidget(original_widget)
            dock.setVisible(True)
            
            logger.debug(f"Component '{component_name}' shown as loaded")
            self.component_shown.emit(component_name)
    
    def _show_failed(self, component_name: str, dock: QDockWidget):
        """Show failed state for a component."""
        if component_name not in self._loading_widgets:
            self._loading_widgets[component_name] = LoadingIndicatorWidget(component_name)
        
        self._loading_widgets[component_name].set_progress(-1.0)
        dock.setWidget(self._loading_widgets[component_name])
        dock.setVisible(True)
        
        logger.debug(f"Component '{component_name}' shown as failed")
    
    def _hide_component(self, component_name: str, dock: QDockWidget):
        """Hide a component."""
        dock.setVisible(False)
        logger.debug(f"Component '{component_name}' hidden")
        self.component_hidden.emit(component_name)
    
    def update_progress(self, component_name: str, progress: float):
        """Update loading progress for a component."""
        with self._lock:
            loading_widget = self._loading_widgets.get(component_name)
            if loading_widget:
                loading_widget.set_progress(progress)
                self.component_loading.emit(component_name, progress)
    
    def update_all_components(self):
        """Update visibility of all registered components."""
        with self._lock:
            for component_name in self._dock_widgets.keys():
                self.update_component_visibility(component_name)
    
    def show_only_loaded(self):
        """Show only loaded components, hide everything else."""
        with self._lock:
            for component_name, dock in self._dock_widgets.items():
                component = self.registry.get_component(component_name)
                if component and component.status == ComponentStatus.LOADED:
                    dock.setVisible(True)
                else:
                    dock.setVisible(False)
    
    def get_visible_components(self) -> List[str]:
        """Get list of visible component names."""
        with self._lock:
            return [
                name for name, dock in self._dock_widgets.items()
                if dock.isVisible()
            ]
    
    def get_hidden_components(self) -> List[str]:
        """Get list of hidden component names."""
        with self._lock:
            return [
                name for name, dock in self._dock_widgets.items()
                if not dock.isVisible()
            ]


# Global singleton
_controller = None
_controller_lock = threading.Lock()


def get_component_visibility_controller() -> ComponentVisibilityController:
    """Get the global component visibility controller singleton."""
    global _controller
    if _controller is None:
        with _controller_lock:
            if _controller is None:
                _controller = ComponentVisibilityController()
    return _controller
