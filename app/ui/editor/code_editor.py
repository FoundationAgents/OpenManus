"""Code editor component with syntax highlighting, line numbers, and folding support."""

import re
from pathlib import Path
from typing import Optional, List

try:
    from PyQt6.QtWidgets import (
        QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QLabel
    )
    from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QTimer
    from PyQt6.QtGui import (
        QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter,
        QTextDocument, QBrush
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.logger import logger
from app.languages.registry import get_language_registry, Language


if PYQT6_AVAILABLE:
    class LineNumberArea(QWidget):
        """Line number display widget for the code editor."""
        
        def __init__(self, editor: "CodeEditor"):
            super().__init__(editor)
            self.editor = editor
        
        def sizeHint(self) -> QSize:
            """Return the suggested size for the line number area."""
            return QSize(self.editor.line_number_area_width(), 0)
        
        def paintEvent(self, event):
            """Paint line numbers."""
            if not PYQT6_AVAILABLE:
                return
            
            self.editor.line_number_area_paint_event(event)


class PythonSyntaxHighlighter(QSyntaxHighlighter if PYQT6_AVAILABLE else object):
    """Syntax highlighter for Python code."""
    
    def __init__(self, document: QTextDocument if PYQT6_AVAILABLE else None):
        if PYQT6_AVAILABLE:
            super().__init__(document)
        
            self.keyword_format = QTextCharFormat()
            self.keyword_format.setForeground(QColor("#0066ff"))
            self.keyword_format.setFontWeight(600)
            
            self.builtin_format = QTextCharFormat()
            self.builtin_format.setForeground(QColor("#7f0000"))
            
            self.comment_format = QTextCharFormat()
            self.comment_format.setForeground(QColor("#008000"))
            self.comment_format.setFontItalic(True)
            
            self.string_format = QTextCharFormat()
            self.string_format.setForeground(QColor("#b20000"))
            
            self.number_format = QTextCharFormat()
            self.number_format.setForeground(QColor("#0066ff"))
        
        self.keywords = [
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
            "or", "pass", "raise", "return", "try", "while", "with", "yield",
            "True", "False", "None"
        ]
        
        self.builtins = [
            "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray",
            "bytes", "callable", "chr", "classmethod", "compile", "complex",
            "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec",
            "filter", "float", "format", "frozenset", "getattr", "globals",
            "hasattr", "hash", "hex", "id", "input", "int", "isinstance",
            "issubclass", "iter", "len", "list", "locals", "map", "max",
            "memoryview", "min", "next", "object", "oct", "open", "ord", "pow",
            "print", "property", "range", "repr", "reversed", "round", "set",
            "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super",
            "tuple", "type", "vars", "zip"
        ]
    
    def highlightBlock(self, text: str) -> None:
        """Highlight a block of Python code."""
        if not PYQT6_AVAILABLE:
            return
        
        # Highlight comments
        comment_index = text.find("#")
        if comment_index >= 0:
            self.setFormat(comment_index, len(text) - comment_index, self.comment_format)
        
        # Highlight strings
        for pattern, quote in [('"""', '"""'), ("'''", "'''"), ('"', '"'), ("'", "'")]:
            start_index = 0
            while True:
                start_index = text.find(pattern, start_index)
                if start_index == -1:
                    break
                
                end_index = text.find(pattern, start_index + len(pattern))
                if end_index == -1:
                    end_index = len(text)
                else:
                    end_index += len(pattern)
                
                self.setFormat(start_index, end_index - start_index, self.string_format)
                start_index = end_index
        
        # Highlight keywords and builtins
        for word in re.findall(r"\b\w+\b", text):
            if word in self.keywords:
                fmt = self.keyword_format
            elif word in self.builtins:
                fmt = self.builtin_format
            else:
                continue
            
            for match in re.finditer(r"\b" + word + r"\b", text):
                self.setFormat(match.start(), len(word), fmt)
        
        # Highlight numbers
        for match in re.finditer(r"\b\d+\b", text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)


if PYQT6_AVAILABLE:
    class CodeEditor(QPlainTextEdit):
        """Rich code editor with syntax highlighting and line numbers."""
        
        content_changed = pyqtSignal()
        file_path_changed = pyqtSignal(str)
        
        def __init__(self, parent=None, file_path: Optional[str] = None, language_id: Optional[str] = None):
            super().__init__(parent)
            
            self.file_path = file_path
            self.language_id = language_id
            self.language: Optional[Language] = None
            self._modified = False
            self._last_saved_content = ""
            
            self.line_number_area = LineNumberArea(self)
            self.highlighter = PythonSyntaxHighlighter(self.document())
            
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            self.setTabStopDistance(40)
            
            font = QFont("Courier New", 10)
            font.setFixedPitch(True)
            self.setFont(font)
            
            self.textChanged.connect(self._on_text_changed)
            self.blockCountChanged.connect(self._update_line_number_area_width)
            self.updateRequest.connect(self._update_line_number_area)
            
            self._update_line_number_area_width(0)
            self._update_syntax_highlighter()
            
            logger.info(f"Created code editor for file: {file_path}")
        
        def set_file_path(self, file_path: str) -> None:
            """Set the file path and detect language."""
            self.file_path = file_path
            
            ext = Path(file_path).suffix.lower()
            registry = get_language_registry()
            language = registry.get_language_by_extension(ext)
            
            if language:
                self.language_id = language.id
                self.language = language
                self._update_syntax_highlighter()
            
            self.file_path_changed.emit(file_path)
        
        def set_language(self, language_id: str) -> None:
            """Set the language for syntax highlighting."""
            registry = get_language_registry()
            language = registry.get_language(language_id)
            
            if language:
                self.language_id = language_id
                self.language = language
                self._update_syntax_highlighter()
        
        def _update_syntax_highlighter(self) -> None:
            """Update the syntax highlighter based on current language."""
            if self.language_id == "python":
                self.highlighter = PythonSyntaxHighlighter(self.document())
            else:
                self.highlighter = PythonSyntaxHighlighter(self.document())
        
        def line_number_area_width(self) -> int:
            """Calculate the width needed for line numbers."""
            digits = len(str(max(1, self.blockCount())))
            return 3 + self.fontMetrics().horizontalAdvance("9") * digits
        
        def _update_line_number_area_width(self, _: int) -> None:
            """Update line number area width when block count changes."""
            self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        
        def _update_line_number_area(self, rect: QRect, dy: int) -> None:
            """Update line number area display."""
            if dy:
                self.line_number_area.scroll(0, dy)
            else:
                self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
            
            if rect.contains(self.viewport().rect()):
                self._update_line_number_area_width(0)
        
        def line_number_area_paint_event(self, event) -> None:
            """Paint line numbers."""
            painter = QPainter(self.line_number_area)
            painter.fillRect(event.rect(), QColor("#f0f0f0"))
            
            block = self.firstVisibleBlock()
            block_number = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()
            
            painter.setPen(QColor("#808080"))
            
            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = str(block_number + 1)
                    painter.drawText(
                        0, int(top), self.line_number_area.width() - 2,
                        self.fontMetrics().height(), 1, number
                    )
                
                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                block_number += 1
        
        def resizeEvent(self, event) -> None:
            """Handle resize event."""
            super().resizeEvent(event)
            
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        
        def _on_text_changed(self) -> None:
            """Handle text change event."""
            self._modified = True
            self.content_changed.emit()
        
        def set_content(self, content: str) -> None:
            """Set the editor content."""
            self.setPlainText(content)
            self._last_saved_content = content
            self._modified = False
        
        def get_content(self) -> str:
            """Get the editor content."""
            return self.toPlainText()
        
        def is_modified(self) -> bool:
            """Check if content has been modified since last save."""
            return self._modified
        
        def save_content(self) -> bool:
            """Save content to file."""
            if not self.file_path:
                return False
            
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.get_content())
                self._modified = False
                self._last_saved_content = self.get_content()
                logger.info(f"Saved file: {self.file_path}")
                return True
            except Exception as e:
                logger.error(f"Error saving file {self.file_path}: {e}")
                return False
        
        def load_content(self) -> bool:
            """Load content from file."""
            if not self.file_path:
                return False
            
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.set_content(content)
                logger.info(f"Loaded file: {self.file_path}")
                return True
            except Exception as e:
                logger.error(f"Error loading file {self.file_path}: {e}")
                return False
        
        def insert_snippet(self, snippet: str) -> None:
            """Insert a code snippet at the current cursor position."""
            cursor = self.textCursor()
            cursor.insertText(snippet)
        
        def get_current_line(self) -> str:
            """Get the current line text."""
            cursor = self.textCursor()
            cursor.select(1)
            return cursor.selectedText()
        
        def get_current_word(self) -> str:
            """Get the current word."""
            cursor = self.textCursor()
            cursor.select(3)
            return cursor.selectedText()


else:
    class CodeEditor:
        """Placeholder for CodeEditor when PyQt6 is not available."""
        def __init__(self, parent=None, file_path: Optional[str] = None, language_id: Optional[str] = None):
            raise RuntimeError("PyQt6 is required for CodeEditor")
