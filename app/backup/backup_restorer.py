"""
Backup Restorer
Handles restoration of system state from backups
"""

import asyncio
import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, backup_service as db_backup_service
from .backup_service import BackupService


class RestoreResult(BaseModel):
    """Result of a restore operation"""
    success: bool
    backup_name: str
    restored_items: List[str]
    failed_items: List[str]
    duration: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BackupRestorer:
    """Handles restoration from backups"""
    
    def __init__(self):
        self.backup_service = BackupService()
        self.workspace_root = Path("./workspace")
        self.config_root = Path("./config")
        self.data_root = Path("./data")
    
    async def restore_backup(self, backup_path: str, 
                           restore_options: Dict[str, bool] = None) -> RestoreResult:
        """Restore system from a backup file"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting restore from: {backup_path}")
            
            # Validate backup file
            if not await self.backup_service.verify_backup(backup_path):
                raise ValueError("Invalid backup file")
            
            # Set default restore options
            if restore_options is None:
                restore_options = {
                    "workspace": True,
                    "config": True,
                    "database": True
                }
            
            # Create backup of current state before restore
            await self._create_pre_restore_backup()
            
            # Extract and restore
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract backup
                await self._extract_backup(backup_path, temp_dir)
                
                # Read metadata
                metadata = await self._read_backup_metadata(temp_dir)
                
                # Restore components
                restored_items = []
                failed_items = []
                
                if restore_options.get("workspace", False) and metadata.get("includes", {}).get("workspace", False):
                    success = await self._restore_workspace(temp_dir)
                    if success:
                        restored_items.append("workspace")
                    else:
                        failed_items.append("workspace")
                
                if restore_options.get("config", False) and metadata.get("includes", {}).get("config", False):
                    success = await self._restore_config(temp_dir)
                    if success:
                        restored_items.append("config")
                    else:
                        failed_items.append("config")
                
                if restore_options.get("database", False) and metadata.get("includes", {}).get("database", False):
                    success = await self._restore_database(temp_dir)
                    if success:
                        restored_items.append("database")
                    else:
                        failed_items.append("database")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update database record
            await self._update_restore_record(backup_path)
            
            result = RestoreResult(
                success=len(failed_items) == 0,
                backup_name=metadata.get("backup_name", "unknown"),
                restored_items=restored_items,
                failed_items=failed_items,
                duration=duration,
                metadata=metadata
            )
            
            if result.success:
                logger.info(f"Restore completed successfully in {duration:.2f}s")
            else:
                logger.warning(f"Restore completed with errors: {failed_items}")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            logger.error(f"Restore failed: {error_msg}")
            
            return RestoreResult(
                success=False,
                backup_name="unknown",
                restored_items=[],
                failed_items=[],
                duration=duration,
                error_message=error_msg
            )
    
    async def _create_pre_restore_backup(self):
        """Create a backup before restoring"""
        try:
            from .backup_service import BackupConfig
            
            pre_restore_config = BackupConfig(
                backup_name="pre_restore_backup",
                backup_type="full",
                include_workspace=True,
                include_config=True,
                include_database=True,
                compression=True,
                encryption=False
            )
            
            result = await self.backup_service.create_backup(pre_restore_config)
            if result.success:
                logger.info(f"Created pre-restore backup: {result.file_path}")
            else:
                logger.warning("Failed to create pre-restore backup")
                
        except Exception as e:
            logger.error(f"Error creating pre-restore backup: {e}")
    
    async def _extract_backup(self, backup_path: str, extract_dir: str):
        """Extract backup file to temporary directory"""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                zip_file.extractall(extract_dir)
            
            logger.debug(f"Extracted backup to: {extract_dir}")
            
        except Exception as e:
            logger.error(f"Error extracting backup: {e}")
            raise
    
    async def _read_backup_metadata(self, extract_dir: str) -> Dict[str, Any]:
        """Read backup metadata"""
        try:
            metadata_path = Path(extract_dir) / "metadata.json"
            if not metadata_path.exists():
                return {}
            
            with open(metadata_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error reading backup metadata: {e}")
            return {}
    
    async def _restore_workspace(self, extract_dir: str) -> bool:
        """Restore workspace from backup"""
        try:
            workspace_backup = Path(extract_dir) / "workspace"
            if not workspace_backup.exists():
                logger.warning("No workspace data in backup")
                return True  # Not an error
            
            # Backup current workspace
            if self.workspace_root.exists():
                workspace_backup_current = self.workspace_root.with_suffix(".backup")
                if workspace_backup_current.exists():
                    shutil.rmtree(workspace_backup_current)
                shutil.move(str(self.workspace_root), str(workspace_backup_current))
            
            # Restore workspace
            shutil.move(str(workspace_backup), str(self.workspace_root))
            
            logger.info("Workspace restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring workspace: {e}")
            return False
    
    async def _restore_config(self, extract_dir: str) -> bool:
        """Restore configuration from backup"""
        try:
            config_backup = Path(extract_dir) / "config"
            if not config_backup.exists():
                logger.warning("No config data in backup")
                return True  # Not an error
            
            # Backup current config
            if self.config_root.exists():
                config_backup_current = self.config_root.with_suffix(".backup")
                if config_backup_current.exists():
                    shutil.rmtree(config_backup_current)
                shutil.move(str(self.config_root), str(config_backup_current))
            
            # Restore config
            shutil.move(str(config_backup), str(self.config_root))
            
            logger.info("Configuration restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring config: {e}")
            return False
    
    async def _restore_database(self, extract_dir: str) -> bool:
        """Restore database from backup"""
        try:
            data_backup = Path(extract_dir) / "data"
            if not data_backup.exists():
                logger.warning("No database data in backup")
                return True  # Not an error
            
            # Close database connections
            # This would need to be coordinated with the database service
            
            # Backup current database
            if self.data_root.exists():
                data_backup_current = self.data_root.with_suffix(".backup")
                if data_backup_current.exists():
                    shutil.rmtree(data_backup_current)
                shutil.move(str(self.data_root), str(data_backup_current))
            
            # Restore database
            shutil.move(str(data_backup), str(self.data_root))
            
            logger.info("Database restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False
    
    async def _update_restore_record(self, backup_path: str):
        """Update restore record in database"""
        try:
            # Find backup record
            async with await database_service.get_connection() as db:
                cursor = await db.execute(
                    "SELECT id FROM backup_records WHERE file_path = ?",
                    (backup_path,)
                )
                result = await cursor.fetchone()
                
                if result:
                    backup_id = result[0]
                    await db.execute(
                        "UPDATE backup_records SET restored_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (backup_id,)
                    )
                    await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating restore record: {e}")
    
    async def list_restorable_backups(self) -> List[Dict[str, Any]]:
        """List backups that can be restored"""
        try:
            backups = await self.backup_service.list_backups()
            
            # Filter for valid backups
            restorable = []
            for backup in backups:
                backup_path = backup['file_path']
                if await self.backup_service.verify_backup(backup_path):
                    restorable.append(backup)
            
            return restorable
            
        except Exception as e:
            logger.error(f"Error listing restorable backups: {e}")
            return []
    
    async def get_restore_preview(self, backup_path: str) -> Dict[str, Any]:
        """Get preview of what would be restored"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract backup metadata only
                with zipfile.ZipFile(backup_path, 'r') as zip_file:
                    if "metadata.json" not in zip_file.namelist():
                        return {"error": "Invalid backup file"}
                    
                    metadata_content = zip_file.read("metadata.json")
                    metadata = json.loads(metadata_content)
                
                # Get file sizes
                file_sizes = {}
                with zipfile.ZipFile(backup_path, 'r') as zip_file:
                    for file_info in zip_file.infolist():
                        if not file_info.is_dir():
                            file_sizes[file_info.filename] = file_info.file_size
                
                return {
                    "backup_name": metadata.get("backup_name"),
                    "backup_type": metadata.get("backup_type"),
                    "created_at": metadata.get("created_at"),
                    "includes": metadata.get("includes", {}),
                    "compression": metadata.get("compression", False),
                    "encryption": metadata.get("encryption", False),
                    "file_sizes": file_sizes,
                    "total_size": sum(file_sizes.values())
                }
                
        except Exception as e:
            logger.error(f"Error getting restore preview: {e}")
            return {"error": str(e)}


# Global backup restorer instance
backup_restorer = BackupRestorer()
