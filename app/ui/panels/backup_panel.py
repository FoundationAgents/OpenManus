"""Backup management panel for the UI."""

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
        QTableWidgetItem, QLabel, QGroupBox, QMessageBox, QTextEdit,
        QProgressBar, QHeaderView
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QThread
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object
    class QThread:
        pass
    def pyqtSignal(*args, **kwargs):
        return None

from app.logger import logger
from app.storage.backup import get_backup_manager, BackupMetadata
from app.storage.guardian import get_guardian
from app.storage.versioning import get_versioning_engine
from app.ui.editor.diff_viewer import DiffViewer


class BackupWorker(QThread):
    """Worker thread for backup operations."""
    
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, operation: str, backup_id: Optional[str] = None):
        super().__init__()
        self.operation = operation
        self.backup_id = backup_id
        self.backup_manager = get_backup_manager()
    
    def run(self):
        """Run the backup operation."""
        try:
            if self.operation == "create":
                self.progress.emit("Creating backup...")
                metadata = self.backup_manager.create_backup(
                    backup_type="full",
                    description="Manual backup from UI",
                    include_versions=True
                )
                if metadata:
                    self.finished.emit(True, f"Backup created: {metadata.backup_id}")
                else:
                    self.finished.emit(False, "Failed to create backup")
            
            elif self.operation == "restore" and self.backup_id:
                self.progress.emit(f"Restoring backup {self.backup_id}...")
                success = self.backup_manager.restore_backup(
                    backup_id=self.backup_id,
                    require_approval=True
                )
                if success:
                    self.finished.emit(True, f"Backup restored: {self.backup_id}")
                else:
                    self.finished.emit(False, f"Failed to restore backup: {self.backup_id}")
            
            elif self.operation == "archive":
                self.progress.emit("Archiving old backups...")
                count = self.backup_manager.archive_old_backups()
                self.finished.emit(True, f"Archived {count} backups")
            
            else:
                self.finished.emit(False, "Unknown operation")
        
        except Exception as e:
            logger.error(f"Error in backup operation: {e}")
            self.finished.emit(False, str(e))


