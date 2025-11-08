"""
Auto-Restart Service

Provides automatic restart capabilities for failed processes and
Windows Service integration.
"""

import asyncio
import json
import os
import platform
import subprocess
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from app.logger import logger


class RestartRecord(BaseModel):
    """Restart record model"""
    id: int
    timestamp: str
    reason: str
    exit_code: Optional[int]
    restart_count: int


class AutoRestartService:
    """Manages automatic process restart"""

    def __init__(self, db_path: str = "./data/reliability.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._max_restarts = 3
        self._restart_delay = 5  # seconds
        self._init_db()

    def _init_db(self):
        """Initialize restart tracking database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS restart_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT NOT NULL,
                    exit_code INTEGER,
                    restart_count INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            conn.close()
            logger.info("Auto-restart database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize auto-restart database: {e}")
            raise

    def record_restart(self, reason: str, exit_code: Optional[int] = None) -> bool:
        """Record a restart event"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    INSERT INTO restart_records (reason, exit_code, restart_count)
                    VALUES (?, ?, ?)
                    """,
                    (reason, exit_code, self._get_restart_count() + 1),
                )
                conn.commit()
                conn.close()
                logger.info(f"Restart recorded: {reason} (exit_code: {exit_code})")
                return True
        except Exception as e:
            logger.error(f"Failed to record restart: {e}")
            return False

    def _get_restart_count(self) -> int:
        """Get the current restart count"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM restart_records
                    WHERE timestamp > datetime('now', '-1 hour')
                    """
                )
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception as e:
            logger.error(f"Failed to get restart count: {e}")
            return 0

    def can_restart(self) -> bool:
        """Check if restart is allowed"""
        restart_count = self._get_restart_count()
        if restart_count >= self._max_restarts:
            logger.warning(
                f"Max restart limit ({self._max_restarts}) reached in the last hour"
            )
            return False
        return True

    async def restart_process(self, process_path: str, reason: str = "process_failure"):
        """Restart a process"""
        try:
            if not self.can_restart():
                logger.error("Cannot restart: max restart limit reached")
                return False

            self.record_restart(reason)

            await asyncio.sleep(self._restart_delay)
            logger.info(f"Restarting process: {process_path}")

            if platform.system() == "Windows":
                subprocess.Popen([process_path])
            else:
                subprocess.Popen([process_path])

            return True
        except Exception as e:
            logger.error(f"Failed to restart process: {e}")
            return False

    def get_restart_history(self, hours: int = 1) -> List[RestartRecord]:
        """Get restart history"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM restart_records
                    WHERE timestamp > datetime('now', ? || ' hours')
                    ORDER BY timestamp DESC
                    """,
                    (f"-{hours}",),
                )
                rows = cursor.fetchall()
                conn.close()

                return [
                    RestartRecord(
                        id=row["id"],
                        timestamp=row["timestamp"],
                        reason=row["reason"],
                        exit_code=row["exit_code"],
                        restart_count=row["restart_count"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get restart history: {e}")
            return []

    def get_restart_status(self) -> Dict[str, Any]:
        """Get restart status"""
        restart_count = self._get_restart_count()
        can_restart = self.can_restart()
        history = self.get_restart_history()

        return {
            "restart_count_1h": restart_count,
            "max_restarts_per_hour": self._max_restarts,
            "can_restart": can_restart,
            "restart_delay": self._restart_delay,
            "recent_restarts": [
                {
                    "timestamp": r.timestamp,
                    "reason": r.reason,
                    "exit_code": r.exit_code,
                }
                for r in history[:5]
            ],
        }


class ServiceManager:
    """Windows Service management"""

    SERVICE_NAME = "ixlinx-agent"

    @staticmethod
    def install_service(script_path: str) -> bool:
        """Install as Windows Service"""
        if platform.system() != "Windows":
            logger.error("Service installation only supported on Windows")
            return False

        try:
            import win32serviceutil
            import win32service
            import win32api

            # Create service class path
            service_module = "app.service_wrapper"

            # Install service
            win32serviceutil.InstallService(
                pythonClassString=service_module + ".OpenmanuService",
                serviceName=ServiceManager.SERVICE_NAME,
                displayName="OpenManus Service",
                startType=win32service.SERVICE_AUTO_START,
            )
            logger.info("Service installed successfully")
            return True
        except ImportError:
            logger.error(
                "pywin32 not installed. Install with: pip install pywin32"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            return False

    @staticmethod
    def start_service() -> bool:
        """Start Windows Service"""
        if platform.system() != "Windows":
            logger.error("Service management only supported on Windows")
            return False

        try:
            import win32serviceutil

            win32serviceutil.StartService(ServiceManager.SERVICE_NAME)
            logger.info("Service started")
            return True
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False

    @staticmethod
    def stop_service() -> bool:
        """Stop Windows Service"""
        if platform.system() != "Windows":
            logger.error("Service management only supported on Windows")
            return False

        try:
            import win32serviceutil

            win32serviceutil.StopService(ServiceManager.SERVICE_NAME)
            logger.info("Service stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False

    @staticmethod
    def remove_service() -> bool:
        """Remove Windows Service"""
        if platform.system() != "Windows":
            logger.error("Service management only supported on Windows")
            return False

        try:
            import win32serviceutil

            win32serviceutil.RemoveService(ServiceManager.SERVICE_NAME)
            logger.info("Service removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove service: {e}")
            return False

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """Get service status"""
        if platform.system() != "Windows":
            return {"status": "not_supported", "platform": platform.system()}

        try:
            import win32serviceutil

            status = win32serviceutil.QueryServiceStatus(ServiceManager.SERVICE_NAME)
            return {
                "service_name": ServiceManager.SERVICE_NAME,
                "status": "running" if status[1] == 4 else "stopped",
                "status_code": status[1],
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"status": "error", "error": str(e)}
