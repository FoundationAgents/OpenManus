"""
Core internationalization functionality for OpenManus.

This module provides the main I18n class and utility functions for handling
text translations across different languages.
"""

import json
import threading
from pathlib import Path
from typing import Dict, Optional, Any
from loguru import logger


class I18n:
    """
    Internationalization class for managing translations.

    This class handles loading language files, switching languages,
    and providing translated text based on the current locale.
    """

    _instance: Optional['I18n'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'I18n':
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the I18n instance."""
        if not hasattr(self, '_initialized'):
            self._current_language = "en"
            self._translations: Dict[str, Dict[str, Any]] = {}
            self._supported_languages = ["en", "zh_cn", "zh_tw", "fr", "de", "ru"]
            self._load_all_translations()
            self._initialized = True

    def _get_translations_dir(self) -> Path:
        """Get the translations directory path."""
        return Path(__file__).parent / "translations"

    def _load_translation_file(self, language: str) -> Dict[str, Any]:
        """
        Load translation file for a specific language.

        Args:
            language: Language code (e.g., 'en', 'zh_cn', 'zh_tw')

        Returns:
            Dictionary containing translations for the language
        """
        translations_dir = self._get_translations_dir()
        file_path = translations_dir / f"{language}.json"

        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Translation file not found: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
            return {}

    def _load_all_translations(self):
        """Load all translation files."""
        for language in self._supported_languages:
            self._translations[language] = self._load_translation_file(language)
            logger.debug(f"Loaded translations for language: {language}")

    def set_language(self, language: str) -> bool:
        """
        Set the current language.

        Args:
            language: Language code to set

        Returns:
            True if language was set successfully, False otherwise
        """
        if language not in self._supported_languages:
            logger.warning(f"Unsupported language: {language}. Using default 'en'.")
            language = "en"

        self._current_language = language
        logger.info(f"Language set to: {language}")
        return True

    def get_current_language(self) -> str:
        """Get the current language code."""
        return self._current_language

    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return self._supported_languages.copy()

    def get_text(self, key: str, **kwargs) -> str:
        """
        Get translated text for the given key.

        Args:
            key: Translation key (supports dot notation for nested keys)
            **kwargs: Variables to substitute in the translated text

        Returns:
            Translated text, or the key itself if translation not found
        """
        # Get translation for current language
        translation = self._get_nested_value(
            self._translations.get(self._current_language, {}), key
        )

        # Fallback to English if translation not found
        if translation is None and self._current_language != "en":
            translation = self._get_nested_value(
                self._translations.get("en", {}), key
            )

        # If still not found, return the key itself
        if translation is None:
            logger.warning(f"Translation not found for key: {key}")
            return key

        # Substitute variables if provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error formatting translation for key '{key}': {e}")
                return translation

        return translation

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search in
            key: Key with dot notation (e.g., 'messages.startup')

        Returns:
            Value if found, None otherwise
        """
        keys = key.split('.')
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current if isinstance(current, str) else None

    def reload_translations(self):
        """Reload all translation files."""
        self._load_all_translations()
        logger.info("Translations reloaded")


# Global instance
_i18n_instance = I18n()


def get_text(key: str, **kwargs) -> str:
    """
    Get translated text for the given key.

    Args:
        key: Translation key
        **kwargs: Variables to substitute in the translated text

    Returns:
        Translated text
    """
    return _i18n_instance.get_text(key, **kwargs)


def set_language(language: str) -> bool:
    """
    Set the current language.

    Args:
        language: Language code to set

    Returns:
        True if successful
    """
    return _i18n_instance.set_language(language)


def get_current_language() -> str:
    """Get the current language code."""
    return _i18n_instance.get_current_language()


def get_supported_languages() -> list:
    """Get list of supported language codes."""
    return _i18n_instance.get_supported_languages()
