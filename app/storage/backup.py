"""Backup manager for scheduled backups, archival, and restore operations."""

import json
import shutil
import tarfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT, config
from app.logger import logger
from app.storage.audit import audit_logger, AuditEventType
from app.storage.guardian import get_guardian
from app.storage.versioning import get_versioning_engine, FileVersion

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not available, scheduled backups will be disabled")


class BackupMetadata(BaseModel):
    """Metadata for a backup archive."""
    
    backup_id: str = Field(..., description="Unique backup identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Backup creation timestamp")
    backup_type: str = Field(..., description="Type of backup: full, incremental, differential")
    archive_path: str = Field(..., description="Path to the backup archive")
    size_bytes: int = Field(..., description="Size of the backup archive in bytes")
    files_count: int = Field(..., description="Number of files in the backup")
    compression: str = Field(default="gzip", description="Compression algorithm used")
    checksum: Optional[str] = Field(None, description="Archive checksum for integrity")
    created_by: str = Field(default="system", description="User who created the backup")
    tags: List[str] = Field(default_factory=list, description="Tags for this backup")
    description: Optional[str] = Field(None, description="Backup description")
    includes_versions: bool = Field(True, description="Whether version history is included")
    includes_workflows: bool = Field(False, description="Whether workflow snapshots are included")
    parent_backup: Optional[str] = Field(None, description="Parent backup ID for incremental")


class BackupDestination(BaseModel):
    """Configuration for a backup destination."""
    
    destination_type: str = Field(..., description="Type: local, s3, azure, gcs")
    path: str = Field(..., description="Local path or cloud bucket/container")
    credentials: Dict[str, str] = Field(default_factory=dict, description="Cloud credentials")
    enabled: bool = Field(True, description="Whether this destination is enabled")


