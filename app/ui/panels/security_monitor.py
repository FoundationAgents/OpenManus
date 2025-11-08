"""
Security Monitor Panel
Displays Guardian security monitoring information
"""

from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QLabel, QPushButton, QComboBox, QTextEdit, QSplitter,
        QGroupBox, QHeaderView, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass
    class QThread:
        pass
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()

if PYQT6_AVAILABLE:
    from app.system_integration.integration_service import system_integration
    from app.guardian.guardian_service import guardian_service


class SecurityWorker(QThread):
    """Worker thread for security monitoring"""
    
    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._running = False
    
    def run(self):
        """Main worker loop"""
        self._running = True
        
        while self._running:
            try:
                # Get security summary
                import asyncio
                summary = asyncio.run(guardian_service.get_security_summary())
                self.update_signal.emit(summary)
                
                # Sleep for update interval
                self.msleep(5000)  # 5 seconds
                
            except Exception as e:
                self.error_signal.emit(str(e))
                self.msleep(10000)  # Wait longer on error
    
    def stop(self):
        """Stop the worker"""
        self._running = False


class SecurityMonitorPanel(QWidget):
    """Security monitoring panel"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Security Monitor")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Summary and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Summary group
        summary_group = QGroupBox("Security Summary")
        summary_layout = QVBoxLayout()
        
        self.total_events_label = QLabel("Total Events (24h): 0")
        self.critical_events_label = QLabel("Critical Events: 0")
        self.high_events_label = QLabel("High Severity: 0")
        self.medium_events_label = QLabel("Medium Severity: 0")
        self.low_events_label = QLabel("Low Severity: 0")
        
        summary_layout.addWidget(self.total_events_label)
        summary_layout.addWidget(self.critical_events_label)
        summary_layout.addWidget(self.high_events_label)
        summary_layout.addWidget(self.medium_events_label)
        summary_layout.addWidget(self.low_events_label)
        
        summary_group.setLayout(summary_layout)
        left_layout.addWidget(summary_group)
        
        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Critical", "High", "Medium", "Low"])
        self.severity_filter.currentTextChanged.connect(self.filter_events)
        filter_layout.addWidget(self.severity_filter)
        
        controls_layout.addLayout(filter_layout)
        
        # Action buttons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_events)
        controls_layout.addWidget(refresh_btn)
        
        clear_critical_btn = QPushButton("Clear Critical Events")
        clear_critical_btn.clicked.connect(self.clear_critical_events)
        controls_layout.addWidget(clear_critical_btn)
        
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side - Events table
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(6)
        self.events_table.setHorizontalHeaderLabels([
            "Time", "Type", "Severity", "Description", "Source IP", "User ID"
        ])
        
        # Configure table
        header = self.events_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        right_layout.addWidget(self.events_table)
        
        # Event details
        details_group = QGroupBox("Event Details")
        details_layout = QVBoxLayout()
        
        self.event_details = QTextEdit()
        self.event_details.setReadOnly(True)
        self.event_details.setMaximumHeight(150)
        
        details_layout.addWidget(self.event_details)
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter sizes
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Connect table selection
        self.events_table.itemSelectionChanged.connect(self.show_event_details)
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start the security monitoring worker"""
        if not PYQT6_AVAILABLE:
            return
        
        self.worker = SecurityWorker()
        self.worker.update_signal.connect(self.update_summary)
        self.worker.error_signal.connect(self.show_error)
        self.worker.start()
    
    def stop_monitoring(self):
        """Stop the security monitoring worker"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
    
    def update_summary(self, summary: Dict[str, Any]):
        """Update security summary"""
        try:
            self.total_events_label.setText(f"Total Events (24h): {summary.get('total_recent_24h', 0)}")
            self.critical_events_label.setText(f"Critical Events: {summary.get('unresolved_critical', 0)}")
            
            severity_counts = summary.get('severity_counts_24h', {})
            self.high_events_label.setText(f"High Severity: {severity_counts.get('high', 0)}")
            self.medium_events_label.setText(f"Medium Severity: {severity_counts.get('medium', 0)}")
            self.low_events_label.setText(f"Low Severity: {severity_counts.get('low', 0)}")
            
            # Update events table
            self.update_events_table()
            
        except Exception as e:
            self.show_error(f"Error updating summary: {e}")
    
    def update_events_table(self):
        """Update the events table"""
        try:
            import asyncio
            
            # Get events from guardian service
            severity_filter = self.severity_filter.currentText()
            if severity_filter == "All":
                events = asyncio.run(guardian_service.get_security_events(limit=100))
            else:
                events = asyncio.run(guardian_service.get_security_events(
                    severity=severity_filter.lower(), limit=100
                ))
            
            # Clear and populate table
            self.events_table.setRowCount(0)
            
            for i, event in enumerate(events):
                self.events_table.insertRow(i)
                
                # Format timestamp
                timestamp = event.get('created_at', '')
                if timestamp:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp_str = dt.strftime("%H:%M:%S")
                    except:
                        timestamp_str = timestamp[:19]
                else:
                    timestamp_str = ''
                
                self.events_table.setItem(i, 0, QTableWidgetItem(timestamp_str))
                self.events_table.setItem(i, 1, QTableWidgetItem(event.get('event_type', '')))
                self.events_table.setItem(i, 2, QTableWidgetItem(event.get('severity', '')))
                self.events_table.setItem(i, 3, QTableWidgetItem(event.get('description', '')))
                self.events_table.setItem(i, 4, QTableWidgetItem(event.get('source_ip', '')))
                self.events_table.setItem(i, 5, QTableWidgetItem(str(event.get('user_id', ''))))
                
                # Color code by severity
                severity = event.get('severity', '').lower()
                if severity == 'critical':
                    color = '#ffcccc'  # Light red
                elif severity == 'high':
                    color = '#ffddcc'  # Light orange
                elif severity == 'medium':
                    color = '#fff3cd'  # Light yellow
                else:
                    color = '#d4edda'  # Light green
                
                for col in range(6):
                    item = self.events_table.item(i, col)
                    if item:
                        item.setBackground(color)
            
        except Exception as e:
            self.show_error(f"Error updating events table: {e}")
    
    def show_event_details(self):
        """Show details for selected event"""
        try:
            current_row = self.events_table.currentRow()
            if current_row < 0:
                self.event_details.clear()
                return
            
            # Get event details
            import asyncio
            events = asyncio.run(guardian_service.get_security_events(limit=100))
            
            if current_row < len(events):
                event = events[current_row]
                
                # Format details
                details = f"""
