"""
FreEco.ai Platform - Ecological Principles
Enhanced OpenManus with environmental responsibility

This module implements ecological principles:
- Energy efficiency and optimization
- Resource optimization (caching, reuse)
- Carbon footprint tracking
- Green computing (efficient model selection)
- Waste reduction
- Sustainability metrics

Part of Ethical AI Framework
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources"""

    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    LLM_TOKENS = "llm_tokens"


@dataclass
class CO2Metric:
    """Carbon footprint metric"""

    operation: str
    co2_grams: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "operation": self.operation,
            "co2_grams": self.co2_grams,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class ResourceUsage:
    """Resource usage record"""

    resource_type: ResourceType
    amount: float
    unit: str
    timestamp: datetime
    operation: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "resource_type": self.resource_type.value,
            "amount": self.amount,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
        }


@dataclass
class SustainabilityMetrics:
    """Sustainability metrics"""

    total_co2_grams: float
    total_energy_kwh: float
    cache_hit_rate: float
    resource_reuse_rate: float
    avg_response_time_ms: float
    total_requests: int

    def co2_per_request(self) -> float:
        """Calculate CO2 per request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_co2_grams / self.total_requests

    def energy_per_request(self) -> float:
        """Calculate energy per request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_energy_kwh / self.total_requests

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "total_co2_grams": self.total_co2_grams,
            "total_energy_kwh": self.total_energy_kwh,
            "cache_hit_rate": self.cache_hit_rate,
            "resource_reuse_rate": self.resource_reuse_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "total_requests": self.total_requests,
            "co2_per_request": self.co2_per_request(),
            "energy_per_request": self.energy_per_request(),
        }


