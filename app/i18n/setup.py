"""
Setup module for initializing internationalization based on configuration.

This module provides functions to initialize the i18n system with the
language settings from the application configuration.
"""

from loguru import logger
from .i18n import set_language, get_current_language


def initialize_i18n_from_config(config):
    """
    Initialize internationalization system from application configuration.
    
    Args:
        config: Application configuration object with language_config property
    """
    try:
        if hasattr(config, 'language_config') and config.language_config:
            locale = config.language_config.locale
            if locale:
                success = set_language(locale)
                if success:
                    logger.info(f"Language initialized to: {locale}")
                else:
                    logger.warning(f"Failed to set language to: {locale}")
            else:
                logger.info("No language locale specified, using default (en)")
        else:
            logger.info("No language configuration found, using default (en)")
    except Exception as e:
        logger.error(f"Error initializing i18n from config: {e}")
        logger.info("Using default language (en)")


def get_configured_language(config) -> str:
    """
    Get the configured language from the application configuration.
    
    Args:
        config: Application configuration object
        
    Returns:
        Language code string, defaults to 'en' if not configured
    """
    try:
        if hasattr(config, 'language_config') and config.language_config:
            return config.language_config.locale or "en"
        return "en"
    except Exception:
        return "en"
