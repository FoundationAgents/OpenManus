"""
Data Integrity System

Ensures data consistency and durability through checksums, WAL mode,
regular integrity checks, and automated backups.
"""

import asyncio
import hashlib
import json
import sqlite3
import threading
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

from pydantic import BaseModel

from app.logger import logger


class BackupInfo(BaseModel):
    """Backup information model"""
    backup_name: str
    backup_type: str  # "full", "incremental", "archive"
    source_path: str
    destination_path: str
    size_bytes: int
    checksum: str
    timestamp: str


class DataIntegrityManager:
    """Manages data integrity and backups"""

    def __init__(self, db_path: str = "./data/reliability.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.data_dir = Path("./data")
        self.backup_dir = Path("./backups")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._optimize_database()

    def _init_db(self):
        """Initialize integrity tracking database"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Enable WAL mode for better durability
            conn.execute("PRAGMA journal_mode=WAL")

            # Configure for reliability
            conn.execute("PRAGMA synchronous=NORMAL")  # Fast but safe
            conn.execute("PRAGMA cache_size=10000")  # Better performance
            conn.execute("PRAGMA temp_store=MEMORY")  # Faster temp operations

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS integrity_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    checksum TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'ok'
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    size_bytes INTEGER,
                    checksum TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    restored BOOLEAN DEFAULT 0
                )
                """
            )

            conn.commit()
            conn.close()
            logger.info("Data integrity database initialized with WAL mode")
        except Exception as e:
            logger.error(f"Failed to initialize integrity database: {e}")
            raise

    def _optimize_database(self):
        """Optimize database for reliability"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                # Run VACUUM to defragment
                conn.execute("VACUUM")

                # Analyze to optimize query plans
                conn.execute("ANALYZE")

                # Build index statistics
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
                for (index_name,) in cursor.fetchall():
                    conn.execute(f"ANALYZE {index_name}")

                conn.commit()
                conn.close()
                logger.debug("Database optimized")
        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum: {e}")
            return ""

    async def check_integrity(self, file_path: str) -> Tuple[bool, str]:
        """Check file integrity"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                # Get last recorded checksum
                cursor = conn.execute(
                    """
                    SELECT checksum FROM integrity_checks
                    WHERE file_path = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (file_path,),
                )
                row = cursor.fetchone()
                conn.close()

                if not row:
                    return True, "No previous checksum record"

                last_checksum = row[0]

                # Calculate current checksum
                current_checksum = self._calculate_checksum(file_path)

                if last_checksum == current_checksum:
                    return True, "Integrity OK"
                else:
                    return False, "Checksum mismatch - file may be corrupted"

        except Exception as e:
            logger.error(f"Failed to check integrity: {e}")
            return False, f"Integrity check failed: {e}"

    async def record_checksum(self, file_path: str) -> bool:
        """Record file checksum"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"File not found: {file_path}")
                return False

            checksum = self._calculate_checksum(file_path)
            file_size = file_path_obj.stat().st_size

            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    INSERT INTO integrity_checks (file_path, file_size, checksum, status)
                    VALUES (?, ?, ?, 'ok')
                    """,
                    (file_path, file_size, checksum),
                )
                conn.commit()
                conn.close()

            logger.debug(f"Recorded checksum for {file_path}: {checksum}")
            return True

        except Exception as e:
            logger.error(f"Failed to record checksum: {e}")
            return False

    async def create_backup(
        self,
        source_path: str,
        backup_type: str = "full",
        destination: Optional[str] = None,
    ) -> Optional[BackupInfo]:
        """Create a backup of a file or directory"""
        try:
            source = Path(source_path)
            if not source.exists():
                logger.error(f"Source not found: {source_path}")
                return None

            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Generate backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source.name}_{backup_type}_{timestamp}"

            if destination:
                backup_path = Path(destination) / backup_name
            else:
                backup_path = self.backup_dir / backup_name

            # Copy file or directory
            if source.is_file():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup_path)
            else:
                shutil.copytree(source, backup_path, dirs_exist_ok=True)

            # Calculate checksum and size
            checksum = self._calculate_checksum(str(backup_path)) if backup_path.is_file() else "dir"
            size_bytes = self._get_path_size(backup_path)

            # Record backup
            backup_info = BackupInfo(
                backup_name=backup_name,
                backup_type=backup_type,
                source_path=str(source),
                destination_path=str(backup_path),
                size_bytes=size_bytes,
                checksum=checksum,
                timestamp=datetime.now().isoformat(),
            )

            # Store backup record
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    INSERT INTO backup_records
                    (backup_name, backup_type, source_path, destination_path, size_bytes, checksum)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        backup_info.backup_name,
                        backup_info.backup_type,
                        backup_info.source_path,
                        backup_info.destination_path,
                        backup_info.size_bytes,
                        backup_info.checksum,
                    ),
                )
                conn.commit()
                conn.close()

            logger.info(f"Backup created: {backup_name}")
            return backup_info

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    async def restore_backup(self, backup_path: str, restore_to: str) -> bool:
        """Restore a backup"""
        try:
            backup = Path(backup_path)
            restore_dest = Path(restore_to)

            if not backup.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Create parent directory if needed
            restore_dest.parent.mkdir(parents=True, exist_ok=True)

            # Restore file or directory
            if backup.is_file():
                shutil.copy2(backup, restore_dest)
            else:
                shutil.copytree(backup, restore_dest, dirs_exist_ok=True)

            # Record restoration
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """
                    UPDATE backup_records SET restored = 1
                    WHERE destination_path = ?
                    """,
                    (backup_path,),
                )
                conn.commit()
                conn.close()

            logger.info(f"Backup restored to: {restore_to}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def _get_path_size(self, path: Path) -> int:
        """Get total size of file or directory"""
        try:
            if path.is_file():
                return path.stat().st_size
            else:
                total = 0
                for item in path.rglob("*"):
                    if item.is_file():
                        total += item.stat().st_size
                return total
        except Exception:
            return 0

    async def cleanup_old_backups(
        self, backup_type: str = "full", keep_count: int = 7
    ) -> int:
        """Delete old backups, keeping only the latest ones"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    """
                    SELECT id, destination_path FROM backup_records
                    WHERE backup_type = ?
                    ORDER BY timestamp DESC
                    OFFSET ?
                    """,
                    (backup_type, keep_count),
                )
                old_backups = cursor.fetchall()

                deleted_count = 0
                for backup_id, backup_path in old_backups:
                    try:
                        path = Path(backup_path)
                        if path.exists():
                            if path.is_file():
                                path.unlink()
                            else:
                                shutil.rmtree(path)
                        conn.execute(
                            "DELETE FROM backup_records WHERE id = ?", (backup_id,)
                        )
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete old backup: {e}")

                conn.commit()
                conn.close()

                logger.info(f"Deleted {deleted_count} old backups")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    def get_backup_history(
        self, backup_type: Optional[str] = None, limit: int = 20
    ) -> List[BackupInfo]:
        """Get backup history"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row

                if backup_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM backup_records
                        WHERE backup_type = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (backup_type, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM backup_records
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )

                rows = cursor.fetchall()
                conn.close()

                return [
                    BackupInfo(
                        backup_name=row["backup_name"],
                        backup_type=row["backup_type"],
                        source_path=row["source_path"],
                        destination_path=row["destination_path"],
                        size_bytes=row["size_bytes"],
                        checksum=row["checksum"],
                        timestamp=row["timestamp"],
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []
