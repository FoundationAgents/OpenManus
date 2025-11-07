"""Editor UI module for code editing and management."""

from app.ui.editor.code_editor import CodeEditor, LineNumberArea, PythonSyntaxHighlighter
from app.ui.editor.editor_container import EditorContainer
from app.ui.editor.terminal_widget import TerminalWidget
from app.ui.editor.diff_viewer import DiffViewer

__all__ = [
    "CodeEditor",
    "LineNumberArea",
    "PythonSyntaxHighlighter",
    "EditorContainer",
    "TerminalWidget",
    "DiffViewer",
]
