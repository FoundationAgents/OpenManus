"""Settings Management Module

Handles FreEco.AI configuration including Minimax M2 API settings.
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class MinimaxConfig:
    """Minimax M2 Pro configuration."""

    api_key: str
    model: str = "minimax-01"
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: str = "https://api.minimax.io/v1"

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ThemeConfig:
    """Theme configuration."""

    mode: str = "dark"  # dark or light
    primary_color: str = "#000000"  # Black for dark mode
    secondary_color: str = "#FFFFFF"  # White for light mode
    accent_color: str = "#10B981"  # Green accent

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(**data)


@dataclass
class FreEcoSettings:
    """FreEco.AI settings."""

    minimax: MinimaxConfig
    theme: ThemeConfig
    auto_save: bool = True
    debug_mode: bool = False

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "minimax": self.minimax.to_dict(),
            "theme": self.theme.to_dict(),
            "auto_save": self.auto_save,
            "debug_mode": self.debug_mode,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(
            minimax=MinimaxConfig.from_dict(data.get("minimax", {})),
            theme=ThemeConfig.from_dict(data.get("theme", {})),
            auto_save=data.get("auto_save", True),
            debug_mode=data.get("debug_mode", False),
        )


class SettingsManager:
    """Manages FreEco.AI settings."""

    def __init__(self, storage_path: str = ".freeco/settings.json"):
        """Initialize settings manager.

        Args:
            storage_path: Path to store settings JSON file.
        """
        self.storage_path = storage_path
        self.settings: FreEcoSettings = FreEcoSettings(
            minimax=MinimaxConfig(api_key=""),
            theme=ThemeConfig(),
        )
        self._ensure_storage()
        self._load_settings()

    def _ensure_storage(self):
        """Ensure storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_settings(self):
        """Load settings from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.settings = FreEcoSettings.from_dict(data)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def _save_settings(self):
        """Save settings to storage."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_settings(self) -> FreEcoSettings:
        """Get current settings.

        Returns:
            FreEcoSettings object.
        """
        return self.settings

    def update_minimax_config(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> MinimaxConfig:
        """Update Minimax M2 configuration.

        Args:
            api_key: Minimax API key.
            model: Model name (minimax-01 or minimax-01-vision).
            temperature: Temperature (0.0-1.0).
            max_tokens: Maximum tokens (1-200000).

        Returns:
            Updated MinimaxConfig.
        """
        if api_key:
            self.settings.minimax.api_key = api_key
        if model:
            self.settings.minimax.model = model
        if temperature is not None:
            self.settings.minimax.temperature = max(0.0, min(1.0, temperature))
        if max_tokens:
            self.settings.minimax.max_tokens = max(1, min(200000, max_tokens))

        self._save_settings()
        return self.settings.minimax

    def update_theme_config(
        self,
        mode: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        accent_color: Optional[str] = None,
    ) -> ThemeConfig:
        """Update theme configuration.

        Args:
            mode: Theme mode (dark or light).
            primary_color: Primary color hex code.
            secondary_color: Secondary color hex code.
            accent_color: Accent color hex code.

        Returns:
            Updated ThemeConfig.
        """
        if mode and mode in ["dark", "light"]:
            self.settings.theme.mode = mode
        if primary_color:
            self.settings.theme.primary_color = primary_color
        if secondary_color:
            self.settings.theme.secondary_color = secondary_color
        if accent_color:
            self.settings.theme.accent_color = accent_color

        self._save_settings()
        return self.settings.theme

    def set_auto_save(self, enabled: bool):
        """Enable or disable auto-save.

        Args:
            enabled: Whether auto-save is enabled.
        """
        self.settings.auto_save = enabled
        self._save_settings()

    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode.

        Args:
            enabled: Whether debug mode is enabled.
        """
        self.settings.debug_mode = enabled
        self._save_settings()

    def validate_minimax_config(self) -> bool:
        """Validate Minimax configuration.

        Returns:
            True if valid, False otherwise.
        """
        return bool(self.settings.minimax.api_key)

    def get_minimax_headers(self) -> dict:
        """Get headers for Minimax API requests.

        Returns:
            Dictionary with authorization headers.
        """
        return {
            "Authorization": f"Bearer {self.settings.minimax.api_key}",
            "Content-Type": "application/json",
        }
