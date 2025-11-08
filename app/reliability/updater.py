"""
Update Management System

Provides auto-updates and version management with rollback capability.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from app.logger import logger


class VersionInfo(BaseModel):
    """Version information model"""
    version: str
    release_date: str
    changelog: str
    download_url: str
    file_hash: str
    size_bytes: int


class UpdateInfo(BaseModel):
    """Update information model"""
    from_version: str
    to_version: str
    timestamp: str
    status: str  # "success", "failed", "rolled_back"
    details: Dict[str, Any]


class UpdateManager:
    """Manages application updates"""

    def __init__(self, app_root: str = "./"):
        self.app_root = Path(app_root)
        self.backup_dir = self.app_root / ".backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._current_version = self._get_current_version()
        self._init_db()

    def _init_db(self):
        """Initialize update tracking database"""
        try:
            db_path = self.app_root / "data" / "reliability.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_version TEXT NOT NULL,
                    to_version TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    details TEXT
                )
                """
            )
            conn.commit()
            conn.close()
            logger.info("Update tracking database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize update database: {e}")

    def _get_current_version(self) -> str:
        """Get current application version"""
        try:
            version_file = self.app_root / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return "unknown"

    def set_current_version(self, version: str) -> bool:
        """Set current application version"""
        try:
            version_file = self.app_root / "VERSION"
            version_file.write_text(version)
            self._current_version = version
            logger.info(f"Version set to: {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to set version: {e}")
            return False

    async def check_for_updates(self) -> Optional[VersionInfo]:
        """Check for available updates"""
        try:
            # This would normally fetch from a version server
            # For now, return None (no updates)
            logger.info(f"Checking for updates (current version: {self._current_version})")
            return None
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return None

    async def download_update(self, version_info: VersionInfo) -> Optional[Path]:
        """Download an update"""
        try:
            logger.info(f"Downloading update: {version_info.version}")

            # Create temp directory for download
            download_dir = self.backup_dir / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)

            download_file = download_dir / f"update_{version_info.version}.zip"

            # This would normally use urllib or requests to download
            # For now, just log the action
            logger.info(f"Update would be downloaded to: {download_file}")

            return download_file

        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None

    async def backup_current_version(self) -> Optional[Path]:
        """Backup current version before update"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{self._current_version}_{timestamp}"

            logger.info(f"Creating backup at: {backup_path}")

            # Copy application files (excluding cache and backups)
            for item in self.app_root.glob("*"):
                if item.name in [".backups", "cache", "logs", "backups"]:
                    continue
                if item.is_file():
                    shutil.copy2(item, backup_path)
                elif item.is_dir():
                    shutil.copytree(item, backup_path / item.name, dirs_exist_ok=True)

            # Record backup info
            backup_info = {
                "version": self._current_version,
                "timestamp": datetime.now().isoformat(),
                "backup_path": str(backup_path),
            }

            backup_info_file = backup_path / "backup_info.json"
            backup_info_file.write_text(json.dumps(backup_info, indent=2))

            logger.info(f"Backup created successfully")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to backup version: {e}")
            return None

    async def install_update(
        self, version_info: VersionInfo, backup_path: Optional[Path] = None
    ) -> bool:
        """Install an update"""
        try:
            logger.info(f"Installing update: {version_info.version}")

            # In a real implementation, this would:
            # 1. Extract the downloaded update
            # 2. Replace files
            # 3. Run migrations if needed
            # 4. Verify installation

            # Update version file
            self.set_current_version(version_info.version)

            # Record update
            self._record_update(
                self._current_version,
                version_info.version,
                "success",
                {"backup_path": str(backup_path)} if backup_path else {},
            )

            logger.info(f"Update installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False

    async def rollback_to_version(self, backup_path: Path) -> bool:
        """Rollback to a previous version"""
        try:
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            logger.warning(f"Rolling back to version from: {backup_path}")

            # Get backup info
            backup_info_file = backup_path / "backup_info.json"
            if backup_info_file.exists():
                backup_info = json.loads(backup_info_file.read_text())
                backup_version = backup_info.get("version", "unknown")
            else:
                backup_version = "unknown"

            # Restore files from backup
            for item in backup_path.glob("*"):
                if item.name == "backup_info.json":
                    continue
                dest = self.app_root / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)

            # Update version
            self.set_current_version(backup_version)

            # Record rollback
            self._record_update(
                self._current_version,
                backup_version,
                "rolled_back",
                {"backup_path": str(backup_path)},
            )

            logger.info(f"Rollback completed to version: {backup_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False

    def _record_update(
        self,
        from_version: str,
        to_version: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record update in database"""
        try:
            with self._lock:
                db_path = self.app_root / "data" / "reliability.db"
                conn = sqlite3.connect(str(db_path))
                conn.execute(
                    """
                    INSERT INTO updates (from_version, to_version, status, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (from_version, to_version, status, json.dumps(details or {})),
                )
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"Failed to record update: {e}")
            return False

    def get_update_history(self, limit: int = 20) -> List[UpdateInfo]:
        """Get update history"""
        try:
            with self._lock:
                db_path = self.app_root / "data" / "reliability.db"
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT from_version, to_version, timestamp, status, details
                    FROM updates
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                conn.close()

                return [
                    UpdateInfo(
                        from_version=row["from_version"],
                        to_version=row["to_version"],
                        timestamp=row["timestamp"],
                        status=row["status"],
                        details=json.loads(row["details"] or "{}"),
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get update history: {e}")
            return []

    def get_available_backups(self) -> List[Path]:
        """Get list of available backups for rollback"""
        try:
            backups = []
            if self.backup_dir.exists():
                for backup in sorted(self.backup_dir.glob("backup_*"), reverse=True):
                    if backup.is_dir():
                        backups.append(backup)
            return backups
        except Exception as e:
            logger.error(f"Failed to get available backups: {e}")
            return []

    def get_update_status(self) -> Dict[str, Any]:
        """Get update manager status"""
        return {
            "current_version": self._current_version,
            "last_update": None,  # Would be populated from history
            "available_backups": len(self.get_available_backups()),
            "update_history": [
                {
                    "from": u.from_version,
                    "to": u.to_version,
                    "status": u.status,
                    "timestamp": u.timestamp,
                }
                for u in self.get_update_history(limit=5)
            ],
        }
