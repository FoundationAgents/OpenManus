"""
Browser automation engine with embedded and external browser support.

This module provides:
1. Embedded browser engine (PyQt6-WebEngine based)
2. External browser adapters (Chrome, Firefox, Edge via CDP/WebDriver)
3. Browser manager for orchestration
4. BrowserRAG helper for content understanding
"""

from app.browser.embedded_engine import EmbeddedBrowserEngine
from app.browser.external_adapter import ChromeAdapter, FirefoxAdapter, EdgeAdapter
from app.browser.manager import BrowserManager
from app.browser.rag_helper import BrowserRAGHelper

__all__ = [
    "EmbeddedBrowserEngine",
    "ChromeAdapter",
    "FirefoxAdapter",
    "EdgeAdapter",
    "BrowserManager",
    "BrowserRAGHelper",
]
