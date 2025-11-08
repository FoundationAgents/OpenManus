"""
Keyboard Navigation - Full keyboard support for the application.
"""

import logging
from typing import Dict, Callable, Optional
from dataclasses import dataclass

try:
    from PyQt6.QtWidgets import QWidget, QMainWindow
    from PyQt6.QtCore import Qt, QObject, QEvent
    from PyQt6.QtGui import QKeySequence, QShortcut
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QObject = object
    QEvent = object

logger = logging.getLogger(__name__)


@dataclass
class KeyBinding:
    """A keyboard shortcut binding."""
    key_sequence: str
    action: Callable
    description: str
    category: str = "General"


class KeyboardNavigationManager(QObject):
    """
    Manages keyboard navigation and shortcuts.
    
    Features:
    - Global keyboard shortcuts
    - Context-specific shortcuts
    - Customizable key bindings
    - Tab navigation between panels
    - Accessibility support
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bindings: Dict[str, KeyBinding] = {}
        self.shortcuts: Dict[str, QShortcut] = {}
        
        if parent:
            parent.installEventFilter(self)
        
        logger.info("Keyboard navigation manager initialized")
    
    def register_shortcut(
        self,
        key_sequence: str,
        action: Callable,
        description: str,
        category: str = "General",
        context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut
    ) -> None:
        """
        Register a keyboard shortcut.
        
        Args:
            key_sequence: Qt key sequence (e.g., "Ctrl+N", "Alt+S")
            action: Function to call when shortcut is triggered
            description: Human-readable description
            category: Category for organization
            context: Shortcut context (Window, Application, Widget)
        """
        if not PYQT6_AVAILABLE:
            logger.warning("PyQt6 not available, shortcuts disabled")
            return
        
        binding = KeyBinding(
            key_sequence=key_sequence,
            action=action,
            description=description,
            category=category
        )
        
        self.bindings[key_sequence] = binding
        
        # Create QShortcut if we have a parent widget
        if self.parent():
            shortcut = QShortcut(QKeySequence(key_sequence), self.parent())
            shortcut.setContext(context)
            shortcut.activated.connect(action)
            self.shortcuts[key_sequence] = shortcut
            
            logger.debug(f"Registered shortcut: {key_sequence} - {description}")
    
    def unregister_shortcut(self, key_sequence: str) -> None:
        """
        Unregister a keyboard shortcut.
        
        Args:
            key_sequence: Key sequence to unregister
        """
        if key_sequence in self.bindings:
            del self.bindings[key_sequence]
        
        if key_sequence in self.shortcuts:
            self.shortcuts[key_sequence].setEnabled(False)
            del self.shortcuts[key_sequence]
            
            logger.debug(f"Unregistered shortcut: {key_sequence}")
    
    def get_all_shortcuts(self) -> Dict[str, KeyBinding]:
        """
        Get all registered shortcuts.
        
        Returns:
            Dictionary of key sequences to bindings
        """
        return self.bindings.copy()
    
    def get_shortcuts_by_category(self, category: str) -> Dict[str, KeyBinding]:
        """
        Get shortcuts for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Dictionary of key sequences to bindings
        """
        return {
            key: binding
            for key, binding in self.bindings.items()
            if binding.category == category
        }
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Event filter for handling keyboard events.
        
        Args:
            obj: Object that received the event
            event: The event
            
        Returns:
            True if event was handled
        """
        if not PYQT6_AVAILABLE:
            return False
        
        if event.type() == QEvent.Type.KeyPress:
            # Handle Tab navigation
            if event.key() == Qt.Key.Key_Tab:
                return self._handle_tab_navigation(obj, event)
        
        return super().eventFilter(obj, event)
    
    def _handle_tab_navigation(self, obj: QObject, event: QEvent) -> bool:
        """Handle Tab key navigation between panels."""
        # Let Qt handle default Tab navigation
        return False


def setup_default_shortcuts(window: QMainWindow, manager: KeyboardNavigationManager):
    """
    Setup default keyboard shortcuts for the application.
    
    Args:
        window: Main window instance
        manager: Keyboard navigation manager
    """
    # File operations
    manager.register_shortcut(
        "Ctrl+N",
        window.new_file,
        "New File",
        "File"
    )
    
    manager.register_shortcut(
        "Ctrl+O",
        window.open_file,
        "Open File",
        "File"
    )
    
    manager.register_shortcut(
        "Ctrl+S",
        window.save_file,
        "Save File",
        "File"
    )
    
    manager.register_shortcut(
        "Ctrl+Q",
        window.close,
        "Quit Application",
        "File"
    )
    
    # View operations
    manager.register_shortcut(
        "F5",
        window.refresh_ui,
        "Refresh UI",
        "View"
    )
    
    manager.register_shortcut(
        "F11",
        lambda: window.showFullScreen() if not window.isFullScreen() else window.showNormal(),
        "Toggle Fullscreen",
        "View"
    )
    
    # Help
    manager.register_shortcut(
        "F1",
        lambda: window.show_about(),
        "Show Help",
        "Help"
    )
    
    logger.info("Default shortcuts configured")


# Common key sequences as constants
class KeySequences:
    """Common keyboard shortcuts."""
    
    # File
    NEW_FILE = "Ctrl+N"
    OPEN_FILE = "Ctrl+O"
    SAVE_FILE = "Ctrl+S"
    SAVE_AS = "Ctrl+Shift+S"
    CLOSE_FILE = "Ctrl+W"
    QUIT = "Ctrl+Q"
    
    # Edit
    UNDO = "Ctrl+Z"
    REDO = "Ctrl+Y"
    CUT = "Ctrl+X"
    COPY = "Ctrl+C"
    PASTE = "Ctrl+V"
    SELECT_ALL = "Ctrl+A"
    FIND = "Ctrl+F"
    REPLACE = "Ctrl+H"
    
    # View
    ZOOM_IN = "Ctrl++"
    ZOOM_OUT = "Ctrl+-"
    ZOOM_RESET = "Ctrl+0"
    FULLSCREEN = "F11"
    REFRESH = "F5"
    
    # Navigation
    NEXT_TAB = "Ctrl+Tab"
    PREV_TAB = "Ctrl+Shift+Tab"
    NEXT_PANEL = "Alt+Right"
    PREV_PANEL = "Alt+Left"
    
    # Application
    SETTINGS = "Alt+S"
    NEW_TASK = "Alt+N"
    HELP = "F1"
