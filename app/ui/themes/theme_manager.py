"""
Theme Manager - Manages application themes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Theme:
    """Application theme definition."""
    name: str
    display_name: str
    colors: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    stylesheet: str = ""
    
    def to_dict(self) -> dict:
        """Convert theme to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "colors": self.colors,
            "fonts": self.fonts,
            "stylesheet": self.stylesheet
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        """Create theme from dictionary."""
        return cls(
            name=data["name"],
            display_name=data["display_name"],
            colors=data.get("colors", {}),
            fonts=data.get("fonts", {}),
            stylesheet=data.get("stylesheet", "")
        )


class ThemeManager:
    """
    Manages application themes.
    
    Features:
    - Built-in themes (Light, Dark)
    - Custom user themes
    - Theme persistence
    - Hot-reloading
    """
    
    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Optional[Theme] = None
        self.themes_dir = Path.home() / ".openmanus" / "themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Theme manager initialized")
    
    def register_theme(self, theme: Theme) -> None:
        """
        Register a theme.
        
        Args:
            theme: Theme to register
        """
        self.themes[theme.name] = theme
        logger.debug(f"Registered theme: {theme.name}")
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """
        Get a theme by name.
        
        Args:
            name: Theme name
            
        Returns:
            Theme or None if not found
        """
        return self.themes.get(name)
    
    def get_all_themes(self) -> list[Theme]:
        """
        Get all available themes.
        
        Returns:
            List of themes
        """
        return list(self.themes.values())
    
    def set_current_theme(self, name: str) -> bool:
        """
        Set the current theme.
        
        Args:
            name: Theme name
            
        Returns:
            True if successful
        """
        theme = self.get_theme(name)
        if theme:
            self.current_theme = theme
            logger.info(f"Current theme set to: {name}")
            return True
        
        logger.warning(f"Theme not found: {name}")
        return False
    
    def get_current_theme(self) -> Optional[Theme]:
        """Get the current theme."""
        return self.current_theme
    
    def save_theme(self, theme: Theme, file_path: Optional[Path] = None) -> None:
        """
        Save a theme to file.
        
        Args:
            theme: Theme to save
            file_path: Optional custom file path
        """
        if file_path is None:
            file_path = self.themes_dir / f"{theme.name}.json"
        
        with open(file_path, 'w') as f:
            json.dump(theme.to_dict(), f, indent=2)
        
        logger.info(f"Theme saved: {theme.name} to {file_path}")
    
    def load_theme(self, file_path: Path) -> Theme:
        """
        Load a theme from file.
        
        Args:
            file_path: Path to theme file
            
        Returns:
            Loaded theme
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        theme = Theme.from_dict(data)
        self.register_theme(theme)
        
        logger.info(f"Theme loaded: {theme.name}")
        return theme
    
    def load_all_themes(self) -> None:
        """Load all themes from themes directory."""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                self.load_theme(theme_file)
            except Exception as e:
                logger.error(f"Error loading theme {theme_file}: {e}")


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """
    Get the global theme manager (singleton).
    
    Returns:
        Global ThemeManager instance
    """
    global _theme_manager
    
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    
    return _theme_manager