Event Type: {event.get('event_type', 'N/A')}
Severity: {event.get('severity', 'N/A')}
Description: {event.get('description', 'N/A')}
Source IP: {event.get('source_ip', 'N/A')}
User ID: {event.get('user_id', 'N/A')}
Timestamp: {event.get('created_at', 'N/A')}
Resolved: {event.get('resolved', False)}

Metadata:
{event.get('metadata', {})}
                """.strip()
                
                self.event_details.setPlainText(details)
            
        except Exception as e:
            self.show_error(f"Error showing event details: {e}")
    
    def filter_events(self):
        """Filter events by severity"""
        self.update_events_table()
    
    def refresh_events(self):
        """Manually refresh events"""
        self.update_events_table()
    
    def clear_critical_events(self):
        """Clear all critical events"""
        try:
            reply = QMessageBox.question(
                self, 'Clear Critical Events',
                'Are you sure you want to mark all critical events as resolved?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # This would call guardian service to resolve critical events
                from datetime import datetime
                self.show_error("Critical events cleared (placeholder)")
                self.refresh_events()
            
        except Exception as e:
            self.show_error(f"Error clearing critical events: {e}")
    
    def show_error(self, message: str):
        """Show error message"""
        if PYQT6_AVAILABLE:
            QMessageBox.critical(self, "Error", message)
        else:
            print(f"Security Monitor Error: {message}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_monitoring()
        super().closeEvent(event)
