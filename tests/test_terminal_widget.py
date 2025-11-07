"""Unit tests for the TerminalWidget module."""

import asyncio
import unittest

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.ui.editor.terminal_widget import TerminalWidget, TerminalOutputWidget


@unittest.skipUnless(PYQT6_AVAILABLE, "PyQt6 is not available")
class TestTerminalOutputWidget(unittest.TestCase):
    """Test cases for the TerminalOutputWidget."""
    
    @classmethod
    def setUpClass(cls):
        """Set up PyQt application."""
        if PYQT6_AVAILABLE:
            cls.app = QApplication.instance() or QApplication([])
    
    def test_create_output_widget(self):
        """Test creating a terminal output widget."""
        widget = TerminalOutputWidget()
        
        self.assertIsNotNone(widget)
        self.assertTrue(widget.isReadOnly())
    
    def test_append_stdout(self):
        """Test appending stdout text."""
        widget = TerminalOutputWidget()
        
        widget.append_stdout("Hello, stdout!")
        
        content = widget.toPlainText()
        self.assertIn("Hello, stdout!", content)
    
    def test_append_stderr(self):
        """Test appending stderr text."""
        widget = TerminalOutputWidget()
        
        widget.append_stderr("Error message")
        
        content = widget.toPlainText()
        self.assertIn("Error message", content)
    
    def test_append_info(self):
        """Test appending info text."""
        widget = TerminalOutputWidget()
        
        widget.append_info("Info message")
        
        content = widget.toPlainText()
        self.assertIn("Info message", content)
    
    def test_clear_output(self):
        """Test clearing output."""
        widget = TerminalOutputWidget()
        
        widget.append_stdout("Text 1")
        widget.append_stdout("Text 2")
        
        self.assertGreater(len(widget.toPlainText()), 0)
        
        widget.clear_output()
        
        self.assertEqual(len(widget.toPlainText()), 0)


@unittest.skipUnless(PYQT6_AVAILABLE, "PyQt6 is not available")
class TestTerminalWidget(unittest.TestCase):
    """Test cases for the TerminalWidget."""
    
    @classmethod
    def setUpClass(cls):
        """Set up PyQt application."""
        if PYQT6_AVAILABLE:
            cls.app = QApplication.instance() or QApplication([])
    
    def test_create_terminal_widget(self):
        """Test creating a terminal widget."""
        widget = TerminalWidget()
        
        self.assertIsNotNone(widget)
        self.assertIsNotNone(widget.command_input)
        self.assertIsNotNone(widget.output_display)
    
    def test_set_workspace_dir(self):
        """Test setting workspace directory."""
        import tempfile
        
        widget = TerminalWidget()
        temp_dir = tempfile.mkdtemp()
        
        widget.set_workspace_dir(temp_dir)
        
        self.assertEqual(str(widget.workspace_dir), temp_dir)
    
    def test_execute_button_state(self):
        """Test execute button state."""
        widget = TerminalWidget()
        
        self.assertTrue(widget.execute_button.isEnabled())
        self.assertFalse(widget.kill_button.isEnabled())
    
    def test_command_input(self):
        """Test command input field."""
        widget = TerminalWidget()
        
        widget.command_input.setText("echo test")
        
        self.assertEqual(widget.command_input.text(), "echo test")
    
    def test_clear_output_button(self):
        """Test clear output button functionality."""
        widget = TerminalWidget()
        
        widget.output_display.append_stdout("test output")
        self.assertGreater(len(widget.output_display.toPlainText()), 0)
        
        widget._on_clear_output()
        
        self.assertEqual(len(widget.output_display.toPlainText()), 0)


if __name__ == '__main__':
    unittest.main()
