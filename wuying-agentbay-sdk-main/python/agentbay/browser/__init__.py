"""
Browser automation operations for the AgentBay SDK.
"""

from .browser import Browser, BrowserOption, BrowserViewport, BrowserScreen, BrowserFingerprint, BrowserProxy
from .browser_agent import BrowserAgent, ActOptions, ActResult, ObserveOptions, ObserveResult, ExtractOptions

__all__ = [
    "Browser",
    "BrowserOption",
    "BrowserViewport",
    "BrowserScreen",
    "BrowserFingerprint",
    "BrowserProxy",
    "BrowserAgent",
    "ActOptions",
    "ActResult",
    "ObserveOptions",
    "ObserveResult",
    "ExtractOptions",
] 