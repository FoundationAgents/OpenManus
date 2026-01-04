"""
FreEco.ai Platform - Stability Module
Enhanced OpenManus with error handling, stability, and adaptation

This module provides comprehensive stability features:
- Intelligent retry mechanisms with exponential backoff
- Graceful degradation with feature fallbacks
- Error recovery with state management and rollback

Part of Enhancement #3: Error Handling, Stability & Adaptation
"""

from .degradation import (
    DegradationEvent,
    Feature,
    GracefulDegradation,
    HealthMetrics,
    HealthStatus,
    QualityLevel,
    ServiceProvider,
    default_degradation,
)
from .error_recovery import (
    ErrorPattern,
    ErrorRecoverySystem,
    Operation,
    Recovery,
    RecoveryStrategy,
    State,
    default_recovery,
)
from .retry_manager import (
    RetryConfig,
    RetryManager,
    RetryStats,
    RetryStrategy,
    default_retry_manager,
    retry,
)


__all__ = [
    # Retry Manager
    "RetryManager",
    "RetryConfig",
    "RetryStats",
    "RetryStrategy",
    "retry",
    "default_retry_manager",
    # Graceful Degradation
    "GracefulDegradation",
    "QualityLevel",
    "HealthStatus",
    "ServiceProvider",
    "Feature",
    "DegradationEvent",
    "HealthMetrics",
    "default_degradation",
    # Error Recovery
    "ErrorRecoverySystem",
    "RecoveryStrategy",
    "State",
    "Operation",
    "ErrorPattern",
    "Recovery",
    "default_recovery",
]
