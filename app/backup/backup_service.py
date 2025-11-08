"""
Backup Service
Manages system backups, scheduling, and restoration
"""

import asyncio
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiofiles
from pydantic import BaseModel

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, backup_service as db_backup_service
from app.versioning.versioning_service import versioning_service


class BackupConfig(BaseModel):
    """Backup configuration"""
    backup_name: str
    backup_type: str  # full, incremental, differential
    include_workspace: bool = True
    include_config: bool = True
    include_database: bool = True
    compression: bool = True
    encryption: bool = False
    locations: List[str] = []


class BackupResult(BaseModel):
    """Result of a backup operation"""
    success: bool
    backup_name: str
    backup_type: str
    file_path: str
    file_size: int
    checksum: str
    duration: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BackupService:
    """Main backup service"""
    
    def __init__(self):
        self.backup_locations = config.backup.backup_locations
        self.workspace_root = Path("./workspace")
        self.config_root = Path("./config")
        self.data_root = Path("./data")
        self._ensure_backup_directories()
    
    def _ensure_backup_directories(self):
        """Ensure backup directories exist"""
        for location in self.backup_locations:
            Path(location).mkdir(parents=True, exist_ok=True)
    
    async def create_backup(self, backup_config: BackupConfig) -> BackupResult:
        """Create a backup with the given configuration"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting backup: {backup_config.backup_name} ({backup_config.backup_type})")
            
            # Generate backup filename
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{backup_config.backup_name}_{timestamp}.zip"
            
            # Create backup file
            backup_path = None
            for location in self.backup_locations:
                backup_path = Path(location) / backup_filename
                break
            
            if not backup_path:
                raise ValueError("No valid backup location found")
            
            # Create backup
            await self._create_backup_file(backup_config, backup_path)
            
            # Calculate checksum
            checksum = await self._calculate_checksum(backup_path)
            file_size = backup_path.stat().st_size
            duration = (datetime.now() - start_time).total_seconds()
            
            # Record in database
            backup_id = await db_backup_service.record_backup(
                backup_name=backup_config.backup_name,
                backup_type=backup_config.backup_type,
                file_path=str(backup_path),
                file_size=file_size,
                checksum=checksum
            )
            
            result = BackupResult(
                success=True,
                backup_name=backup_config.backup_name,
                backup_type=backup_config.backup_type,
                file_path=str(backup_path),
                file_size=file_size,
                checksum=checksum,
                duration=duration,
                metadata={"backup_id": backup_id}
            )
            
            logger.info(f"Backup completed successfully: {backup_path} ({file_size} bytes, {duration:.2f}s)")
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            logger.error(f"Backup failed: {error_msg}")
            
            return BackupResult(
                success=False,
                backup_name=backup_config.backup_name,
                backup_type=backup_config.backup_type,
                file_path="",
                file_size=0,
                checksum="",
                duration=duration,
                error_message=error_msg
            )
    
    async def _create_backup_file(self, backup_config: BackupConfig, backup_path: Path):
        """Create the backup file"""
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED if backup_config.compression else zipfile.ZIP_STORED) as zip_file:
            # Add workspace if included
            if backup_config.include_workspace and self.workspace_root.exists():
                await self._add_directory_to_zip(zip_file, self.workspace_root, "workspace")
            
            # Add config if included
            if backup_config.include_config and self.config_root.exists():
                await self._add_directory_to_zip(zip_file, self.config_root, "config")
            
            # Add database if included
            if backup_config.include_database:
                await self._add_database_to_zip(zip_file)
            
            # Add metadata
            metadata = {
                "backup_name": backup_config.backup_name,
                "backup_type": backup_config.backup_type,
                "created_at": datetime.now().isoformat(),
                "includes": {
                    "workspace": backup_config.include_workspace,
                    "config": backup_config.include_config,
                    "database": backup_config.include_database
                },
                "compression": backup_config.compression,
                "encryption": backup_config.encryption
            }
            
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
    
    async def _add_directory_to_zip(self, zip_file: zipfile.ZipFile, directory: Path, arcname: str):
        """Add a directory to the zip file"""
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # Calculate relative path
                rel_path = file_path.relative_to(directory)
                zip_arcname = f"{arcname}/{rel_path}"
                
                # Add file to zip
                zip_file.write(file_path, zip_arcname)
    
    async def _add_database_to_zip(self, zip_file: zipfile.ZipFile):
        """Add database files to the zip"""
        # Add main database
        db_path = Path("./data/system.db")
        if db_path.exists():
            zip_file.write(db_path, "data/system.db")
        
        # Add vector store if exists
        vector_path = Path(config.knowledge_graph.graph_storage_path)
        if vector_path.exists():
            await self._add_directory_to_zip(zip_file, vector_path, "data/knowledge_graph")
        
        # Add version data if exists
        version_path = Path("./data/versions")
        if version_path.exists():
            await self._add_directory_to_zip(zip_file, version_path, "data/versions")
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def list_backups(self, backup_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        return await db_backup_service.list_backups(backup_type)
    
    async def get_backup_info(self, backup_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific backup"""
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = None
                cursor = await db.execute(
                    "SELECT * FROM backup_records WHERE id = ?", (backup_id,)
                )
                backup = await cursor.fetchone()
                
                if backup:
                    return {
                        "id": backup[0],
                        "backup_name": backup[1],
                        "backup_type": backup[2],
                        "file_path": backup[3],
                        "file_size": backup[4],
                        "checksum": backup[5],
                        "created_at": backup[6],
                        "restored_at": backup[7]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return None
    
    async def verify_backup(self, backup_path: str) -> bool:
        """Verify a backup file integrity"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return False
            
            # Check if it's a valid zip file
            try:
                with zipfile.ZipFile(backup_file, 'r') as zip_file:
                    # Check if metadata exists
                    if "metadata.json" not in zip_file.namelist():
                        return False
                    
                    # Read and validate metadata
                    metadata_content = zip_file.read("metadata.json")
                    metadata = json.loads(metadata_content)
                    
                    required_fields = ["backup_name", "backup_type", "created_at", "includes"]
                    for field in required_fields:
                        if field not in metadata:
                            return False
                
                return True
                
            except (zipfile.BadZipFile, json.JSONDecodeError, KeyError):
                return False
                
        except Exception as e:
            logger.error(f"Error verifying backup: {e}")
            return False
    
    async def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup"""
        try:
            # Get backup info
            backup_info = await self.get_backup_info(backup_id)
            if not backup_info:
                return False
            
            # Delete file
            backup_path = Path(backup_info["file_path"])
            if backup_path.exists():
                backup_path.unlink()
            
            # Update database
            async with await database_service.get_connection() as db:
                await db.execute("DELETE FROM backup_records WHERE id = ?", (backup_id,))
                await db.commit()
            
            logger.info(f"Deleted backup {backup_id}: {backup_info['backup_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup {backup_id}: {e}")
            return False
    
    async def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            # Get all backups sorted by date
            backups = await self.list_backups()
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Keep only the most recent N backups
            max_backups = config.backup.max_backups
            if len(backups) <= max_backups:
                return
            
            # Delete old backups
            to_delete = backups[max_backups:]
            for backup in to_delete:
                await self.delete_backup(backup['id'])
            
            logger.info(f"Cleaned up {len(to_delete)} old backups")
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        try:
            async with await database_service.get_connection() as db:
                # Get total backups
                cursor = await db.execute("SELECT COUNT(*) FROM backup_records")
                total_backups = (await cursor.fetchone())[0]
                
                # Get total size
                cursor = await db.execute("SELECT SUM(file_size) FROM backup_records")
                total_size = (await cursor.fetchone())[0] or 0
                
                # Get recent backups (last 7 days)
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM backup_records 
                    WHERE created_at > datetime('now', '-7 days')
                """)
                recent_backups = (await cursor.fetchone())[0]
                
                # Get backup types distribution
                cursor = await db.execute("""
                    SELECT backup_type, COUNT(*) 
                    FROM backup_records 
                    GROUP BY backup_type
                """)
                type_distribution = dict(await cursor.fetchall())
                
                return {
                    "total_backups": total_backups,
                    "total_size_bytes": total_size,
                    "total_size_mb": total_size / (1024 * 1024),
                    "recent_backups_7d": recent_backups,
                    "type_distribution": type_distribution,
                    "backup_locations": self.backup_locations
                }
                
        except Exception as e:
            logger.error(f"Error getting backup statistics: {e}")
            return {}


# Global backup service instance
backup_service = BackupService()
