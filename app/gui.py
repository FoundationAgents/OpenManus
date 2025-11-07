"""
PyQt6 GUI interface for the OpenManus agent framework.
Provides a modern, cross-platform desktop interface for agent interaction.
"""

import asyncio
import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter,
        QTabWidget, QScrollArea, QFrame, QComboBox, QCheckBox,
        QProgressBar, QMessageBox, QFileDialog, QMenuBar, QStatusBar,
        QToolBar, QAction, QDockWidget, QListWidget, QTreeWidgetItem,
        QTreeWidget, QGroupBox, QRadioButton, QSlider
    )
    from PyQt6.QtCore import (
        Qt, QThread, pyqtSignal, QTimer, QSize, QSettings,
        pyqtSlot, QObject
    )
    from PyQt6.QtGui import (
        QFont, QIcon, QPixmap, QPalette, QColor, QSyntaxHighlighter,
        QTextCharFormat, QTextDocument, QAction as QGuiAction
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    
    # Create dummy classes for when PyQt6 is not available
    class QWidget:
        pass
    class QMainWindow:
        pass
    class QApplication:
        pass

from app.config import config
from app.logger import logger
from app.agent.manus import Manus
from app.flow.flow_factory import FlowFactory, FlowType


class WorkerThread(QThread):
    """Worker thread for running agent tasks asynchronously."""
    
    response_received = pyqtSignal(str, str)  # agent_id, response
    error_occurred = pyqtSignal(str, str)  # agent_id, error
    task_completed = pyqtSignal(str, bool)  # agent_id, success
    status_update = pyqtSignal(str, str)  # agent_id, status
    
    def __init__(self, agent_id: str, prompt: str, mode: str = "chat"):
        super().__init__()
        self.agent_id = agent_id
        self.prompt = prompt
        self.mode = mode
        self._running = True
        
    def run(self):
        """Run the agent task."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if self.mode == "chat":
                result = loop.run_until_complete(self._run_chat())
            else:
                result = loop.run_until_complete(self._run_agent_flow())
                
            self.task_completed.emit(self.agent_id, True)
            self.response_received.emit(self.agent_id, result)
            
        except Exception as e:
            logger.error(f"Worker thread error: {e}")
            self.error_occurred.emit(self.agent_id, str(e))
            self.task_completed.emit(self.agent_id, False)
            
    async def _run_chat(self) -> str:
        """Run chat mode with Manus agent."""
        agent = await Manus.create()
        try:
            self.status_update.emit(self.agent_id, "Initializing agent...")
            result = await agent.run(self.prompt)
            return str(result)
        finally:
            await agent.cleanup()
            
    async def _run_agent_flow(self) -> str:
        """Run agent flow mode."""
        from app.agent.manus import Manus
        from app.agent.data_analysis import DataAnalysis
        
        agents = {"manus": await Manus.create()}
        if config.run_flow_config.use_data_analysis_agent:
            agents["data_analysis"] = DataAnalysis()
            
        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        
        self.status_update.emit(self.agent_id, "Executing agent flow...")
        result = await flow.execute(self.prompt)
        return str(result)
        
    def stop(self):
        """Stop the worker thread."""
        self._running = False


class SyntaxHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter for code blocks."""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        
    def highlightBlock(self, text: str):
        """Highlight text blocks."""
        # Simple highlighting for code blocks
        if text.strip().startswith("```"):
            format = QTextCharFormat()
            format.setForeground(QColor("#888888"))
            self.setFormat(0, len(text), format)


class ChatWidget(QWidget):
    """Widget for chat interactions."""
    
    send_request = pyqtSignal(str, str)  # prompt, mode
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["chat", "agent_flow", "ade"])
        mode_layout.addWidget(self.mode_combo)
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        
        # Apply syntax highlighting
        self.highlighter = SyntaxHighlighter(self.chat_display.document())
        
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter your prompt here...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
    def send_message(self):
        """Send the current message."""
        prompt = self.input_field.text().strip()
        if prompt:
            mode = self.mode_combo.currentText()
            self.send_request.emit(prompt, mode)
            self.input_field.clear()
            
    def add_message(self, sender: str, message: str, timestamp: Optional[str] = None):
        """Add a message to the chat display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
        formatted_message = f"[{timestamp}] {sender}: {message}\n"
        self.chat_display.append(formatted_message)
        
    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()


class ProcessMonitorWidget(QWidget):
    """Widget for monitoring running processes."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Process list
        self.process_list = QTreeWidget()
        self.process_list.setHeaderLabels(["Process ID", "Command", "Status", "PID"])
        self.process_list.setColumnCount(4)
        
        layout.addWidget(self.process_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_processes)
        button_layout.addWidget(self.refresh_button)
        
        self.terminate_button = QPushButton("Terminate")
        self.terminate_button.clicked.connect(self.terminate_selected)
        button_layout.addWidget(self.terminate_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def setup_timer(self):
        """Setup auto-refresh timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_processes)
        self.timer.start(5000)  # Refresh every 5 seconds
        
    def refresh_processes(self):
        """Refresh the process list."""
        try:
            from app.local_service import local_service
            processes = local_service.list_processes()
            
            self.process_list.clear()
            
            for proc_info in processes:
                item = QTreeWidgetItem([
                    proc_info["process_id"][:8] + "...",
                    proc_info["command"][:50] + "..." if len(proc_info["command"]) > 50 else proc_info["command"],
                    "Running" if proc_info["is_running"] else "Stopped",
                    str(proc_info["pid"])
                ])
                self.process_list.addTopLevelItem(item)
                
        except Exception as e:
            logger.error(f"Error refreshing processes: {e}")
            
    def terminate_selected(self):
        """Terminate the selected process."""
        current_item = self.process_list.currentItem()
        if current_item:
            process_id = current_item.text(0)
            # In a real implementation, you'd need to store the full process ID
            QMessageBox.information(self, "Terminate Process", f"Process {process_id} termination requested")


class FileExplorerWidget(QWidget):
    """Widget for exploring workspace files."""
    
    file_selected = pyqtSignal(str)  # file_path
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_directory = "."
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        self.path_label = QLabel("Path: .")
        nav_layout.addWidget(self.path_label)
        
        nav_layout.addStretch()
        
        self.up_button = QPushButton("Up")
        self.up_button.clicked.connect(self.go_up)
        nav_layout.addWidget(self.up_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_files)
        nav_layout.addWidget(self.refresh_button)
        
        layout.addLayout(nav_layout)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.file_list)
        
        self.setLayout(layout)
        
    def refresh_files(self):
        """Refresh the file list."""
        try:
            from app.local_service import local_service
            files = local_service.list_files(self.current_directory)
            
            self.file_list.clear()
            
            # Add parent directory option
            if self.current_directory != ".":
                self.file_list.addItem("../")
                
            # Add directories first
            for file_path in files:
                if file_path.endswith("/"):
                    self.file_list.addItem(file_path)
                    
            # Add files
            for file_path in files:
                if not file_path.endswith("/"):
                    self.file_list.addItem(file_path)
                    
            self.path_label.setText(f"Path: {self.current_directory}")
            
        except Exception as e:
            logger.error(f"Error refreshing files: {e}")
            
    def on_item_double_clicked(self, item):
        """Handle double-click on file items."""
        file_name = item.text()
        
        if file_name.endswith("/"):
            # Directory
            if file_name == "../":
                self.go_up()
            else:
                if self.current_directory == ".":
                    self.current_directory = file_name.rstrip("/")
                else:
                    self.current_directory = f"{self.current_directory}/{file_name.rstrip('/')}"
                self.refresh_files()
        else:
            # File
            if self.current_directory == ".":
                full_path = file_name
            else:
                full_path = f"{self.current_directory}/{file_name}"
            self.file_selected.emit(full_path)
            
    def go_up(self):
        """Go up one directory."""
        if self.current_directory != ".":
            parts = self.current_directory.split("/")
            if len(parts) > 1:
                self.current_directory = "/".join(parts[:-1])
            else:
                self.current_directory = "."
            self.refresh_files()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.workers: Dict[str, WorkerThread] = {}
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the main UI."""
        self.setWindowTitle("OpenManus - Advanced Agent Framework")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Chat
        self.chat_widget = ChatWidget()
        self.chat_widget.send_request.connect(self.handle_send_request)
        splitter.addWidget(self.chat_widget)
        
        # Right panel - Tabs
        right_panel = QTabWidget()
        
        # Process monitor tab
        self.process_monitor = ProcessMonitorWidget()
        right_panel.addTab(self.process_monitor, "Processes")
        
        # File explorer tab
        self.file_explorer = FileExplorerWidget()
        self.file_explorer.file_selected.connect(self.handle_file_selected)
        right_panel.addTab(self.file_explorer, "Files")
        
        # Settings tab
        self.settings_widget = self.create_settings_widget()
        right_panel.addTab(self.settings_widget, "Settings")
        
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
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
        
        new_action = QAction("New Chat", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Workspace", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        theme_menu = view_menu.addMenu("Theme")
        
        light_action = QAction("Light", self)
        light_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_action)
        
        dark_action = QAction("Dark", self)
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Clear chat action
        clear_action = QAction("Clear Chat", self)
        clear_action.triggered.connect(self.chat_widget.clear_chat)
        toolbar.addAction(clear_action)
        
        toolbar.addSeparator()
        
        # Mode actions
        chat_action = QAction("Chat Mode", self)
        chat_action.triggered.connect(lambda: self.set_mode("chat"))
        toolbar.addAction(chat_action)
        
        flow_action = QAction("Agent Flow", self)
        flow_action.triggered.connect(lambda: self.set_mode("agent_flow"))
        toolbar.addAction(flow_action)
        
        ade_action = QAction("ADE Mode", self)
        ade_action.triggered.connect(lambda: self.set_mode("ade"))
        toolbar.addAction(ade_action)
        
    def create_settings_widget(self) -> QWidget:
        """Create the settings widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # LLM Settings
        llm_group = QGroupBox("LLM Settings")
        llm_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(config.llm.keys()))
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        llm_layout.addLayout(model_layout)
        
        # API settings
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_input)
        llm_layout.addLayout(api_layout)
        
        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)
        
        # Local Service Settings
        service_group = QGroupBox("Local Service Settings")
        service_layout = QVBoxLayout()
        
        # Enable local service
        self.enable_local_service = QCheckBox("Enable Local Service")
        self.enable_local_service.setChecked(config.local_service.use_local_service)
        service_layout.addWidget(self.enable_local_service)
        
        # Workspace directory
        workspace_layout = QHBoxLayout()
        workspace_layout.addWidget(QLabel("Workspace:"))
        self.workspace_input = QLineEdit()
        self.workspace_input.setText(config.local_service.workspace_directory)
        workspace_layout.addWidget(self.workspace_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_workspace)
        workspace_layout.addWidget(browse_button)
        
        service_layout.addLayout(workspace_layout)
        service_group.setLayout(service_layout)
        layout.addWidget(service_group)
        
        # UI Settings
        ui_group = QGroupBox("UI Settings")
        ui_layout = QVBoxLayout()
        
        # Theme selection
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "auto"])
        self.theme_combo.setCurrentText(config.ui.theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        ui_layout.addLayout(theme_layout)
        
        # Auto-save
        self.auto_save_check = QCheckBox("Auto-save conversations")
        self.auto_save_check.setChecked(config.ui.auto_save)
        ui_layout.addWidget(self.auto_save_check)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
        
    def apply_theme(self):
        """Apply the current theme."""
        theme = config.ui.theme
        
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
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
            """)
        else:
            self.setStyleSheet("")  # Use default light theme
            
    def set_theme(self, theme: str):
        """Set the application theme."""
        config.ui.theme = theme
        self.apply_theme()
        
    def set_mode(self, mode: str):
        """Set the current mode."""
        self.chat_widget.mode_combo.setCurrentText(mode)
        self.status_bar.showMessage(f"Mode: {mode}")
        
    def new_chat(self):
        """Start a new chat."""
        self.chat_widget.clear_chat()
        self.status_bar.showMessage("New chat started")
        
    def open_workspace(self):
        """Open a workspace directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace Directory")
        if directory:
            self.workspace_input.setText(directory)
            config.local_service.workspace_directory = directory
            self.file_explorer.current_directory = "."
            self.file_explorer.refresh_files()
            
    def browse_workspace(self):
        """Browse for workspace directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace Directory")
        if directory:
            self.workspace_input.setText(directory)
            
    def handle_send_request(self, prompt: str, mode: str):
        """Handle a send request from the chat widget."""
        agent_id = f"agent_{len(self.workers)}"
        
        # Add user message to chat
        self.chat_widget.add_message("User", prompt)
        
        # Create and start worker
        worker = WorkerThread(agent_id, prompt, mode)
        worker.response_received.connect(self.handle_response)
        worker.error_occurred.connect(self.handle_error)
        worker.task_completed.connect(self.handle_task_completed)
        worker.status_update.connect(self.handle_status_update)
        
        self.workers[agent_id] = worker
        worker.start()
        
        self.status_bar.showMessage(f"Processing request with {mode} mode...")
        
    def handle_response(self, agent_id: str, response: str):
        """Handle a response from a worker."""
        self.chat_widget.add_message("Agent", response)
        
    def handle_error(self, agent_id: str, error: str):
        """Handle an error from a worker."""
        self.chat_widget.add_message("Error", f"Agent error: {error}")
        self.status_bar.showMessage(f"Error: {error}")
        
    def handle_task_completed(self, agent_id: str, success: bool):
        """Handle task completion."""
        if agent_id in self.workers:
            del self.workers[agent_id]
            
        if success:
            self.status_bar.showMessage("Task completed successfully")
        else:
            self.status_bar.showMessage("Task completed with errors")
            
    def handle_status_update(self, agent_id: str, status: str):
        """Handle status updates."""
        self.status_bar.showMessage(f"Agent {agent_id}: {status}")
        
    def handle_file_selected(self, file_path: str):
        """Handle file selection."""
        # In a real implementation, you might open a file viewer/editor
        self.status_bar.showMessage(f"Selected file: {file_path}")
        
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(self, "About OpenManus", 
                         "OpenManus - Advanced Agent Framework\n\n"
                         "A powerful agent framework with multi-modal capabilities,\n"
                         "local execution, and intelligent planning.")
                         
    def load_settings(self):
        """Load application settings."""
        settings = QSettings("OpenManus", "AgentFramework")
        
        # Restore window geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # Restore other settings as needed
        
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop all workers
        for worker in self.workers.values():
            worker.stop()
            worker.wait()
            
        # Save settings
        settings = QSettings("OpenManus", "AgentFramework")
        settings.setValue("geometry", self.saveGeometry())
        
        # Cleanup local service
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.cleanup_resources())
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        event.accept()
        
    async def cleanup_resources(self):
        """Cleanup application resources."""
        from app.local_service import local_service
        await local_service.cleanup()


def run_gui():
    """Run the PyQt6 GUI application."""
    if not PYQT6_AVAILABLE:
        logger.error("PyQt6 is not installed. GUI mode is not available.")
        logger.info("To install PyQt6, run: pip install PyQt6")
        return
        
    app = QApplication(sys.argv)
    app.setApplicationName("OpenManus")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())