"""UI Panel for monitoring adaptive sandbox execution and displaying decisions.

Shows:
- Sandbox environment configuration
- Granted capabilities
- Isolation level and why
- Resource usage and limits
- Runtime anomalies
- Guardian decisions
"""

from typing import Dict, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QGroupBox, QScrollArea, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.logger import logger


class AdaptiveSandboxMonitorPanel(QWidget):
    """Panel for monitoring adaptive sandbox execution."""
    
    # Display name and description for panel discovery
    DISPLAY_NAME = "Adaptive Sandbox Monitor"
    DESCRIPTION = "Monitor adaptive sandbox execution, capabilities, and isolation levels"
    DEPENDENCIES = []
    
    # Signals
    environment_changed = pyqtSignal(dict)  # Emitted when environment config changes
    isolation_escalated = pyqtSignal(dict)  # Emitted when isolation level escalates
    anomaly_detected = pyqtSignal(dict)     # Emitted when anomaly is detected
    
    def __init__(self, parent=None):
        """Initialize adaptive sandbox monitor panel."""
        super().__init__(parent)
        self.current_sandbox_id = None
        self.sandbox_data = {}
        self.setup_ui()
        logger.info("Initialized Adaptive Sandbox Monitor Panel")
    
    def setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget for different views
        tabs = QTabWidget()
        tabs.addTab(self._create_environment_tab(), "Environment")
        tabs.addTab(self._create_capabilities_tab(), "Capabilities")
        tabs.addTab(self._create_resources_tab(), "Resources")
        tabs.addTab(self._create_monitoring_tab(), "Monitoring")
        tabs.addTab(self._create_decisions_tab(), "Guardian Decisions")
        
        layout.addWidget(tabs)
        
        # Status bar
        status = self._create_status_bar()
        layout.addWidget(status)
    
    def _create_header(self) -> QWidget:
        """Create header section."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.sandbox_label = QLabel("No Sandbox Selected")
        self.sandbox_label.setFont(QFont("Courier", 10, QFont.Weight.Bold))
        layout.addWidget(self.sandbox_label)
        
        layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_data)
        layout.addWidget(self.clear_btn)
        
        return widget
    
    def _create_environment_tab(self) -> QWidget:
        """Create environment configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Isolation level
        iso_group = QGroupBox("Isolation Level")
        iso_layout = QVBoxLayout(iso_group)
        self.isolation_label = QLabel("Not set")
        self.isolation_label.setFont(QFont("Courier", 10))
        iso_layout.addWidget(self.isolation_label)
        layout.addWidget(iso_group)
        
        # Environment variables table
        env_group = QGroupBox("Environment Variables")
        env_layout = QVBoxLayout(env_group)
        
        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.env_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        env_layout.addWidget(self.env_table)
        
        layout.addWidget(env_group)
        
        return widget
    
    def _create_capabilities_tab(self) -> QWidget:
        """Create capabilities tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Allowed tools
        tools_group = QGroupBox("Allowed Tools")
        tools_layout = QVBoxLayout(tools_group)
        self.tools_table = QTableWidget()
        self.tools_table.setColumnCount(1)
        self.tools_table.setHorizontalHeaderLabels(["Tool"])
        tools_layout.addWidget(self.tools_table)
        layout.addWidget(tools_group)
        
        # Allowed paths
        paths_group = QGroupBox("File System Access")
        paths_layout = QVBoxLayout(paths_group)
        self.paths_table = QTableWidget()
        self.paths_table.setColumnCount(2)
        self.paths_table.setHorizontalHeaderLabels(["Path", "Access Mode"])
        self.paths_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        paths_layout.addWidget(self.paths_table)
        layout.addWidget(paths_group)
        
        # Network
        network_group = QGroupBox("Network Access")
        network_layout = QVBoxLayout(network_group)
        self.network_label = QLabel("Disabled")
        self.network_label.setStyleSheet("color: red;")
        network_layout.addWidget(self.network_label)
        layout.addWidget(network_group)
        
        return widget
    
    def _create_resources_tab(self) -> QWidget:
        """Create resource limits tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.resources_table = QTableWidget()
        self.resources_table.setColumnCount(3)
        self.resources_table.setHorizontalHeaderLabels(["Resource", "Limit", "Current"])
        self.resources_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.resources_table)
        
        return widget
    
    def _create_monitoring_tab(self) -> QWidget:
        """Create runtime monitoring tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Current metrics
        metrics_group = QGroupBox("Current Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        metrics_layout.addWidget(self.metrics_table)
        layout.addWidget(metrics_group)
        
        # Anomalies
        anomaly_group = QGroupBox("Detected Anomalies")
        anomaly_layout = QVBoxLayout(anomaly_group)
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(3)
        self.anomaly_table.setHorizontalHeaderLabels(["Type", "Severity", "Reason"])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        anomaly_layout.addWidget(self.anomaly_table)
        layout.addWidget(anomaly_group)
        
        return widget
    
    def _create_decisions_tab(self) -> QWidget:
        """Create Guardian decisions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Decisions
        decisions_group = QGroupBox("Guardian Decisions")
        decisions_layout = QVBoxLayout(decisions_group)
        self.decisions_table = QTableWidget()
        self.decisions_table.setColumnCount(4)
        self.decisions_table.setHorizontalHeaderLabels(["Operation", "Result", "Risk Level", "Reason"])
        self.decisions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        decisions_layout.addWidget(self.decisions_table)
        layout.addWidget(decisions_group)
        
        # Details
        details_group = QGroupBox("Decision Details")
        details_layout = QVBoxLayout(details_group)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        layout.addWidget(details_group)
        
        return widget
    
    def _create_status_bar(self) -> QWidget:
        """Create status bar."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.last_update_label = QLabel("")
        layout.addWidget(self.last_update_label)
        
        return widget
    
    def display_sandbox_environment(self, sandbox_data: Dict[str, Any]) -> None:
        """Display sandbox environment configuration.
        
        Args:
            sandbox_data: Sandbox configuration dictionary
        """
        self.sandbox_data = sandbox_data
        self.current_sandbox_id = sandbox_data.get("sandbox_id", "unknown")
        
        # Update header
        self.sandbox_label.setText(f"Sandbox: {self.current_sandbox_id}")
        
        # Update isolation level
        isolation = sandbox_data.get("isolation_level", "UNKNOWN")
        self.isolation_label.setText(f"Level: {isolation}\n{self._get_isolation_description(isolation)}")
        
        # Update environment variables
        self._update_environment_table(sandbox_data.get("environment", {}).get("environment_variables", {}))
        
        # Update capabilities
        granted = sandbox_data.get("granted_capabilities", {})
        self._update_tools_table(granted.get("allowed_tools", []))
        self._update_paths_table(sandbox_data.get("environment", {}).get("volume_mounts", {}))
        
        # Network access
        network_enabled = granted.get("network_enabled", False)
        self.network_label.setText("Enabled" if network_enabled else "Disabled")
        self.network_label.setStyleSheet("color: green;" if network_enabled else "color: red;")
        
        # Resources
        resources = sandbox_data.get("environment", {}).get("resource_limits", {})
        self._update_resources_table(resources)
        
        # Monitoring
        monitoring = sandbox_data.get("monitoring", {})
        if monitoring:
            self._update_monitoring_data(monitoring)
        
        # Status
        is_active = sandbox_data.get("is_active", False)
        self.status_label.setText("Active" if is_active else "Inactive")
        self.status_label.setStyleSheet("color: green;" if is_active else "color: red;")
        
        self.environment_changed.emit(sandbox_data)
    
    def _get_isolation_description(self, level: str) -> str:
        """Get human-readable isolation level description."""
        descriptions = {
            "TRUSTED": "Full trust - inherit environment as-is",
            "MONITORED": "Monitored - filtered environment, all ops logged",
            "RESTRICTED": "Restricted - granted capabilities only",
            "SANDBOXED": "Sandboxed - minimal environment, strict isolation",
            "ISOLATED": "Isolated - full VM isolation if anomaly detected",
        }
        return descriptions.get(level, "Unknown isolation level")
    
    def _update_environment_table(self, env_vars: Dict[str, str]) -> None:
        """Update environment variables table."""
        self.env_table.setRowCount(len(env_vars))
        
        for row, (var, value) in enumerate(env_vars.items()):
            var_item = QTableWidgetItem(var)
            value_item = QTableWidgetItem(str(value)[:50])  # Truncate long values
            
            self.env_table.setItem(row, 0, var_item)
            self.env_table.setItem(row, 1, value_item)
    
    def _update_tools_table(self, tools: list) -> None:
        """Update allowed tools table."""
        self.tools_table.setRowCount(len(tools))
        
        for row, tool in enumerate(tools):
            item = QTableWidgetItem(tool)
            self.tools_table.setItem(row, 0, item)
    
    def _update_paths_table(self, volume_mounts: Dict) -> None:
        """Update file system access table."""
        self.paths_table.setRowCount(len(volume_mounts))
        
        for row, (host_path, (container_path, mode)) in enumerate(volume_mounts.items()):
            path_item = QTableWidgetItem(host_path)
            mode_item = QTableWidgetItem(mode)
            
            self.paths_table.setItem(row, 0, path_item)
            self.paths_table.setItem(row, 1, mode_item)
    
    def _update_resources_table(self, resources: Dict) -> None:
        """Update resource limits table."""
        limits = [
            ("CPU", f"{resources.get('cpu_percent', 100)}%", ""),
            ("Memory", f"{resources.get('memory_mb', 512)}MB", ""),
            ("Timeout", f"{resources.get('timeout_seconds', 300)}s", ""),
        ]
        
        self.resources_table.setRowCount(len(limits))
        
        for row, (resource, limit, current) in enumerate(limits):
            res_item = QTableWidgetItem(resource)
            limit_item = QTableWidgetItem(limit)
            current_item = QTableWidgetItem(current)
            
            self.resources_table.setItem(row, 0, res_item)
            self.resources_table.setItem(row, 1, limit_item)
            self.resources_table.setItem(row, 2, current_item)
    
    def _update_monitoring_data(self, monitoring: Dict) -> None:
        """Update monitoring metrics and anomalies."""
        # Current metrics
        current = monitoring.get("current_metrics", {})
        metrics = [
            ("CPU", f"{current.get('cpu_percent', 0):.1f}%"),
            ("Memory", f"{current.get('memory_mb', 0)}MB"),
            ("Open Files", str(current.get('open_files', 0))),
            ("Network Connections", str(current.get('network_connections', 0))),
            ("Subprocesses", str(current.get('subprocess_count', 0))),
        ]
        
        self.metrics_table.setRowCount(len(metrics))
        
        for row, (metric, value) in enumerate(metrics):
            metric_item = QTableWidgetItem(metric)
            value_item = QTableWidgetItem(value)
            
            self.metrics_table.setItem(row, 0, metric_item)
            self.metrics_table.setItem(row, 1, value_item)
        
        # Recent anomalies
        anomalies = monitoring.get("recent_anomalies", [])
        self.anomaly_table.setRowCount(len(anomalies))
        
        for row, anomaly in enumerate(anomalies):
            type_item = QTableWidgetItem(anomaly.get("type", "UNKNOWN"))
            severity_item = QTableWidgetItem(f"{anomaly.get('severity', 0):.2f}")
            reason_item = QTableWidgetItem(anomaly.get("reason", ""))
            
            # Color code by severity
            if anomaly.get("severity", 0) > 0.7:
                severity_item.setBackground(QColor(255, 100, 100))  # Red
            elif anomaly.get("severity", 0) > 0.4:
                severity_item.setBackground(QColor(255, 200, 100))  # Orange
            
            self.anomaly_table.setItem(row, 0, type_item)
            self.anomaly_table.setItem(row, 1, severity_item)
            self.anomaly_table.setItem(row, 2, reason_item)
    
    def display_guardian_decision(self, decision_data: Dict[str, Any]) -> None:
        """Display a Guardian decision.
        
        Args:
            decision_data: Guardian decision dictionary
        """
        # Add to decisions table
        row = self.decisions_table.rowCount()
        self.decisions_table.insertRow(row)
        
        operation = decision_data.get("operation", "")
        result = "Approved" if decision_data.get("approved", False) else "Denied"
        risk = decision_data.get("risk_level", "UNKNOWN")
        reason = decision_data.get("reason", "")
        
        self.decisions_table.setItem(row, 0, QTableWidgetItem(operation))
        self.decisions_table.setItem(row, 1, QTableWidgetItem(result))
        self.decisions_table.setItem(row, 2, QTableWidgetItem(risk))
        self.decisions_table.setItem(row, 3, QTableWidgetItem(reason))
        
        # Update details
        details_text = (
            f"Operation: {operation}\n"
            f"Result: {result}\n"
            f"Risk Level: {risk}\n"
            f"Reason: {reason}\n"
            f"Conditions: {', '.join(decision_data.get('conditions', []))}"
        )
        
        self.details_text.setText(details_text)
    
    def record_isolation_escalation(self, old_level: str, new_level: str, reason: str) -> None:
        """Record isolation level escalation.
        
        Args:
            old_level: Previous isolation level
            new_level: New isolation level
            reason: Reason for escalation
        """
        self.isolation_label.setText(
            f"Level: {new_level} (escalated from {old_level})\n"
            f"Reason: {reason}\n{self._get_isolation_description(new_level)}"
        )
        
        self.isolation_escalated.emit({
            "old_level": old_level,
            "new_level": new_level,
            "reason": reason,
        })
    
    def refresh_data(self) -> None:
        """Refresh displayed data."""
        logger.debug("Refreshing sandbox monitor data")
        self.status_label.setText("Ready")
    
    def clear_data(self) -> None:
        """Clear all displayed data."""
        self.sandbox_label.setText("No Sandbox Selected")
        self.sandbox_data = {}
        self.current_sandbox_id = None
        
        self.env_table.setRowCount(0)
        self.tools_table.setRowCount(0)
        self.paths_table.setRowCount(0)
        self.resources_table.setRowCount(0)
        self.metrics_table.setRowCount(0)
        self.anomaly_table.setRowCount(0)
        self.decisions_table.setRowCount(0)
        
        self.details_text.clear()
        self.status_label.setText("Ready")