class BackupManager:
    """Manager for scheduling and executing backups."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._lock = threading.RLock()
        self._backup_dir = PROJECT_ROOT / "data" / "backups"
        self._archive_dir = PROJECT_ROOT / "data" / "archives"
        self._metadata_dir = self._backup_dir / "metadata"
        
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self._versioning = get_versioning_engine()
        self._guardian = get_guardian()
        
        self._scheduler = None
        self._backup_counter = 0
        self._destinations: List[BackupDestination] = []
        self._backup_callback: Optional[Callable[[BackupMetadata], None]] = None
        
        if SCHEDULER_AVAILABLE:
            self._scheduler = BackgroundScheduler()
            self._scheduler.start()
            logger.info("Backup scheduler started")
        
        self._load_destinations()
        logger.info(f"BackupManager initialized with backup directory: {self._backup_dir}")
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        with self._lock:
            self._backup_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"backup_{timestamp}_{self._backup_counter:04d}"
    
    def _load_destinations(self) -> None:
        """Load backup destinations from configuration."""
        try:
            backup_config = getattr(config, 'backup', None)
            if backup_config and hasattr(backup_config, 'destinations'):
                self._destinations = [BackupDestination(**dest) for dest in backup_config.destinations]
                logger.info(f"Loaded {len(self._destinations)} backup destinations")
        except Exception as e:
            logger.error(f"Error loading backup destinations: {e}")
            self._destinations = [
                BackupDestination(
                    destination_type="local",
                    path=str(self._backup_dir),
                    enabled=True
                )
            ]
    
    def set_backup_callback(self, callback: Callable[[BackupMetadata], None]) -> None:
        """Set a callback to be called when a backup completes.
        
        Args:
            callback: Function that takes a BackupMetadata
        """
        with self._lock:
            self._backup_callback = callback
    
    def create_backup(
        self,
        backup_type: str = "full",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_versions: bool = True,
        include_workflows: bool = False,
        created_by: str = "system"
    ) -> Optional[BackupMetadata]:
        """Create a backup archive.
        
        Args:
            backup_type: Type of backup (full, incremental, differential)
            description: Backup description
            tags: Tags for the backup
            include_versions: Include version history
            include_workflows: Include workflow snapshots
            created_by: User creating the backup
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        backup_id = self._generate_backup_id()
        
        audit_logger.log_event(
            AuditEventType.BACKUP_STARTED,
            user=created_by,
            resource=backup_id,
            details={"backup_type": backup_type, "description": description}
        )
        
        logger.info(f"Creating {backup_type} backup: {backup_id}")
        
        try:
            archive_name = f"{backup_id}.tar.gz"
            archive_path = self._backup_dir / archive_name
            
            with tarfile.open(archive_path, "w:gz") as tar:
                files_count = 0
                
                if include_versions:
                    versions_dir = self._versioning._versions_dir
                    if versions_dir.exists():
                        tar.add(versions_dir, arcname="versions")
                        files_count += sum(1 for _ in versions_dir.rglob("*") if _.is_file())
                        logger.debug(f"Added versions directory to backup")
                
                if include_workflows:
                    workflows_dir = PROJECT_ROOT / "data" / "workflows"
                    if workflows_dir.exists():
                        tar.add(workflows_dir, arcname="workflows")
                        files_count += sum(1 for _ in workflows_dir.rglob("*") if _.is_file())
                        logger.debug(f"Added workflows directory to backup")
                
                workspace_dir = PROJECT_ROOT / "workspace"
                if workspace_dir.exists():
                    tar.add(workspace_dir, arcname="workspace")
                    files_count += sum(1 for _ in workspace_dir.rglob("*") if _.is_file())
                    logger.debug(f"Added workspace directory to backup")
            
            size_bytes = archive_path.stat().st_size
            
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                archive_path=str(archive_path),
                size_bytes=size_bytes,
                files_count=files_count,
                created_by=created_by,
                tags=tags or [],
                description=description,
                includes_versions=include_versions,
                includes_workflows=include_workflows
            )
            
            self._save_metadata(metadata)
            
            audit_logger.log_event(
                AuditEventType.BACKUP_COMPLETED,
                user=created_by,
                resource=backup_id,
                details={
                    "size_bytes": size_bytes,
                    "files_count": files_count,
                    "archive_path": str(archive_path)
                }
            )
            
            if self._backup_callback:
                try:
                    self._backup_callback(metadata)
                except Exception as e:
                    logger.error(f"Error in backup callback: {e}")
            
            logger.info(f"Backup completed: {backup_id} ({size_bytes} bytes, {files_count} files)")
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating backup {backup_id}: {e}")
            audit_logger.log_event(
                AuditEventType.BACKUP_FAILED,
                user=created_by,
                resource=backup_id,
                success=False,
                error_message=str(e)
            )
            return None
    
    def _save_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to disk."""
        metadata_file = self._metadata_dir / f"{metadata.backup_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata.model_dump(mode='json'), f, indent=2, default=str)
    
    def _load_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata from disk."""
        metadata_file = self._metadata_dir / f"{backup_id}.json"
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BackupMetadata.model_validate(data)
        except Exception as e:
            logger.error(f"Error loading metadata for {backup_id}: {e}")
            return None
    
    def get_backups(self, limit: Optional[int] = None) -> List[BackupMetadata]:
        """Get all backups, sorted by timestamp (newest first).
        
        Args:
            limit: Maximum number of backups to return
            
        Returns:
            List of BackupMetadata
        """
        backups = []
        
        for metadata_file in sorted(self._metadata_dir.glob("*.json"), reverse=True):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    backups.append(BackupMetadata.model_validate(data))
                    
                    if limit and len(backups) >= limit:
                        break
            except Exception as e:
                logger.error(f"Error loading metadata from {metadata_file}: {e}")
        
        return backups
    
    def get_backup(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get metadata for a specific backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            BackupMetadata or None if not found
        """
        return self._load_metadata(backup_id)
    
    def restore_backup(
        self,
        backup_id: str,
        target_path: Optional[Path] = None,
        user: str = "system",
        require_approval: bool = True
    ) -> bool:
        """Restore from a backup.
        
        Args:
            backup_id: ID of the backup to restore
            target_path: Path to restore to (defaults to original locations)
            user: User performing the restore
            require_approval: Whether to require Guardian approval
            
        Returns:
            True if successful, False otherwise
        """
        metadata = self.get_backup(backup_id)
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        if not Path(metadata.archive_path).exists():
            logger.error(f"Backup archive not found: {metadata.archive_path}")
            return False
        
        target_path = target_path or PROJECT_ROOT
        
        if require_approval:
            approved = self._guardian.validate_restore_operation(
                backup_id=backup_id,
                target_path=str(target_path),
                user=user
            )
            
            if not approved:
                logger.warning(f"Restore operation rejected by Guardian: {backup_id}")
                return False
        
        audit_logger.log_event(
            AuditEventType.RESTORE_STARTED,
            user=user,
            resource=backup_id,
            details={"target_path": str(target_path)}
        )
        
        logger.info(f"Restoring backup {backup_id} to {target_path}")
        
        try:
            with tarfile.open(metadata.archive_path, "r:gz") as tar:
                tar.extractall(path=target_path)
            
            audit_logger.log_event(
                AuditEventType.RESTORE_COMPLETED,
                user=user,
                resource=backup_id,
                details={"target_path": str(target_path)}
            )
            
            logger.info(f"Restore completed: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup {backup_id}: {e}")
            audit_logger.log_event(
                AuditEventType.RESTORE_FAILED,
                user=user,
                resource=backup_id,
                success=False,
                error_message=str(e)
            )
            return False
    
    def archive_old_backups(
        self,
        days_threshold: int = 30,
        keep_count: int = 10
    ) -> int:
        """Archive old backups to free up space.
        
        Moves backups older than threshold to archive storage, keeping at least keep_count recent backups.
        
        Args:
            days_threshold: Archive backups older than this many days
            keep_count: Always keep at least this many recent backups
            
        Returns:
            Number of backups archived
        """
        logger.info(f"Archiving backups older than {days_threshold} days")
        
        backups = self.get_backups()
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        archived_count = 0
        
        for i, backup in enumerate(backups):
            if i < keep_count:
                continue
            
            if backup.timestamp < cutoff_date:
                try:
                    archive_path = Path(backup.archive_path)
                    if archive_path.exists():
                        target_path = self._archive_dir / archive_path.name
                        shutil.move(str(archive_path), str(target_path))
                        
                        backup.archive_path = str(target_path)
                        self._save_metadata(backup)
                        
                        audit_logger.log_event(
                            AuditEventType.ARCHIVE_CREATED,
                            resource=backup.backup_id,
                            details={"target_path": str(target_path)}
                        )
                        
                        archived_count += 1
                        logger.debug(f"Archived backup: {backup.backup_id}")
                except Exception as e:
                    logger.error(f"Error archiving backup {backup.backup_id}: {e}")
        
        logger.info(f"Archived {archived_count} backups")
        return archived_count
    
    def delete_backup(
        self,
        backup_id: str,
        user: str = "system",
        require_approval: bool = True
    ) -> bool:
        """Delete a backup.
        
        Args:
            backup_id: ID of the backup to delete
            user: User performing the delete
            require_approval: Whether to require Guardian approval
            
        Returns:
            True if successful, False otherwise
        """
        metadata = self.get_backup(backup_id)
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        if require_approval:
            approved = self._guardian.validate_delete_operation(
                resource=f"backup:{backup_id}",
                user=user
            )
            
            if not approved:
                logger.warning(f"Delete operation rejected by Guardian: {backup_id}")
                return False
        
        try:
            archive_path = Path(metadata.archive_path)
            if archive_path.exists():
                archive_path.unlink()
            
            metadata_file = self._metadata_dir / f"{backup_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            audit_logger.log_event(
                AuditEventType.ARCHIVE_DELETED,
                user=user,
                resource=backup_id
            )
            
            logger.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup {backup_id}: {e}")
            return False
    
    def schedule_backup(
        self,
        schedule_type: str = "cron",
        schedule_config: Optional[Dict[str, Any]] = None,
        backup_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Schedule automatic backups.
        
        Args:
            schedule_type: "cron" or "interval"
            schedule_config: Configuration for the schedule
            backup_config: Configuration for the backup
            
        Returns:
            True if successful, False otherwise
        """
        if not SCHEDULER_AVAILABLE:
            logger.error("Scheduler not available, cannot schedule backups")
            return False
        
        schedule_config = schedule_config or {}
        backup_config = backup_config or {}
        
        try:
            if schedule_type == "cron":
                trigger = CronTrigger(**schedule_config)
            elif schedule_type == "interval":
                trigger = IntervalTrigger(**schedule_config)
            else:
                logger.error(f"Invalid schedule type: {schedule_type}")
                return False
            
            self._scheduler.add_job(
                func=lambda: self.create_backup(**backup_config),
                trigger=trigger,
                id=f"backup_{schedule_type}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled {schedule_type} backup with config: {schedule_config}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling backup: {e}")
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics.
        
        Returns:
            Dictionary with backup stats
        """
        backups = self.get_backups()
        
        total_size = sum(backup.size_bytes for backup in backups)
        total_files = sum(backup.files_count for backup in backups)
        
        by_type = {}
        for backup in backups:
            by_type[backup.backup_type] = by_type.get(backup.backup_type, 0) + 1
        
        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "total_files": total_files,
            "by_type": by_type,
            "latest_backup": backups[0].timestamp.isoformat() if backups else None
        }
    
    def cleanup_old_backups(self, retention_days: int = 90) -> int:
        """Delete backups older than retention period.
        
        Args:
            retention_days: Number of days to retain backups
            
        Returns:
            Number of backups deleted
        """
        logger.info(f"Cleaning up backups older than {retention_days} days")
        
        backups = self.get_backups()
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        for backup in backups:
            if backup.timestamp < cutoff_date:
                if self.delete_backup(backup.backup_id, require_approval=False):
                    deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} old backups")
        return deleted_count


def get_backup_manager() -> BackupManager:
    """Get the singleton BackupManager instance."""
    return BackupManager()
