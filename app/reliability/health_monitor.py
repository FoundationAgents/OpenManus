"""
Health Monitoring System

Provides continuous health checks for LLM, database, disk space, memory,
and other critical components.
"""

import asyncio
import os
import psutil
import sqlite3
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from app.logger import logger


class HealthStatus(str, Enum):
    """Health status enumeration"""
    OK = "✓"
    WARNING = "⚠"
    CRITICAL = "✗"


class ComponentHealth(BaseModel):
    """Component health model"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: str


class HealthMonitor:
    """Monitors system and component health"""

    def __init__(self, db_path: str = "./data/reliability.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._health_history: Dict[str, List[ComponentHealth]] = {}
        self._max_history = 100
        self._thresholds = {
            "disk_warning_gb": 2.0,
            "disk_critical_gb": 0.5,
            "memory_warning_percent": 80,
            "memory_critical_percent": 95,
            "llm_timeout_seconds": 30,
            "db_timeout_seconds": 5,
        }
        self._init_db()

    def _init_db(self):
        """Initialize health history database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            conn.close()
            logger.info("Health history database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize health history database: {e}")

    def _record_health(self, health: ComponentHealth):
        """Record health check result"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                import json
                conn.execute(
                    """
                    INSERT INTO health_history (component_name, status, message, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (health.name, health.status.value, health.message, json.dumps(health.details)),
                )
                conn.commit()
                conn.close()

                # Store in memory history
                if health.name not in self._health_history:
                    self._health_history[health.name] = []

                self._health_history[health.name].append(health)
                if len(self._health_history[health.name]) > self._max_history:
                    self._health_history[health.name] = self._health_history[
                        health.name
                    ][-self._max_history :]
        except Exception as e:
            logger.error(f"Failed to record health: {e}")

    async def check_llm_health(self) -> ComponentHealth:
        """Check LLM service health"""
        try:
            from app.llm.client import openai_client

            # Attempt a simple API call with timeout
            try:
                # Create a timeout task
                async def health_check():
                    result = await openai_client.get_health_status()
                    return result

                result = await asyncio.wait_for(
                    health_check(), timeout=self._thresholds["llm_timeout_seconds"]
                )

                if result.get("status") == "ok":
                    health = ComponentHealth(
                        name="llm",
                        status=HealthStatus.OK,
                        message="LLM service is responsive",
                        details=result,
                        timestamp=datetime.now().isoformat(),
                    )
                else:
                    health = ComponentHealth(
                        name="llm",
                        status=HealthStatus.WARNING,
                        message="LLM service is slow or degraded",
                        details=result,
                        timestamp=datetime.now().isoformat(),
                    )
            except asyncio.TimeoutError:
                health = ComponentHealth(
                    name="llm",
                    status=HealthStatus.CRITICAL,
                    message=f"LLM service timeout (>{self._thresholds['llm_timeout_seconds']}s)",
                    details={"timeout": self._thresholds["llm_timeout_seconds"]},
                    timestamp=datetime.now().isoformat(),
                )

            self._record_health(health)
            return health
        except Exception as e:
            health = ComponentHealth(
                name="llm",
                status=HealthStatus.CRITICAL,
                message=f"LLM health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now().isoformat(),
            )
            self._record_health(health)
            return health

    async def check_database_health(self) -> ComponentHealth:
        """Check database health"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=self._thresholds["db_timeout_seconds"])
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()

            if result:
                health = ComponentHealth(
                    name="database",
                    status=HealthStatus.OK,
                    message="Database is responding normally",
                    details={"db_path": self.db_path},
                    timestamp=datetime.now().isoformat(),
                )
            else:
                health = ComponentHealth(
                    name="database",
                    status=HealthStatus.CRITICAL,
                    message="Database health check returned no result",
                    details={"db_path": self.db_path},
                    timestamp=datetime.now().isoformat(),
                )
        except Exception as e:
            health = ComponentHealth(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now().isoformat(),
            )

        self._record_health(health)
        return health

    async def check_disk_health(self) -> ComponentHealth:
        """Check disk space health"""
        try:
            # Get disk usage
            disk_usage = psutil.disk_usage("/")
            free_gb = disk_usage.free / (1024 ** 3)

            if free_gb < self._thresholds["disk_critical_gb"]:
                status = HealthStatus.CRITICAL
                message = f"Critical: Only {free_gb:.2f}GB disk space remaining"
            elif free_gb < self._thresholds["disk_warning_gb"]:
                status = HealthStatus.WARNING
                message = f"Warning: Only {free_gb:.2f}GB disk space remaining"
            else:
                status = HealthStatus.OK
                message = f"Disk space is healthy ({free_gb:.2f}GB free)"

            health = ComponentHealth(
                name="disk",
                status=status,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(disk_usage.total / (1024 ** 3), 2),
                    "used_percent": disk_usage.percent,
                },
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            health = ComponentHealth(
                name="disk",
                status=HealthStatus.WARNING,
                message=f"Disk health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now().isoformat(),
            )

        self._record_health(health)
        return health

    async def check_memory_health(self) -> ComponentHealth:
        """Check memory health"""
        try:
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent >= self._thresholds["memory_critical_percent"]:
                status = HealthStatus.CRITICAL
                message = f"Critical: Memory usage at {memory_percent}%"
            elif memory_percent >= self._thresholds["memory_warning_percent"]:
                status = HealthStatus.WARNING
                message = f"Warning: Memory usage at {memory_percent}%"
            else:
                status = HealthStatus.OK
                message = f"Memory usage is healthy ({memory_percent}%)"

            health = ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "used_gb": round(memory.used / (1024 ** 3), 2),
                    "available_gb": round(memory.available / (1024 ** 3), 2),
                    "percent": memory_percent,
                },
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            health = ComponentHealth(
                name="memory",
                status=HealthStatus.WARNING,
                message=f"Memory health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now().isoformat(),
            )

        self._record_health(health)
        return health

    async def check_all_health(self) -> Dict[str, ComponentHealth]:
        """Check health of all components"""
        results = {}

        # Run all health checks concurrently
        tasks = [
            self.check_llm_health(),
            self.check_database_health(),
            self.check_disk_health(),
            self.check_memory_health(),
        ]

        health_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in health_results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
            else:
                results[result.name] = result

        return results

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT component_name, status, message, timestamp
                    FROM health_history
                    WHERE (component_name, timestamp) IN (
                        SELECT component_name, MAX(timestamp)
                        FROM health_history
                        GROUP BY component_name
                    )
                    ORDER BY component_name
                    """
                )
                rows = cursor.fetchall()
                conn.close()

                components = {}
                overall_status = HealthStatus.OK

                for row in rows:
                    status = HealthStatus(row["status"])
                    components[row["component_name"]] = {
                        "status": status.value,
                        "message": row["message"],
                        "timestamp": row["timestamp"],
                    }

                    # Update overall status
                    if status == HealthStatus.CRITICAL:
                        overall_status = HealthStatus.CRITICAL
                    elif status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                        overall_status = HealthStatus.WARNING

                return {
                    "overall_status": overall_status.value,
                    "timestamp": datetime.now().isoformat(),
                    "components": components,
                }
        except Exception as e:
            logger.error(f"Failed to get health summary: {e}")
            return {
                "overall_status": HealthStatus.CRITICAL.value,
                "error": str(e),
                "components": {},
            }

    def format_health_report(self) -> str:
        """Format health status as human-readable report"""
        summary = self.get_health_summary()
        lines = [
            f"System Health Report - {summary.get('timestamp')}",
            f"Overall Status: {summary.get('overall_status')}",
            "",
        ]

        for component, details in summary.get("components", {}).items():
            lines.append(
                f"  {component}: {details['status']} - {details['message']}"
            )

        return "\n".join(lines)
