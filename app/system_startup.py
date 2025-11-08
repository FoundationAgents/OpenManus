"""
System Startup Script
Initializes all system components and starts the application
"""

import asyncio
import signal
import sys
from pathlib import Path

from app.logger import logger
from app.config import config
from app.system_integration.integration_service import system_integration
from app.ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


class SystemApplication:
    """Main application class that coordinates system startup and shutdown"""
    
    def __init__(self):
        self.qt_app = None
        self.main_window = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize_system(self):
        """Initialize all system components"""
        try:
            logger.info("Starting OpenManus System Integration...")
            
            # Initialize system integration service
            await system_integration.initialize()
            
            logger.info("System initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all system components"""
        try:
            logger.info("Shutting down OpenManus System...")
            
            # Shutdown system integration
            await system_integration.shutdown()
            
            logger.info("System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def setup_gui(self):
        """Setup the GUI application"""
        try:
            # Create Qt application
            self.qt_app = QApplication(sys.argv)
            self.qt_app.setApplicationName("OpenManus IDE")
            self.qt_app.setApplicationVersion("1.0.0")
            
            # Create main window
            self.main_window = MainWindow()
            self.main_window.show()
            
            logger.info("GUI setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup GUI: {e}")
            raise
    
    def run(self):
        """Run the application"""
        try:
            # Check if GUI is enabled
            if not config.ui.enable_gui:
                logger.info("GUI disabled, running in headless mode")
                # Run headless mode
                asyncio.run(self._run_headless())
            else:
                # Run with GUI
                self._run_with_gui()
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Application error: {e}")
            sys.exit(1)
    
    async def _run_headless(self):
        """Run in headless mode"""
        try:
            # Initialize system
            await self.initialize_system()
            
            # Keep running
            logger.info("System running in headless mode. Press Ctrl+C to stop.")
            
            # Simple event loop
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Headless mode error: {e}")
        finally:
            await self.shutdown()
    
    def _run_with_gui(self):
        """Run with GUI"""
        try:
            # Setup GUI first
            self.setup_gui()
            
            # Initialize system in background
            asyncio.create_task(self._initialize_system_async())
            
            # Run Qt event loop
            exit_code = self.qt_app.exec()
            
            # Cleanup
            asyncio.run(self.shutdown())
            
            sys.exit(exit_code)
            
        except Exception as e:
            logger.error(f"GUI mode error: {e}")
            sys.exit(1)
    
    async def _initialize_system_async(self):
        """Initialize system asynchronously for GUI mode"""
        try:
            await self.initialize_system()
        except Exception as e:
            logger.error(f"System initialization error: {e}")


def main():
    """Main entry point"""
    # Ensure data directories exist
    Path("./data").mkdir(exist_ok=True)
    Path("./workspace").mkdir(exist_ok=True)
    Path("./backups").mkdir(exist_ok=True)
    Path("./config").mkdir(exist_ok=True)
    
    # Create and run application
    app = SystemApplication()
    app.run()


if __name__ == "__main__":
    main()
