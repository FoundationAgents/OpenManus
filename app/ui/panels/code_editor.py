"""
Code editor panel for the IDE layout.
Provides syntax highlighting and code editing capabilities.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
        QComboBox, QPushButton, QFileDialog, QMessageBox
    )
    from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
    from PyQt6.QtCore import pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass
    class QSyntaxHighlighter:
        pass
    class QTextCharFormat:
        pass
    class QColor:
        def __init__(self, *args):
            pass
    def pyqtSignal(*args, **kwargs):
        class DummySignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return DummySignal()


if PYQT6_AVAILABLE:
    class SyntaxHighlighter(QSyntaxHighlighter):
        """Simple Python syntax highlighter."""
        
        def __init__(self, document):
            super().__init__(document)
            
        def highlightBlock(self, text: str):
            """Highlight text blocks with basic syntax highlighting."""
            if not text.strip():
                return
                
            keywords = [
                "def", "class", "if", "else", "elif", "for", "while",
                "return", "import", "from", "as", "try", "except",
                "finally", "with", "async", "await", "yield"
            ]
            
            format = QTextCharFormat()
            format.setForeground(QColor("#569CD6"))
            
            for keyword in keywords:
                index = text.find(keyword)
                while index != -1:
                    self.setFormat(index, len(keyword), format)
                    index = text.find(keyword, index + 1)
else:
    class SyntaxHighlighter:
        """Dummy syntax highlighter."""
        def __init__(self, document):
            pass


class CodeEditorPanel(QWidget):
    """Central code editor panel for the IDE."""
    
    file_opened = pyqtSignal(str) if PYQT6_AVAILABLE else None
    file_saved = pyqtSignal(str) if PYQT6_AVAILABLE else None
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the code editor UI."""
        layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file open")
        toolbar_layout.addWidget(self.file_label)
        
        toolbar_layout.addStretch()
        
        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self.open_file)
        toolbar_layout.addWidget(self.open_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.save_button)
        
        layout.addLayout(toolbar_layout)
        
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 10))
        self.editor.setPlaceholderText("Open a file to edit or start typing...")
        
        self.highlighter = SyntaxHighlighter(self.editor.document())
        
        layout.addWidget(self.editor)
        
        self.setLayout(layout)
        
    def open_file(self):
        """Open a file for editing."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                self.editor.setText(content)
                self.current_file = file_path
                self.file_label.setText(f"File: {file_path}")
                if self.file_opened:
                    self.file_opened.emit(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
                
    def save_file(self):
        """Save the current file."""
        if not self.current_file:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
            )
            if not file_path:
                return
            self.current_file = file_path
            
        try:
            with open(self.current_file, 'w') as f:
                f.write(self.editor.toPlainText())
            self.file_label.setText(f"File: {self.current_file}")
            if self.file_saved:
                self.file_saved.emit(self.current_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
            
    def set_code(self, code: str):
        """Set the code in the editor."""
        self.editor.setText(code)
        
    def get_code(self) -> str:
        """Get the code from the editor."""
        return self.editor.toPlainText()
        
    def clear_editor(self):
        """Clear the editor."""
        self.editor.clear()
        self.current_file = None
        self.file_label.setText("No file open")
