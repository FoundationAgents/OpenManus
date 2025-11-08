"""
Theme Engine for iXlinx Agent IDE.

Provides built-in and custom themes for the application.
"""

from .theme_manager import ThemeManager, Theme, get_theme_manager
from .builtin_themes import LightTheme, DarkTheme, BUILTIN_THEMES

__all__ = [
    "ThemeManager",
    "Theme",
    "get_theme_manager",
    "LightTheme",
    "DarkTheme",
    "BUILTIN_THEMES"
]
