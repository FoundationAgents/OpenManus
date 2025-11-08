"""Runtime monitoring for adaptive sandboxes.

Monitors resource usage (CPU, memory, file operations, network) and
triggers Guardian reassessment and isolation level escalation on anomalies.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque

from app.logger import logger
from app.sandbox.adaptive.isolation_levels import IsolationLevel, get_isolation_config


class AnomalyType(Enum):
    """Type of detected anomaly."""
    CPU_SPIKE = "cpu_spike"
    MEMORY_SPIKE = "memory_spike"
    EXCESSIVE_FILE_OPS = "excessive_file_ops"
    SUSPICIOUS_NETWORK = "suspicious_network"
    SUBPROCESS_EXPLOSION = "subprocess_explosion"
    TIMEOUT_RISK = "timeout_risk"
    PERMISSION_VIOLATION = "permission_violation"


@dataclass
class ResourceMetrics:
    """Current resource usage metrics."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    open_files: int
    network_connections: int
    subprocess_count: int
    disk_io_ops: int


@dataclass
class Anomaly:
    """Detected anomaly."""
    type: AnomalyType
    severity: float  # 0-1
    timestamp: float
    details: Dict
    reason: str


class AdaptiveRuntimeMonitor:
    """Monitors runtime behavior and triggers isolation escalation.
    
    Tracks:
    - Resource usage (CPU, memory)
    - File operations and access patterns
    - Network activity
    - Process creation
    - Syscall patterns
    
    Triggers isolation escalation on:
    - Resource limit breaches
    - Suspicious patterns
    - Guardian risk assessment
    """
    
    def __init__(
        self,
        sandbox_id: str,
        initial_isolation_level: IsolationLevel,
        check_interval: float = 1.0,
        history_size: int = 100,
    ):
        """Initialize runtime monitor.
        
        Args:
            sandbox_id: ID of the sandbox to monitor
            initial_isolation_level: Initial isolation level
            check_interval: How often to check resources (seconds)
            history_size: How many metrics to retain in history
        """
        self.sandbox_id = sandbox_id
        self.current_isolation_level = initial_isolation_level
        self.check_interval = check_interval
        self.history_size = history_size
        
        # Metrics tracking
        self.metrics_history: deque = deque(maxlen=history_size)
        self.anomalies: deque = deque(maxlen=history_size)
        
        # Thresholds (will be set from isolation config)
        self.cpu_alert_threshold = 80.0
        self.memory_alert_threshold_mb = 512
        self.max_open_files = 1000
        self.max_network_connections = 100
        self.max_subprocesses = 10
        self.max_file_ops_per_second = 1000
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.baseline_cpu = 0.0
        self.baseline_memory = 0.0
        
        # Violation tracking
        self.violations = defaultdict(int)
        
        logger.info(
            f"Initialized adaptive monitor for sandbox {sandbox_id} "
            f"at level {initial_isolation_level.name}"
        )
    
    def update_thresholds(self, isolation_level: IsolationLevel) -> None:
        """Update thresholds based on isolation level."""
        config = get_isolation_config(isolation_level)
        
        if config.enforce_cpu_limit:
            self.cpu_alert_threshold = config.cpu_percent
        
        if config.enforce_memory_limit:
            self.memory_alert_threshold_mb = config.memory_mb
        
        logger.debug(
            f"Updated thresholds for {isolation_level.name}: "
            f"CPU={self.cpu_alert_threshold}%, Memory={self.memory_alert_threshold_mb}MB"
        )
    
    def record_metrics(self, metrics: ResourceMetrics) -> None:
        """Record resource metrics snapshot.
        
        Args:
            metrics: Current resource metrics
        """
        self.metrics_history.append(metrics)
        
        # Check for anomalies
        anomalies = self._detect_anomalies(metrics)
        for anomaly in anomalies:
            self.anomalies.append(anomaly)
            logger.warning(f"Detected anomaly: {anomaly.type.value} - {anomaly.reason}")
    
    def _detect_anomalies(self, current: ResourceMetrics) -> list:
        """Detect anomalies in current metrics."""
        anomalies = []
        config = get_isolation_config(self.current_isolation_level)
        
        # CPU spike detection
        if config.enforce_cpu_limit and current.cpu_percent > self.cpu_alert_threshold:
            anomalies.append(Anomaly(
                type=AnomalyType.CPU_SPIKE,
                severity=min(1.0, current.cpu_percent / 100.0),
                timestamp=current.timestamp,
                details={"cpu_percent": current.cpu_percent, "threshold": self.cpu_alert_threshold},
                reason=f"CPU usage {current.cpu_percent}% exceeds threshold {self.cpu_alert_threshold}%",
            ))
            self.violations["cpu_spike"] += 1
        
        # Memory spike detection
        if config.enforce_memory_limit and current.memory_mb > self.memory_alert_threshold_mb:
            anomalies.append(Anomaly(
                type=AnomalyType.MEMORY_SPIKE,
                severity=min(1.0, current.memory_mb / (self.memory_alert_threshold_mb * 2)),
                timestamp=current.timestamp,
                details={"memory_mb": current.memory_mb, "threshold": self.memory_alert_threshold_mb},
                reason=f"Memory {current.memory_mb}MB exceeds threshold {self.memory_alert_threshold_mb}MB",
            ))
            self.violations["memory_spike"] += 1
        
        # File operation spike
        if hasattr(self, '_last_metrics') and self._last_metrics:
            time_delta = current.timestamp - self._last_metrics.timestamp
            if time_delta > 0:
                ops_per_second = (current.disk_io_ops - self._last_metrics.disk_io_ops) / time_delta
                if ops_per_second > self.max_file_ops_per_second:
                    anomalies.append(Anomaly(
                        type=AnomalyType.EXCESSIVE_FILE_OPS,
                        severity=min(1.0, ops_per_second / (self.max_file_ops_per_second * 2)),
                        timestamp=current.timestamp,
                        details={"ops_per_second": ops_per_second},
                        reason=f"File operations {ops_per_second:.0f}/s exceed threshold",
                    ))
                    self.violations["excessive_file_ops"] += 1
        
        # Subprocess explosion detection
        if current.subprocess_count > self.max_subprocesses:
            anomalies.append(Anomaly(
                type=AnomalyType.SUBPROCESS_EXPLOSION,
                severity=min(1.0, current.subprocess_count / (self.max_subprocesses * 3)),
                timestamp=current.timestamp,
                details={"subprocess_count": current.subprocess_count},
                reason=f"Subprocess count {current.subprocess_count} exceeds threshold {self.max_subprocesses}",
            ))
            self.violations["subprocess_explosion"] += 1
        
        # Network connection spike
        if current.network_connections > self.max_network_connections:
            anomalies.append(Anomaly(
                type=AnomalyType.SUSPICIOUS_NETWORK,
                severity=min(1.0, current.network_connections / (self.max_network_connections * 2)),
                timestamp=current.timestamp,
                details={"connections": current.network_connections},
                reason=f"Network connections {current.network_connections} exceed threshold",
            ))
            self.violations["suspicious_network"] += 1
        
        self._last_metrics = current
        return anomalies
    
    def should_escalate_isolation(self) -> Tuple[bool, Optional[IsolationLevel]]:
        """Determine if isolation level should be escalated.
        
        Returns:
            Tuple of (should_escalate, next_isolation_level)
        """
        if not self.anomalies:
            return False, None
        
        # Count violations in recent history
        recent_anomalies = list(self.anomalies)[-10:]
        violation_count = len(recent_anomalies)
        
        # Calculate average anomaly severity
        avg_severity = sum(a.severity for a in recent_anomalies) / len(recent_anomalies)
        
        # Escalate if multiple anomalies or high severity
        should_escalate = violation_count >= 3 or avg_severity > 0.7
        
        if should_escalate:
            config = get_isolation_config(self.current_isolation_level)
            next_level = config.escalate_to_level
            
            if next_level and next_level != self.current_isolation_level:
                logger.warning(
                    f"Recommending isolation escalation from {self.current_isolation_level.name} "
                    f"to {next_level.name} (violations: {violation_count}, severity: {avg_severity:.2f})"
                )
                return True, next_level
        
        return False, None
    
    def escalate_isolation(self, new_level: IsolationLevel) -> bool:
        """Escalate to a new isolation level.
        
        Args:
            new_level: New isolation level
        
        Returns:
            True if escalation was performed
        """
        if new_level.value <= self.current_isolation_level.value:
            logger.warning(
                f"Cannot escalate from {self.current_isolation_level.name} to {new_level.name}"
            )
            return False
        
        logger.info(
            f"Escalating isolation level from {self.current_isolation_level.name} "
            f"to {new_level.name}"
        )
        
        self.current_isolation_level = new_level
        self.update_thresholds(new_level)
        return True
    
    def get_metrics_summary(self) -> Dict:
        """Get summary of current metrics and violations."""
        if not self.metrics_history:
            return {
                "sandbox_id": self.sandbox_id,
                "current_isolation_level": self.current_isolation_level.name,
                "metrics_count": 0,
                "anomaly_count": len(self.anomalies),
                "violations": dict(self.violations),
            }
        
        latest = self.metrics_history[-1]
        
        return {
            "sandbox_id": self.sandbox_id,
            "current_isolation_level": self.current_isolation_level.name,
            "current_metrics": {
                "timestamp": latest.timestamp,
                "cpu_percent": latest.cpu_percent,
                "memory_mb": latest.memory_mb,
                "open_files": latest.open_files,
                "network_connections": latest.network_connections,
                "subprocess_count": latest.subprocess_count,
                "disk_io_ops": latest.disk_io_ops,
            },
            "metrics_count": len(self.metrics_history),
            "anomaly_count": len(self.anomalies),
            "recent_anomalies": [
                {
                    "type": a.type.value,
                    "severity": a.severity,
                    "reason": a.reason,
                }
                for a in list(self.anomalies)[-5:]
            ],
            "violations": dict(self.violations),
        }
    
    async def start_monitoring(self, get_metrics_callback) -> None:
        """Start monitoring loop.
        
        Args:
            get_metrics_callback: Async function that returns current ResourceMetrics
        """
        if self.is_monitoring:
            logger.warning(f"Monitor for {self.sandbox_id} already running")
            return
        
        self.is_monitoring = True
        logger.info(f"Starting monitoring for sandbox {self.sandbox_id}")
        
        async def monitor_loop():
            while self.is_monitoring:
                try:
                    metrics = await get_metrics_callback()
                    if metrics:
                        self.record_metrics(metrics)
                    
                    # Check for escalation
                    should_escalate, next_level = self.should_escalate_isolation()
                    if should_escalate and next_level:
                        self.escalate_isolation(next_level)
                    
                    await asyncio.sleep(self.check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(self.check_interval)
        
        self.monitor_task = asyncio.create_task(monitor_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring loop."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await asyncio.wait_for(self.monitor_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        logger.info(f"Stopped monitoring for sandbox {self.sandbox_id}")
