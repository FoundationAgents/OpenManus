"""
PyQt6 GUI interface for the iXlinx Agent framework.
Provides a modern IDE-style interface with multi-pane layout.
"""

import sys

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from app.logger import logger


def run_gui():
    """Run the PyQt6 GUI application using the new IDE layout."""
    if not PYQT6_AVAILABLE:
        logger.error("PyQt6 is not installed. GUI mode is not available.")
        logger.info("To install PyQt6, run: pip install PyQt6")
        return
    
    # Import the new UI main window
    from app.ui.main_window import MainWindow
    
    app = QApplication(sys.argv)
    app.setApplicationName("iXlinx Agent IDE")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
