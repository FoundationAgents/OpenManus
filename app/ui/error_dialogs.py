"""
User-friendly error dialogs and messages.

Shows friendly error messages to users without exposing technical stack traces.
"""

import logging
from typing import Optional
from enum import Enum

try:
    from PyQt6.QtWidgets import (
        QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton,
        QTextEdit, QHBoxLayout, QWidget
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object
    QMessageBox = object

from app.ui.message_bus import get_message_bus, EventTypes

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorDialog(QDialog):
    """
    User-friendly error dialog.
    
    Shows a friendly error message with optional details and suggestions.
    """
    
    def __init__(
        self,
        title: str,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.message = message
        self.details = details
        self.suggestion = suggestion
        self.severity = severity
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the error dialog UI."""
        self.setWindowTitle(self.title)
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Error message
        message_label = QLabel(f"<b>{self.message}</b>")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Suggestion
        if self.suggestion:
            layout.addSpacing(10)
            suggestion_label = QLabel(f"💡 <i>{self.suggestion}</i>")
            suggestion_label.setWordWrap(True)
            suggestion_label.setStyleSheet("color: #0066cc;")
            layout.addWidget(suggestion_label)
        
        # Details (collapsible)
        if self.details:
            layout.addSpacing(10)
            
            details_label = QLabel("Technical Details:")
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setPlainText(self.details)
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            layout.addWidget(details_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)
        
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)


def show_error(
    title: str,
    message: str,
    details: Optional[str] = None,
    suggestion: Optional[str] = None,
    parent=None
) -> None:
    """
    Show an error dialog.
    
    Args:
        title: Dialog title
        message: User-friendly error message
        details: Technical details (optional)
        suggestion: Suggestion for fixing the error (optional)
        parent: Parent widget
    """
    if not PYQT6_AVAILABLE:
        logger.error(f"{title}: {message}")
        if details:
            logger.error(f"Details: {details}")
        return
    
    dialog = ErrorDialog(
        title=title,
        message=message,
        details=details,
        suggestion=suggestion,
        severity=ErrorSeverity.ERROR,
        parent=parent
    )
    dialog.exec()
    
    # Log the error
    logger.error(f"{title}: {message}")
    if details:
        logger.debug(f"Error details: {details}")
    
    # Publish to message bus
    message_bus = get_message_bus()
    message_bus.publish(EventTypes.ERROR_OCCURRED, {
        "title": title,
        "message": message,
        "details": details,
        "suggestion": suggestion
    })


def show_warning(
    title: str,
    message: str,
    parent=None
) -> None:
    """
    Show a warning dialog.
    
    Args:
        title: Dialog title
        message: Warning message
        parent: Parent widget
    """
    if not PYQT6_AVAILABLE:
        logger.warning(f"{title}: {message}")
        return
    
    QMessageBox.warning(parent, title, message)
    logger.warning(f"{title}: {message}")


def show_info(
    title: str,
    message: str,
    parent=None
) -> None:
    """
    Show an info dialog.
    
    Args:
        title: Dialog title
        message: Info message
        parent: Parent widget
    """
    if not PYQT6_AVAILABLE:
        logger.info(f"{title}: {message}")
        return
    
    QMessageBox.information(parent, title, message)
    logger.info(f"{title}: {message}")


def ask_yes_no(
    title: str,
    message: str,
    parent=None
) -> bool:
    """
    Ask a yes/no question.
    
    Args:
        title: Dialog title
        message: Question message
        parent: Parent widget
        
    Returns:
        True if user clicked Yes
    """
    if not PYQT6_AVAILABLE:
        logger.info(f"{title}: {message}")
        return True  # Default to yes
    
    result = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    
    return result == QMessageBox.StandardButton.Yes


# Common error messages with friendly translations

def show_llm_connection_error(error: str, parent=None):
    """Show LLM connection error."""
    show_error(
        title="LLM Connection Failed",
        message="Unable to connect to the language model endpoint.",
        details=error,
        suggestion="Check your internet connection and LLM API settings in Preferences.",
        parent=parent
    )


def show_component_load_error(component_name: str, error: str, parent=None):
    """Show component load error."""
    show_error(
        title="Component Load Failed",
        message=f"The {component_name} component failed to load.",
        details=error,
        suggestion="Try restarting the application or check if dependencies are installed.",
        parent=parent
    )


def show_file_error(operation: str, file_path: str, error: str, parent=None):
    """Show file operation error."""
    show_error(
        title=f"File {operation.title()} Failed",
        message=f"Unable to {operation} the file: {file_path}",
        details=error,
        suggestion="Check file permissions and ensure the path is correct.",
        parent=parent
    )


def show_tool_error(tool_name: str, error: str, parent=None):
    """Show tool execution error."""
    show_error(
        title="Tool Execution Failed",
        message=f"The {tool_name} tool encountered an error.",
        details=error,
        suggestion="Check the tool configuration and try again.",
        parent=parent
    )


def show_agent_error(agent_name: str, error: str, parent=None):
    """Show agent error."""
    show_error(
        title="Agent Error",
        message=f"Agent '{agent_name}' encountered an error.",
        details=error,
        suggestion="Check agent configuration and ensure all dependencies are available.",
        parent=parent
    )


def show_network_error(operation: str, error: str, parent=None):
    """Show network error."""
    show_error(
        title="Network Error",
        message=f"Network operation failed: {operation}",
        details=error,
        suggestion="Check your internet connection and firewall settings.",
        parent=parent
    )


def show_dependency_error(component: str, missing_deps: list[str], parent=None):
    """Show dependency error."""
    deps_str = ", ".join(missing_deps)
    show_error(
        title="Missing Dependencies",
        message=f"Cannot load {component} due to missing dependencies.",
        details=f"Missing: {deps_str}",
        suggestion=f"Install missing dependencies: pip install {' '.join(missing_deps)}",
        parent=parent
    )


def show_configuration_error(setting_name: str, error: str, parent=None):
    """Show configuration error."""
    show_error(
        title="Configuration Error",
        message=f"Invalid configuration for {setting_name}.",
        details=error,
        suggestion="Check your settings in Preferences and ensure all required fields are filled.",
        parent=parent
    )


class ErrorHandler:
    """
    Global error handler that shows user-friendly error dialogs.
    
    Can be used as a context manager or decorator.
    
    Example:
        with ErrorHandler("Loading File"):
            load_file(path)
    """
    
    def __init__(self, operation: str, parent=None):
        self.operation = operation
        self.parent = parent
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            show_error(
                title=f"{self.operation} Failed",
                message=f"An error occurred during: {self.operation}",
                details=str(exc_val),
                parent=self.parent
            )
            return True  # Suppress the exception
        return False
    
    def __call__(self, func):
        """Use as a decorator."""
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper
