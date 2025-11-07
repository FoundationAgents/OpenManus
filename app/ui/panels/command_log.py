"""
Command log panel for displaying execution history and command logs.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
        QLabel, QLineEdit, QComboBox
    )
    from PyQt6.QtGui import QFont, QTextCursor, QColor
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass


class CommandLogPanel(QWidget):
    """Panel for displaying command execution logs."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the command log UI."""
        layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        
        toolbar_layout.addWidget(QLabel("Command Execution Log"))
        toolbar_layout.addStretch()
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["All", "Info", "Warning", "Error", "Debug"])
        toolbar_layout.addWidget(QLabel("Level:"))
        toolbar_layout.addWidget(self.log_level_combo)
        
        self.clear_button = QPushButton("Clear")
        toolbar_layout.addWidget(self.clear_button)
        
        layout.addLayout(toolbar_layout)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier New", 9))
        
        layout.addWidget(self.log_display)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search logs...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        self.setLayout(layout)
        
    def add_log(self, level: str, message: str, timestamp: str = None):
        """Add a log entry."""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
        
        if PYQT6_AVAILABLE:
            if level.lower() == "error":
                self.log_display.setTextColor(QColor("#FF0000"))
            elif level.lower() == "warning":
                self.log_display.setTextColor(QColor("#FFA500"))
            elif level.lower() == "debug":
                self.log_display.setTextColor(QColor("#808080"))
            else:
                self.log_display.setTextColor(QColor("#000000"))
            
        self.log_display.append(log_entry)
        
    def on_search_changed(self, text: str):
        """Handle search text changes."""
        pass
        
    def clear_logs(self):
        """Clear all logs."""
        self.log_display.clear()
        
    def export_logs(self, file_path: str):
        """Export logs to a file."""
        try:
            with open(file_path, 'w') as f:
                f.write(self.log_display.toPlainText())
        except Exception as e:
            self.add_log("error", f"Failed to export logs: {e}")
