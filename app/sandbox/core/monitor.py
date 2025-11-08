"""
Resource monitoring system for sandbox operations.

This module provides real-time monitoring of sandbox resource usage,
including CPU, memory, disk, and network metrics, with killswitch
functionality when limits are exceeded.
"""

import asyncio
import psutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

import docker
from docker.models.containers import Container

from app.logger import logger
from app.sandbox.core.audit import AuditLogger, OperationType, OperationStatus, AuditLog, ResourceUsage


class TriggerType(Enum):
    """Resource limit trigger types."""
    CPU_LIMIT = "cpu_limit"
    MEMORY_LIMIT = "memory_limit"
    DISK_LIMIT = "disk_limit"
    TIMEOUT = "timeout"
    CUSTOM = "custom"


@dataclass
class ResourceLimits:
    """Resource limits for a sandbox."""
    cpu_percent: float = 80.0
    memory_mb: int = 512
    disk_mb: int = 1024
    timeout_seconds: int = 300
    network_bandwidth_mbps: Optional[float] = None
    custom_limits: Dict[str, Any] = None


@dataclass
class ResourceAlert:
    """Resource usage alert."""
    timestamp: datetime
    sandbox_id: str
    trigger_type: TriggerType
    current_value: float
    limit_value: float
    severity: str  # "warning", "critical"
    message: str