class BackupPanel(QWidget):
    """Panel for managing backups, archives, and restore points."""
    
    backup_created = pyqtSignal(str)
    backup_restored = pyqtSignal(str)
    
    def __init__(self, parent=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is required for BackupPanel")
        
        super().__init__(parent)
        
        self.backup_manager = get_backup_manager()
        self.guardian = get_guardian()
        self.versioning = get_versioning_engine()
        
        self.worker: Optional[BackupWorker] = None
        self.current_backups = []
        
        self._setup_guardian_callback()
        self._setup_ui()
        self._refresh_backups()
        
        logger.info("BackupPanel initialized")
    
    def _setup_guardian_callback(self):
        """Set up Guardian approval callback."""
        def approval_callback(request):
            from app.ui.dialogs.command_validation import CommandValidationDialog
            
            dialog = CommandValidationDialog(
                command=f"{request.operation} on {request.resource}",
                reason=request.reason,
                parent=self
            )
            result = dialog.exec()
            return dialog.get_result()
        
        self.guardian.set_approval_callback(approval_callback)
    
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        title = QLabel("Backup Manager")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        layout.addWidget(title)
        
        control_group = QGroupBox("Backup Controls")
        control_layout = QHBoxLayout()
        
        self.create_backup_btn = QPushButton("Create Backup")
        self.create_backup_btn.clicked.connect(self._on_create_backup)
        control_layout.addWidget(self.create_backup_btn)
        
        self.restore_backup_btn = QPushButton("Restore Selected")
        self.restore_backup_btn.clicked.connect(self._on_restore_backup)
        control_layout.addWidget(self.restore_backup_btn)
        
        self.preview_diff_btn = QPushButton("Preview Diff")
        self.preview_diff_btn.clicked.connect(self._on_preview_diff)
        control_layout.addWidget(self.preview_diff_btn)
        
        self.archive_btn = QPushButton("Archive Old Backups")
        self.archive_btn.clicked.connect(self._on_archive_old)
        control_layout.addWidget(self.archive_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_backups)
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        stats_group = QGroupBox("Backup Statistics")
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(100)
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        backups_group = QGroupBox("Backup History")
        backups_layout = QVBoxLayout()
        
        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(6)
        self.backups_table.setHorizontalHeaderLabels([
            "Backup ID", "Timestamp", "Type", "Size", "Files", "Description"
        ])
        self.backups_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.backups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.backups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        backups_layout.addWidget(self.backups_table)
        
        backups_group.setLayout(backups_layout)
        layout.addWidget(backups_group)
        
        self.setLayout(layout)
    
    def _refresh_backups(self):
        """Refresh the backup list."""
        try:
            self.current_backups = self.backup_manager.get_backups(limit=50)
            
            self.backups_table.setRowCount(len(self.current_backups))
            
            for i, backup in enumerate(self.current_backups):
                self.backups_table.setItem(i, 0, QTableWidgetItem(backup.backup_id))
                self.backups_table.setItem(i, 1, QTableWidgetItem(
                    backup.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ))
                self.backups_table.setItem(i, 2, QTableWidgetItem(backup.backup_type))
                self.backups_table.setItem(i, 3, QTableWidgetItem(
                    self._format_size(backup.size_bytes)
                ))
                self.backups_table.setItem(i, 4, QTableWidgetItem(str(backup.files_count)))
                self.backups_table.setItem(i, 5, QTableWidgetItem(
                    backup.description or ""
                ))
            
            self._update_stats()
            self.status_label.setText(f"Loaded {len(self.current_backups)} backups")
            
        except Exception as e:
            logger.error(f"Error refreshing backups: {e}")
            self.status_label.setText(f"Error: {e}")
    
    def _update_stats(self):
        """Update backup statistics."""
        try:
            stats = self.backup_manager.get_backup_stats()
            version_stats = self.versioning.get_storage_stats()
            
            stats_text = f"""
<b>Backup Statistics:</b>
- Total Backups: {stats['total_backups']}
- Total Size: {self._format_size(stats['total_size_bytes'])}
- Total Files: {stats['total_files']}
- Latest Backup: {stats['latest_backup'] or 'None'}

<b>Versioning Statistics:</b>
- Tracked Files: {version_stats['total_files']}
- Total Versions: {version_stats['total_versions']}
- Storage Objects: {version_stats['total_objects']}
- Storage Size: {self._format_size(version_stats['total_size_bytes'])}
            """
            
            self.stats_text.setHtml(stats_text)
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _on_create_backup(self):
        """Handle create backup button click."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "A backup operation is already in progress")
            return
        
        reply = QMessageBox.question(
            self,
            "Create Backup",
            "Create a new backup of the workspace and version history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_backup_operation("create")
    
    def _on_restore_backup(self):
        """Handle restore backup button click."""
        selected = self.backups_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a backup to restore")
            return
        
        row = self.backups_table.currentRow()
        if row < 0 or row >= len(self.current_backups):
            return
        
        backup = self.current_backups[row]
        
        reply = QMessageBox.question(
            self,
            "Restore Backup",
            f"Restore backup {backup.backup_id}?\n\n"
            f"This will require Guardian approval and may overwrite current files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_backup_operation("restore", backup.backup_id)
    
    def _on_preview_diff(self):
        """Handle preview diff button click."""
        selected = self.backups_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a backup to preview")
            return
        
        row = self.backups_table.currentRow()
        if row < 0 or row >= len(self.current_backups):
            return
        
        backup = self.current_backups[row]
        
        QMessageBox.information(
            self,
            "Preview Diff",
            f"Diff preview for backup {backup.backup_id}\n\n"
            f"Timestamp: {backup.timestamp}\n"
            f"Type: {backup.backup_type}\n"
            f"Size: {self._format_size(backup.size_bytes)}\n"
            f"Files: {backup.files_count}\n\n"
            f"Full diff preview functionality will extract and compare files."
        )
    
    def _on_archive_old(self):
        """Handle archive old backups button click."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "A backup operation is already in progress")
            return
        
        reply = QMessageBox.question(
            self,
            "Archive Old Backups",
            "Move old backups to archive storage?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_backup_operation("archive")
    
    def _start_backup_operation(self, operation: str, backup_id: Optional[str] = None):
        """Start a backup operation in a worker thread."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.create_backup_btn.setEnabled(False)
        self.restore_backup_btn.setEnabled(False)
        self.archive_btn.setEnabled(False)
        
        self.worker = BackupWorker(operation, backup_id)
        self.worker.finished.connect(self._on_operation_finished)
        self.worker.progress.connect(self._on_operation_progress)
        self.worker.start()
    
    def _on_operation_progress(self, message: str):
        """Handle operation progress update."""
        self.status_label.setText(message)
    
    def _on_operation_finished(self, success: bool, message: str):
        """Handle operation completion."""
        self.progress_bar.setVisible(False)
        self.create_backup_btn.setEnabled(True)
        self.restore_backup_btn.setEnabled(True)
        self.archive_btn.setEnabled(True)
        
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self._refresh_backups()
        else:
            QMessageBox.warning(self, "Error", message)
        
        self.worker = None
