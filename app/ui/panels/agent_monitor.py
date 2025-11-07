"""
Agent monitor panel for real-time agent status and metrics.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QProgressBar, QHeaderView
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass


class AgentMonitorPanel(QWidget):
    """Panel for monitoring agent status and metrics."""
    
    def __init__(self):
        super().__init__()
        self.agent_data = {}
        self.init_ui()
        
    def init_ui(self):
        """Initialize the agent monitor UI."""
        layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        
        toolbar_layout.addWidget(QLabel("Agent Status Monitor"))
        toolbar_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        toolbar_layout.addWidget(self.refresh_button)
        
        layout.addLayout(toolbar_layout)
        
        if PYQT6_AVAILABLE:
            self.agent_table = QTableWidget()
            self.agent_table.setColumnCount(6)
            self.agent_table.setHorizontalHeaderLabels([
                "Agent ID", "Type", "Status", "Tasks", "Tokens Used", "Progress"
            ])
            
            self.agent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.agent_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            
            header = self.agent_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
            layout.addWidget(self.agent_table)
            
            self._add_sample_agents()
        else:
            placeholder_label = QLabel("Agent monitor requires PyQt6")
            layout.addWidget(placeholder_label)
        
        self.setLayout(layout)
        
    def _add_sample_agents(self):
        """Add sample agent data for display."""
        if not PYQT6_AVAILABLE:
            return
            
        sample_agents = [
            {
                "id": "manus_001",
                "type": "Manus",
                "status": "Idle",
                "tasks": 5,
                "tokens": 0
            },
            {
                "id": "data_analysis_001",
                "type": "DataAnalysis",
                "status": "Idle",
                "tasks": 0,
                "tokens": 0
            },
            {
                "id": "planning_001",
                "type": "Planning",
                "status": "Ready",
                "tasks": 3,
                "tokens": 250
            }
        ]
        
        for agent in sample_agents:
            self.add_agent(agent)
            
    def add_agent(self, agent_data: dict):
        """Add an agent to the monitor."""
        if not PYQT6_AVAILABLE:
            return
            
        row = self.agent_table.rowCount()
        self.agent_table.insertRow(row)
        
        id_item = QTableWidgetItem(agent_data.get("id", "Unknown"))
        self.agent_table.setItem(row, 0, id_item)
        
        type_item = QTableWidgetItem(agent_data.get("type", "Unknown"))
        self.agent_table.setItem(row, 1, type_item)
        
        status = agent_data.get("status", "Unknown")
        status_item = QTableWidgetItem(status)
        
        if status == "Running":
            status_item.setBackground(QColor("#90EE90"))
        elif status == "Idle":
            status_item.setBackground(QColor("#D3D3D3"))
        elif status == "Error":
            status_item.setBackground(QColor("#FFB6C1"))
        elif status == "Ready":
            status_item.setBackground(QColor("#87CEEB"))
            
        self.agent_table.setItem(row, 2, status_item)
        
        tasks_item = QTableWidgetItem(str(agent_data.get("tasks", 0)))
        self.agent_table.setItem(row, 3, tasks_item)
        
        tokens_item = QTableWidgetItem(str(agent_data.get("tokens", 0)))
        self.agent_table.setItem(row, 4, tokens_item)
        
        progress = QProgressBar()
        progress.setValue(agent_data.get("progress", 0))
        self.agent_table.setCellWidget(row, 5, progress)
        
        self.agent_data[agent_data.get("id", "")] = agent_data
        
    def update_agent_status(self, agent_id: str, status: str):
        """Update the status of an agent."""
        if not PYQT6_AVAILABLE:
            return
            
        for row in range(self.agent_table.rowCount()):
            item = self.agent_table.item(row, 0)
            if item and item.text() == agent_id:
                status_item = self.agent_table.item(row, 2)
                if status_item:
                    status_item.setText(status)
                    
                    if status == "Running":
                        status_item.setBackground(QColor("#90EE90"))
                    elif status == "Idle":
                        status_item.setBackground(QColor("#D3D3D3"))
                    elif status == "Error":
                        status_item.setBackground(QColor("#FFB6C1"))
                break
                
    def update_agent_tokens(self, agent_id: str, tokens: int):
        """Update the token count for an agent."""
        if not PYQT6_AVAILABLE:
            return
            
        for row in range(self.agent_table.rowCount()):
            item = self.agent_table.item(row, 0)
            if item and item.text() == agent_id:
                tokens_item = self.agent_table.item(row, 4)
                if tokens_item:
                    tokens_item.setText(str(tokens))
                break
                
    def update_agent_progress(self, agent_id: str, progress: int):
        """Update the progress for an agent."""
        if not PYQT6_AVAILABLE:
            return
            
        for row in range(self.agent_table.rowCount()):
            item = self.agent_table.item(row, 0)
            if item and item.text() == agent_id:
                progress_widget = self.agent_table.cellWidget(row, 5)
                if progress_widget:
                    progress_widget.setValue(progress)
                break
                
    def clear_agents(self):
        """Clear all agents from the monitor."""
        if PYQT6_AVAILABLE:
            self.agent_table.setRowCount(0)
        self.agent_data.clear()
