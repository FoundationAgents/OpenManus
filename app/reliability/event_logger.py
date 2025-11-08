"""
Event Logging System

Provides comprehensive structured logging for operations, crashes, and diagnostics.
"""

import asyncio
import gzip
import json
import logging
import platform
import sqlite3
import threading
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from app.logger import logger as base_logger


class LogEvent(BaseModel):
    """Structured log event model"""
    timestamp: str
    level: str
    component: str
    event_type: str
    message: str
    details: Dict[str, Any]
    user: Optional[str] = None
    session_id: Optional[str] = None


class DiagnosticsBundle(BaseModel):
    """Diagnostics bundle model"""
    bundle_name: str
    created_at: str
    bundle_path: str
    logs_included: int
    config_included: bool
    system_info_included: bool


class EventLogger:
    """Comprehensive event logging system"""

    def __init__(self, db_path: str = "./data/reliability.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = self._generate_session_id()
        self._init_db()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        from uuid import uuid4
        return str(uuid4())

    def _init_db(self):
        """Initialize event logging database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    user TEXT,
                    session_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create index for faster queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_level
                ON events(level)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_component
                ON events(component)
                """
            )

            conn.commit()
            conn.close()
            base_logger.info("Event logger database initialized")
        except Exception as e:
            base_logger.error(f"Failed to initialize event logger: {e}")

    async def log_event(
        self,
        level: str,
        component: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
    ) -> bool:
        """Log an event"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    INSERT INTO events
                    (level, component, event_type, message, details, user, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        level,
                        component,
                        event_type,
                        message,
                        json.dumps(details or {}),
                        user,
                        self._session_id,
                    ),
                )
                conn.commit()
                conn.close()

                # Also write to file log
                await self._write_file_log(
                    level, component, event_type, message, details
                )
                return True

        except Exception as e:
            base_logger.error(f"Failed to log event: {e}")
            return False

    async def _write_file_log(
        self,
        level: str,
        component: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Write event to file log"""
        try:
            log_file = self.logs_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"

            event = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "component": component,
                "event_type": event_type,
                "message": message,
                "details": details or {},
                "session_id": self._session_id,
            }

            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")

        except Exception as e:
            base_logger.error(f"Failed to write file log: {e}")

    async def get_events(
        self,
        component: Optional[str] = None,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000,
    ) -> List[LogEvent]:
        """Get events from history"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT timestamp, level, component, event_type, message, details, user, session_id
                    FROM events
                    WHERE timestamp > datetime('now', ? || ' hours')
                """
                params = [f"-{hours}"]

                if component:
                    query += " AND component = ?"
                    params.append(component)

                if level:
                    query += " AND level = ?"
                    params.append(level)

                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                conn.close()

                return [
                    LogEvent(
                        timestamp=row["timestamp"],
                        level=row["level"],
                        component=row["component"],
                        event_type=row["event_type"],
                        message=row["message"],
                        details=json.loads(row["details"] or "{}"),
                        user=row["user"],
                        session_id=row["session_id"],
                    )
                    for row in rows
                ]

        except Exception as e:
            base_logger.error(f"Failed to get events: {e}")
            return []

    async def cleanup_old_logs(self, keep_days: int = 90) -> int:
        """Delete old log entries and files"""
        try:
            deleted_files = 0
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    DELETE FROM events
                    WHERE timestamp < datetime('now', ? || ' days')
                    """,
                    (f"-{keep_days}",),
                )
                conn.commit()
                conn.close()

            # Delete old log files
            cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime("%Y%m%d")
            for log_file in self.logs_dir.glob("events_*.jsonl"):
                file_date = log_file.stem.split("_")[1]
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_files += 1

            base_logger.info(f"Deleted {deleted_files} old log files")
            return deleted_files

        except Exception as e:
            base_logger.error(f"Failed to cleanup old logs: {e}")
            return 0

    async def create_diagnostics_bundle(self, include_config: bool = True) -> Optional[DiagnosticsBundle]:
        """Create a diagnostics bundle"""
        try:
            bundle_name = f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            bundle_path = Path("./diagnostics") / f"{bundle_name}.zip"
            bundle_path.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add recent logs
                logs_count = 0
                for log_file in sorted(self.logs_dir.glob("events_*.jsonl"))[-7:]:
                    zf.write(log_file, arcname=f"logs/{log_file.name}")
                    logs_count += 1

                # Add system info
                system_info = self._get_system_info()
                zf.writestr(
                    "system_info.json",
                    json.dumps(system_info, indent=2)
                )

                # Add config if requested
                if include_config:
                    config_path = Path("./config")
                    if config_path.exists():
                        for config_file in config_path.rglob("*.toml"):
                            zf.write(config_file, arcname=f"config/{config_file.name}")

                # Add health summary
                from app.reliability.health_monitor import HealthMonitor
                try:
                    health_monitor = HealthMonitor()
                    health_summary = health_monitor.get_health_summary()
                    zf.writestr(
                        "health_summary.json",
                        json.dumps(health_summary, indent=2)
                    )
                except Exception:
                    pass

            bundle_info = DiagnosticsBundle(
                bundle_name=bundle_name,
                created_at=datetime.now().isoformat(),
                bundle_path=str(bundle_path),
                logs_included=logs_count,
                config_included=include_config,
                system_info_included=True,
            )

            base_logger.info(f"Diagnostics bundle created: {bundle_path}")
            return bundle_info

        except Exception as e:
            base_logger.error(f"Failed to create diagnostics bundle: {e}")
            return None

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import psutil
        return {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total_gb": round(psutil.disk_usage("/").total / (1024 ** 3), 2),
                "free_gb": round(psutil.disk_usage("/").free / (1024 ** 3), 2),
                "percent": psutil.disk_usage("/").percent,
            },
        }

    def get_session_id(self) -> str:
        """Get current session ID"""
        return self._session_id

    async def search_logs(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search logs by message content"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT timestamp, level, component, event_type, message, details
                    FROM events
                    WHERE message LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit),
                )
                rows = cursor.fetchall()
                conn.close()

                return [
                    {
                        "timestamp": row[0],
                        "level": row[1],
                        "component": row[2],
                        "event_type": row[3],
                        "message": row[4],
                        "details": json.loads(row[5] or "{}"),
                    }
                    for row in rows
                ]

        except Exception as e:
            base_logger.error(f"Failed to search logs: {e}")
            return []
