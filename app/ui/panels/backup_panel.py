"""
Backup Panel
Displays and manages system backups
"""

from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QLabel, QPushButton, QLineEdit, QTextEdit, QSplitter,
        QGroupBox, QHeaderView, QMessageBox, QComboBox,
        QProgressBar, QCheckBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

if PYQT6_AVAILABLE:
    from app.system_integration.integration_service import system_integration
    from app.backup.backup_service import backup_service
    from app.backup.backup_scheduler import backup_scheduler


class BackupWorker(QThread):
    """Worker thread for backup operations"""
    
    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    backup_result_signal = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self._running = False
        self._tasks = []
    
    def run(self):
        """Main worker loop"""
        self._running = True
        
        while self._running:
            try:
                # Process any pending tasks
                if self._tasks:
                    task = self._tasks.pop(0)
                    self._process_task(task)
                
                # Regular update every 5 seconds
                import asyncio
                stats = asyncio.run(backup_service.get_backup_statistics())
                self.update_signal.emit(stats)
                
                self.msleep(5000)  # 5 seconds
                
            except Exception as e:
                self.error_signal.emit(str(e))
                self.msleep(10000)  # Wait longer on error
    
    def _process_task(self, task: Dict[str, Any]):
        """Process a specific task"""
        task_type = task.get('type')
        
        try:
            import asyncio
            
            if task_type == 'create_backup':
                backup_config = task.get('config')
                result = asyncio.run(backup_service.create_backup(backup_config))
                self.backup_result_signal.emit(result)
            
            elif task_type == 'delete_backup':
                backup_id = task.get('backup_id')
                success = asyncio.run(backup_service.delete_backup(backup_id))
                self.backup_result_signal.emit({'success': success, 'backup_id': backup_id})
            
        except Exception as e:
            self.error_signal.emit(f"Error processing task {task_type}: {e}")
    
    def add_task(self, task: Dict[str, Any]):
        """Add a task to the queue"""
        self._tasks.append(task)
    
    def stop(self):
        """Stop the worker"""
        self._running = False