class EcologicalSystem:
    """
    Ecological principles implementation

    Features:
    - Energy efficiency tracking
    - Resource optimization
    - Carbon footprint monitoring
    - Green model selection
    - Waste reduction
    - Sustainability reporting

    Example:
        eco = EcologicalSystem()

        # Track operation
        with eco.track_operation("llm_call"):
            result = call_llm()

        # Get green model
        model = eco.select_green_model("text_generation")

        # Get sustainability metrics
        metrics = eco.get_sustainability_metrics()
    """

    def __init__(self):
        """Initialize ecological system"""
        self.co2_log: list[CO2Metric] = []
        self.resource_log: list[ResourceUsage] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.resources_reused = 0
        self.resources_created = 0
        self.operation_times: list[float] = []

        # CO2 emission factors (grams per unit)
        self.co2_factors = {
            "cpu_hour": 50.0,  # grams per CPU hour
            "memory_gb_hour": 5.0,  # grams per GB-hour
            "network_gb": 20.0,  # grams per GB transferred
            "llm_1k_tokens": 0.5,  # grams per 1000 tokens
        }

        # Green model preferences (lower is better)
        self.model_efficiency = {
            "gpt-4.1-nano": 1.0,  # Most efficient
            "gpt-4.1-mini": 2.0,
            "gemini-2.5-flash": 1.5,
            "claude-3-haiku": 2.5,
            "gpt-4": 5.0,  # Least efficient
        }

    def optimize_energy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize task for energy efficiency

        Args:
            task: Task configuration

        Returns:
            Optimized task configuration
        """
        optimized = task.copy()

        # Use smaller model if possible
        if "model" in task:
            current_model = task["model"]
            if current_model in self.model_efficiency:
                # Suggest more efficient model
                efficient_models = sorted(
                    self.model_efficiency.items(), key=lambda x: x[1]
                )
                optimized["model"] = efficient_models[0][0]
                logger.info(f"Optimized model: {current_model} -> {optimized['model']}")

        # Reduce max_tokens if not critical
        if "max_tokens" in task and task.get("priority", "normal") != "high":
            original_tokens = task["max_tokens"]
            optimized["max_tokens"] = min(original_tokens, 1000)
            if optimized["max_tokens"] < original_tokens:
                logger.info(
                    f"Reduced max_tokens: {original_tokens} -> {optimized['max_tokens']}"
                )

        # Enable caching
        optimized["use_cache"] = True

        return optimized

    def cache_result(self, key: str, value: Any) -> bool:
        """
        Cache a result for reuse

        Args:
            key: Cache key
            value: Value to cache

        Returns:
            True if cached successfully
        """
        # This would integrate with PerformanceOptimizer's cache
        # For now, just track the cache operation
        self.cache_hits += 1
        self.resources_reused += 1

        logger.debug(f"Cached result: {key}")
        return True

    def track_carbon(self, operation: str, **kwargs) -> CO2Metric:
        """
        Track carbon footprint of an operation

        Args:
            operation: Operation name
            **kwargs: Operation details (cpu_hours, memory_gb_hours, etc.)

        Returns:
            CO2Metric with calculated footprint
        """
        co2_grams = 0.0
        details = {}

        # Calculate CO2 for each resource
        if "cpu_hours" in kwargs:
            cpu_co2 = kwargs["cpu_hours"] * self.co2_factors["cpu_hour"]
            co2_grams += cpu_co2
            details["cpu_co2"] = cpu_co2

        if "memory_gb_hours" in kwargs:
            memory_co2 = kwargs["memory_gb_hours"] * self.co2_factors["memory_gb_hour"]
            co2_grams += memory_co2
            details["memory_co2"] = memory_co2

        if "network_gb" in kwargs:
            network_co2 = kwargs["network_gb"] * self.co2_factors["network_gb"]
            co2_grams += network_co2
            details["network_co2"] = network_co2

        if "llm_tokens" in kwargs:
            token_co2 = (kwargs["llm_tokens"] / 1000) * self.co2_factors[
                "llm_1k_tokens"
            ]
            co2_grams += token_co2
            details["token_co2"] = token_co2

        metric = CO2Metric(
            operation=operation,
            co2_grams=co2_grams,
            timestamp=datetime.now(),
            details=details,
        )

        self.co2_log.append(metric)

        logger.info(f"Carbon footprint: {operation} = {co2_grams:.2f}g CO2")

        return metric

    def select_green_model(self, task_type: str, quality_threshold: float = 0.8) -> str:
        """
        Select most efficient model for task

        Args:
            task_type: Type of task
            quality_threshold: Minimum quality threshold (0-1)

        Returns:
            Model name
        """
        # For now, return most efficient model
        # In production, would consider task requirements
        efficient_models = sorted(self.model_efficiency.items(), key=lambda x: x[1])

        selected_model = efficient_models[0][0]

        logger.info(f"Selected green model: {selected_model} for {task_type}")

        return selected_model

    def cleanup_resources(self) -> Dict[str, int]:
        """
        Clean up unused resources

        Returns:
            Dictionary with cleanup statistics
        """
        # This would integrate with actual resource management
        # For now, simulate cleanup

        cleaned = {
            "cache_entries": 0,
            "temp_files": 0,
            "memory_mb": 0,
        }

        # Clean old CO2 metrics (keep last 7 days)
        cutoff = datetime.now() - timedelta(days=7)
        original_count = len(self.co2_log)
        self.co2_log = [m for m in self.co2_log if m.timestamp >= cutoff]
        cleaned["cache_entries"] = original_count - len(self.co2_log)

        logger.info(f"Cleaned up {cleaned['cache_entries']} old metrics")

        return cleaned

    def get_sustainability_metrics(self) -> SustainabilityMetrics:
        """
        Get sustainability metrics

        Returns:
            SustainabilityMetrics object
        """
        # Calculate total CO2
        total_co2 = sum(m.co2_grams for m in self.co2_log)

        # Estimate energy from CO2 (rough approximation)
        # Assuming 500g CO2 per kWh (global average)
        total_energy = total_co2 / 500.0

        # Calculate cache hit rate
        total_cache_ops = self.cache_hits + self.cache_misses
        cache_hit_rate = (
            self.cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0
        )

        # Calculate resource reuse rate
        total_resources = self.resources_reused + self.resources_created
        reuse_rate = (
            self.resources_reused / total_resources if total_resources > 0 else 0.0
        )

        # Calculate average response time
        avg_time = (
            sum(self.operation_times) / len(self.operation_times)
            if self.operation_times
            else 0.0
        )

        # Total requests (approximate from CO2 log)
        total_requests = len(self.co2_log)

        return SustainabilityMetrics(
            total_co2_grams=total_co2,
            total_energy_kwh=total_energy,
            cache_hit_rate=cache_hit_rate,
            resource_reuse_rate=reuse_rate,
            avg_response_time_ms=avg_time,
            total_requests=total_requests,
        )

    def track_operation(self, operation_name: str):
        """
        Context manager for tracking operation metrics

        Args:
            operation_name: Name of operation

        Example:
            with eco.track_operation("llm_call"):
                result = call_llm()
        """
        return OperationTracker(self, operation_name)

    def record_resource_usage(
        self,
        resource_type: ResourceType,
        amount: float,
        unit: str,
        operation: Optional[str] = None,
    ):
        """
        Record resource usage

        Args:
            resource_type: Type of resource
            amount: Amount used
            unit: Unit of measurement
            operation: Optional operation name
        """
        usage = ResourceUsage(
            resource_type=resource_type,
            amount=amount,
            unit=unit,
            timestamp=datetime.now(),
            operation=operation,
        )

        self.resource_log.append(usage)
        self.resources_created += 1


class OperationTracker:
    """Context manager for tracking operations"""

    def __init__(self, eco_system: EcologicalSystem, operation_name: str):
        """
        Initialize operation tracker

        Args:
            eco_system: EcologicalSystem instance
            operation_name: Name of operation
        """
        self.eco_system = eco_system
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start tracking"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and record metrics"""
        duration_ms = (time.time() - self.start_time) * 1000
        self.eco_system.operation_times.append(duration_ms)

        # Estimate resource usage based on duration
        # These are rough estimates for tracking purposes
        cpu_hours = duration_ms / (1000 * 3600)  # Convert ms to hours

        # Track carbon footprint
        self.eco_system.track_carbon(
            self.operation_name,
            cpu_hours=cpu_hours,
        )

        logger.debug(
            f"Operation {self.operation_name} completed in {duration_ms:.1f}ms"
        )


# Global ecological system instance
default_ecological = EcologicalSystem()
