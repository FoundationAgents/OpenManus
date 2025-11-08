"""
UI package for OpenManus IDE-style interface.

Provides a multi-pane IDE layout with dockable widgets for code editing,
agent orchestration, command validation, workflows, logs, and monitoring.

GUI-First Architecture:
- Message Bus: Decoupled component communication
- State Manager: Centralized state management
- Component Discovery: Auto-discover and load panels
- Progressive Loading: Non-blocking UI initialization
- Theme Engine: Customizable themes
- Error Dialogs: User-friendly error handling
"""

from app.ui.main_window import MainWindow
from app.ui.message_bus import get_message_bus, MessageBus, EventTypes
from app.ui.state_manager import get_state_manager, StateManager
from app.ui.component_discovery import get_component_discovery, ComponentDiscovery
from app.ui.progressive_loading import ProgressiveLoader, load_ui_progressively
from app.ui.async_ui_updates import get_task_manager, AsyncTaskManager, run_async
from app.ui.error_dialogs import (
    show_error, show_warning, show_info, ask_yes_no, ErrorHandler
)
from app.ui.keyboard_navigation import KeyboardNavigationManager, KeySequences

__all__ = [
    # Main window
    "MainWindow",
    
    # Core architecture
    "get_message_bus",
    "MessageBus",
    "EventTypes",
    "get_state_manager",
    "StateManager",
    "get_component_discovery",
    "ComponentDiscovery",
    
    # Loading and async
    "ProgressiveLoader",
    "load_ui_progressively",
    "get_task_manager",
    "AsyncTaskManager",
    "run_async",
    
    # User interaction
    "show_error",
    "show_warning",
    "show_info",
    "ask_yes_no",
    "ErrorHandler",
    "KeyboardNavigationManager",
    "KeySequences",
]
