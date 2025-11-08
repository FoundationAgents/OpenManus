"""
Main IDE window with dockable panels and central code editor.
"""

import asyncio
import sys
from typing import Dict, Optional

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QDockWidget,
        QSplitter, QMenuBar, QStatusBar, QToolBar, QAction, QMessageBox,
        QFileDialog, QApplication, QComboBox, QLabel, QLineEdit, QPushButton,
        QGroupBox
    )
    from PyQt6.QtCore import (
        Qt, QSettings, QSize, pyqtSignal, pyqtSlot, QThread, QTimer
    )
    from PyQt6.QtGui import QIcon, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QMainWindow:
        pass
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()


from app.ui.panels import (
    CodeEditorPanel,
    AgentControlPanel,
    WorkflowVisualizerPanel,
    CommandLogPanel,
    ConsolePanel,
    AgentMonitorPanel,
    SecurityMonitorPanel,
    KnowledgeGraphPanel,
    RetrievalInsightsPanel,
    BackupPanel,
    ResourceCatalogPanel,
)
from app.ui.dialogs import CommandValidationDialog
from app.config import config
from app.logger import logger


class MainWindow(QMainWindow):
    """Main IDE window with dockable panels for agent orchestration."""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("OpenManus", "IDE")
        self.workers: Dict[str, QThread] = {}
        self.init_ui()
        self.load_layout()
        
    def init_ui(self):
        """Initialize the main window UI."""
        self.setWindowTitle("OpenManus IDE - Agent Development Environment")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget with code editor
        self.central_editor = CodeEditorPanel()
        self.setCentralWidget(self.central_editor)
        
        # Create dock panels
        self.create_docks()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply theme
        self.apply_theme()
        
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_file = QAction("New File", self)
        new_file.setShortcut("Ctrl+N")
        new_file.triggered.connect(self.new_file)
        file_menu.addAction(new_file)
        
        open_file = QAction("Open File", self)
        open_file.setShortcut("Ctrl+O")
        open_file.triggered.connect(self.open_file)
        file_menu.addAction(open_file)
        
        save_file = QAction("Save File", self)
        save_file.setShortcut("Ctrl+S")
        save_file.triggered.connect(self.save_file)
        file_menu.addAction(save_file)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Window arrangement options
        arrange_menu = view_menu.addMenu("Layout")
        
        reset_layout = QAction("Reset Layout", self)
        reset_layout.triggered.connect(self.reset_layout)
        arrange_menu.addAction(reset_layout)
        
        arrange_menu.addSeparator()
        
        # Theme submenu
        theme_menu = view_menu.addMenu("Theme")
        
        light_action = QAction("Light", self)
        light_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_action)
        
        dark_action = QAction("Dark", self)
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_action)
        
        # Window menu
        window_menu = menubar.addMenu("Window")
        
        # Toggles for dock visibility
        for dock_name in ["Editor", "Agent Control", "Workflow", "Logs", "Console", "Monitor"]:
            action = QAction(f"Toggle {dock_name} Panel", self)
            action.setCheckable(True)
            action.setChecked(True)
            window_menu.addAction(action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        validate_cmd = QAction("Validate Command", self)
        validate_cmd.triggered.connect(self.show_command_validation)
        tools_menu.addAction(validate_cmd)
        
        tools_menu.addSeparator()
        
        workspace_action = QAction("Select Workspace", self)
        workspace_action.triggered.connect(self.select_workspace)
        tools_menu.addAction(workspace_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # File operations
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Workspace selector
        toolbar.addWidget(QLabel("Workspace:"))
        
        self.workspace_combo = QComboBox()
        self.workspace_combo.addItems(["Default", "Project A", "Project B"])
        toolbar.addWidget(self.workspace_combo)
        
        toolbar.addStretch()
        
        # Quick actions
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_ui)
        toolbar.addAction(refresh_action)
        
    def create_docks(self):
        """Create dockable panels."""
        
        # Agent Control Dock
        self.agent_dock = QDockWidget("Agent Control", self)
        self.agent_panel = AgentControlPanel()
        self.agent_dock.setWidget(self.agent_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.agent_dock)
        
        # Workflow Dock
        self.workflow_dock = QDockWidget("Workflow", self)
        self.workflow_panel = WorkflowVisualizerPanel()
        self.workflow_dock.setWidget(self.workflow_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.workflow_dock)
        
        # Command Log Dock
        self.log_dock = QDockWidget("Command Log", self)
        self.log_panel = CommandLogPanel()
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        
        # Console Dock
        self.console_dock = QDockWidget("Sandbox Console", self)
        self.console_panel = ConsolePanel()
        self.console_dock.setWidget(self.console_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)
        
        # Agent Monitor Dock
        self.monitor_dock = QDockWidget("Agent Status", self)
        self.monitor_panel = AgentMonitorPanel()
        self.monitor_dock.setWidget(self.monitor_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.monitor_dock)
        
        # Security Monitor Dock
        self.security_dock = QDockWidget("Security Monitor", self)
        self.security_panel = SecurityMonitorPanel()
        self.security_dock.setWidget(self.security_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.security_dock)
        
        # Knowledge Graph Dock
        self.knowledge_dock = QDockWidget("Knowledge Graph", self)
        self.knowledge_panel = KnowledgeGraphPanel()
        self.knowledge_dock.setWidget(self.knowledge_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.knowledge_dock)
        
        # Retrieval Insights Dock
        self.retrieval_dock = QDockWidget("Retrieval Insights", self)
        self.retrieval_panel = RetrievalInsightsPanel()
        self.retrieval_dock.setWidget(self.retrieval_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.retrieval_dock)
        
        # Backup Dock
        self.backup_dock = QDockWidget("Backup Management", self)
        self.backup_panel = BackupPanel()
        self.backup_dock.setWidget(self.backup_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.backup_dock)

        # Resource Catalog Dock
        self.resource_dock = QDockWidget("Resource Catalog", self)
        self.resource_panel = ResourceCatalogPanel()
        self.resource_dock.setWidget(self.resource_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.resource_dock)
        
        # Tab the right docks together
        self.tabifyDockWidget(self.agent_dock, self.workflow_dock)
        self.tabifyDockWidget(self.workflow_dock, self.monitor_dock)
        self.tabifyDockWidget(self.monitor_dock, self.security_dock)
        self.tabifyDockWidget(self.security_dock, self.knowledge_dock)
        self.tabifyDockWidget(self.knowledge_dock, self.retrieval_dock)
        
        # Tab the bottom docks together
        self.tabifyDockWidget(self.log_dock, self.console_dock)
        self.tabifyDockWidget(self.backup_dock, self.resource_dock)
        
        # Set initial active tabs
        self.agent_dock.raise_()
        self.log_dock.raise_()
        
    def new_file(self):
        """Create a new file."""
        self.central_editor.clear_editor()
        self.status_bar.showMessage("New file created")
        
    def open_file(self):
        """Open a file."""
        self.central_editor.open_file()
        
    def save_file(self):
        """Save the current file."""
        self.central_editor.save_file()
        
    def select_workspace(self):
        """Select a workspace directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if directory:
            config.local_service.workspace_directory = directory
            self.status_bar.showMessage(f"Workspace changed to {directory}")
            
    def show_command_validation(self):
        """Show command validation dialog."""
        dialog = CommandValidationDialog(
            "ls -la /etc",
            "This command accesses system configuration files"
        )
        result = dialog.exec()
        if result == 1:  # Accepted
            self.status_bar.showMessage("Command approved")
        else:
            self.status_bar.showMessage("Command rejected")
            
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OpenManus IDE",
            "OpenManus IDE - Agent Development Environment\n\n"
            "A comprehensive IDE for agent orchestration and execution.\n\n"
            "Features:\n"
            "- Code editing with syntax highlighting\n"
            "- Agent orchestration and control\n"
            "- Workflow visualization\n"
            "- Real-time monitoring and logging\n"
            "- Command validation through Guardian\n"
        )
        
    def refresh_ui(self):
        """Refresh the UI."""
        self.log_panel.add_log("info", "UI refreshed")
        self.status_bar.showMessage("UI refreshed")
        
    def apply_theme(self):
        """Apply the current theme."""
        theme = config.ui.theme
        
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QDockWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3c3f41;
                }
                QTextEdit {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QLineEdit {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QPushButton {
                    background-color: #4c5052;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QPushButton:hover {
                    background-color: #5c6062;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #4c5052;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: #4c5052;
                }
                QToolBar {
                    background-color: #2b2b2b;
                    border: 1px solid #3c3f41;
                }
                QComboBox {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QTableWidget {
                    background-color: #3c3f41;
                    color: #ffffff;
                    gridline-color: #555555;
                }
                QHeaderView::section {
                    background-color: #4c5052;
                    color: #ffffff;
                    padding: 5px;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("")
            
    def set_theme(self, theme: str):
        """Set the application theme."""
        config.ui.theme = theme
        self.settings.setValue("theme", theme)
        self.apply_theme()
        self.status_bar.showMessage(f"Theme changed to {theme}")
        
    def reset_layout(self):
        """Reset the layout to default."""
        # Restore default dock positions
        self.agent_dock.setFloating(False)
        self.workflow_dock.setFloating(False)
        self.log_dock.setFloating(False)
        self.console_dock.setFloating(False)
        self.monitor_dock.setFloating(False)
        self.backup_dock.setFloating(False)
        self.resource_dock.setFloating(False)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.agent_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.workflow_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.monitor_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.backup_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.resource_dock)
        self.tabifyDockWidget(self.backup_dock, self.resource_dock)
        
        self.status_bar.showMessage("Layout reset to default")
        
    def load_layout(self):
        """Load saved layout and state."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
            
        theme = self.settings.value("theme", "light")
        config.ui.theme = theme
        
    def closeEvent(self, event):
        """Handle window close event."""
        # Save layout and state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("theme", config.ui.theme)
        
        # Stop all workers
        for worker in self.workers.values():
            if hasattr(worker, 'stop'):
                worker.stop()
            worker.quit()
            worker.wait()
            
        event.accept()


def run_gui():
    """Run the PyQt6 GUI application."""
    if not PYQT6_AVAILABLE:
        logger.error("PyQt6 is not installed. GUI mode is not available.")
        logger.info("To install PyQt6, run: pip install PyQt6")
        return
        
    app = QApplication(sys.argv)
    app.setApplicationName("OpenManus IDE")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
