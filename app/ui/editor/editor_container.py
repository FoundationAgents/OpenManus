"""Editor container with tab management and file tree integration."""

from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTreeWidget,
        QTreeWidgetItem, QSplitter, QPushButton, QLabel, QFileDialog,
        QMessageBox, QMenu, QInputDialog
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.logger import logger
from app.ui.editor.code_editor import CodeEditor


@dataclass
class OpenFile:
    """Represents an open file in the editor."""
    file_path: str
    editor: "CodeEditor"
    language_id: Optional[str] = None


class EditorContainer(QWidget):
    """Container for managing multiple editor tabs and file tree."""
    
    file_opened = pyqtSignal(str)
    file_saved = pyqtSignal(str)
    file_closed = pyqtSignal(str)
    
    def __init__(self, parent=None, workspace_dir: str = "./workspace"):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is required for EditorContainer")
        
        super().__init__(parent)
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        self.open_files: Dict[str, OpenFile] = {}
        self.current_file: Optional[str] = None
        
        self._setup_ui()
        logger.info(f"Initialized EditorContainer with workspace: {self.workspace_dir}")
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        if not PYQT6_AVAILABLE:
            return
        
        layout = QHBoxLayout()
        
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        left_label = QLabel("File Tree")
        left_layout.addWidget(left_label)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Files")
        self.file_tree.itemDoubleClicked.connect(self._on_file_tree_item_double_clicked)
        left_layout.addWidget(self.file_tree)
        
        btn_layout = QHBoxLayout()
        self.btn_new_file = QPushButton("New File")
        self.btn_new_file.clicked.connect(self._on_new_file)
        btn_layout.addWidget(self.btn_new_file)
        
        self.btn_open_file = QPushButton("Open File")
        self.btn_open_file.clicked.connect(self._on_open_file)
        btn_layout.addWidget(self.btn_open_file)
        
        left_layout.addLayout(btn_layout)
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(250)
        
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        
        tab_layout = QHBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        tab_layout.addWidget(self.tabs)
        center_layout.addLayout(tab_layout)
        
        right_panel_layout = QVBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        right_panel_layout.addWidget(self.save_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self._on_close)
        right_panel_layout.addWidget(self.close_button)
        
        right_panel_layout.addStretch()
        
        right_panel = QWidget()
        right_panel.setLayout(right_panel_layout)
        right_panel.setMaximumWidth(100)
        
        center_layout.addLayout(right_panel_layout)
        center_panel.setLayout(center_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def open_file(self, file_path: str, language_id: Optional[str] = None) -> bool:
        """Open a file in the editor.
        
        Args:
            file_path: Path to the file to open.
            language_id: Optional language ID for syntax highlighting.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            file_path = str(Path(file_path).resolve())
            
            if file_path in self.open_files:
                tab_index = list(self.open_files.keys()).index(file_path)
                self.tabs.setCurrentIndex(tab_index)
                return True
            
            editor = CodeEditor(file_path=file_path, language_id=language_id)
            
            if Path(file_path).exists():
                editor.load_content()
            
            tab_label = Path(file_path).name
            tab_index = self.tabs.addTab(editor, tab_label)
            
            open_file = OpenFile(file_path, editor, language_id)
            self.open_files[file_path] = open_file
            
            self.tabs.setCurrentIndex(tab_index)
            self.current_file = file_path
            
            self.file_opened.emit(file_path)
            logger.info(f"Opened file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {e}")
            return False
    
    def close_file(self, file_path: Optional[str] = None) -> bool:
        """Close a file.
        
        Args:
            file_path: Path to the file to close. If None, closes current file.
            
        Returns:
            True if successful, False otherwise.
        """
        file_path = file_path or self.current_file
        if not file_path:
            return False
        
        if file_path in self.open_files:
            open_file = self.open_files[file_path]
            
            if open_file.editor.is_modified():
                response = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"File '{Path(file_path).name}' has unsaved changes. Save before closing?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                )
                
                if response == QMessageBox.StandardButton.Save:
                    if not open_file.editor.save_content():
                        return False
            
            tab_index = list(self.open_files.keys()).index(file_path)
            self.tabs.removeTab(tab_index)
            
            del self.open_files[file_path]
            
            if self.current_file == file_path:
                self.current_file = None
            
            self.file_closed.emit(file_path)
            logger.info(f"Closed file: {file_path}")
            return True
        
        return False
    
    def save_current_file(self) -> bool:
        """Save the current file.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.current_file:
            return False
        
        open_file = self.open_files.get(self.current_file)
        if not open_file:
            return False
        
        if open_file.editor.save_content():
            self.file_saved.emit(self.current_file)
            return True
        
        return False
    
    def get_current_editor(self) -> Optional[CodeEditor]:
        """Get the current editor widget.
        
        Returns:
            Current CodeEditor or None if no file is open.
        """
        if not self.current_file:
            return None
        
        open_file = self.open_files.get(self.current_file)
        return open_file.editor if open_file else None
    
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change event."""
        if index >= 0 and index < len(self.open_files):
            self.current_file = list(self.open_files.keys())[index]
    
    def _on_tab_close_requested(self, index: int) -> None:
        """Handle tab close request."""
        if index >= 0 and index < len(self.open_files):
            file_path = list(self.open_files.keys())[index]
            self.close_file(file_path)
    
    def _on_file_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle file tree item double click."""
        file_path = item.data(0, 1)
        
        if file_path and Path(file_path).is_file():
            self.open_file(file_path)
    
    def _on_new_file(self) -> None:
        """Handle new file button click."""
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if ok and name:
            file_path = self.workspace_dir / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            self.open_file(str(file_path))
            self._refresh_file_tree()
    
    def _on_open_file(self) -> None:
        """Handle open file button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", str(self.workspace_dir)
        )
        if file_path:
            self.open_file(file_path)
    
    def _on_save(self) -> None:
        """Handle save button click."""
        self.save_current_file()
    
    def _on_close(self) -> None:
        """Handle close button click."""
        self.close_file()
    
    def _refresh_file_tree(self) -> None:
        """Refresh the file tree display."""
        self.file_tree.clear()
        
        for item in self.workspace_dir.rglob("*"):
            if item.is_file():
                parent = self.file_tree
                rel_path = item.relative_to(self.workspace_dir)
                
                for part in rel_path.parts[:-1]:
                    found = False
                    for i in range(parent.topLevelItemCount()):
                        existing = parent.topLevelItem(i)
                        if existing.text(0) == part:
                            parent = existing
                            found = True
                            break
                    
                    if not found:
                        new_item = QTreeWidgetItem()
                        new_item.setText(0, part)
                        parent.addChild(new_item)
                        parent = new_item
                
                file_item = QTreeWidgetItem()
                file_item.setText(0, item.name)
                file_item.setData(0, 1, str(item))
                parent.addChild(file_item)
    
    def set_workspace_dir(self, workspace_dir: str) -> None:
        """Set the workspace directory.
        
        Args:
            workspace_dir: Path to the workspace directory.
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._refresh_file_tree()
