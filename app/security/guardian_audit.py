"""
Guardian Audit Trail for logging and querying security decisions.

Maintains detailed audit logs of all validation decisions with:
- Command information
- Risk assessment results
- User approval decisions
- Execution outcomes
- Timestamps and source information
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from app.logger import logger
from app.config import config

if TYPE_CHECKING:
    from .guardian_agent import ValidationRequest, ValidationDecision


class GuardianAudit:
    """
    Audit trail manager for Guardian validation decisions.

    Stores and queries validation decisions in SQLite database.
    """

    def __init__(self, db_path: str = "./data/guardian.db"):
        """
        Initialize Guardian Audit.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._initialize_db()

    def _initialize_db(self):
        """Initialize database and create tables."""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guardian_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    command TEXT NOT NULL,
                    source TEXT NOT NULL,
                    agent_id TEXT,
                    user_id INTEGER,
                    tool_name TEXT,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    approval_status TEXT NOT NULL,
                    approved BOOLEAN NOT NULL,
                    reason TEXT,
                    required_permissions TEXT,
                    blocking_factors TEXT,
                    execution_result TEXT,
                    working_dir TEXT,
                    metadata TEXT,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_approval_status (approval_status),
                    INDEX idx_risk_level (risk_level)
                )
            """)

            # Create statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guardian_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_validations INTEGER DEFAULT 0,
                    approved_count INTEGER DEFAULT 0,
                    rejected_count INTEGER DEFAULT 0,
                    pending_count INTEGER DEFAULT 0,
                    timeout_count INTEGER DEFAULT 0,
                    avg_risk_score REAL DEFAULT 0,
                    UNIQUE(timestamp)
                )
            """)

            conn.commit()
            conn.close()

            self._initialized = True
            logger.info(f"Guardian audit database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing Guardian audit database: {e}")

    async def log_decision(
        self,
        request: "ValidationRequest",  # noqa: F821
        decision: "ValidationDecision"  # noqa: F821
    ) -> int:
        """
        Log a validation decision.

        Args:
            request: The validation request
            decision: The validation decision

        Returns:
            Log entry ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO guardian_audit_log (
                    timestamp, command, source, agent_id, user_id, tool_name,
                    risk_level, risk_score, approval_status, approved, reason,
                    required_permissions, blocking_factors, working_dir, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                request.command,
                request.source.value,
                request.agent_id,
                request.user_id,
                request.tool_name,
                decision.risk_level.value,
                decision.risk_score,
                decision.approval_status.value,
                decision.approved,
                decision.reason,
                json.dumps(decision.required_permissions),
                json.dumps(decision.blocking_factors),
                request.working_dir,
                json.dumps(request.metadata or {})
            ))

            conn.commit()
            log_id = cursor.lastrowid
            conn.close()

            logger.debug(f"Guardian decision logged: id={log_id}, command={request.command}, approved={decision.approved}")
            return log_id
        except Exception as e:
            logger.error(f"Error logging Guardian decision: {e}")
            return -1

    async def log_execution_result(
        self,
        log_id: int,
        success: bool,
        exit_code: int,
        stdout: str = "",
        stderr: str = ""
    ):
        """
        Log the execution result of an approved command.

        Args:
            log_id: The audit log ID
            success: Whether execution was successful
            exit_code: Process exit code
            stdout: Standard output
            stderr: Standard error
        """
        try:
            result = {
                "success": success,
                "exit_code": exit_code,
                "stdout_length": len(stdout),
                "stderr_length": len(stderr),
                "timestamp": datetime.now().isoformat()
            }

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE guardian_audit_log
                SET execution_result = ?
                WHERE id = ?
            """, (json.dumps(result), log_id))

            conn.commit()
            conn.close()

            logger.debug(f"Execution result logged: id={log_id}, success={success}, exit_code={exit_code}")
        except Exception as e:
            logger.error(f"Error logging execution result: {e}")

    async def query_log(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query audit log.

        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            filters: Optional filters (command, risk_level, approval_status, user_id, etc.)

        Returns:
            List of audit log records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM guardian_audit_log WHERE 1=1"
            params = []

            # Apply filters
            if filters:
                if "command" in filters:
                    query += " AND command LIKE ?"
                    params.append(f"%{filters['command']}%")

                if "risk_level" in filters:
                    query += " AND risk_level = ?"
                    params.append(filters["risk_level"])

                if "approval_status" in filters:
                    query += " AND approval_status = ?"
                    params.append(filters["approval_status"])

                if "user_id" in filters:
                    query += " AND user_id = ?"
                    params.append(filters["user_id"])

                if "approved" in filters:
                    query += " AND approved = ?"
                    params.append(1 if filters["approved"] else 0)

                if "date_from" in filters:
                    query += " AND timestamp >= ?"
                    params.append(filters["date_from"])

                if "date_to" in filters:
                    query += " AND timestamp <= ?"
                    params.append(filters["date_to"])

            # Order and paginate
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                record = dict(row)
                # Parse JSON fields
                try:
                    record["required_permissions"] = json.loads(record.get("required_permissions", "[]"))
                except:
                    record["required_permissions"] = []

                try:
                    record["blocking_factors"] = json.loads(record.get("blocking_factors", "[]"))
                except:
                    record["blocking_factors"] = []

                try:
                    record["execution_result"] = json.loads(record.get("execution_result", "{}"))
                except:
                    record["execution_result"] = {}

                try:
                    record["metadata"] = json.loads(record.get("metadata", "{}"))
                except:
                    record["metadata"] = {}

                records.append(record)

            conn.close()
            return records
        except Exception as e:
            logger.error(f"Error querying Guardian audit log: {e}")
            return []

    async def get_statistics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            cursor.execute("""
                SELECT
                    COUNT(*) as total_validations,
                    SUM(CASE WHEN approved = 1 THEN 1 ELSE 0 END) as approved_count,
                    SUM(CASE WHEN approved = 0 THEN 1 ELSE 0 END) as rejected_count,
                    SUM(CASE WHEN approval_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                    SUM(CASE WHEN approval_status = 'timeout' THEN 1 ELSE 0 END) as timeout_count,
                    AVG(risk_score) as avg_risk_score,
                    MIN(risk_score) as min_risk_score,
                    MAX(risk_score) as max_risk_score
                FROM guardian_audit_log
                WHERE timestamp >= ?
            """, (cutoff_date,))

            row = cursor.fetchone()

            # Count by risk level
            cursor.execute("""
                SELECT risk_level, COUNT(*) as count
                FROM guardian_audit_log
                WHERE timestamp >= ?
                GROUP BY risk_level
            """, (cutoff_date,))

            risk_level_counts = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            return {
                "period_days": days,
                "total_validations": row[0] or 0,
                "approved_count": row[1] or 0,
                "rejected_count": row[2] or 0,
                "pending_count": row[3] or 0,
                "timeout_count": row[4] or 0,
                "approval_rate": (row[1] or 0) / (row[0] or 1) * 100,
                "avg_risk_score": row[5] or 0,
                "min_risk_score": row[6] or 0,
                "max_risk_score": row[7] or 0,
                "risk_level_breakdown": risk_level_counts,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting Guardian statistics: {e}")
            return {}

    async def export_log(
        self,
        filepath: str,
        filters: Optional[Dict[str, Any]] = None
    ):
        """
        Export audit log to JSON file.

        Args:
            filepath: Path to export to
            filters: Optional filters
        """
        try:
            records = await self.query_log(limit=10000, filters=filters)

            with open(filepath, 'w') as f:
                json.dump({
                    "export_timestamp": datetime.now().isoformat(),
                    "total_records": len(records),
                    "records": records
                }, f, indent=2, default=str)

            logger.info(f"Guardian audit log exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting Guardian audit log: {e}")

    async def cleanup_old_records(
        self,
        days: int = 90
    ):
        """
        Clean up old audit records.

        Args:
            days: Delete records older than N days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            cursor.execute("""
                DELETE FROM guardian_audit_log
                WHERE timestamp < ?
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(f"Deleted {deleted_count} old Guardian audit records (older than {days} days)")
        except Exception as e:
            logger.error(f"Error cleaning up Guardian audit records: {e}")
