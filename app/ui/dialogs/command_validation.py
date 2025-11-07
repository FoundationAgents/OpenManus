"""
Command validation dialog for Guardian-driven confirmations.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QGroupBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QDialog:
        pass
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()


class CommandValidationDialog(QDialog):
    """Dialog for validating and approving commands through Guardian."""
    
    approved = pyqtSignal(str) if PYQT6_AVAILABLE else None
    rejected = pyqtSignal(str) if PYQT6_AVAILABLE else None
    
    def __init__(self, command: str, reason: str = "", parent=None):
        super().__init__(parent)
        self.command = command
        self.reason = reason
        self.init_ui()
        
    def init_ui(self):
        """Initialize the command validation dialog."""
        self.setWindowTitle("Command Validation - Guardian")
        self.setGeometry(100, 100, 500, 350)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("Guardian Command Validation")
        if PYQT6_AVAILABLE:
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(12)
            title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        command_group = QGroupBox("Command to Execute")
        command_layout = QVBoxLayout()
        
        self.command_display = QTextEdit()
        self.command_display.setText(self.command)
        self.command_display.setReadOnly(True)
        self.command_display.setFont(QFont("Courier New", 10))
        self.command_display.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                padding: 5px;
            }
        """)
        command_layout.addWidget(self.command_display)
        
        command_group.setLayout(command_layout)
        layout.addWidget(command_group)
        
        if self.reason:
            reason_group = QGroupBox("Validation Reason")
            reason_layout = QVBoxLayout()
            
            reason_label = QLabel(self.reason)
            reason_layout.addWidget(reason_label)
            
            reason_group.setLayout(reason_layout)
            layout.addWidget(reason_group)
        
        risk_group = QGroupBox("Risk Assessment")
        risk_layout = QVBoxLayout()
        
        risk_label = QLabel("⚠️ This command requires validation before execution.")
        risk_label.setStyleSheet("color: #FF8C00; font-weight: bold;")
        risk_layout.addWidget(risk_label)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        approve_button = QPushButton("Approve")
        approve_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        approve_button.clicked.connect(self.approve_command)
        button_layout.addWidget(approve_button)
        
        reject_button = QPushButton("Reject")
        reject_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        reject_button.clicked.connect(self.reject_command)
        button_layout.addWidget(reject_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def approve_command(self):
        """Approve the command."""
        if self.approved:
            self.approved.emit(self.command)
        self.accept()
        
    def reject_command(self):
        """Reject the command."""
        if self.rejected:
            self.rejected.emit(self.command)
        self.reject()
        
    def get_result(self) -> bool:
        """Get the result of the validation (True for approved, False for rejected)."""
        if PYQT6_AVAILABLE:
            return self.result() == QDialog.DialogCode.Accepted
        return False
