"""
FreEco.ai Platform - Performance Module
Enhanced OpenManus with performance optimization
"""

from .monitoring import MonitoringSystem, default_monitor
from .optimizer import PerformanceOptimizer, default_optimizer


__all__ = [
    "PerformanceOptimizer",
    "default_optimizer",
    "MonitoringSystem",
    "default_monitor",
]
