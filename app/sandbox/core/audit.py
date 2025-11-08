"""
Audit logging system for sandbox operations.

This module provides comprehensive audit logging for all sandbox operations,
including resource usage, command execution, and security events.
"""

import asyncio
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

from app.logger import logger


class OperationType(Enum):
    """Types of sandbox operations."""
    SANDBOX_CREATE = "sandbox_create"
    SANDBOX_DELETE = "sandbox_delete"
    COMMAND_EXECUTE = "command_execute"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    RESOURCE_EXCEEDED = "resource_exceeded"
    GUARDIAN_APPROVAL = "guardian_approval"
    GUARDIAN_DENIAL = "guardian_denial"
    KILL_SWITCH = "kill_switch"


class OperationStatus(Enum):
    """Operation status."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DENIED = "denied"
    CANCELLED = "cancelled"


@dataclass
class ResourceUsage:
    """Resource usage metrics."""
    cpu_percent: float
    memory_mb: int
    disk_mb: int
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0


@dataclass
class AuditLog:
    """Audit log entry."""
    timestamp: datetime
    agent_id: str
    sandbox_id: str
    operation_type: OperationType
    status: OperationStatus
    details: Dict[str, Any]
    resource_usage: Optional[ResourceUsage] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogger:
    """Audit logger for sandbox operations.

    Provides persistent storage and querying of audit logs using SQLite.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            db_path: Path to SQLite database file. Defaults to workspace/audit.db
        """
        if db_path is None:
            db_path = Path("workspace/audit.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create audit_logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT NOT NULL,
                    resource_usage TEXT,
                    duration_ms INTEGER,
                    error_message TEXT,
                    metadata TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON audit_logs(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sandbox_id ON audit_logs(sandbox_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_type ON audit_logs(operation_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON audit_logs(status)")

            conn.commit()
            conn.close()
            logger.info(f"Initialized audit database at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
            raise

    async def log_operation(self, log_entry: AuditLog) -> None:
        """Log an operation to the database.

        Args:
            log_entry: Audit log entry to record.
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Convert dataclass to dict and serialize complex fields
                details_json = json.dumps(log_entry.details)
                resource_usage_json = json.dumps(asdict(log_entry.resource_usage)) if log_entry.resource_usage else None
                metadata_json = json.dumps(log_entry.metadata) if log_entry.metadata else None

                cursor.execute("""
                    INSERT INTO audit_logs (
                        timestamp, agent_id, sandbox_id, operation_type, status,
                        details, resource_usage, duration_ms, error_message, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.timestamp if isinstance(log_entry.timestamp, str) else log_entry.timestamp.isoformat(),
                    log_entry.agent_id,
                    log_entry.sandbox_id,
                    log_entry.operation_type.value,
                    log_entry.status.value,
                    details_json,
                    resource_usage_json,
                    log_entry.duration_ms,
                    log_entry.error_message,
                    metadata_json
                ))

                conn.commit()
                conn.close()

            except Exception as e:
                logger.error(f"Failed to log audit entry: {e}")

    async def get_logs(
        self,
        agent_id: Optional[str] = None,
        sandbox_id: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        status: Optional[OperationStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Query audit logs with filters.

        Args:
            agent_id: Filter by agent ID.
            sandbox_id: Filter by sandbox ID.
            operation_type: Filter by operation type.
            status: Filter by status.
            start_time: Filter by start time.
            end_time: Filter by end time.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of audit log entries.
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Build query with filters
                query = "SELECT * FROM audit_logs WHERE 1=1"
                params = []

                if agent_id:
                    query += " AND agent_id = ?"
                    params.append(agent_id)

                if sandbox_id:
                    query += " AND sandbox_id = ?"
                    params.append(sandbox_id)

                if operation_type:
                    query += " AND operation_type = ?"
                    params.append(operation_type.value)

                if status:
                    query += " AND status = ?"
                    params.append(status.value)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())

                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()

                # Convert rows to AuditLog objects
                logs = []
                for row in rows:
                    log = self._row_to_audit_log(row)
                    logs.append(log)

                return logs

            except Exception as e:
                logger.error(f"Failed to query audit logs: {e}")
                return []

    def _row_to_audit_log(self, row: sqlite3.Row) -> AuditLog:
        """Convert database row to AuditLog object."""
        return AuditLog(
            timestamp=datetime.fromisoformat(row[1]),
            agent_id=row[2],
            sandbox_id=row[3],
            operation_type=OperationType(row[4]),
            status=OperationStatus(row[5]),
            details=json.loads(row[6]),
            resource_usage=ResourceUsage(**json.loads(row[7])) if row[7] else None,
            duration_ms=row[8],
            error_message=row[9],
            metadata=json.loads(row[10]) if row[10] else None
        )

    async def get_agent_summary(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for an agent.

        Args:
            agent_id: Agent ID to summarize.
            days: Number of days to look back.

        Returns:
            Summary statistics.
        """
        start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = start_time.replace(day=start_time.day - days)

        logs = await self.get_logs(
            agent_id=agent_id,
            start_time=start_time,
            limit=10000
        )

        summary = {
            "agent_id": agent_id,
            "period_days": days,
            "total_operations": len(logs),
            "operations_by_type": {},
            "operations_by_status": {},
            "total_duration_ms": 0,
            "error_count": 0,
            "resource_usage_summary": {
                "avg_cpu_percent": 0,
                "avg_memory_mb": 0,
                "max_memory_mb": 0
            }
        }

        cpu_values = []
        memory_values = []

        for log in logs:
            # Count by type
            op_type = log.operation_type.value
            summary["operations_by_type"][op_type] = summary["operations_by_type"].get(op_type, 0) + 1

            # Count by status
            status = log.status.value
            summary["operations_by_status"][status] = summary["operations_by_status"].get(status, 0) + 1

            # Duration
            if log.duration_ms:
                summary["total_duration_ms"] += log.duration_ms

            # Errors
            if log.status in [OperationStatus.FAILURE, OperationStatus.TIMEOUT, OperationStatus.DENIED]:
                summary["error_count"] += 1

            # Resource usage
            if log.resource_usage:
                cpu_values.append(log.resource_usage.cpu_percent)
                memory_values.append(log.resource_usage.memory_mb)
                summary["resource_usage_summary"]["max_memory_mb"] = max(
                    summary["resource_usage_summary"]["max_memory_mb"],
                    log.resource_usage.memory_mb
                )

        # Calculate averages
        if cpu_values:
            summary["resource_usage_summary"]["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
        if memory_values:
            summary["resource_usage_summary"]["avg_memory_mb"] = sum(memory_values) / len(memory_values)

        return summary

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up old audit logs.

        Args:
            days_to_keep: Number of days to keep logs.

        Returns:
            Number of deleted records.
        """
        cutoff_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_time = cutoff_time.replace(day=cutoff_time.day - days_to_keep)

        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("DELETE FROM audit_logs WHERE timestamp < ?", (cutoff_time.isoformat(),))
                deleted_count = cursor.rowcount

                conn.commit()
                conn.close()

                logger.info(f"Cleaned up {deleted_count} old audit log entries")
                return deleted_count

            except Exception as e:
                logger.error(f"Failed to cleanup old logs: {e}")
                return 0

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Database statistics.
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Total records
                cursor.execute("SELECT COUNT(*) FROM audit_logs")
                total_records = cursor.fetchone()[0]

                # Records by operation type
                cursor.execute("""
                    SELECT operation_type, COUNT(*) 
                    FROM audit_logs 
                    GROUP BY operation_type
                """)
                operation_counts = dict(cursor.fetchall())

                # Records by status
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM audit_logs 
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())

                # Database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]

                conn.close()

                return {
                    "total_records": total_records,
                    "database_size_bytes": db_size,
                    "records_by_operation": operation_counts,
                    "records_by_status": status_counts,
                    "database_path": str(self.db_path)
                }

            except Exception as e:
                logger.error(f"Failed to get database stats: {e}")
                return {}


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger