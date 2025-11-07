"""
Console panel for sandbox output and system feedback.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
        QLabel, QLineEdit
    )
    from PyQt6.QtGui import QFont, QTextCursor, QColor
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass


class ConsolePanel(QWidget):
    """Panel for displaying sandbox console output."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the console UI."""
        layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        
        toolbar_layout.addWidget(QLabel("Sandbox Console"))
        toolbar_layout.addStretch()
        
        self.scroll_lock_button = QPushButton("Auto-scroll")
        self.scroll_lock_button.setCheckable(True)
        self.scroll_lock_button.setChecked(True)
        toolbar_layout.addWidget(self.scroll_lock_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        toolbar_layout.addWidget(self.clear_button)
        
        layout.addLayout(toolbar_layout)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Courier New", 9))
        
        if PYQT6_AVAILABLE:
            self.console_output.setStyleSheet("""
                QTextEdit {
                    background-color: #000000;
                    color: #00FF00;
                    border: 1px solid #333333;
                }
            """)
        
        layout.addWidget(self.console_output)
        
        self.setLayout(layout)
        
    def write_output(self, text: str, color: str = "#00FF00"):
        """Write text to the console."""
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        
        if PYQT6_AVAILABLE:
            self.console_output.setTextColor(QColor(color))
        self.console_output.append(text)
        
        if self.scroll_lock_button.isChecked():
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
        
    def write_error(self, text: str):
        """Write error text to the console."""
        self.write_output(text, "#FF0000")
        
    def write_warning(self, text: str):
        """Write warning text to the console."""
        self.write_output(text, "#FFA500")
        
    def write_info(self, text: str):
        """Write info text to the console."""
        self.write_output(text, "#00FFFF")
        
    def clear_console(self):
        """Clear the console output."""
        self.console_output.clear()
