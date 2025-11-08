"""
Database Optimization System

Provides SQLite tuning and transaction management for reliability.
"""

import asyncio
import sqlite3
import threading
from typing import Any, Dict, Optional

from app.logger import logger


class DatabaseOptimizer:
    """SQLite database optimization and tuning"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._transaction_depth = 0
        self._in_transaction = False
        self._transaction_conn: Optional[sqlite3.Connection] = None
        self.retry_attempts = 3
        self.retry_delay = 0.1  # seconds

    def optimize_for_reliability(self) -> bool:
        """Apply reliability optimizations to SQLite"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                # Enable WAL mode for concurrent read/write
                conn.execute("PRAGMA journal_mode=WAL")
                logger.info("Enabled WAL (Write-Ahead Logging) mode")

                # PRAGMA synchronous controls how carefully SQLite writes to disk
                # NORMAL = safe for most use cases, faster than FULL
                conn.execute("PRAGMA synchronous=NORMAL")
                logger.info("Set PRAGMA synchronous=NORMAL")

                # Increase page cache size for better performance
                conn.execute("PRAGMA cache_size=10000")
                logger.info("Set PRAGMA cache_size=10000")

                # Use memory for temporary tables
                conn.execute("PRAGMA temp_store=MEMORY")
                logger.info("Set PRAGMA temp_store=MEMORY")

                # Enable foreign key support
                conn.execute("PRAGMA foreign_keys=ON")
                logger.info("Enabled foreign key constraints")

                # Set timeout for busy database
                conn.execute("PRAGMA busy_timeout=5000")  # 5 seconds
                logger.info("Set PRAGMA busy_timeout=5000")

                conn.commit()
                conn.close()

                return True

        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")
            return False

    def begin_transaction(self) -> bool:
        """Start an explicit transaction"""
        try:
            with self._lock:
                if self._transaction_depth == 0:
                    self._transaction_conn = sqlite3.connect(self.db_path)
                    self._transaction_conn.execute("BEGIN")
                    self._in_transaction = True
                    logger.debug("Transaction started")

                self._transaction_depth += 1
                return True

        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            return False

    def commit_transaction(self) -> bool:
        """Commit current transaction"""
        try:
            with self._lock:
                self._transaction_depth = max(0, self._transaction_depth - 1)

                if self._transaction_depth == 0 and self._in_transaction and self._transaction_conn:
                    self._transaction_conn.execute("COMMIT")
                    self._transaction_conn.close()
                    self._transaction_conn = None
                    self._in_transaction = False
                    logger.debug("Transaction committed")

                return True

        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            return False

    def rollback_transaction(self) -> bool:
        """Rollback current transaction"""
        try:
            with self._lock:
                self._transaction_depth = max(0, self._transaction_depth - 1)

                if self._in_transaction and self._transaction_conn:
                    self._transaction_conn.execute("ROLLBACK")
                    self._transaction_conn.close()
                    self._transaction_conn = None
                    self._in_transaction = False
                    logger.debug("Transaction rolled back")

                return True

        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            return False

    async def execute_with_retry(
        self,
        query: str,
        params: tuple = (),
        fetch: bool = False,
    ) -> Optional[Any]:
        """Execute query with automatic retry on SQLITE_BUSY"""
        for attempt in range(self.retry_attempts):
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.execute(query, params)

                    if fetch:
                        result = cursor.fetchall()
                    else:
                        result = cursor.rowcount

                    conn.commit()
                    conn.close()

                    return result

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self.retry_attempts - 1:
                    logger.debug(
                        f"Database locked, retrying... (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Database operation failed: {e}")
                    return None

            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                return None

        return None

    def vacuum_database(self) -> bool:
        """Defragment database"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("VACUUM")
                conn.close()
                logger.info("Database vacuumed (defragmented)")
                return True

        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False

    def analyze_database(self) -> bool:
        """Analyze database for query optimization"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("ANALYZE")
                conn.close()
                logger.info("Database analyzed")
                return True

        except Exception as e:
            logger.error(f"Failed to analyze database: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                # Get page count and page size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]

                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]

                # Get journal mode
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]

                # Get synchronous setting
                cursor = conn.execute("PRAGMA synchronous")
                synchronous_level = cursor.fetchone()[0]

                # Get cache size
                cursor = conn.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]

                # Get table count
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )
                table_count = cursor.fetchone()[0]

                # Get index count
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
                )
                index_count = cursor.fetchone()[0]

                conn.close()

                db_size_mb = (page_count * page_size) / (1024 * 1024)

                return {
                    "size_mb": round(db_size_mb, 2),
                    "page_count": page_count,
                    "page_size": page_size,
                    "journal_mode": journal_mode,
                    "synchronous": "NORMAL" if synchronous_level == 1 else f"LEVEL_{synchronous_level}",
                    "cache_size": cache_size,
                    "table_count": table_count,
                    "index_count": index_count,
                }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def optimize_indexes(self) -> bool:
        """Optimize indexes in database"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                # Get all indexes
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                )
                indexes = cursor.fetchall()

                for (index_name,) in indexes:
                    try:
                        conn.execute(f"REINDEX {index_name}")
                    except Exception as e:
                        logger.warning(f"Failed to reindex {index_name}: {e}")

                conn.commit()
                conn.close()

                logger.info(f"Optimized {len(indexes)} indexes")
                return True

        except Exception as e:
            logger.error(f"Failed to optimize indexes: {e}")
            return False

    def enable_foreign_keys(self) -> bool:
        """Enable foreign key constraints"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA foreign_keys=ON")
                conn.close()
                logger.info("Foreign key constraints enabled")
                return True

        except Exception as e:
            logger.error(f"Failed to enable foreign keys: {e}")
            return False

    def check_database_integrity(self) -> Dict[str, Any]:
        """Check database integrity"""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)

                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]

                conn.close()

                if result == "ok":
                    return {
                        "integrity": "ok",
                        "status": "Database is in good state",
                    }
                else:
                    return {
                        "integrity": "error",
                        "status": result,
                    }

        except Exception as e:
            logger.error(f"Failed to check database integrity: {e}")
            return {
                "integrity": "error",
                "status": str(e),
            }

    async def maintenance_task(self):
        """Run periodic maintenance tasks"""
        try:
            logger.info("Starting database maintenance")

            # Analyze database
            self.analyze_database()

            # Optimize indexes
            self.optimize_indexes()

            # Check integrity
            integrity = self.check_database_integrity()
            if integrity["integrity"] != "ok":
                logger.warning(f"Database integrity issue: {integrity['status']}")

            logger.info("Database maintenance completed")

        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
