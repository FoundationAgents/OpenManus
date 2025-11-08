"""
Modern search backends for web search with HTTP/2 support.

This module provides modern search engine implementations using HTTP/2,
structured results parsing, and connection pooling.
"""

from .base import ModernSearchBackend, StructuredSearchResult
from .serpapi_backend import SerpApiBackend
from .brave_backend import BraveSearchBackend
from .duckduckgo_backend import DuckDuckGoBackend
from .google_backend import GoogleCustomSearchBackend

__all__ = [
    "ModernSearchBackend",
    "StructuredSearchResult", 
    "SerpApiBackend",
    "BraveSearchBackend",
    "DuckDuckGoBackend",
    "GoogleCustomSearchBackend",
]