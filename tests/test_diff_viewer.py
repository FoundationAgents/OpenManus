"""Unit tests for the DiffViewer module."""

import unittest
from app.ui.editor.diff_viewer import DiffViewer, DiffLine

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


@unittest.skipUnless(PYQT6_AVAILABLE, "PyQt6 is not available")
class TestDiffLine(unittest.TestCase):
    """Test cases for the DiffLine class."""
    
    def test_create_diff_line(self):
        """Test creating a diff line."""
        line = DiffLine("added", "print('hello')", 1)
        
        self.assertEqual(line.line_type, "added")
        self.assertEqual(line.content, "print('hello')")
        self.assertEqual(line.line_number, 1)
    
    def test_diff_line_types(self):
        """Test different diff line types."""
        added = DiffLine("added", "new line")
        removed = DiffLine("removed", "old line")
        context = DiffLine("context", "unchanged line")
        header = DiffLine("header", "@@ -1,5 +1,6 @@")
        
        self.assertEqual(added.line_type, "added")
        self.assertEqual(removed.line_type, "removed")
        self.assertEqual(context.line_type, "context")
        self.assertEqual(header.line_type, "header")


@unittest.skipUnless(PYQT6_AVAILABLE, "PyQt6 is not available")
class TestDiffViewer(unittest.TestCase):
    """Test cases for the DiffViewer widget."""
    
    @classmethod
    def setUpClass(cls):
        """Set up PyQt application."""
        if PYQT6_AVAILABLE:
            cls.app = QApplication.instance() or QApplication([])
    
    def test_diff_computation(self):
        """Test diff computation."""
        viewer = DiffViewer()
        
        original = "line1\nline2\nline3\n"
        current = "line1\nmodified\nline3\n"
        
        viewer.set_content(current, original)
        
        added, removed, changed = viewer.get_diff_summary()
        
        self.assertGreater(len(viewer.diff_lines), 0)
        self.assertTrue(added > 0 or removed > 0)
    
    def test_get_diff_summary(self):
        """Test getting diff summary."""
        viewer = DiffViewer()
        
        original = "a\nb\nc\n"
        current = "a\nx\nc\n"
        
        viewer.set_content(current, original)
        
        added, removed, changed = viewer.get_diff_summary()
        
        self.assertIsInstance(added, int)
        self.assertIsInstance(removed, int)
        self.assertIsInstance(changed, int)
        self.assertEqual(changed, added + removed)
    
    def test_empty_diff(self):
        """Test diff with identical content."""
        viewer = DiffViewer()
        
        content = "line1\nline2\n"
        viewer.set_content(content, content)
        
        added, removed, changed = viewer.get_diff_summary()
        
        self.assertEqual(added, 0)
        self.assertEqual(removed, 0)
    
    def test_export_diff(self):
        """Test exporting diff to file."""
        import tempfile
        
        viewer = DiffViewer()
        
        original = "line1\nline2\n"
        current = "line1\nmodified\n"
        
        viewer.set_content(current, original)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            temp_path = f.name
        
        try:
            result = viewer.export_diff(temp_path)
            self.assertTrue(result)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertGreater(len(content), 0)
        finally:
            import os
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
