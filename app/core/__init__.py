"""
Core module for smart component auto-loading system.
"""

from app.core.component_registry import ComponentRegistry, ComponentMetadata
from app.core.resource_monitor import ResourceMonitor
from app.core.error_isolation import ErrorIsolation
from app.core.lazy_loader import LazyLoader
from app.core.parallel_loader import ParallelLoader
from app.core.startup_detection import StartupDetection
from app.core.smart_startup import SmartStartup

__all__ = [
    "ComponentRegistry",
    "ComponentMetadata",
    "ResourceMonitor",
    "ErrorIsolation",
    "LazyLoader",
    "ParallelLoader",
    "StartupDetection",
    "SmartStartup",
]
