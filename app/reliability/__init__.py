"""
Production Hardening & Reliability Module

Provides crash recovery, auto-restart, health monitoring, graceful degradation,
data integrity, event logging, update management, and watchdog services
for production deployment.
"""

from .crash_recovery import CrashRecoveryManager, CheckpointManager
from .auto_restart import AutoRestartService, ServiceManager
from .health_monitor import HealthMonitor, HealthStatus
from .degradation import GracefulDegradationManager
from .data_integrity import DataIntegrityManager
from .event_logger import EventLogger, DiagnosticsBundle
from .db_optimization import DatabaseOptimizer
from .watchdog import WatchdogService

__all__ = [
    "CrashRecoveryManager",
    "CheckpointManager",
    "AutoRestartService",
    "ServiceManager",
    "HealthMonitor",
    "HealthStatus",
    "GracefulDegradationManager",
    "DataIntegrityManager",
    "EventLogger",
    "DiagnosticsBundle",
    "DatabaseOptimizer",
    "WatchdogService",
]
