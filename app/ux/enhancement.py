"""
FreEco.ai Platform - UX Enhancement
Enhanced OpenManus with improved user experience

This module provides comprehensive UX improvements:
- User-friendly logging with rich formatting
- Real-time progress tracking
- Colored output and tables
- Notifications (desktop, email)
- Context-sensitive help
- Internationalization support

Part of Enhancement #5: Performance, UX & Evaluation
"""

import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for user-friendly messages"""

    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Notification channels"""

    CONSOLE = "console"
    DESKTOP = "desktop"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class ProgressBar:
    """Progress bar state"""

    total: int
    current: int = 0
    description: str = ""
    start_time: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

    def update(self, increment: int = 1):
        """Update progress"""
        self.current = min(self.current + increment, self.total)

    def get_percentage(self) -> float:
        """Get completion percentage"""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100

    def get_eta(self) -> Optional[float]:
        """Get estimated time remaining in seconds"""
        if self.current == 0:
            return None

        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed
        remaining = self.total - self.current

        if rate == 0:
            return None

        return remaining / rate

    def is_complete(self) -> bool:
        """Check if progress is complete"""
        return self.current >= self.total


class UXEnhancement:
    """
    User experience enhancement system

    Features:
    - Rich console output with colors
    - Progress bars with ETA
    - Formatted tables
    - Desktop notifications
    - Email notifications
    - Context-sensitive help
    - Multi-language support

    Example:
        ux = UXEnhancement()

        # User-friendly logging
        ux.log_user_friendly("Processing started", LogLevel.INFO)

        # Progress tracking
        progress = ux.create_progress_bar(total=100, description="Processing")
        for i in range(100):
            process_item(i)
            ux.update_progress(progress)

        # Rich formatting
        data = {"name": "Alice", "age": 30}
        ux.print_table([data])

        # Notifications
        ux.send_notification("Task complete!", NotificationChannel.DESKTOP)
    """

    def __init__(self, enable_colors: bool = True, language: str = "en"):
        """
        Initialize UX enhancement system

        Args:
            enable_colors: Enable colored output
            language: Language code (en, es, fr, etc.)
        """
        self.enable_colors = enable_colors and self._supports_color()
        self.language = language
        self.progress_bars: Dict[str, ProgressBar] = {}
        self.translations: Dict[str, Dict[str, str]] = self._load_translations()

        # ANSI color codes
        self.colors = {
            "reset": "\033[0m",
            "bold": "\033[1m",
            "dim": "\033[2m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",
        }

    def log_user_friendly(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a user-friendly message

        Args:
            message: Message to log
            level: Log level
            details: Optional details dictionary
        """
        # Translate message if needed
        translated_message = self.translate(message)

        # Format with color
        formatted_message = self._format_log_message(translated_message, level)

        # Print to console
        print(formatted_message)

        # Log to standard logger
        if level == LogLevel.DEBUG:
            logger.debug(message)
        elif level == LogLevel.INFO:
            logger.info(message)
        elif level == LogLevel.SUCCESS:
            logger.info(f"✓ {message}")
        elif level == LogLevel.WARNING:
            logger.warning(message)
        elif level == LogLevel.ERROR:
            logger.error(message)
        elif level == LogLevel.CRITICAL:
            logger.critical(message)

        # Print details if provided
        if details:
            self._print_details(details)

    def create_progress_bar(
        self,
        total: int,
        description: str = "",
        bar_id: Optional[str] = None,
    ) -> str:
        """
        Create a progress bar

        Args:
            total: Total number of items
            description: Description of the task
            bar_id: Optional unique ID (generated if not provided)

        Returns:
            Progress bar ID
        """
        if bar_id is None:
            bar_id = f"progress_{len(self.progress_bars)}"

        self.progress_bars[bar_id] = ProgressBar(
            total=total,
            description=description,
        )

        return bar_id

    def update_progress(
        self,
        bar_id: str,
        increment: int = 1,
        message: Optional[str] = None,
    ):
        """
        Update progress bar

        Args:
            bar_id: Progress bar ID
            increment: Amount to increment
            message: Optional status message
        """
        if bar_id not in self.progress_bars:
            logger.warning(f"Progress bar not found: {bar_id}")
            return

        progress = self.progress_bars[bar_id]
        progress.update(increment)

        # Render progress bar
        self._render_progress_bar(progress, message)

    def _render_progress_bar(
        self,
        progress: ProgressBar,
        message: Optional[str] = None,
    ):
        """Render progress bar to console"""
        percentage = progress.get_percentage()
        bar_length = 40
        filled_length = int(bar_length * progress.current // progress.total)

        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        # Build status line
        status = f"\r{progress.description}: |{bar}| {percentage:.1f}% "
        status += f"({progress.current}/{progress.total})"

        # Add ETA if available
        eta = progress.get_eta()
        if eta is not None:
            status += f" ETA: {eta:.0f}s"

        # Add message if provided
        if message:
            status += f" - {message}"

        # Color the output
        if self.enable_colors:
            if progress.is_complete():
                status = self._colorize(status, "green")
            else:
                status = self._colorize(status, "cyan")

        # Print (overwrite previous line)
        print(status, end="", flush=True)

        # New line if complete
        if progress.is_complete():
            print()

    def print_table(
        self,
        data: List[Dict[str, Any]],
        headers: Optional[List[str]] = None,
        title: Optional[str] = None,
    ):
        """
        Print formatted table

        Args:
            data: List of dictionaries with data
            headers: Optional list of headers (uses dict keys if not provided)
            title: Optional table title
        """
        if not data:
            print("(empty table)")
            return

        # Get headers
        if headers is None:
            headers = list(data[0].keys())

        # Calculate column widths
        col_widths = {h: len(str(h)) for h in headers}
        for row in data:
            for header in headers:
                value = str(row.get(header, ""))
                col_widths[header] = max(col_widths[header], len(value))

        # Print title if provided
        if title:
            print(f"\n{self._colorize(title, 'bold')}")

        # Print header
        header_row = " | ".join(str(h).ljust(col_widths[h]) for h in headers)
        if self.enable_colors:
            header_row = self._colorize(header_row, "bold")
        print(header_row)

        # Print separator
        separator = "-+-".join("-" * col_widths[h] for h in headers)
        print(separator)

        # Print rows
        for row in data:
            row_str = " | ".join(
                str(row.get(h, "")).ljust(col_widths[h]) for h in headers
            )
            print(row_str)

        print()  # Empty line after table

    def send_notification(
        self,
        message: str,
        channel: NotificationChannel = NotificationChannel.CONSOLE,
        title: Optional[str] = None,
    ):
        """
        Send notification

        Args:
            message: Notification message
            channel: Notification channel
            title: Optional notification title
        """
        if channel == NotificationChannel.CONSOLE:
            self._send_console_notification(message, title)

        elif channel == NotificationChannel.DESKTOP:
            self._send_desktop_notification(message, title)

        elif channel == NotificationChannel.EMAIL:
            self._send_email_notification(message, title)

        elif channel == NotificationChannel.WEBHOOK:
            self._send_webhook_notification(message, title)

    def _send_console_notification(self, message: str, title: Optional[str]):
        """Send console notification"""
        if title:
            print(f"\n{self._colorize('🔔 ' + title, 'bold')}")
        print(f"{self._colorize(message, 'cyan')}\n")

    def _send_desktop_notification(self, message: str, title: Optional[str]):
        """Send desktop notification (platform-specific)"""
        try:
            import platform

            system = platform.system()

            if system == "Darwin":  # macOS
                import subprocess

                title = title or "FreEco.ai"
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display notification "{message}" with title "{title}"',
                    ]
                )

            elif system == "Linux":
                import subprocess

                title = title or "FreEco.ai"
                subprocess.run(["notify-send", title, message])

            elif system == "Windows":
                from win10toast import ToastNotifier

                toaster = ToastNotifier()
                toaster.show_toast(title or "FreEco.ai", message, duration=5)

            logger.info(f"Desktop notification sent: {message}")

        except Exception as e:
            logger.warning(f"Failed to send desktop notification: {e}")
            # Fallback to console
            self._send_console_notification(message, title)

    def _send_email_notification(self, message: str, title: Optional[str]):
        """Send email notification"""
        # Placeholder - would integrate with email service
        logger.info(f"Email notification: {title or 'Notification'} - {message}")

    def _send_webhook_notification(self, message: str, title: Optional[str]):
        """Send webhook notification"""
        # Placeholder - would integrate with webhook service
        logger.info(f"Webhook notification: {title or 'Notification'} - {message}")

    def get_help(self, context: str) -> str:
        """
        Get context-sensitive help

        Args:
            context: Context identifier

        Returns:
            Help text
        """
        help_texts = {
            "planning": "FreEco.ai uses advanced planning strategies to break down complex tasks.",
            "retry": "Automatic retry with exponential backoff is enabled for transient failures.",
            "cache": "Results are cached to improve performance. Use clear_cache() to invalidate.",
            "error": "Errors are automatically recovered when possible. Check logs for details.",
        }

        return help_texts.get(context, "No help available for this context.")

    def translate(self, text: str) -> str:
        """
        Translate text to current language

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        if self.language == "en":
            return text

        if self.language in self.translations:
            return self.translations[self.language].get(text, text)

        return text

    def _format_log_message(self, message: str, level: LogLevel) -> str:
        """Format log message with color and icon"""
        icons = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️ ",
            LogLevel.SUCCESS: "✅",
            LogLevel.WARNING: "⚠️ ",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🚨",
        }

        colors = {
            LogLevel.DEBUG: "dim",
            LogLevel.INFO: "blue",
            LogLevel.SUCCESS: "green",
            LogLevel.WARNING: "yellow",
            LogLevel.ERROR: "red",
            LogLevel.CRITICAL: "red",
        }

        icon = icons.get(level, "")
        color = colors.get(level, "white")

        formatted = f"{icon} {message}"

        if self.enable_colors:
            formatted = self._colorize(formatted, color)

        return formatted

    def _print_details(self, details: Dict[str, Any]):
        """Print details dictionary"""
        print(self._colorize("Details:", "bold"))
        for key, value in details.items():
            print(f"  {key}: {value}")

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        if not self.enable_colors:
            return text

        color_code = self.colors.get(color, self.colors["reset"])
        reset_code = self.colors["reset"]

        return f"{color_code}{text}{reset_code}"

    def _supports_color(self) -> bool:
        """Check if terminal supports color"""
        # Check if stdout is a terminal
        if not hasattr(sys.stdout, "isatty"):
            return False

        if not sys.stdout.isatty():
            return False

        # Check for color support
        import os

        if os.getenv("TERM") == "dumb":
            return False

        return True

    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation dictionaries"""
        return {
            "es": {  # Spanish
                "Processing started": "Procesamiento iniciado",
                "Task complete": "Tarea completada",
                "Error occurred": "Ocurrió un error",
            },
            "fr": {  # French
                "Processing started": "Traitement commencé",
                "Task complete": "Tâche terminée",
                "Error occurred": "Une erreur s'est produite",
            },
            "de": {  # German
                "Processing started": "Verarbeitung gestartet",
                "Task complete": "Aufgabe abgeschlossen",
                "Error occurred": "Fehler aufgetreten",
            },
        }


# Global UX enhancement instance
default_ux = UXEnhancement()
