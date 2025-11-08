"""
Project Manager - GUI for creating and managing projects.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QListWidget, QListWidgetItem, QFileDialog,
        QDialog, QFormLayout, QTextEdit, QDialogButtonBox,
        QGroupBox, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object
    QDialog = object

from app.ui.state_manager import get_state_manager
from app.ui.message_bus import get_message_bus, EventTypes

logger = logging.getLogger(__name__)


class NewProjectDialog(QDialog):
    """Dialog for creating a new project."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout()
        
        # Form
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        form.addRow("Project Name:", self.name_edit)
        
        # Location
        location_layout = QHBoxLayout()
        self.location_edit = QLineEdit()
        self.location_edit.setText(str(Path.home() / "OpenManusProjects"))
        location_layout.addWidget(self.location_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_btn)
        
        form.addRow("Location:", location_layout)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form.addRow("Description:", self.description_edit)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _browse_location(self):
        """Browse for project location."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Location")
        if directory:
            self.location_edit.setText(directory)
    
    def get_project_info(self) -> Dict[str, Any]:
        """Get project information."""
        return {
            "name": self.name_edit.text(),
            "location": Path(self.location_edit.text()),
            "description": self.description_edit.toPlainText()
        }


class ProjectManager(QWidget):
    """
    Project Manager panel.
    
    Features:
    - Create new projects
    - Open existing projects
    - Recent projects list
    - Project properties
    """
    
    DISPLAY_NAME = "Project Manager"
    DESCRIPTION = "Manage projects and workspaces"
    DEPENDENCIES = []
    
    project_opened = pyqtSignal(str, Path)
    project_created = pyqtSignal(str, Path)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_manager = get_state_manager()
        self.message_bus = get_message_bus()
        self.projects_dir = Path.home() / ".openmanus" / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
        self.init_ui()
        self.load_recent_projects()
    
    def init_ui(self):
        """Initialize the project manager UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Project Manager</h2>")
        layout.addWidget(title)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        new_btn = QPushButton("New Project")
        new_btn.clicked.connect(self.create_new_project)
        actions_layout.addWidget(new_btn)
        
        open_btn = QPushButton("Open Project")
        open_btn.clicked.connect(self.open_project)
        actions_layout.addWidget(open_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Recent projects
        recent_group = QGroupBox("Recent Projects")
        recent_layout = QVBoxLayout()
        
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._open_recent_project)
        recent_layout.addWidget(self.recent_list)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # Current project info
        self.current_project_label = QLabel("<i>No project open</i>")
        layout.addWidget(self.current_project_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def create_new_project(self):
        """Create a new project."""
        dialog = NewProjectDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            project_info = dialog.get_project_info()
            
            try:
                project_name = project_info["name"]
                location = project_info["location"]
                description = project_info["description"]
                
                if not project_name:
                    QMessageBox.warning(self, "Error", "Project name is required")
                    return
                
                # Create project directory
                project_path = location / project_name
                project_path.mkdir(parents=True, exist_ok=True)
                
                # Create project metadata
                metadata = {
                    "name": project_name,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
                
                metadata_file = project_path / ".openmanus_project.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Created project: {project_name} at {project_path}")
                
                # Open the project
                self._open_project_path(project_path)
                
                self.project_created.emit(project_name, project_path)
                
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create project: {e}")
    
    def open_project(self):
        """Open an existing project."""
        directory = QFileDialog.getExistingDirectory(self, "Open Project")
        
        if directory:
            project_path = Path(directory)
            self._open_project_path(project_path)
    
    def _open_project_path(self, project_path: Path):
        """Open a project from path."""
        try:
            # Check for project metadata
            metadata_file = project_path / ".openmanus_project.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                project_name = metadata.get("name", project_path.name)
            else:
                project_name = project_path.name
                metadata = {}
            
            # Update state
            self.state_manager.set_project(
                name=project_name,
                path=project_path,
                **metadata
            )
            
            # Update UI
            self.current_project_label.setText(
                f"<b>Current Project:</b> {project_name}<br>"
                f"<b>Path:</b> {project_path}"
            )
            
            # Add to recent
            self._add_to_recent(project_name, project_path)
            
            logger.info(f"Opened project: {project_name}")
            self.project_opened.emit(project_name, project_path)
            
        except Exception as e:
            logger.error(f"Error opening project: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
    
    def _open_recent_project(self, item: QListWidgetItem):
        """Open a recent project."""
        project_path = Path(item.data(Qt.ItemDataRole.UserRole))
        self._open_project_path(project_path)
    
    def load_recent_projects(self):
        """Load recent projects list."""
        try:
            recent_file = self.projects_dir / "recent.json"
            
            if recent_file.exists():
                with open(recent_file, 'r') as f:
                    recent = json.load(f)
                
                self.recent_list.clear()
                
                for project in recent:
                    name = project["name"]
                    path = Path(project["path"])
                    
                    if path.exists():
                        item = QListWidgetItem(f"{name} - {path}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        self.recent_list.addItem(item)
            
        except Exception as e:
            logger.error(f"Error loading recent projects: {e}")
    
    def _add_to_recent(self, project_name: str, project_path: Path):
        """Add project to recent list."""
        try:
            recent_file = self.projects_dir / "recent.json"
            
            # Load existing
            recent = []
            if recent_file.exists():
                with open(recent_file, 'r') as f:
                    recent = json.load(f)
            
            # Remove if already exists
            recent = [p for p in recent if p["path"] != str(project_path)]
            
            # Add to front
            recent.insert(0, {
                "name": project_name,
                "path": str(project_path),
                "opened_at": datetime.now().isoformat()
            })
            
            # Keep only last 10
            recent = recent[:10]
            
            # Save
            with open(recent_file, 'w') as f:
                json.dump(recent, f, indent=2)
            
            # Reload list
            self.load_recent_projects()
            
        except Exception as e:
            logger.error(f"Error saving recent projects: {e}")