class ResourceMonitor:
    """Resource monitor for sandbox instances.

    Provides real-time monitoring of resource usage and automatic
    termination when limits are exceeded.
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize resource monitor.

        Args:
            audit_logger: Audit logger for recording events.
        """
        self.audit_logger = audit_logger
        self.docker_client = docker.from_env()
        self._monitored_sandboxes: Dict[str, Dict[str, Any]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 5.0  # seconds
        self._is_running = False
        self._killswitch_handlers: List[Callable[[str, ResourceAlert], None]] = []

    def start_monitoring(self) -> None:
        """Start the resource monitoring task."""
        if self._is_running:
            return

        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Resource monitoring started")

    def stop_monitoring(self) -> None:
        """Stop the resource monitoring task."""
        self._is_running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                # Wait for the task to complete
                if not self._monitoring_task.done():
                    self._monitoring_task.cancel()
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")

    def add_sandbox(
        self,
        sandbox_id: str,
        container: Container,
        agent_id: str,
        limits: ResourceLimits,
        process_pid: Optional[int] = None
    ) -> None:
        """Add a sandbox to monitor.

        Args:
            sandbox_id: Sandbox identifier.
            container: Docker container instance.
            agent_id: Agent ID owning the sandbox.
            limits: Resource limits.
            process_pid: Optional process PID for process-based monitoring.
        """
        self._monitored_sandboxes[sandbox_id] = {
            "container": container,
            "agent_id": agent_id,
            "limits": limits,
            "process_pid": process_pid,
            "start_time": time.time(),
            "last_check": time.time(),
            "alerts_count": 0,
            "kill_triggered": False
        }
        logger.info(f"Added sandbox {sandbox_id} to monitoring")

    def remove_sandbox(self, sandbox_id: str) -> None:
        """Remove a sandbox from monitoring.

        Args:
            sandbox_id: Sandbox identifier.
        """
        if sandbox_id in self._monitored_sandboxes:
            del self._monitored_sandboxes[sandbox_id]
            logger.info(f"Removed sandbox {sandbox_id} from monitoring")

    def add_killswitch_handler(self, handler: Callable[[str, ResourceAlert], None]) -> None:
        """Add a custom killswitch handler.

        Args:
            handler: Function to call when killswitch is triggered.
        """
        self._killswitch_handlers.append(handler)

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_running:
            try:
                await self._check_all_sandboxes()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self._monitoring_interval)

    async def _check_all_sandboxes(self) -> None:
        """Check resource usage for all monitored sandboxes."""
        current_time = time.time()
        sandboxes_to_remove = []

        for sandbox_id, sandbox_info in self._monitored_sandboxes.items():
            try:
                # Skip if already killed
                if sandbox_info["kill_triggered"]:
                    continue

                # Check timeout
                elapsed = current_time - sandbox_info["start_time"]
                if elapsed > sandbox_info["limits"].timeout_seconds:
                    await self._trigger_killswitch(
                        sandbox_id,
                        ResourceAlert(
                            timestamp=datetime.now(timezone.utc),
                            sandbox_id=sandbox_id,
                            trigger_type=TriggerType.TIMEOUT,
                            current_value=elapsed,
                            limit_value=sandbox_info["limits"].timeout_seconds,
                            severity="critical",
                            message=f"Sandbox timeout exceeded ({elapsed:.1f}s > {sandbox_info['limits'].timeout_seconds}s)"
                        )
                    )
                    continue

                # Get resource usage
                usage = await self._get_resource_usage(sandbox_id, sandbox_info)
                if usage is None:
                    continue

                # Check resource limits
                await self._check_resource_limits(sandbox_id, sandbox_info, usage)

                sandbox_info["last_check"] = current_time

            except Exception as e:
                logger.error(f"Error monitoring sandbox {sandbox_id}: {e}")
                # Consider removing if container no longer exists
                try:
                    sandbox_info["container"].reload()
                except:
                    sandboxes_to_remove.append(sandbox_id)

        # Remove dead sandboxes
        for sandbox_id in sandboxes_to_remove:
            self.remove_sandbox(sandbox_id)

    async def _get_resource_usage(self, sandbox_id: str, sandbox_info: Dict[str, Any]) -> Optional[ResourceUsage]:
        """Get current resource usage for a sandbox.

        Args:
            sandbox_id: Sandbox identifier.
            sandbox_info: Sandbox information.

        Returns:
            Current resource usage or None if unavailable.
        """
        try:
            container = sandbox_info["container"]
            stats = container.stats(stream=False)

            # CPU usage calculation
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

            # Memory usage
            memory_mb = stats["memory_stats"]["usage"] // (1024 * 1024)

            # Network usage
            network_bytes_sent = stats["networks"].get("eth0", {}).get("tx_bytes", 0) if "networks" in stats else 0
            network_bytes_recv = stats["networks"].get("eth0", {}).get("rx_bytes", 0) if "networks" in stats else 0

            # Disk usage (approximation)
            disk_mb = memory_mb  # Simplified - could use container filesystem stats

            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                disk_mb=disk_mb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv
            )

        except Exception as e:
            logger.error(f"Failed to get resource usage for {sandbox_id}: {e}")
            return None

    async def _check_resource_limits(
        self,
        sandbox_id: str,
        sandbox_info: Dict[str, Any],
        usage: ResourceUsage
    ) -> None:
        """Check if resource limits are exceeded.

        Args:
            sandbox_id: Sandbox identifier.
            sandbox_info: Sandbox information.
            usage: Current resource usage.
        """
        limits = sandbox_info["limits"]
        alerts = []

        # Check CPU limit
        if usage.cpu_percent > limits.cpu_percent:
            alerts.append(ResourceAlert(
                timestamp=datetime.now(timezone.utc),
                sandbox_id=sandbox_id,
                trigger_type=TriggerType.CPU_LIMIT,
                current_value=usage.cpu_percent,
                limit_value=limits.cpu_percent,
                severity="warning" if usage.cpu_percent < limits.cpu_percent * 1.2 else "critical",
                message=f"CPU usage exceeded: {usage.cpu_percent:.1f}% > {limits.cpu_percent}%"
            ))

        # Check memory limit
        if usage.memory_mb > limits.memory_mb:
            alerts.append(ResourceAlert(
                timestamp=datetime.now(timezone.utc),
                sandbox_id=sandbox_id,
                trigger_type=TriggerType.MEMORY_LIMIT,
                current_value=usage.memory_mb,
                limit_value=limits.memory_mb,
                severity="warning" if usage.memory_mb < limits.memory_mb * 1.2 else "critical",
                message=f"Memory usage exceeded: {usage.memory_mb}MB > {limits.memory_mb}MB"
            ))

        # Check disk limit
        if usage.disk_mb > limits.disk_mb:
            alerts.append(ResourceAlert(
                timestamp=datetime.now(timezone.utc),
                sandbox_id=sandbox_id,
                trigger_type=TriggerType.DISK_LIMIT,
                current_value=usage.disk_mb,
                limit_value=limits.disk_mb,
                severity="warning" if usage.disk_mb < limits.disk_mb * 1.2 else "critical",
                message=f"Disk usage exceeded: {usage.disk_mb}MB > {limits.disk_mb}MB"
            ))

        # Process alerts
        for alert in alerts:
            await self._handle_alert(sandbox_id, sandbox_info, alert)

    async def _handle_alert(
        self,
        sandbox_id: str,
        sandbox_info: Dict[str, Any],
        alert: ResourceAlert
    ) -> None:
        """Handle a resource alert.

        Args:
            sandbox_id: Sandbox identifier.
            sandbox_info: Sandbox information.
            alert: Resource alert.
        """
        sandbox_info["alerts_count"] += 1

        # Log alert
        logger.warning(f"Resource alert for {sandbox_id}: {alert.message}")

        # Record in audit log
        if self.audit_logger:
            audit_log = AuditLog(
                timestamp=alert.timestamp,
                agent_id=sandbox_info["agent_id"],
                sandbox_id=sandbox_id,
                operation_type=OperationType.RESOURCE_EXCEEDED,
                status=OperationStatus.SUCCESS,
                details={
                    "alert": alert.message,
                    "trigger_type": alert.trigger_type.value,
                    "current_value": alert.current_value,
                    "limit_value": alert.limit_value,
                    "severity": alert.severity,
                    "total_alerts": sandbox_info["alerts_count"]
                },
                resource_usage=None  # Will be filled by the actual usage
            )
            await self.audit_logger.log_operation(audit_log)

        # Trigger killswitch for critical alerts
        if alert.severity == "critical":
            await self._trigger_killswitch(sandbox_id, alert)

    async def _trigger_killswitch(self, sandbox_id: str, alert: ResourceAlert) -> None:
        """Trigger killswitch for a sandbox.

        Args:
            sandbox_id: Sandbox identifier.
            alert: Resource alert that triggered the killswitch.
        """
        sandbox_info = self._monitored_sandboxes.get(sandbox_id)
        if not sandbox_info or sandbox_info["kill_triggered"]:
            return

        sandbox_info["kill_triggered"] = True
        logger.critical(f"Triggering killswitch for sandbox {sandbox_id}: {alert.message}")

        try:
            # Kill the container
            container = sandbox_info["container"]
            container.kill()
            logger.info(f"Killed container for sandbox {sandbox_id}")

            # Record killswitch event
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=datetime.now(timezone.utc),
                    agent_id=sandbox_info["agent_id"],
                    sandbox_id=sandbox_id,
                    operation_type=OperationType.KILL_SWITCH,
                    status=OperationStatus.SUCCESS,
                    details={
                        "reason": alert.message,
                        "trigger_type": alert.trigger_type.value,
                        "current_value": alert.current_value,
                        "limit_value": alert.limit_value,
                        "uptime_seconds": time.time() - sandbox_info["start_time"]
                    }
                )
                await self.audit_logger.log_operation(audit_log)

            # Call custom handlers
            for handler in self._killswitch_handlers:
                try:
                    handler(sandbox_id, alert)
                except Exception as e:
                    logger.error(f"Error in killswitch handler: {e}")

        except Exception as e:
            logger.error(f"Failed to kill sandbox {sandbox_id}: {e}")

            # Record failure
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=datetime.now(timezone.utc),
                    agent_id=sandbox_info["agent_id"],
                    sandbox_id=sandbox_id,
                    operation_type=OperationType.KILL_SWITCH,
                    status=OperationStatus.FAILURE,
                    details={"reason": alert.message, "error": str(e)},
                    error_message=str(e)
                )
                await self.audit_logger.log_operation(audit_log)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics.

        Returns:
            Monitoring statistics.
        """
        return {
            "is_running": self._is_running,
            "monitoring_interval": self._monitoring_interval,
            "monitored_sandboxes": len(self._monitored_sandboxes),
            "killswitch_handlers": len(self._killswitch_handlers),
            "sandbox_details": {
                sid: {
                    "agent_id": info["agent_id"],
                    "uptime_seconds": time.time() - info["start_time"],
                    "alerts_count": info["alerts_count"],
                    "kill_triggered": info["kill_triggered"],
                    "limits": {
                        "cpu_percent": info["limits"].cpu_percent,
                        "memory_mb": info["limits"].memory_mb,
                        "timeout_seconds": info["limits"].timeout_seconds
                    }
                }
                for sid, info in self._monitored_sandboxes.items()
            }
        }

    async def get_sandbox_metrics(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for a specific sandbox.

        Args:
            sandbox_id: Sandbox identifier.

        Returns:
            Current metrics or None if sandbox not found.
        """
        sandbox_info = self._monitored_sandboxes.get(sandbox_id)
        if not sandbox_info:
            return None

        usage = await self._get_resource_usage(sandbox_id, sandbox_info)
        
        return {
            "sandbox_id": sandbox_id,
            "agent_id": sandbox_info["agent_id"],
            "uptime_seconds": time.time() - sandbox_info["start_time"],
            "alerts_count": sandbox_info["alerts_count"],
            "kill_triggered": sandbox_info["kill_triggered"],
            "current_usage": asdict(usage) if usage else None,
            "limits": {
                "cpu_percent": sandbox_info["limits"].cpu_percent,
                "memory_mb": sandbox_info["limits"].memory_mb,
                "disk_mb": sandbox_info["limits"].disk_mb,
                "timeout_seconds": sandbox_info["limits"].timeout_seconds
            }
        }