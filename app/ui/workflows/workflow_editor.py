"""Workflow editor and runner UI"""
import asyncio
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QTextEdit,
        QLabel,
        QFileDialog,
        QMessageBox,
        QSplitter,
        QGroupBox,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QProgressBar,
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from app.workflows.callbacks import EventType, LoggingCallback
from app.workflows.manager import WorkflowManager
from app.workflows.models import WorkflowExecutionState

if PYQT_AVAILABLE:
    from app.ui.workflows.workflow_visualizer import WorkflowVisualizer


if PYQT_AVAILABLE:
    class WorkflowEditor(QWidget):
        """Main workflow editor and execution interface"""
        
        # Signals
        workflow_loaded = pyqtSignal(str)
        execution_started = pyqtSignal(str)
        execution_completed = pyqtSignal(str)
        state_updated = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.manager = WorkflowManager()
            self.current_workflow_id: Optional[str] = None
            self.execution_task: Optional[asyncio.Task] = None
            self.logging_callback = LoggingCallback(verbose=False)
            
            # Setup callback
            self.manager.add_callback(self._on_workflow_event)
            
            self._setup_ui()
            self._setup_update_timer()
        
        def _setup_ui(self):
            """Setup UI components"""
            layout = QVBoxLayout(self)
            
            # Control panel
            control_group = QGroupBox("Workflow Control")
            control_layout = QHBoxLayout()
            
            self.load_btn = QPushButton("Load Workflow")
            self.load_btn.clicked.connect(self._on_load_workflow)
            control_layout.addWidget(self.load_btn)
            
            self.execute_btn = QPushButton("Execute")
            self.execute_btn.clicked.connect(self._on_execute_workflow)
            self.execute_btn.setEnabled(False)
            control_layout.addWidget(self.execute_btn)
            
            self.pause_btn = QPushButton("Pause")
            self.pause_btn.clicked.connect(self._on_pause_workflow)
            self.pause_btn.setEnabled(False)
            control_layout.addWidget(self.pause_btn)
            
            self.resume_btn = QPushButton("Resume")
            self.resume_btn.clicked.connect(self._on_resume_workflow)
            self.resume_btn.setEnabled(False)
            control_layout.addWidget(self.resume_btn)
            
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self._on_cancel_workflow)
            self.cancel_btn.setEnabled(False)
            control_layout.addWidget(self.cancel_btn)
            
            control_layout.addStretch()
            control_group.setLayout(control_layout)
            layout.addWidget(control_group)
            
            # Main content area with splitter
            splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Visualizer
            viz_group = QGroupBox("Workflow Visualization")
            viz_layout = QVBoxLayout()
            
            self.visualizer = WorkflowVisualizer()
            viz_layout.addWidget(self.visualizer)
            
            # Zoom controls
            zoom_layout = QHBoxLayout()
            zoom_in_btn = QPushButton("Zoom In")
            zoom_in_btn.clicked.connect(self.visualizer.zoom_in)
            zoom_layout.addWidget(zoom_in_btn)
            
            zoom_out_btn = QPushButton("Zoom Out")
            zoom_out_btn.clicked.connect(self.visualizer.zoom_out)
            zoom_layout.addWidget(zoom_out_btn)
            
            reset_zoom_btn = QPushButton("Reset Zoom")
            reset_zoom_btn.clicked.connect(self.visualizer.reset_zoom)
            zoom_layout.addWidget(reset_zoom_btn)
            
            zoom_layout.addStretch()
            viz_layout.addLayout(zoom_layout)
            
            viz_group.setLayout(viz_layout)
            splitter.addWidget(viz_group)
            
            # Status panel
            status_group = QGroupBox("Execution Status")
            status_layout = QVBoxLayout()
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            status_layout.addWidget(self.progress_bar)
            
            # Status label
            self.status_label = QLabel("No workflow loaded")
            status_layout.addWidget(self.status_label)
            
            # Node status table
            self.status_table = QTableWidget()
            self.status_table.setColumnCount(4)
            self.status_table.setHorizontalHeaderLabels(["Node ID", "Status", "Attempts", "Duration"])
            self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            status_layout.addWidget(self.status_table)
            
            status_group.setLayout(status_layout)
            splitter.addWidget(status_group)
            
            # Logs panel
            log_group = QGroupBox("Execution Log")
            log_layout = QVBoxLayout()
            
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            log_layout.addWidget(self.log_text)
            
            clear_log_btn = QPushButton("Clear Log")
            clear_log_btn.clicked.connect(self.log_text.clear)
            log_layout.addWidget(clear_log_btn)
            
            log_group.setLayout(log_layout)
            splitter.addWidget(log_group)
            
            # Set splitter sizes
            splitter.setSizes([400, 200, 200])
            
            layout.addWidget(splitter)
            self.setLayout(layout)
        
        def _setup_update_timer(self):
            """Setup timer for UI updates"""
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self._update_status)
            self.update_timer.start(500)  # Update every 500ms
        
        def _on_load_workflow(self):
            """Load workflow from file"""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Workflow",
                "",
                "Workflow Files (*.yaml *.yml *.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            try:
                workflow_id = self.manager.load_workflow(Path(file_path))
                self.current_workflow_id = workflow_id
                
                # Load visualization
                dag = self.manager.get_workflow_dag(workflow_id)
                if dag:
                    self.visualizer.load_workflow(dag)
                
                # Update status
                workflow = self.manager.get_workflow(workflow_id)
                self.status_label.setText(
                    f"Loaded: {workflow.metadata.name} (v{workflow.metadata.version})"
                )
                
                # Enable execute button
                self.execute_btn.setEnabled(True)
                
                # Log
                self._log(f"Loaded workflow: {workflow.metadata.name}")
                
                self.workflow_loaded.emit(workflow_id)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load workflow: {e}")
        
        def _on_execute_workflow(self):
            """Execute the loaded workflow"""
            if not self.current_workflow_id:
                return
            
            # Create task for async execution
            loop = asyncio.get_event_loop()
            self.execution_task = loop.create_task(self._execute_async())
            
            # Update UI
            self.execute_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            
            self._log("Starting workflow execution...")
            self.execution_started.emit(self.current_workflow_id)
        
        async def _execute_async(self):
            """Async workflow execution"""
            try:
                state = await self.manager.execute_workflow(self.current_workflow_id)
                
                # Update UI on completion
                self._log(f"Workflow completed with status: {state.status}")
                self.execution_completed.emit(self.current_workflow_id)
                
            except Exception as e:
                self._log(f"Workflow execution failed: {e}")
                QMessageBox.critical(self, "Execution Error", f"Workflow failed: {e}")
            
            finally:
                # Reset UI
                self.execute_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
                self.resume_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
        
        def _on_pause_workflow(self):
            """Pause workflow execution"""
            if self.current_workflow_id:
                self.manager.pause_workflow(self.current_workflow_id)
                self.pause_btn.setEnabled(False)
                self.resume_btn.setEnabled(True)
                self._log("Workflow paused")
        
        def _on_resume_workflow(self):
            """Resume workflow execution"""
            if self.current_workflow_id:
                self.manager.resume_workflow(self.current_workflow_id)
                self.pause_btn.setEnabled(True)
                self.resume_btn.setEnabled(False)
                self._log("Workflow resumed")
        
        def _on_cancel_workflow(self):
            """Cancel workflow execution"""
            if self.current_workflow_id:
                self.manager.cancel_workflow(self.current_workflow_id)
                self.cancel_btn.setEnabled(False)
                self._log("Workflow cancelled")
        
        def _update_status(self):
            """Update status display"""
            if not self.current_workflow_id:
                return
            
            state = self.manager.get_workflow_state(self.current_workflow_id)
            if not state:
                return
            
            # Update visualizer
            self.visualizer.update_state(state)
            
            # Update progress bar
            total_nodes = len(state.definition.nodes)
            completed = len([
                r for r in state.node_results.values()
                if r.status.value in ["completed", "failed", "skipped"]
            ])
            
            if total_nodes > 0:
                progress = int((completed / total_nodes) * 100)
                self.progress_bar.setValue(progress)
            
            # Update status table
            self._update_status_table(state)
            
            self.state_updated.emit()
        
        def _update_status_table(self, state: WorkflowExecutionState):
            """Update node status table"""
            self.status_table.setRowCount(len(state.node_results))
            
            for row, (node_id, result) in enumerate(state.node_results.items()):
                # Node ID
                self.status_table.setItem(row, 0, QTableWidgetItem(node_id))
                
                # Status
                status_item = QTableWidgetItem(result.status.value)
                self.status_table.setItem(row, 1, status_item)
                
                # Attempts
                self.status_table.setItem(row, 2, QTableWidgetItem(str(result.attempts)))
                
                # Duration
                if result.end_time and result.start_time:
                    duration = result.end_time - result.start_time
                    self.status_table.setItem(row, 3, QTableWidgetItem(f"{duration:.2f}s"))
                else:
                    self.status_table.setItem(row, 3, QTableWidgetItem("-"))
        
        def _on_workflow_event(self, event):
            """Handle workflow events"""
            # Log event
            msg = f"[{event.event_type.value}]"
            if event.node_id:
                msg += f" {event.node_id}"
            if event.error:
                msg += f" - Error: {event.error}"
            
            self._log(msg)
        
        def _log(self, message: str):
            """Add message to log"""
            self.log_text.append(message)

else:
    class WorkflowEditor:
        """Placeholder when PyQt6 is not available"""
        def __init__(self, parent=None):
            raise ImportError("PyQt6 is required for WorkflowEditor")
