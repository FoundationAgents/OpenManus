"""
Agent control panel for orchestrating agent execution.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QComboBox, QLineEdit, QTextEdit, QGroupBox, QListWidget,
        QListWidgetItem
    )
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtGui import QFont, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()


class AgentControlPanel(QWidget):
    """Panel for controlling agent pools and execution."""
    
    agent_run = pyqtSignal(str, str) if PYQT6_AVAILABLE else None
    agent_stop = pyqtSignal(str) if PYQT6_AVAILABLE else None
    
    def __init__(self):
        super().__init__()
        self.agent_status = {}
        self.init_ui()
        
    def init_ui(self):
        """Initialize the agent control UI."""
        layout = QVBoxLayout()
        
        agent_group = QGroupBox("Agent Selection")
        agent_layout = QVBoxLayout()
        
        agent_label = QLabel("Agent Type:")
        agent_layout.addWidget(agent_label)
        
        self.agent_combo = QComboBox()
        self.agent_combo.addItems(["Manus", "DataAnalysis", "Planning", "ReAct"])
        agent_layout.addWidget(self.agent_combo)
        
        agent_group.setLayout(agent_layout)
        layout.addWidget(agent_group)
        
        prompt_group = QGroupBox("Prompt")
        prompt_layout = QVBoxLayout()
        
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        prompt_layout.addWidget(self.prompt_input)
        
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)
        
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.on_run_clicked)
        button_layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        status_group = QGroupBox("Agent Status")
        status_layout = QVBoxLayout()
        
        self.status_list = QListWidget()
        self.status_list.setMaximumHeight(150)
        status_layout.addWidget(self.status_list)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        mode_group = QGroupBox("Execution Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["chat", "agent_flow", "ade", "multi_agent"])
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.mode_combo)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def on_run_clicked(self):
        """Handle run button click."""
        agent_type = self.agent_combo.currentText()
        prompt = self.prompt_input.text().strip()
        
        if prompt:
            if self.agent_run:
                self.agent_run.emit(agent_type, prompt)
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.add_status(f"{agent_type} agent running...")
        
    def on_stop_clicked(self):
        """Handle stop button click."""
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
        if self.agent_stop:
            self.agent_stop.emit(self.agent_combo.currentText())
        self.add_status("Agent stopped")
        
    def add_status(self, message: str):
        """Add a status message."""
        item = QListWidgetItem(message)
        self.status_list.addItem(item)
        self.status_list.scrollToBottom()
        
    def update_agent_status(self, agent_id: str, status: str):
        """Update agent status."""
        self.agent_status[agent_id] = status
        self.add_status(f"{agent_id}: {status}")
        
    def clear_status(self):
        """Clear status messages."""
        self.status_list.clear()
        self.agent_status.clear()
