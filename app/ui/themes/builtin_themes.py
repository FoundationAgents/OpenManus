"""
Built-in themes for OpenManus IDE.
"""

from .theme_manager import Theme


class LightTheme(Theme):
    """Light theme (default)."""
    
    def __init__(self):
        super().__init__(
            name="light",
            display_name="Light",
            colors={
                "background": "#ffffff",
                "foreground": "#000000",
                "primary": "#0066cc",
                "secondary": "#6c757d",
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
                "border": "#dee2e6",
                "hover": "#f8f9fa",
                "selected": "#e9ecef"
            },
            fonts={
                "default": "Segoe UI, Arial, sans-serif",
                "mono": "Courier New, Consolas, monospace"
            },
            stylesheet="""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QDockWidget {
                    background-color: #f8f9fa;
                    color: #000000;
                    border: 1px solid #dee2e6;
                }
                QTextEdit, QPlainTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #dee2e6;
                    font-family: 'Courier New', monospace;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #dee2e6;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #0066cc;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0052a3;
                }
                QPushButton:pressed {
                    background-color: #003d7a;
                }
                QMenuBar {
                    background-color: #f8f9fa;
                    color: #000000;
                }
                QMenuBar::item:selected {
                    background-color: #e9ecef;
                }
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #dee2e6;
                }
                QMenu::item:selected {
                    background-color: #e9ecef;
                }
                QToolBar {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    spacing: 5px;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #dee2e6;
                    padding: 5px;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #000000;
                    gridline-color: #dee2e6;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    color: #000000;
                    padding: 5px;
                    border: 1px solid #dee2e6;
                }
                QTabWidget::pane {
                    border: 1px solid #dee2e6;
                }
                QTabBar::tab {
                    background-color: #f8f9fa;
                    color: #000000;
                    padding: 8px 16px;
                    border: 1px solid #dee2e6;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                }
                QStatusBar {
                    background-color: #f8f9fa;
                    color: #000000;
                }
            """
        )


class DarkTheme(Theme):
    """Dark theme."""
    
    def __init__(self):
        super().__init__(
            name="dark",
            display_name="Dark",
            colors={
                "background": "#1e1e1e",
                "foreground": "#d4d4d4",
                "primary": "#0e639c",
                "secondary": "#3e3e42",
                "success": "#4ec9b0",
                "warning": "#ce9178",
                "error": "#f48771",
                "border": "#3e3e42",
                "hover": "#2a2d2e",
                "selected": "#094771"
            },
            fonts={
                "default": "Segoe UI, Arial, sans-serif",
                "mono": "Courier New, Consolas, monospace"
            },
            stylesheet="""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                QDockWidget {
                    background-color: #252526;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                }
                QDockWidget::title {
                    background-color: #2d2d30;
                    padding: 5px;
                }
                QTextEdit, QPlainTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                    font-family: 'Courier New', monospace;
                }
                QLineEdit {
                    background-color: #3c3c3c;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #0e639c;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #094771;
                }
                QMenuBar {
                    background-color: #2d2d30;
                    color: #d4d4d4;
                }
                QMenuBar::item:selected {
                    background-color: #3e3e42;
                }
                QMenu {
                    background-color: #252526;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                }
                QMenu::item:selected {
                    background-color: #094771;
                }
                QToolBar {
                    background-color: #2d2d30;
                    border: 1px solid #3e3e42;
                    spacing: 5px;
                }
                QComboBox {
                    background-color: #3c3c3c;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                    padding: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #252526;
                    color: #d4d4d4;
                    selection-background-color: #094771;
                }
                QTableWidget {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    gridline-color: #3e3e42;
                }
                QHeaderView::section {
                    background-color: #2d2d30;
                    color: #d4d4d4;
                    padding: 5px;
                    border: 1px solid #3e3e42;
                }
                QTabWidget::pane {
                    border: 1px solid #3e3e42;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d30;
                    color: #d4d4d4;
                    padding: 8px 16px;
                    border: 1px solid #3e3e42;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                }
                QTabBar::tab:hover {
                    background-color: #3e3e42;
                }
                QStatusBar {
                    background-color: #007acc;
                    color: #ffffff;
                }
                QScrollBar:vertical {
                    background-color: #1e1e1e;
                    width: 12px;
                }
                QScrollBar::handle:vertical {
                    background-color: #424242;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #4e4e4e;
                }
                QScrollBar:horizontal {
                    background-color: #1e1e1e;
                    height: 12px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #424242;
                    border-radius: 6px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #4e4e4e;
                }
            """
        )


# Dictionary of built-in themes
BUILTIN_THEMES = {
    "light": LightTheme(),
    "dark": DarkTheme()
}


def register_builtin_themes(theme_manager):
    """
    Register all built-in themes with the theme manager.
    
    Args:
        theme_manager: ThemeManager instance
    """
    for theme in BUILTIN_THEMES.values():
        theme_manager.register_theme(theme)