class BackupPanel(QWidget):
    """Backup management panel"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Backup Management")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Summary and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Summary group
        summary_group = QGroupBox("Backup Summary")
        summary_layout = QVBoxLayout()
        
        self.total_backups_label = QLabel("Total Backups: 0")
        self.total_size_label = QLabel("Total Size: 0 MB")
        self.recent_backups_label = QLabel("Recent (7d): 0")
        self.last_backup_label = QLabel("Last Backup: Never")
        
        summary_layout.addWidget(self.total_backups_label)
        summary_layout.addWidget(self.total_size_label)
        summary_layout.addWidget(self.recent_backups_label)
        summary_layout.addWidget(self.last_backup_label)
        
        summary_group.setLayout(summary_layout)
        left_layout.addWidget(summary_group)
        
        # Controls group
        controls_group = QGroupBox("Backup Controls")
        controls_layout = QVBoxLayout()
        
        # Create backup controls
        create_layout = QHBoxLayout()
        create_layout.addWidget(QLabel("Name:"))
        
        self.backup_name_input = QLineEdit()
        self.backup_name_input.setPlaceholderText("Enter backup name...")
        create_layout.addWidget(self.backup_name_input)
        
        controls_layout.addLayout(create_layout)
        
        # Backup type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        
        self.backup_type_combo = QComboBox()
        self.backup_type_combo.addItems(["full", "incremental", "differential"])
        type_layout.addWidget(self.backup_type_combo)
        
        controls_layout.addLayout(type_layout)
        
        # Options
        options_layout = QVBoxLayout()
        
        self.include_workspace_cb = QCheckBox("Include Workspace")
        self.include_workspace_cb.setChecked(True)
        options_layout.addWidget(self.include_workspace_cb)
        
        self.include_config_cb = QCheckBox("Include Config")
        self.include_config_cb.setChecked(True)
        options_layout.addWidget(self.include_config_cb)
        
        self.include_database_cb = QCheckBox("Include Database")
        self.include_database_cb.setChecked(True)
        options_layout.addWidget(self.include_database_cb)
        
        controls_layout.addLayout(options_layout)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create Backup")
        create_btn.clicked.connect(self.create_backup)
        actions_layout.addWidget(create_btn)
        
        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(self.restore_selected)
        actions_layout.addWidget(restore_btn)
        
        cleanup_btn = QPushButton("Cleanup Old")
        cleanup_btn.clicked.connect(self.cleanup_old)
        actions_layout.addWidget(cleanup_btn)
        
        controls_layout.addLayout(actions_layout)
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side - Backup list
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Backup list
        list_group = QGroupBox("Available Backups")
        list_layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.backup_filter = QComboBox()
        self.backup_filter.addItems(["All", "full", "incremental", "differential"])
        self.backup_filter.currentTextChanged.connect(self.filter_backups)
        filter_layout.addWidget(self.backup_filter)
        
        list_layout.addLayout(filter_layout)
        
        # Backups table
        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(6)
        self.backups_table.setHorizontalHeaderLabels([
            "Name", "Type", "Size", "Created", "Checksum", "ID"
        ])
        
        # Configure table
        header = self.backups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.backups_table.setAlternatingRowColors(True)
        self.backups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        list_layout.addWidget(self.backups_table)
        list_group.setLayout(list_layout)
        right_layout.addWidget(list_group)
        
        # Backup details
        details_group = QGroupBox("Backup Details")
        details_layout = QVBoxLayout()
        
        self.backup_details = QTextEdit()
        self.backup_details.setReadOnly(True)
        self.backup_details.setMaximumHeight(150)
        
        details_layout.addWidget(self.backup_details)
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter sizes
        splitter.setSizes([350, 650])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Connect table selection
        self.backups_table.itemSelectionChanged.connect(self.show_backup_details)
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start the backup worker"""
        if not PYQT6_AVAILABLE:
            return
        
        self.worker = BackupWorker()
        self.worker.update_signal.connect(self.update_summary)
        self.worker.error_signal.connect(self.show_error)
        self.worker.backup_result_signal.connect(self.handle_backup_result)
        self.worker.start()
    
    def stop_monitoring(self):
        """Stop the backup worker"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
    
    def update_summary(self, stats: Dict[str, Any]):
        """Update backup summary"""
        try:
            self.total_backups_label.setText(f"Total Backups: {stats.get('total_backups', 0)}")
            self.total_size_label.setText(f"Total Size: {stats.get('total_size_mb', 0):.2f} MB")
            self.recent_backups_label.setText(f"Recent (7d): {stats.get('recent_backups_7d', 0)}")
            
            # Find last backup time
            import asyncio
            backups = asyncio.run(backup_service.list_backups())
            if backups:
                last_backup = backups[0]['created_at']
                self.last_backup_label.setText(f"Last Backup: {last_backup[:19] if last_backup else 'Never'}")
            else:
                self.last_backup_label.setText("Last Backup: Never")
            
            # Update backup table
            self.update_backups_table()
            
        except Exception as e:
            self.show_error(f"Error updating summary: {e}")
    
    def update_backups_table(self):
        """Update the backups table"""
        try:
            import asyncio
            
            # Get backups with filter
            backup_filter = self.backup_filter.currentText()
            if backup_filter == "All":
                backups = asyncio.run(backup_service.list_backups())
            else:
                backups = asyncio.run(backup_service.list_backups(backup_filter.lower()))
            
            # Clear and populate table
            self.backups_table.setRowCount(0)
            
            for i, backup in enumerate(backups):
                self.backups_table.insertRow(i)
                
                # Format size
                size_bytes = backup.get('file_size', 0)
                size_mb = size_bytes / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB"
                
                # Format timestamp
                created_at = backup.get('created_at', '')
                time_str = created_at[:19] if created_at else 'Unknown'
                
                # Shorten checksum
                checksum = backup.get('checksum', '')
                checksum_short = checksum[:16] + "..." if len(checksum) > 16 else checksum
                
                self.backups_table.setItem(i, 0, QTableWidgetItem(backup.get('backup_name', '')))
                self.backups_table.setItem(i, 1, QTableWidgetItem(backup.get('backup_type', '')))
                self.backups_table.setItem(i, 2, QTableWidgetItem(size_str))
                self.backups_table.setItem(i, 3, QTableWidgetItem(time_str))
                self.backups_table.setItem(i, 4, QTableWidgetItem(checksum_short))
                self.backups_table.setItem(i, 5, QTableWidgetItem(str(backup.get('id', ''))))
            
        except Exception as e:
            self.show_error(f"Error updating backups table: {e}")
    
    def show_backup_details(self):
        """Show details for selected backup"""
        try:
            current_row = self.backups_table.currentRow()
            if current_row < 0:
                self.backup_details.clear()
                return
            
            backup_id = int(self.backups_table.item(current_row, 5).text())
            
            # Get backup info
            import asyncio
            backup_info = asyncio.run(backup_service.get_backup_info(backup_id))
            
            if backup_info:
                details = f"""
