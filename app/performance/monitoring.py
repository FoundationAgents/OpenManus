"""
FreEco.ai Platform - Monitoring System
Enhanced OpenManus with real-time monitoring and alerting

This module provides comprehensive monitoring capabilities:
- Real-time system metrics (CPU, memory, network)
- Custom business metrics
- Trend analysis
- Threshold-based alerting
- Time-series metric storage
- Dashboard generation

Part of Enhancement #5: Performance, UX & Evaluation
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types"""

    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"  # Can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Summary statistics


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Metric data point"""

    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "type": self.metric_type.value,
            "tags": self.tags,
        }


@dataclass
class Alert:
    """Alert record"""

    metric_name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "metric": self.metric_name,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class TrendAnalysis:
    """Trend analysis result"""

    metric_name: str
    direction: str  # "increasing", "decreasing", "stable"
    slope: float  # Rate of change
    confidence: float  # 0.0 to 1.0
    prediction: Optional[float] = None  # Predicted next value

    def __str__(self) -> str:
        return (
            f"{self.metric_name}: {self.direction} "
            f"(slope={self.slope:.3f}, confidence={self.confidence:.2f})"
        )


@dataclass
class SystemMetrics:
    """System resource metrics"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_percent": self.disk_percent,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
        }


class MonitoringSystem:
    """
    Real-time monitoring and alerting system

    Features:
    - System metrics collection (CPU, memory, disk, network)
    - Custom metric tracking
    - Time-series storage with configurable retention
    - Trend analysis and prediction
    - Threshold-based alerting
    - Alert callbacks for notifications
    - Dashboard data generation

    Example:
        monitor = MonitoringSystem()

        # Track custom metric
        monitor.track_custom_metric("api_calls", 150, MetricType.COUNTER)

        # Set alert threshold
        monitor.set_alert("cpu_percent", threshold=80.0, severity=AlertSeverity.WARNING)

        # Get trend analysis
        trend = monitor.analyze_trends("api_calls")
        print(trend)

        # Get dashboard data
        dashboard = monitor.get_dashboard()
    """

    def __init__(
        self,
        collection_interval: int = 60,
        retention_hours: int = 24,
        max_metrics_per_series: int = 1000,
    ):
        """
        Initialize monitoring system

        Args:
            collection_interval: Seconds between metric collections
            retention_hours: Hours to retain metrics
            max_metrics_per_series: Maximum metrics per time series
        """
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        self.max_metrics_per_series = max_metrics_per_series

        # Metric storage (metric_name -> deque of Metric objects)
        self.metrics: Dict[str, deque] = {}

        # Alert configuration (metric_name -> (threshold, severity))
        self.alert_thresholds: Dict[str, tuple] = {}

        # Active alerts
        self.active_alerts: List[Alert] = []

        # Alert callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        # Last collection time
        self.last_collection: Optional[datetime] = None

        # Network baseline for calculating deltas
        self._network_baseline = None

    def collect_metrics(self) -> SystemMetrics:
        """
        Collect system metrics

        Returns:
            SystemMetrics with current system state
        """
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)

        # Get disk usage
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent

        # Get network usage
        network = psutil.net_io_counters()

        # Calculate network delta if we have a baseline
        if self._network_baseline is None:
            self._network_baseline = network
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        else:
            network_sent_mb = (
                network.bytes_sent - self._network_baseline.bytes_sent
            ) / (1024 * 1024)
            network_recv_mb = (
                network.bytes_recv - self._network_baseline.bytes_recv
            ) / (1024 * 1024)
            self._network_baseline = network

        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_percent=disk_percent,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
        )

        # Store metrics
        self._store_metric("cpu_percent", cpu_percent, MetricType.GAUGE)
        self._store_metric("memory_percent", memory_percent, MetricType.GAUGE)
        self._store_metric("memory_used_mb", memory_used_mb, MetricType.GAUGE)
        self._store_metric("disk_percent", disk_percent, MetricType.GAUGE)
        self._store_metric("network_sent_mb", network_sent_mb, MetricType.COUNTER)
        self._store_metric("network_recv_mb", network_recv_mb, MetricType.COUNTER)

        # Check alerts
        self._check_alerts(metrics)

        self.last_collection = datetime.now()

        return metrics

    def track_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Track a custom metric

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags for the metric
        """
        self._store_metric(name, value, metric_type, tags or {})

        # Check if this triggers an alert
        if name in self.alert_thresholds:
            threshold, severity = self.alert_thresholds[name]
            if value > threshold:
                self._trigger_alert(name, value, threshold, severity)

    def _store_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Store a metric in time series"""
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.max_metrics_per_series)

        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            metric_type=metric_type,
            tags=tags or {},
        )

        self.metrics[name].append(metric)

        # Clean up old metrics
        self._cleanup_old_metrics(name)

    def _cleanup_old_metrics(self, metric_name: str):
        """Remove metrics older than retention period"""
        if metric_name not in self.metrics:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        # Remove old metrics from the front of the deque
        while (
            self.metrics[metric_name]
            and self.metrics[metric_name][0].timestamp < cutoff_time
        ):
            self.metrics[metric_name].popleft()

    def set_alert(
        self,
        metric_name: str,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        """
        Set alert threshold for a metric

        Args:
            metric_name: Name of metric to monitor
            threshold: Threshold value
            severity: Alert severity
        """
        self.alert_thresholds[metric_name] = (threshold, severity)
        logger.info(f"Alert set: {metric_name} > {threshold} ({severity.value})")

    def _check_alerts(self, metrics: SystemMetrics):
        """Check if any metrics exceed alert thresholds"""
        metrics_dict = metrics.to_dict()

        for metric_name, (threshold, severity) in self.alert_thresholds.items():
            if metric_name in metrics_dict:
                value = metrics_dict[metric_name]
                if isinstance(value, (int, float)) and value > threshold:
                    self._trigger_alert(metric_name, value, threshold, severity)

    def _trigger_alert(
        self,
        metric_name: str,
        value: float,
        threshold: float,
        severity: AlertSeverity,
    ):
        """Trigger an alert"""
        alert = Alert(
            metric_name=metric_name,
            severity=severity,
            message=f"{metric_name} exceeded threshold: {value:.2f} > {threshold:.2f}",
            value=value,
            threshold=threshold,
            timestamp=datetime.now(),
        )

        self.active_alerts.append(alert)

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        logger.warning(f"ALERT: {alert.message}")

    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """
        Register callback for alerts

        Args:
            callback: Function to call when alert is triggered
        """
        self.alert_callbacks.append(callback)

    def analyze_trends(
        self,
        metric_name: str,
        window_size: int = 10,
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trends for a metric

        Args:
            metric_name: Name of metric to analyze
            window_size: Number of recent data points to analyze

        Returns:
            TrendAnalysis or None if insufficient data
        """
        if metric_name not in self.metrics:
            return None

        recent_metrics = list(self.metrics[metric_name])[-window_size:]

        if len(recent_metrics) < 3:
            return None

        # Calculate slope using linear regression
        values = [m.value for m in recent_metrics]
        n = len(values)
        x = list(range(n))

        # Simple linear regression
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # Determine direction
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        # Calculate confidence (R-squared)
        if denominator == 0:
            confidence = 0.0
        else:
            predictions = [y_mean + slope * (i - x_mean) for i in x]
            ss_res = sum((values[i] - predictions[i]) ** 2 for i in range(n))
            ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

            if ss_tot == 0:
                confidence = 0.0
            else:
                confidence = 1 - (ss_res / ss_tot)

        # Predict next value
        prediction = y_mean + slope * (n - x_mean)

        return TrendAnalysis(
            metric_name=metric_name,
            direction=direction,
            slope=slope,
            confidence=max(0.0, min(1.0, confidence)),
            prediction=prediction,
        )

    def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a metric

        Args:
            metric_name: Name of metric

        Returns:
            Dictionary with min, max, avg, current
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return None

        values = [m.value for m in self.metrics[metric_name]]

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "current": values[-1],
            "count": len(values),
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """
        Get dashboard data

        Returns:
            Dictionary with dashboard information
        """
        # Collect current metrics
        current_metrics = self.collect_metrics()

        # Get all metric stats
        metric_stats = {}
        for metric_name in self.metrics.keys():
            stats = self.get_metric_stats(metric_name)
            if stats:
                metric_stats[metric_name] = stats

        # Get trend analyses
        trends = {}
        for metric_name in self.metrics.keys():
            trend = self.analyze_trends(metric_name)
            if trend:
                trends[metric_name] = {
                    "direction": trend.direction,
                    "slope": trend.slope,
                    "confidence": trend.confidence,
                    "prediction": trend.prediction,
                }

        # Get active alerts
        active_alerts = [
            alert.to_dict() for alert in self.active_alerts if not alert.acknowledged
        ]

        return {
            "timestamp": datetime.now().isoformat(),
            "current_metrics": current_metrics.to_dict(),
            "metric_stats": metric_stats,
            "trends": trends,
            "active_alerts": active_alerts,
            "alert_count": len(active_alerts),
        }

    def acknowledge_alert(self, alert_index: int):
        """
        Acknowledge an alert

        Args:
            alert_index: Index of alert to acknowledge
        """
        if 0 <= alert_index < len(self.active_alerts):
            self.active_alerts[alert_index].acknowledged = True
            logger.info(
                f"Alert acknowledged: {self.active_alerts[alert_index].message}"
            )

    def clear_acknowledged_alerts(self):
        """Clear all acknowledged alerts"""
        self.active_alerts = [a for a in self.active_alerts if not a.acknowledged]

    def get_metric_history(
        self,
        metric_name: str,
        hours: Optional[int] = None,
    ) -> List[Metric]:
        """
        Get metric history

        Args:
            metric_name: Name of metric
            hours: Number of hours of history (all if None)

        Returns:
            List of Metric objects
        """
        if metric_name not in self.metrics:
            return []

        metrics = list(self.metrics[metric_name])

        if hours is not None:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]

        return metrics


# Global monitoring instance
default_monitor = MonitoringSystem()
