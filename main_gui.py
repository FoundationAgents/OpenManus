#!/usr/bin/env python3
"""
OpenManus GUI - Main Entry Point

GUI-first application entry point. Launches the IDE with progressive component loading.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication, QSplashScreen, QMainWindow
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QPixmap, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("ERROR: PyQt6 is not installed. GUI mode requires PyQt6.")
    print("Install with: pip install PyQt6")
    sys.exit(1)

from app.logger import logger
from app.config import config
from app.ui.main_window import MainWindow
from app.ui.message_bus import get_message_bus, EventTypes
from app.ui.state_manager import get_state_manager
from app.ui.component_discovery import get_component_discovery
from app.ui.progressive_loading import ProgressiveLoader, load_ui_progressively
from app.ui.error_dialogs import show_error


class OpenManusGUI:
    """
    Main OpenManus GUI Application.
    
    Features:
    - GUI-first architecture
    - Progressive component loading
    - Splash screen during startup
    - Component auto-discovery
    - Reactive state management
    """
    
    def __init__(self):
        """Initialize the GUI application."""
        self.app = None
        self.main_window = None
        self.splash = None
        self.message_bus = get_message_bus()
        self.state_manager = get_state_manager()
        
        logger.info("OpenManus GUI initialized")
    
    def create_splash_screen(self) -> QSplashScreen:
        """
        Create and show splash screen.
        
        Returns:
            QSplashScreen instance
        """
        # Create a simple splash screen
        splash_pix = QPixmap(600, 400)
        splash_pix.fill(Qt.GlobalColor.white)
        
        splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.setFont(QFont("Arial", 12))
        splash.showMessage(
            "OpenManus IDE\n\nInitializing...",
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.black
        )
        splash.show()
        
        return splash
    
    def setup_logging(self):
        """Configure logging for GUI mode."""
        # Ensure logs directory exists
        log_dir = Path.home() / ".openmanus" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure file handler
        log_file = log_dir / "gui.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        logger.info(f"Logging configured (file: {log_file})")
    
    def initialize_components(self):
        """Initialize core components."""
        try:
            # Discover available components
            discovery = get_component_discovery()
            components = discovery.discover_components()
            
            logger.info(f"Discovered {len(components)} components")
            
            available = discovery.get_available_components()
            unavailable = discovery.get_unavailable_components()
            
            if available:
                logger.info(f"Available components: {[c.name for c in available]}")
            
            if unavailable:
                logger.warning(f"Unavailable components: {[(c.name, c.error) for c in unavailable]}")
            
            # Publish app started event
            self.message_bus.publish(EventTypes.APP_STARTED, {
                "components": len(components),
                "available": len(available),
                "unavailable": len(unavailable)
            })
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}", exc_info=True)
            show_error(
                "Initialization Error",
                "Failed to initialize some components. The application may not function correctly.",
                details=str(e),
                suggestion="Check the log file for details and ensure all dependencies are installed."
            )
    
    def create_main_window(self) -> MainWindow:
        """
        Create the main window.
        
        Returns:
            MainWindow instance
        """
        try:
            window = MainWindow()
            
            # Subscribe to component events
            self.message_bus.on(EventTypes.COMPONENT_LOADED)(
                lambda msg: logger.info(f"Component loaded: {msg.data.get('name')}")
            )
            
            self.message_bus.on(EventTypes.COMPONENT_FAILED)(
                lambda msg: logger.error(
                    f"Component failed: {msg.data.get('name')} - {msg.data.get('error')}"
                )
            )
            
            return window
            
        except Exception as e:
            logger.error(f"Error creating main window: {e}", exc_info=True)
            show_error(
                "Startup Error",
                "Failed to create the main window.",
                details=str(e),
                suggestion="Try restarting the application. If the problem persists, check the log file."
            )
            sys.exit(1)
    
    def load_components_progressively(self, window: MainWindow):
        """
        Load UI components progressively.
        
        Args:
            window: Main window instance
        """
        try:
            # Create progressive loader
            loader = load_ui_progressively(window)
            
            # Connect signals
            def on_component_loaded(comp_name, comp_instance):
                logger.info(f"Component ready: {comp_name}")
                if self.splash:
                    self.splash.showMessage(
                        f"Loading {comp_name}...",
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                        Qt.GlobalColor.black
                    )
            
            def on_all_loaded():
                logger.info("All components loaded")
                if self.splash:
                    self.splash.finish(window)
                    self.splash = None
                
                # Show main window
                window.show()
                window.raise_()
                window.activateWindow()
            
            def on_progress(current, total, comp_name):
                if self.splash:
                    self.splash.showMessage(
                        f"Loading components... ({current}/{total})\n{comp_name}",
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                        Qt.GlobalColor.black
                    )
            
            loader.component_loaded.connect(on_component_loaded)
            loader.all_loaded.connect(on_all_loaded)
            loader.load_progress.connect(on_progress)
            
            # Start loading
            QTimer.singleShot(100, loader.start_loading)
            
        except Exception as e:
            logger.error(f"Error loading components: {e}", exc_info=True)
            if self.splash:
                self.splash.close()
            show_error(
                "Component Loading Error",
                "Failed to load UI components.",
                details=str(e),
                suggestion="Some features may not be available. Check the log file for details."
            )
            # Still show the window even if loading failed
            window.show()
    
    def run(self):
        """Run the GUI application."""
        try:
            # Setup logging
            self.setup_logging()
            
            logger.info("=" * 60)
            logger.info("OpenManus GUI Starting")
            logger.info("=" * 60)
            
            # Create Qt application
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("OpenManus IDE")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("OpenManus")
            
            # Show splash screen
            self.splash = self.create_splash_screen()
            self.app.processEvents()
            
            # Initialize components
            self.splash.showMessage(
                "Discovering components...",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.black
            )
            self.app.processEvents()
            
            self.initialize_components()
            
            # Create main window
            self.splash.showMessage(
                "Creating main window...",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.black
            )
            self.app.processEvents()
            
            self.main_window = self.create_main_window()
            
            # Load components progressively
            self.load_components_progressively(self.main_window)
            
            # Run event loop
            logger.info("Entering Qt event loop")
            exit_code = self.app.exec()
            
            logger.info(f"Application exited with code {exit_code}")
            return exit_code
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            return 0
            
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            show_error(
                "Fatal Error",
                "An unexpected error occurred.",
                details=str(e),
                suggestion="The application will now exit. Please check the log file for details."
            )
            return 1
        
        finally:
            # Cleanup
            logger.info("Application cleanup")
            self.message_bus.publish(EventTypes.APP_CLOSING, {})


def main():
    """Main entry point."""
    gui = OpenManusGUI()
    return gui.run()


if __name__ == "__main__":
    sys.exit(main())
