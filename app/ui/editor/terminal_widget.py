"""Integrated terminal widget for executing commands."""

import asyncio
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
        QLineEdit, QLabel, QComboBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont, QColor, QTextCharFormat
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.logger import logger
from app.local_service import local_service


class TerminalOutputWidget(QPlainTextEdit):
    """Terminal output display widget."""
    
    def __init__(self, parent=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is required for TerminalOutputWidget")
        
        super().__init__(parent)
        self.setReadOnly(True)
        
        font = QFont("Courier New", 9)
        font.setFixedPitch(True)
        self.setFont(font)
        
        self.stdout_format = QTextCharFormat()
        self.stdout_format.setForeground(QColor("#00ff00"))
        
        self.stderr_format = QTextCharFormat()
        self.stderr_format.setForeground(QColor("#ff0000"))
        
        self.info_format = QTextCharFormat()
        self.info_format.setForeground(QColor("#00aaff"))
    
    def append_stdout(self, text: str) -> None:
        """Append stdout text."""
        cursor = self.textCursor()
        cursor.movePosition(1)
        cursor.insertText(text, self.stdout_format)
        self.setTextCursor(cursor)
    
    def append_stderr(self, text: str) -> None:
        """Append stderr text."""
        cursor = self.textCursor()
        cursor.movePosition(1)
        cursor.insertText(text, self.stderr_format)
        self.setTextCursor(cursor)
    
    def append_info(self, text: str) -> None:
        """Append info text."""
        cursor = self.textCursor()
        cursor.movePosition(1)
        cursor.insertText(text, self.info_format)
        self.setTextCursor(cursor)
    
    def clear_output(self) -> None:
        """Clear all output."""
        self.clear()


class CommandExecutor(QThread):
    """Worker thread for executing commands asynchronously."""
    
    output_ready = pyqtSignal(str, str)  # output_type, text
    execution_finished = pyqtSignal(int, str, str)  # exit_code, stdout, stderr
    
    def __init__(self, command: str, cwd: Optional[str] = None):
        super().__init__()
        self.command = command
        self.cwd = cwd
    
    def run(self):
        """Execute the command in a worker thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._execute())
            
            exit_code = result.get("exit_code", -1)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            
            self.execution_finished.emit(exit_code, stdout, stderr)
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            self.execution_finished.emit(-1, "", str(e))
    
    async def _execute(self):
        """Execute the command asynchronously."""
        result = await local_service.execute_command(
            self.command,
            cwd=self.cwd,
            capture_output=True
        )
        return result


class TerminalWidget(QWidget):
    """Integrated terminal widget for executing commands."""
    
    def __init__(self, parent=None, workspace_dir: str = "./workspace"):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is required for TerminalWidget")
        
        super().__init__(parent)
        self.workspace_dir = workspace_dir
        self.current_process_id: Optional[str] = None
        self.executor_thread: Optional[CommandExecutor] = None
        
        self._setup_ui()
        logger.info(f"Initialized TerminalWidget with workspace: {workspace_dir}")
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        control_layout = QHBoxLayout()
        
        label = QLabel("Command:")
        control_layout.addWidget(label)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command (e.g., python script.py, npm run build)")
        self.command_input.returnPressed.connect(self._on_execute_command)
        control_layout.addWidget(self.command_input)
        
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self._on_execute_command)
        control_layout.addWidget(self.execute_button)
        
        self.kill_button = QPushButton("Kill")
        self.kill_button.clicked.connect(self._on_kill_process)
        self.kill_button.setEnabled(False)
        control_layout.addWidget(self.kill_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._on_clear_output)
        control_layout.addWidget(self.clear_button)
        
        layout.addLayout(control_layout)
        
        self.output_display = TerminalOutputWidget()
        layout.addWidget(self.output_display)
        
        self.setLayout(layout)
    
    def _on_execute_command(self) -> None:
        """Handle execute command button click."""
        command = self.command_input.text().strip()
        if not command:
            return
        
        self.output_display.append_info(f"\n$ {command}\n")
        
        self.executor_thread = CommandExecutor(command, self.workspace_dir)
        self.executor_thread.output_ready.connect(self._on_output_ready)
        self.executor_thread.execution_finished.connect(self._on_execution_finished)
        
        self.execute_button.setEnabled(False)
        self.kill_button.setEnabled(True)
        
        self.executor_thread.start()
    
    def _on_output_ready(self, output_type: str, text: str) -> None:
        """Handle output ready signal."""
        if output_type == "stdout":
            self.output_display.append_stdout(text)
        elif output_type == "stderr":
            self.output_display.append_stderr(text)
        else:
            self.output_display.append_info(text)
    
    def _on_execution_finished(self, exit_code: int, stdout: str, stderr: str) -> None:
        """Handle execution finished signal."""
        if stdout:
            self.output_display.append_stdout(stdout)
        if stderr:
            self.output_display.append_stderr(stderr)
        
        self.output_display.append_info(f"\nProcess exited with code: {exit_code}\n")
        
        self.execute_button.setEnabled(True)
        self.kill_button.setEnabled(False)
        self.current_process_id = None
    
    def _on_kill_process(self) -> None:
        """Handle kill process button click."""
        if self.current_process_id:
            asyncio.create_task(local_service.terminate_process(self.current_process_id))
            self.output_display.append_info("\nProcess terminated.\n")
            self.execute_button.setEnabled(True)
            self.kill_button.setEnabled(False)
    
    def _on_clear_output(self) -> None:
        """Handle clear output button click."""
        self.output_display.clear_output()
    
    def execute_command(self, command: str, cwd: Optional[str] = None) -> None:
        """Execute a command.
        
        Args:
            command: Command to execute.
            cwd: Working directory for the command.
        """
        self.command_input.setText(command)
        self.workspace_dir = cwd or self.workspace_dir
        self._on_execute_command()
    
    def set_workspace_dir(self, workspace_dir: str) -> None:
        """Set the workspace directory.
        
        Args:
            workspace_dir: Path to the workspace directory.
        """
        self.workspace_dir = workspace_dir
