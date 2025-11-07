"""Unit tests for the CodeEditor module."""

import tempfile
import unittest
from pathlib import Path

from app.ui.editor.code_editor import CodeEditor

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


@unittest.skipUnless(PYQT6_AVAILABLE, "PyQt6 is not available")
class TestCodeEditor(unittest.TestCase):
    """Test cases for the CodeEditor widget."""
    
    @classmethod
    def setUpClass(cls):
        """Set up PyQt application."""
        if PYQT6_AVAILABLE:
            cls.app = QApplication.instance() or QApplication([])
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_editor(self):
        """Test creating a code editor."""
        editor = CodeEditor()
        
        self.assertIsNotNone(editor)
        self.assertIsNone(editor.file_path)
        self.assertFalse(editor.is_modified())
    
    def test_set_content(self):
        """Test setting editor content."""
        editor = CodeEditor()
        content = "print('hello')\nprint('world')"
        
        editor.set_content(content)
        
        self.assertEqual(editor.get_content(), content)
        self.assertFalse(editor.is_modified())
    
    def test_content_modification(self):
        """Test content modification tracking."""
        editor = CodeEditor()
        editor.set_content("initial")
        
        self.assertFalse(editor.is_modified())
        
        cursor = editor.textCursor()
        cursor.insertText("\nmodified")
        editor.setTextCursor(cursor)
        
        self.assertTrue(editor.is_modified())
    
    def test_file_operations(self):
        """Test file load and save operations."""
        file_path = Path(self.temp_dir) / "test.py"
        content = "def hello():\n    print('hello')\n"
        
        file_path.write_text(content)
        
        editor = CodeEditor(file_path=str(file_path))
        result = editor.load_content()
        
        self.assertTrue(result)
        self.assertEqual(editor.get_content(), content)
        self.assertFalse(editor.is_modified())
    
    def test_save_content(self):
        """Test saving content to file."""
        file_path = Path(self.temp_dir) / "output.py"
        content = "x = 42\n"
        
        editor = CodeEditor(file_path=str(file_path))
        editor.set_content(content)
        
        result = editor.save_content()
        
        self.assertTrue(result)
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_text(), content)
    
    def test_set_file_path(self):
        """Test setting file path and language detection."""
        editor = CodeEditor()
        python_file = Path(self.temp_dir) / "script.py"
        
        editor.set_file_path(str(python_file))
        
        self.assertEqual(editor.file_path, str(python_file))
        self.assertEqual(editor.language_id, "python")
    
    def test_set_language(self):
        """Test setting language for syntax highlighting."""
        editor = CodeEditor()
        
        editor.set_language("javascript")
        
        self.assertEqual(editor.language_id, "javascript")
    
    def test_insert_snippet(self):
        """Test inserting code snippet."""
        editor = CodeEditor()
        editor.set_content("")
        
        editor.insert_snippet("print('snippet')")
        
        self.assertIn("snippet", editor.get_content())
    
    def test_get_current_line(self):
        """Test getting current line."""
        editor = CodeEditor()
        editor.set_content("line1\nline2\nline3")
        
        cursor = editor.textCursor()
        cursor.movePosition(1, 1)
        editor.setTextCursor(cursor)
        
        line = editor.get_current_line()
        self.assertIsNotNone(line)
    
    def test_line_number_area_width(self):
        """Test line number area width calculation."""
        editor = CodeEditor()
        editor.set_content("line1\nline2\nline3\nline4\nline5")
        
        width = editor.line_number_area_width()
        self.assertGreater(width, 0)


if __name__ == '__main__':
    unittest.main()
