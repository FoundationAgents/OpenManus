"""
FreEco.ai Platform - Graceful Degradation System
Enhanced OpenManus with intelligent feature fallbacks and service redundancy

This module provides graceful degradation capabilities to maintain service
availability even when components fail or become unavailable.

Part of Enhancement #3: Error Handling, Stability & Adaptation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Service quality levels"""

    FULL = "full"  # All features available
    HIGH = "high"  # Most features available
    MEDIUM = "medium"  # Core features available
    LOW = "low"  # Minimal features available
    DEGRADED = "degraded"  # Emergency mode


class HealthStatus(Enum):
    """Service health status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class ServiceProvider:
    """Service provider configuration"""

    name: str
    priority: int  # Lower is higher priority
    is_available: bool = True
    health_score: float = 1.0  # 0.0 to 1.0
    last_check: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0

    def get_success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def record_success(self):
        """Record successful operation"""
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)  # Decay failures
        self.health_score = min(1.0, self.health_score + 0.1)
        self.last_check = datetime.now()

    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.health_score = max(0.0, self.health_score - 0.2)
        self.last_check = datetime.now()

        # Mark as unavailable if too many failures
        if self.failure_count >= 3:
            self.is_available = False


@dataclass
class Feature:
    """Feature configuration"""

    name: str
    is_enabled: bool = True
    is_critical: bool = False  # Critical features can't be disabled
    quality_level: QualityLevel = QualityLevel.FULL
    dependencies: List[str] = field(default_factory=list)
    fallback: Optional[str] = None  # Name of fallback feature

    def can_disable(self) -> bool:
        """Check if feature can be disabled"""
        return not self.is_critical


@dataclass
class DegradationEvent:
    """Degradation event record"""

    timestamp: datetime
    feature: str
    reason: str
    quality_before: QualityLevel
    quality_after: QualityLevel
    auto_recovered: bool = False


@dataclass
class HealthMetrics:
    """Health monitoring metrics"""

    overall_health: HealthStatus
    quality_level: QualityLevel
    enabled_features: int
    disabled_features: int
    available_providers: int
    unavailable_providers: int
    degradation_events: int
    last_check: datetime


class GracefulDegradation:
    """
    Graceful degradation system for maintaining service availability

    Features:
    - Feature fallbacks - Disable non-critical features when needed
    - Service redundancy - Multiple providers for each service
    - Quality levels - Adjust quality vs. availability
    - Health monitoring - Track service health in real-time
    - Alert system - Notify on degradation events
    - Auto-recovery - Automatically re-enable features when healthy

    Example:
        degradation = GracefulDegradation()

        # Register features
        degradation.register_feature("advanced_planning", critical=False)
        degradation.register_feature("basic_planning", critical=True)

        # Register service providers
        degradation.register_provider("llm", "openai", priority=1)
        degradation.register_provider("llm", "anthropic", priority=2)

        # Use with fallback
        result = degradation.execute_with_fallback(
            "llm",
            lambda provider: call_llm(provider),
        )
    """

    def __init__(self):
        """Initialize graceful degradation system"""
        self.features: Dict[str, Feature] = {}
        self.providers: Dict[str, List[ServiceProvider]] = {}
        self.current_quality = QualityLevel.FULL
        self.degradation_log: List[DegradationEvent] = []
        self.alert_callbacks: List[Callable] = []

        # Initialize with default features
        self._init_default_features()

    def _init_default_features(self):
        """Initialize default features"""
        # Critical features (always enabled)
        self.register_feature(
            "basic_planning",
            critical=True,
            quality_level=QualityLevel.LOW,
        )
        self.register_feature(
            "error_handling",
            critical=True,
            quality_level=QualityLevel.LOW,
        )

        # Non-critical features (can be disabled)
        self.register_feature(
            "advanced_planning",
            critical=False,
            quality_level=QualityLevel.HIGH,
            fallback="basic_planning",
        )
        self.register_feature(
            "tree_of_thoughts",
            critical=False,
            quality_level=QualityLevel.FULL,
            dependencies=["advanced_planning"],
        )
        self.register_feature(
            "reflection_engine",
            critical=False,
            quality_level=QualityLevel.HIGH,
        )
        self.register_feature(
            "multimodal_tools",
            critical=False,
            quality_level=QualityLevel.MEDIUM,
        )

    def register_feature(
        self,
        name: str,
        critical: bool = False,
        quality_level: QualityLevel = QualityLevel.FULL,
        dependencies: Optional[List[str]] = None,
        fallback: Optional[str] = None,
    ):
        """
        Register a feature for degradation management

        Args:
            name: Feature name
            critical: Whether feature is critical (can't be disabled)
            quality_level: Minimum quality level for this feature
            dependencies: List of feature names this depends on
            fallback: Name of fallback feature if this one fails
        """
        self.features[name] = Feature(
            name=name,
            is_critical=critical,
            quality_level=quality_level,
            dependencies=dependencies or [],
            fallback=fallback,
        )
        logger.info(f"Registered feature: {name} (critical={critical})")

    def register_provider(
        self,
        service: str,
        provider_name: str,
        priority: int = 1,
    ):
        """
        Register a service provider for redundancy

        Args:
            service: Service name (e.g., "llm", "database")
            provider_name: Provider name (e.g., "openai", "anthropic")
            priority: Priority (lower is higher priority)
        """
        if service not in self.providers:
            self.providers[service] = []

        provider = ServiceProvider(
            name=provider_name,
            priority=priority,
        )

        self.providers[service].append(provider)
        self.providers[service].sort(key=lambda p: p.priority)

        logger.info(
            f"Registered provider: {service}/{provider_name} (priority={priority})"
        )

    def disable_feature(self, feature_name: str, reason: str = "") -> bool:
        """
        Disable a non-critical feature

        Args:
            feature_name: Name of feature to disable
            reason: Reason for disabling

        Returns:
            True if feature was disabled, False if it's critical
        """
        if feature_name not in self.features:
            logger.warning(f"Unknown feature: {feature_name}")
            return False

        feature = self.features[feature_name]

        if not feature.can_disable():
            logger.warning(f"Cannot disable critical feature: {feature_name}")
            return False

        if not feature.is_enabled:
            logger.info(f"Feature already disabled: {feature_name}")
            return True

        # Disable feature
        feature.is_enabled = False

        # Log degradation event
        event = DegradationEvent(
            timestamp=datetime.now(),
            feature=feature_name,
            reason=reason,
            quality_before=self.current_quality,
            quality_after=self._calculate_quality_level(),
        )
        self.degradation_log.append(event)

        # Update quality level
        self.current_quality = event.quality_after

        # Send alerts
        self._send_alert(f"Feature disabled: {feature_name} - {reason}")

        logger.warning(f"Disabled feature: {feature_name} - {reason}")
        return True

    def enable_feature(self, feature_name: str) -> bool:
        """
        Enable a feature

        Args:
            feature_name: Name of feature to enable

        Returns:
            True if feature was enabled
        """
        if feature_name not in self.features:
            logger.warning(f"Unknown feature: {feature_name}")
            return False

        feature = self.features[feature_name]

        if feature.is_enabled:
            logger.info(f"Feature already enabled: {feature_name}")
            return True

        # Check dependencies
        for dep in feature.dependencies:
            if dep not in self.features or not self.features[dep].is_enabled:
                logger.warning(
                    f"Cannot enable {feature_name}: dependency {dep} not enabled"
                )
                return False

        # Enable feature
        feature.is_enabled = True

        # Update quality level
        old_quality = self.current_quality
        self.current_quality = self._calculate_quality_level()

        # Log recovery
        if old_quality != self.current_quality:
            event = DegradationEvent(
                timestamp=datetime.now(),
                feature=feature_name,
                reason="Auto-recovery",
                quality_before=old_quality,
                quality_after=self.current_quality,
                auto_recovered=True,
            )
            self.degradation_log.append(event)

        logger.info(f"Enabled feature: {feature_name}")
        return True

    def switch_provider(
        self, service: str, reason: str = ""
    ) -> Optional[ServiceProvider]:
        """
        Switch to next available provider for a service

        Args:
            service: Service name
            reason: Reason for switching

        Returns:
            New provider if available, None otherwise
        """
        if service not in self.providers:
            logger.warning(f"Unknown service: {service}")
            return None

        providers = self.providers[service]

        # Find next available provider
        for provider in providers:
            if provider.is_available and provider.health_score > 0.3:
                logger.info(
                    f"Switched to provider: {service}/{provider.name} - {reason}"
                )
                return provider

        logger.error(f"No available providers for service: {service}")
        return None

    def execute_with_fallback(
        self,
        service: str,
        operation: Callable[[ServiceProvider], Any],
        max_attempts: int = 3,
    ) -> Any:
        """
        Execute operation with automatic provider fallback

        Args:
            service: Service name
            operation: Operation to execute (receives provider as argument)
            max_attempts: Maximum attempts across all providers

        Returns:
            Result of successful operation

        Raises:
            Exception if all providers fail
        """
        if service not in self.providers:
            raise ValueError(f"Unknown service: {service}")

        providers = [p for p in self.providers[service] if p.is_available]

        if not providers:
            raise RuntimeError(f"No available providers for service: {service}")

        last_exception = None
        attempts = 0

        for provider in providers:
            if attempts >= max_attempts:
                break

            try:
                attempts += 1
                result = operation(provider)
                provider.record_success()
                return result

            except Exception as e:
                last_exception = e
                provider.record_failure()
                logger.warning(
                    f"Provider {service}/{provider.name} failed: {e}. "
                    f"Trying next provider..."
                )
                continue

        # All providers failed
        raise RuntimeError(
            f"All providers failed for service: {service}"
        ) from last_exception

    def adjust_quality(self, level: QualityLevel):
        """
        Manually adjust quality level

        Args:
            level: Target quality level
        """
        if level == self.current_quality:
            return

        old_level = self.current_quality
        self.current_quality = level

        # Disable features based on quality level
        for feature in self.features.values():
            if feature.quality_level.value > level.value and not feature.is_critical:
                self.disable_feature(feature.name, f"Quality adjusted to {level.value}")

        logger.info(f"Quality adjusted: {old_level.value} -> {level.value}")

    def monitor_health(self) -> HealthMetrics:
        """
        Monitor overall system health

        Returns:
            HealthMetrics with current health status
        """
        enabled_features = sum(1 for f in self.features.values() if f.is_enabled)
        disabled_features = len(self.features) - enabled_features

        total_providers = sum(len(providers) for providers in self.providers.values())
        available_providers = sum(
            sum(1 for p in providers if p.is_available)
            for providers in self.providers.values()
        )
        unavailable_providers = total_providers - available_providers

        # Determine overall health
        if disabled_features == 0 and unavailable_providers == 0:
            health = HealthStatus.HEALTHY
        elif disabled_features <= 2 and unavailable_providers <= 1:
            health = HealthStatus.DEGRADED
        elif disabled_features <= 4 and unavailable_providers <= 2:
            health = HealthStatus.UNHEALTHY
        elif enabled_features > 0:
            health = HealthStatus.CRITICAL
        else:
            health = HealthStatus.DOWN

        return HealthMetrics(
            overall_health=health,
            quality_level=self.current_quality,
            enabled_features=enabled_features,
            disabled_features=disabled_features,
            available_providers=available_providers,
            unavailable_providers=unavailable_providers,
            degradation_events=len(self.degradation_log),
            last_check=datetime.now(),
        )

    def _calculate_quality_level(self) -> QualityLevel:
        """Calculate current quality level based on enabled features"""
        enabled_features = [f for f in self.features.values() if f.is_enabled]

        if not enabled_features:
            return QualityLevel.DEGRADED

        # Get highest quality level among enabled features
        max_quality = max(f.quality_level for f in enabled_features)
        return max_quality

    def _send_alert(self, message: str):
        """Send alert to registered callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def register_alert_callback(self, callback: Callable[[str], None]):
        """
        Register callback for degradation alerts

        Args:
            callback: Function to call with alert message
        """
        self.alert_callbacks.append(callback)

    def get_degradation_log(self) -> List[DegradationEvent]:
        """Get degradation event log"""
        return self.degradation_log.copy()

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled

        Args:
            feature_name: Feature name

        Returns:
            True if feature is enabled
        """
        if feature_name not in self.features:
            return False
        return self.features[feature_name].is_enabled

    def get_available_provider(self, service: str) -> Optional[ServiceProvider]:
        """
        Get best available provider for a service

        Args:
            service: Service name

        Returns:
            Best available provider or None
        """
        if service not in self.providers:
            return None

        available = [p for p in self.providers[service] if p.is_available]
        if not available:
            return None

        # Return highest priority (lowest priority number) with good health
        return max(available, key=lambda p: (p.health_score, -p.priority))


# Global degradation manager instance
default_degradation = GracefulDegradation()
