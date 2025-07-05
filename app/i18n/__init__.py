"""
Internationalization (i18n) module for OpenManus.

This module provides internationalization support for the OpenManus project,
allowing the application to display text in multiple languages.

Supported languages:
- en: English (default)
- zh_cn: Simplified Chinese
- zh_tw: Traditional Chinese
"""

from .i18n import I18n, get_text, set_language, get_current_language
from .setup import initialize_i18n_from_config, get_configured_language

# Convenience aliases for common translation keys
def t(key: str, **kwargs) -> str:
    """Shorthand for get_text()"""
    return get_text(key, **kwargs)

def msg(key: str, **kwargs) -> str:
    """Get message text"""
    return get_text(f"messages.{key}", **kwargs)

def err(key: str, **kwargs) -> str:
    """Get error text"""
    return get_text(f"errors.{key}", **kwargs)

def tool_text(tool: str, key: str, **kwargs) -> str:
    """Get tool-specific text"""
    return get_text(f"tools.{tool}.{key}", **kwargs)

def agent_text(agent: str, key: str, **kwargs) -> str:
    """Get agent-specific text"""
    return get_text(f"agents.{agent}.{key}", **kwargs)

def status_text(key: str, **kwargs) -> str:
    """Get status text"""
    return get_text(f"status.{key}", **kwargs)

def config_text(key: str, **kwargs) -> str:
    """Get config text"""
    return get_text(f"config.{key}", **kwargs)

def log_text(category: str, key: str, **kwargs) -> str:
    """Get log text"""
    return get_text(f"logs.{category}.{key}", **kwargs)

def log_agent(key: str, **kwargs) -> str:
    """Get agent log text"""
    return get_text(f"logs.agent.{key}", **kwargs)

def log_error(key: str, **kwargs) -> str:
    """Get error log text"""
    return get_text(f"logs.errors.{key}", **kwargs)

def log_token(key: str, **kwargs) -> str:
    """Get token log text"""
    return get_text(f"logs.tokens.{key}", **kwargs)

def log_tool(key: str, **kwargs) -> str:
    """Get tool log text"""
    return get_text(f"logs.tools.{key}", **kwargs)

def log_flow(key: str, **kwargs) -> str:
    """Get flow log text"""
    return get_text(f"logs.flow.{key}", **kwargs)

__all__ = [
    "I18n", "get_text", "set_language", "get_current_language",
    "initialize_i18n_from_config", "get_configured_language",
    "t", "msg", "err", "tool_text", "agent_text", "status_text", "config_text",
    "log_text", "log_agent", "log_error", "log_token", "log_tool", "log_flow"
]
