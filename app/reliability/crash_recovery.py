"""
Crash Recovery System

Provides automatic state checkpointing and recovery mechanisms to ensure
the system can resume work after crashes.
"""

import asyncio
import json
import sqlite3
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from app.logger import logger


class CheckpointData(BaseModel):
    """Checkpoint data model"""
    timestamp: str
    checkpoint_id: str
    state: Dict[str, Any]
    metadata: Dict[str, Any]
    checksum: str


class CheckpointManager:
    """Manages checkpoints for state recovery"""

    def __init__(self, db_path: str = "./data/reliability.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize checkpoint database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    state TEXT NOT NULL,
                    metadata TEXT,
                    checksum TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_checkpoint_id TEXT,
                    last_recovered_id TEXT,
                    recovery_count INTEGER DEFAULT 0,
                    last_recovery_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            conn.close()
            logger.info("Checkpoint database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize checkpoint database: {e}")
            raise

    def save_checkpoint(
        self,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save a checkpoint"""
        import hashlib

        try:
            with self._lock:
                # Calculate checksum
                state_json = json.dumps(state, sort_keys=True, default=str)
                checksum = hashlib.sha256(state_json.encode()).hexdigest()

                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoints
                    (checkpoint_id, state, metadata, checksum)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        checkpoint_id,
                        state_json,
                        json.dumps(metadata or {}),
                        checksum,
                    ),
                )
                conn.commit()
                conn.close()
                logger.debug(f"Checkpoint saved: {checkpoint_id} (checksum: {checksum})")
                return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """Get a checkpoint"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, timestamp, state, metadata, checksum
                    FROM checkpoints
                    WHERE checkpoint_id = ?
                    """,
                    (checkpoint_id,),
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    return CheckpointData(
                        checkpoint_id=row[0],
                        timestamp=row[1],
                        state=json.loads(row[2]),
                        metadata=json.loads(row[3]),
                        checksum=row[4],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get checkpoint: {e}")
            return None

    def get_latest_checkpoint(self) -> Optional[CheckpointData]:
        """Get the latest checkpoint"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT checkpoint_id, timestamp, state, metadata, checksum
                    FROM checkpoints
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    return CheckpointData(
                        checkpoint_id=row[0],
                        timestamp=row[1],
                        state=json.loads(row[2]),
                        metadata=json.loads(row[3]),
                        checksum=row[4],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint: {e}")
            return None

    def delete_old_checkpoints(self, keep_count: int = 10) -> bool:
        """Delete old checkpoints, keeping only the latest ones"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM checkpoints
                    """
                )
                count = cursor.fetchone()[0]

                if count > keep_count:
                    cursor = conn.execute(
                        """
                        DELETE FROM checkpoints
                        WHERE id NOT IN (
                            SELECT id FROM checkpoints
                            ORDER BY created_at DESC
                            LIMIT ?
                        )
                        """,
                        (keep_count,),
                    )
                    conn.commit()
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} old checkpoints")

                conn.close()
                return True
        except Exception as e:
            logger.error(f"Failed to delete old checkpoints: {e}")
            return False


class CrashRecoveryManager:
    """Manages automatic crash recovery"""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self.checkpoint_manager = (
            checkpoint_manager or CheckpointManager()
        )
        self._checkpoint_interval = 30  # seconds
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._recovery_count = 0
        self._last_crash_time: Optional[datetime] = None

    async def start(self):
        """Start crash recovery manager"""
        self._is_running = True
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        logger.info("Crash recovery manager started")

    async def stop(self):
        """Stop crash recovery manager"""
        self._is_running = False
        if self._checkpoint_task:
            try:
                await asyncio.wait_for(self._checkpoint_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Checkpoint loop did not complete in time")
        logger.info("Crash recovery manager stopped")

    async def _checkpoint_loop(self):
        """Periodic checkpoint loop"""
        while self._is_running:
            try:
                await asyncio.sleep(self._checkpoint_interval)
                await self.create_checkpoint()
            except Exception as e:
                logger.error(f"Error in checkpoint loop: {e}")

    async def create_checkpoint(self, state: Optional[Dict[str, Any]] = None) -> bool:
        """Create a checkpoint"""
        try:
            checkpoint_id = f"checkpoint_{datetime.now().isoformat()}"
            checkpoint_state = state or {}
            metadata = {
                "recovery_count": self._recovery_count,
                "last_crash_time": self._last_crash_time.isoformat()
                if self._last_crash_time
                else None,
            }

            return self.checkpoint_manager.save_checkpoint(
                checkpoint_id, checkpoint_state, metadata
            )
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return False

    async def recover_from_crash(self) -> Optional[Dict[str, Any]]:
        """Recover system state from latest checkpoint"""
        try:
            checkpoint = self.checkpoint_manager.get_latest_checkpoint()
            if checkpoint:
                self._recovery_count += 1
                self._last_crash_time = datetime.now()
                logger.info(
                    f"Recovered from crash using checkpoint: {checkpoint.checkpoint_id}"
                )
                return checkpoint.state
            return None
        except Exception as e:
            logger.error(f"Failed to recover from crash: {e}")
            return None

    def get_recovery_status(self) -> Dict[str, Any]:
        """Get crash recovery status"""
        latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint()
        return {
            "is_running": self._is_running,
            "recovery_count": self._recovery_count,
            "last_crash_time": (
                self._last_crash_time.isoformat() if self._last_crash_time else None
            ),
            "latest_checkpoint": (
                {
                    "id": latest_checkpoint.checkpoint_id,
                    "timestamp": latest_checkpoint.timestamp,
                }
                if latest_checkpoint
                else None
            ),
        }

    async def handle_exception(self, exception: Exception, traceback_str: str = ""):
        """Handle an exception and prepare for recovery"""
        try:
            error_context = {
                "exception": str(exception),
                "exception_type": type(exception).__name__,
                "traceback": traceback_str or traceback.format_exc(),
                "timestamp": datetime.now().isoformat(),
            }

            await self.create_checkpoint(state={"error_context": error_context})
            self._recovery_count += 1
            self._last_crash_time = datetime.now()

            logger.error(f"Exception handled and checkpoint created: {exception}")
        except Exception as e:
            logger.error(f"Failed to handle exception: {e}")
