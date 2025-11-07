"""Diff viewer for comparing file versions."""

from pathlib import Path
from typing import Optional, List, Tuple

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
        QLabel, QComboBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QTextCharFormat
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.logger import logger


class DiffLine:
    """Represents a single line in a diff."""
    
    def __init__(self, line_type: str, content: str, line_number: Optional[int] = None):
        """
        Args:
            line_type: "added", "removed", "context", or "header"
            content: The actual line content
            line_number: The line number (optional)
        """
        self.line_type = line_type
        self.content = content
        self.line_number = line_number


class DiffViewer(QWidget):
    """Diff viewer widget for comparing file versions."""
    
    file_reverted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is required for DiffViewer")
        
        super().__init__(parent)
        
        self.current_content = ""
        self.original_content = ""
        self.diff_lines: List[DiffLine] = []
        
        self._setup_ui()
        logger.info("Initialized DiffViewer")
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        control_layout = QHBoxLayout()
        
        label = QLabel("Diff View:")
        control_layout.addWidget(label)
        
        self.view_mode = QComboBox()
        self.view_mode.addItems(["Inline", "Side-by-side"])
        self.view_mode.currentIndexChanged.connect(self._on_view_mode_changed)
        control_layout.addWidget(self.view_mode)
        
        self.revert_button = QPushButton("Revert Changes")
        self.revert_button.clicked.connect(self._on_revert_changes)
        control_layout.addWidget(self.revert_button)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        self.diff_display = QPlainTextEdit()
        self.diff_display.setReadOnly(True)
        
        font = QFont("Courier New", 9)
        font.setFixedPitch(True)
        self.diff_display.setFont(font)
        
        layout.addWidget(self.diff_display)
        
        self.setLayout(layout)
    
    def set_content(self, current_content: str, original_content: str) -> None:
        """Set the content for comparison.
        
        Args:
            current_content: The current/modified content.
            original_content: The original/reference content.
        """
        self.current_content = current_content
        self.original_content = original_content
        self._compute_diff()
        self._render_diff()
    
    def _compute_diff(self) -> None:
        """Compute the diff between current and original content."""
        self.diff_lines = []
        
        current_lines = self.current_content.splitlines(keepends=True)
        original_lines = self.original_content.splitlines(keepends=True)
        
        try:
            import difflib
            differ = difflib.unified_diff(
                original_lines, current_lines,
                fromfile="original", tofile="current",
                lineterm=''
            )
            
            for line in differ:
                if line.startswith('---') or line.startswith('+++'):
                    self.diff_lines.append(DiffLine("header", line))
                elif line.startswith('+'):
                    self.diff_lines.append(DiffLine("added", line[1:]))
                elif line.startswith('-'):
                    self.diff_lines.append(DiffLine("removed", line[1:]))
                elif line.startswith('@'):
                    self.diff_lines.append(DiffLine("header", line))
                else:
                    self.diff_lines.append(DiffLine("context", line[1:] if line.startswith(' ') else line))
        except Exception as e:
            logger.error(f"Error computing diff: {e}")
            self.diff_lines = []
    
    def _render_diff(self) -> None:
        """Render the diff to the display."""
        self.diff_display.clear()
        
        added_format = QTextCharFormat()
        added_format.setForeground(QColor("#00aa00"))
        added_format.setBackground(QColor("#eeffee"))
        
        removed_format = QTextCharFormat()
        removed_format.setForeground(QColor("#aa0000"))
        removed_format.setBackground(QColor("#ffeeee"))
        
        header_format = QTextCharFormat()
        header_format.setForeground(QColor("#0066ff"))
        header_format.setFontWeight(600)
        
        context_format = QTextCharFormat()
        context_format.setForeground(QColor("#666666"))
        
        cursor = self.diff_display.textCursor()
        
        for diff_line in self.diff_lines:
            if diff_line.line_type == "added":
                prefix = "+ "
                fmt = added_format
            elif diff_line.line_type == "removed":
                prefix = "- "
                fmt = removed_format
            elif diff_line.line_type == "header":
                prefix = ""
                fmt = header_format
            else:
                prefix = "  "
                fmt = context_format
            
            cursor.movePosition(1)
            cursor.insertText(prefix + diff_line.content + "\n", fmt)
        
        self.diff_display.setTextCursor(cursor)
    
    def _on_view_mode_changed(self, index: int) -> None:
        """Handle view mode change."""
        self._render_diff()
    
    def _on_revert_changes(self) -> None:
        """Handle revert changes button click."""
        self.current_content = self.original_content
        self._compute_diff()
        self._render_diff()
        self.file_reverted.emit(self.original_content)
    
    def get_diff_summary(self) -> Tuple[int, int, int]:
        """Get a summary of changes.
        
        Returns:
            Tuple of (added_lines, removed_lines, changed_lines)
        """
        added = sum(1 for line in self.diff_lines if line.line_type == "added")
        removed = sum(1 for line in self.diff_lines if line.line_type == "removed")
        changed = added + removed
        
        return added, removed, changed
    
    def export_diff(self, output_path: str) -> bool:
        """Export the diff to a file.
        
        Args:
            output_path: Path where to save the diff.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in self.diff_lines:
                    if line.line_type == "added":
                        f.write(f"+ {line.content}\n")
                    elif line.line_type == "removed":
                        f.write(f"- {line.content}\n")
                    elif line.line_type == "header":
                        f.write(f"{line.content}\n")
                    else:
                        f.write(f"  {line.content}\n")
            return True
        except Exception as e:
            logger.error(f"Error exporting diff: {e}")
            return False
