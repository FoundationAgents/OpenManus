"""
Agent monitor panel for real-time agent status and metrics with resilience features.
"""

import time
from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QProgressBar, QHeaderView, QTabWidget,
        QTextEdit, QSplitter, QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox,
        QMessageBox, QComboBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QPalette
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass


class AgentMonitorPanel(QWidget):
    """Panel for monitoring agent status and metrics with resilience features."""
    
    # Signals for resilience events
    agent_replacement_requested = pyqtSignal(str, str)  # agent_id, reason
    
    def __init__(self, resilience_manager=None):
        super().__init__()
        self.resilience_manager = resilience_manager
        self.agent_data = {}
        self.resilience_events = []
        self.init_ui()
        
        # Setup refresh timer
        if PYQT6_AVAILABLE:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_data)
            self.refresh_timer.start(5000)  # Refresh every 5 seconds
            
            # Connect signals
            self.agent_replacement_requested.connect(self.handle_replacement_request)
        
    def init_ui(self):
        """Initialize the agent monitor UI with resilience features."""
        layout = QVBoxLayout()
        
        # Create tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Agent Status Tab
        self.agent_status_tab = self._create_agent_status_tab()
        self.tab_widget.addTab(self.agent_status_tab, "Agent Status")
        
        # Resilience Events Tab
        self.resilience_tab = self._create_resilience_tab()
        self.tab_widget.addTab(self.resilience_tab, "Resilience Events")
        
        # Configuration Tab
        self.config_tab = self._create_config_tab()
        self.tab_widget.addTab(self.config_tab, "Configuration")
        
        layout.addWidget(self.tab_widget)
        
        if not PYQT6_AVAILABLE:
            placeholder_label = QLabel("Agent monitor requires PyQt6")
            layout.addWidget(placeholder_label)
        
        self.setLayout(layout)
    
    def _create_agent_status_tab(self) -> QWidget:
        """Create the agent status tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(QLabel("Agent Status Monitor"))
        toolbar_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(self.refresh_button)
        
        self.replace_button = QPushButton("Replace Selected")
        self.replace_button.clicked.connect(self.replace_selected_agent)
        toolbar_layout.addWidget(self.replace_button)
        
        layout.addLayout(toolbar_layout)
        
        # Agent table with enhanced columns
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(10)
        self.agent_table.setHorizontalHeaderLabels([
            "Agent ID", "Type", "Status", "Health", "Tasks", "Success Rate", 
            "Errors", "Latency", "Last Activity", "Actions"
        ])
        
        self.agent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.agent_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        header = self.agent_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.agent_table)
        
        tab.setLayout(layout)
        return tab
    
    def _create_resilience_tab(self) -> QWidget:
        """Create the resilience events tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(QLabel("Resilience Events"))
        toolbar_layout.addStretch()
        
        self.clear_events_button = QPushButton("Clear Events")
        self.clear_events_button.clicked.connect(self.clear_events)
        toolbar_layout.addWidget(self.clear_events_button)
        
        layout.addLayout(toolbar_layout)
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(6)
        self.events_table.setHorizontalHeaderLabels([
            "Timestamp", "Event Type", "Agent ID", "Description", "Severity", "Details"
        ])
        
        self.events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.events_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.events_table)
        
        # Event details
        self.event_details = QTextEdit()
        self.event_details.setMaximumHeight(150)
        self.event_details.setPlaceholderText("Select an event to see details...")
        layout.addWidget(self.event_details)
        
        tab.setLayout(layout)
        return tab
    
    def _create_config_tab(self) -> QWidget:
        """Create the configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Resilience Configuration
        config_group = QGroupBox("Resilience Configuration")
        config_layout = QVBoxLayout()
        
        # Auto-replacement
        self.auto_replace_checkbox = QCheckBox("Enable Automatic Replacement")
        self.auto_replace_checkbox.setChecked(True)
        config_layout.addWidget(self.auto_replace_checkbox)
        
        # Thresholds
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Max Consecutive Errors:"))
        self.max_errors_spinbox = QSpinBox()
        self.max_errors_spinbox.setRange(1, 10)
        self.max_errors_spinbox.setValue(3)
        threshold_layout.addWidget(self.max_errors_spinbox)
        threshold_layout.addStretch()
        config_layout.addLayout(threshold_layout)
        
        threshold_layout2 = QHBoxLayout()
        threshold_layout2.addWidget(QLabel("Min Health Score:"))
        self.min_health_spinbox = QDoubleSpinBox()
        self.min_health_spinbox.setRange(0.0, 1.0)
        self.min_health_spinbox.setSingleStep(0.1)
        self.min_health_spinbox.setValue(0.3)
        threshold_layout2.addWidget(self.min_health_spinbox)
        threshold_layout2.addStretch()
        config_layout.addLayout(threshold_layout2)
        
        # Health check interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Health Check Interval (s):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(5, 300)
        self.interval_spinbox.setValue(30)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        config_layout.addLayout(interval_layout)
        
        # Apply button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()
        self.apply_config_button = QPushButton("Apply Configuration")
        self.apply_config_button.clicked.connect(self.apply_configuration)
        apply_layout.addWidget(self.apply_config_button)
        config_layout.addLayout(apply_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Statistics
        stats_group = QGroupBox("Resilience Statistics")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("No statistics available")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
        
    def refresh_data(self):
        """Refresh agent data from resilience manager."""
        if not PYQT6_AVAILABLE or not self.resilience_manager:
            return
        
        try:
            # Get resilience status
            status = self.resilience_manager.get_resilience_status()
            
            # Update agent table
            self._update_agent_table(status)
            
            # Update events table
            self._update_events_table(status.get("recent_events", []))
            
            # Update statistics
            self._update_statistics(status.get("health_summary", {}))
            
        except Exception as e:
            print(f"Error refreshing data: {e}")
    
    def _update_agent_table(self, status: Dict[str, Any]):
        """Update the agent status table."""
        telemetry_data = self.resilience_manager.health_monitor.get_all_telemetry()
        
        self.agent_table.setRowCount(0)
        
        for agent_id, telemetry in telemetry_data.items():
            row = self.agent_table.rowCount()
            self.agent_table.insertRow(row)
            
            # Agent ID
            id_item = QTableWidgetItem(agent_id)
            self.agent_table.setItem(row, 0, id_item)
            
            # Type/Role
            type_item = QTableWidgetItem(telemetry.role.value)
            self.agent_table.setItem(row, 1, type_item)
            
            # Status
            health_status = telemetry.get_status()
            status_item = QTableWidgetItem(health_status.value)
            
            # Color code by status
            if health_status.value == "healthy":
                status_item.setBackground(QColor("#90EE90"))
            elif health_status.value == "warning":
                status_item.setBackground(QColor("#FFD700"))
            elif health_status.value == "degraded":
                status_item.setBackground(QColor("#FFA500"))
            elif health_status.value == "failed":
                status_item.setBackground(QColor("#FF6B6B"))
            elif health_status.value == "recovering":
                status_item.setBackground(QColor("#87CEEB"))
                
            self.agent_table.setItem(row, 2, status_item)
            
            # Health Score
            health_score = telemetry.get_health_score()
            health_item = QTableWidgetItem(f"{health_score:.2f}")
            self.agent_table.setItem(row, 3, health_item)
            
            # Tasks
            tasks_item = QTableWidgetItem(str(telemetry.command_count))
            self.agent_table.setItem(row, 4, tasks_item)
            
            # Success Rate
            success_rate = (telemetry.success_count / max(telemetry.command_count, 1)) * 100
            success_item = QTableWidgetItem(f"{success_rate:.1f}%")
            self.agent_table.setItem(row, 5, success_item)
            
            # Errors
            errors_item = QTableWidgetItem(str(telemetry.error_count))
            self.agent_table.setItem(row, 6, errors_item)
            
            # Latency
            latency_item = QTableWidgetItem(f"{telemetry.average_latency:.2f}s")
            self.agent_table.setItem(row, 7, latency_item)
            
            # Last Activity
            last_activity = time.strftime("%H:%M:%S", time.localtime(telemetry.last_activity))
            activity_item = QTableWidgetItem(last_activity)
            self.agent_table.setItem(row, 8, activity_item)
            
            # Actions button
            replace_button = QPushButton("Replace")
            replace_button.clicked.connect(lambda checked, aid=agent_id: self.replace_agent(aid))
            self.agent_table.setCellWidget(row, 9, replace_button)
            
            self.agent_data[agent_id] = {
                "telemetry": telemetry,
                "health_status": health_status,
                "health_score": health_score
            }
    
    def _update_events_table(self, events: list):
        """Update the resilience events table."""
        self.events_table.setRowCount(0)
        
        for event in reversed(events[-50:]):  # Show last 50 events
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            
            # Timestamp
            timestamp = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
            timestamp_item = QTableWidgetItem(timestamp)
            self.events_table.setItem(row, 0, timestamp_item)
            
            # Event Type
            type_item = QTableWidgetItem(event.type.value)
            self.events_table.setItem(row, 1, type_item)
            
            # Agent ID
            agent_item = QTableWidgetItem(event.agent_id)
            self.events_table.setItem(row, 2, agent_item)
            
            # Description
            desc_item = QTableWidgetItem(event.description[:50] + "..." if len(event.description) > 50 else event.description)
            self.events_table.setItem(row, 3, desc_item)
            
            # Severity
            severity_item = QTableWidgetItem(event.severity)
            
            # Color code by severity
            if event.severity == "critical":
                severity_item.setBackground(QColor("#FF6B6B"))
            elif event.severity == "error":
                severity_item.setBackground(QColor("#FFA500"))
            elif event.severity == "warning":
                severity_item.setBackground(QColor("#FFD700"))
                
            self.events_table.setItem(row, 4, severity_item)
            
            # Details
            details = str(event.metadata)[:30] + "..." if len(str(event.metadata)) > 30 else str(event.metadata)
            details_item = QTableWidgetItem(details)
            self.events_table.setItem(row, 5, details_item)
        
        self.resilience_events = events
    
    def _update_statistics(self, health_summary: Dict[str, Any]):
        """Update the statistics display."""
        stats_text = f"""
        Total Agents: {health_summary.get('total_agents', 0)}
        Healthy Agents: {health_summary.get('healthy_agents', 0)}
        Unhealthy Agents: {health_summary.get('unhealthy_agents', 0)}
        Average Health Score: {health_summary.get('average_health_score', 0):.2f}
        Recent Replacements: {health_summary.get('recent_replacements', 0)}
        Total Events: {health_summary.get('total_events', 0)}
        """
        self.stats_label.setText(stats_text.strip())
    
    def replace_agent(self, agent_id: str):
        """Replace a specific agent."""
        if not self.resilience_manager:
            return
        
        reply = QMessageBox.question(
            self, 
            'Confirm Agent Replacement',
            f'Are you sure you want to replace agent {agent_id}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.resilience_manager.manually_replace_agent(agent_id, "Manual UI intervention")
            if success:
                QMessageBox.information(self, "Success", f"Agent {agent_id} replacement initiated")
            else:
                QMessageBox.warning(self, "Failed", f"Failed to replace agent {agent_id}")
    
    def replace_selected_agent(self):
        """Replace the currently selected agent."""
        if not PYQT6_AVAILABLE:
            return
            
        current_row = self.agent_table.currentRow()
        if current_row >= 0:
            agent_id_item = self.agent_table.item(current_row, 0)
            if agent_id_item:
                agent_id = agent_id_item.text()
                self.replace_agent(agent_id)
    
    def clear_events(self):
        """Clear the events display."""
        if PYQT6_AVAILABLE:
            self.events_table.setRowCount(0)
            self.event_details.clear()
    
    def apply_configuration(self):
        """Apply resilience configuration changes."""
        if not self.resilience_manager:
            return
        
        try:
            # Update configuration
            self.resilience_manager.config.enable_auto_replacement = self.auto_replace_checkbox.isChecked()
            self.resilience_manager.config.max_consecutive_errors = self.max_errors_spinbox.value()
            self.resilience_manager.config.min_health_score = self.min_health_spinbox.value()
            self.resilience_manager.config.health_check_interval = self.interval_spinbox.value()
            
            QMessageBox.information(self, "Success", "Configuration applied successfully")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to apply configuration: {e}")
    
    def handle_replacement_request(self, agent_id: str, reason: str):
        """Handle agent replacement requests."""
        if self.resilience_manager:
            self.resilience_manager.manually_replace_agent(agent_id, reason)
    
    def add_agent(self, agent_data: dict):
        """Add an agent to the monitor (legacy compatibility)."""
        # This method is kept for backward compatibility
        # The new system uses telemetry data from the resilience manager
        pass
    
    def update_agent_status(self, agent_id: str, status: str):
        """Update the status of an agent (legacy compatibility)."""
        # This method is kept for backward compatibility
        pass
    
    def update_agent_tokens(self, agent_id: str, tokens: int):
        """Update the token count for an agent (legacy compatibility)."""
        # This method is kept for backward compatibility
        pass
    
    def update_agent_progress(self, agent_id: str, progress: int):
        """Update the progress for an agent (legacy compatibility)."""
        # This method is kept for backward compatibility
        pass
    
    def clear_agents(self):
        """Clear all agents from the monitor."""
        if PYQT6_AVAILABLE:
            self.agent_table.setRowCount(0)
        self.agent_data.clear()
