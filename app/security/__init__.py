"""
FreEco.ai Platform - Security Module
Enhanced OpenManus with military-grade security
"""

from .anti_hacking import AntiHackingSystem, default_anti_hacking
from .security_manager import SecurityManager, default_security


__all__ = [
    "SecurityManager",
    "default_security",
    "AntiHackingSystem",
    "default_anti_hacking",
]
