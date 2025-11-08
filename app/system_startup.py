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
from app.reliability.crash_recovery import CrashRecoveryManager
from app.reliability.health_monitor import HealthMonitor
from app.reliability.event_logger import EventLogger
from app.reliability.db_optimization import DatabaseOptimizer
from PyQt6.QtWidgets import QApplication

# Smart startup system
from app.core.smart_startup import get_smart_startup
from app.profiling.startup_profiler import get_startup_profiler


class SystemApplication:
    """Main application class that coordinates system startup and shutdown"""
    
    def __init__(self):
        self.qt_app = None
        self.main_window = None
        self.crash_recovery_manager = None
        self.health_monitor = None
        self.event_logger = None
        self.db_optimizer = None
        self.smart_startup = get_smart_startup()
        self.startup_profiler = get_startup_profiler()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize_system(self):
        """Initialize all system components using smart startup"""
        try:
            logger.info("Starting OpenManus System with Smart Startup...")
            
            # Start profiling
            self.startup_profiler.start_profiling()
            
            # Execute smart startup
            report = await self.smart_startup.startup_async(
                on_progress=self._log_startup_progress
            )
            
            # Initialize reliability components
            await self._initialize_reliability()
            
            # Initialize system integration service
            # Create and save performance profile
            profile = self.startup_profiler.create_profile(report.total_duration_ms)
            logger.info("\n" + self.startup_profiler.format_profile(profile))
            
            # Save profile to disk
            try:
                self.startup_profiler.save_profile(profile)
            except Exception as e:
                logger.warning(f"Failed to save startup profile: {e}")
            
            # Initialize system integration service (if not already loaded)
            await system_integration.initialize()
            
            logger.info("System initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def _initialize_reliability(self):
        """Initialize reliability and monitoring components"""
        try:
            db_path = str(Path("./data/reliability.db"))
            
            # Initialize database optimizer
            self.db_optimizer = DatabaseOptimizer(db_path)
            self.db_optimizer.optimize_for_reliability()
            logger.info("Database optimizer initialized")
            
            # Initialize crash recovery
            self.crash_recovery_manager = CrashRecoveryManager(db_path)
            await self.crash_recovery_manager.start()
            logger.info("Crash recovery manager started")
            
            # Initialize health monitor
            self.health_monitor = HealthMonitor(db_path)
            logger.info("Health monitor initialized")
            
            # Initialize event logger
            self.event_logger = EventLogger(db_path)
            logger.info("Event logger initialized")
            
            # Log system startup
            await self.event_logger.log_event(
                level="INFO",
                component="system",
                event_type="startup",
                message="System started successfully",
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize reliability components: {e}")
    def _log_startup_progress(self, phase: str, progress: float):
        """Log startup progress."""
        if progress >= 0:
            logger.debug(f"Startup: {phase} - {progress:.0f}%")
    
    async def shutdown(self):
        """Shutdown all system components"""
        try:
            logger.info("Shutting down OpenManus System...")
            
            # Log shutdown event
            if self.event_logger:
                await self.event_logger.log_event(
                    level="INFO",
                    component="system",
                    event_type="shutdown",
                    message="System shutting down",
                )
            
            # Shutdown crash recovery manager
            if self.crash_recovery_manager:
                await self.crash_recovery_manager.stop()
            
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
    Path("./data/profiles").mkdir(exist_ok=True)
    Path("./workspace").mkdir(exist_ok=True)
    Path("./backups").mkdir(exist_ok=True)
    Path("./config").mkdir(exist_ok=True)
    
    # Create and run application
    app = SystemApplication()
    app.run()


if __name__ == "__main__":
    main()