Backup Name: {backup_info.get('backup_name', 'N/A')}
Type: {backup_info.get('backup_type', 'N/A')}
File Path: {backup_info.get('file_path', 'N/A')}
File Size: {backup_info.get('file_size', 0):,} bytes
Checksum: {backup_info.get('checksum', 'N/A')}
Created: {backup_info.get('created_at', 'N/A')}
Restored: {backup_info.get('restored_at', 'Never')}
                """.strip()
                
                self.backup_details.setPlainText(details)
            else:
                self.backup_details.setPlainText("Backup details not found")
            
        except Exception as e:
            self.show_error(f"Error showing backup details: {e}")
    
    def create_backup(self):
        """Create a new backup"""
        try:
            name = self.backup_name_input.text().strip()
            if not name:
                self.show_error("Please enter a backup name")
                return
            
            # Create backup configuration
            from app.backup.backup_service import BackupConfig
            backup_config = BackupConfig(
                backup_name=name,
                backup_type=self.backup_type_combo.currentText(),
                include_workspace=self.include_workspace_cb.isChecked(),
                include_config=self.include_config_cb.isChecked(),
                include_database=self.include_database_cb.isChecked(),
                compression=True,
                encryption=False
            )
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            
            # Add task to worker
            if self.worker:
                self.worker.add_task({
                    'type': 'create_backup',
                    'config': backup_config
                })
            
        except Exception as e:
            self.show_error(f"Error creating backup: {e}")
    
    def restore_selected(self):
        """Restore selected backup"""
        try:
            current_row = self.backups_table.currentRow()
            if current_row < 0:
                self.show_error("Please select a backup to restore")
                return
            
            backup_id = int(self.backups_table.item(current_row, 5).text())
            backup_name = self.backups_table.item(current_row, 0).text()
            
            reply = QMessageBox.question(
                self, 'Restore Backup',
                f'Are you sure you want to restore backup "{backup_name}"?\n\n'
                'This will replace current files and data!',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_error("Restore functionality (placeholder)")
            
        except Exception as e:
            self.show_error(f"Error restoring backup: {e}")
    
    def cleanup_old(self):
        """Clean up old backups"""
        try:
            reply = QMessageBox.question(
                self, 'Cleanup Old Backups',
                'This will remove old backups based on retention policy.\n\n'
                'Are you sure?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import asyncio
                asyncio.run(backup_service.cleanup_old_backups())
                self.show_error("Old backups cleaned up")
            
        except Exception as e:
            self.show_error(f"Error cleaning up old backups: {e}")
    
    def filter_backups(self):
        """Filter backups by type"""
        self.update_backups_table()
    
    def handle_backup_result(self, result: Any):
        """Handle backup operation result"""
        try:
            self.progress_bar.setVisible(False)
            
            if hasattr(result, 'success'):
                if result.success:
                    QMessageBox.information(self, "Success", f"Backup created: {result.file_path}")
                    self.backup_name_input.clear()
                else:
                    QMessageBox.critical(self, "Error", f"Backup failed: {result.error_message}")
            
            elif isinstance(result, dict):
                if result.get('success'):
                    QMessageBox.information(self, "Success", f"Operation completed")
                else:
                    QMessageBox.critical(self, "Error", f"Operation failed")
            
        except Exception as e:
            self.show_error(f"Error handling backup result: {e}")
    
    def show_error(self, message: str):
        """Show error message"""
        if PYQT6_AVAILABLE:
            QMessageBox.critical(self, "Error", message)
        else:
            print(f"Backup Panel Error: {message}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_monitoring()
        super().closeEvent(event)
