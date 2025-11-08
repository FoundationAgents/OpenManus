"""
Versioning Service
Manages file versions and snapshots
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import aiofiles
from pydantic import BaseModel

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, versioning_service as db_version_service
from .diff_engine import DiffEngine


class FileVersion(BaseModel):
    """Represents a file version"""
    id: Optional[int] = None
    file_path: str
    version: int
    content_hash: str
    content: Optional[bytes] = None
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None


class VersioningService:
    """Main versioning service"""
    
    def __init__(self):
        self.diff_engine = DiffEngine()
        self.workspace_root = Path("./workspace")
        self.version_storage = Path("./data/versions")
        self.version_storage.mkdir(parents=True, exist_ok=True)
        self._auto_snapshot_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize versioning service"""
        if not config.versioning.enable_versioning:
            logger.info("Versioning service disabled in configuration")
            return
        
        logger.info("Initializing versioning service...")
        
        # Start auto-snapshot task if enabled
        if config.versioning.auto_snapshot:
            self._running = True
            self._auto_snapshot_task = asyncio.create_task(self._auto_snapshot_loop())
        
        logger.info("Versioning service initialized")
    
    async def stop(self):
        """Stop versioning service"""
        logger.info("Stopping versioning service...")
        self._running = False
        
        if self._auto_snapshot_task:
            self._auto_snapshot_task.cancel()
            try:
                await self._auto_snapshot_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Versioning service stopped")
    
    async def create_version(self, file_path: str, content: Optional[bytes] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create a new version of a file"""
        try:
            # If content not provided, read from file
            if content is None:
                full_path = self.workspace_root / file_path
                if not full_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                async with aiofiles.open(full_path, 'rb') as f:
                    content = await f.read()
            
            # Calculate content hash
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Check if this version already exists
            latest_version = await self.get_latest_version(file_path)
            if latest_version and latest_version.content_hash == content_hash:
                logger.debug(f"Content unchanged for {file_path}, skipping version creation")
                return latest_version.id
            
            # Create version metadata
            version_metadata = metadata or {}
            version_metadata.update({
                "file_size": len(content),
                "created_by": "system",
                "creation_method": "manual"
            })
            
            # Save to database
            version_id = await db_version_service.create_version(
                file_path=file_path,
                content=content,
                metadata=version_metadata
            )
            
            # Save to file system if configured
            if config.versioning.storage_backend == "filesystem":
                await self._save_version_to_filesystem(version_id, file_path, content)
            
            logger.info(f"Created version {version_id} for {file_path}")
            return version_id
            
        except Exception as e:
            logger.error(f"Error creating version for {file_path}: {e}")
            raise
    
    async def get_version(self, file_path: str, version: int) -> Optional[FileVersion]:
        """Get a specific version of a file"""
        try:
            # Get from database
            version_data = await db_version_service.get_version(file_path, version)
            if not version_data:
                return None
            
            # Load content if needed
            content = version_data.get('content')
            if content is None and config.versioning.storage_backend == "filesystem":
                content = await self._load_version_from_filesystem(
                    version_data['id'], file_path
                )
            
            return FileVersion(**version_data, content=content)
            
        except Exception as e:
            logger.error(f"Error getting version {version} for {file_path}: {e}")
            return None
    
    async def get_latest_version(self, file_path: str) -> Optional[FileVersion]:
        """Get the latest version of a file"""
        try:
            version_data = await db_version_service.get_latest_version(file_path)
            if not version_data:
                return None
            
            # Load content if needed
            content = version_data.get('content')
            if content is None and config.versioning.storage_backend == "filesystem":
                content = await self._load_version_from_filesystem(
                    version_data['id'], file_path
                )
            
            return FileVersion(**version_data, content=content)
            
        except Exception as e:
            logger.error(f"Error getting latest version for {file_path}: {e}")
            return None
    
    async def list_versions(self, file_path: str, limit: int = 50) -> List[FileVersion]:
        """List all versions of a file"""
        try:
            versions_data = await db_version_service.list_versions(file_path)
            
            versions = []
            for version_data in versions_data[:limit]:
                # For list view, don't load content by default
                versions.append(FileVersion(**version_data))
            
            return versions
            
        except Exception as e:
            logger.error(f"Error listing versions for {file_path}: {e}")
            return []
    
    async def restore_version(self, file_path: str, version: int) -> bool:
        """Restore a file to a specific version"""
        try:
            # Get the version to restore
            file_version = await self.get_version(file_path, version)
            if not file_version:
                logger.error(f"Version {version} not found for {file_path}")
                return False
            
            # Write content to file
            full_path = self.workspace_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(file_version.content)
            
            logger.info(f"Restored {file_path} to version {version}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring version {version} for {file_path}: {e}")
            return False
    
    async def compare_versions(self, file_path: str, version1: int, version2: int) -> Dict[str, Any]:
        """Compare two versions of a file"""
        try:
            # Get both versions
            v1 = await self.get_version(file_path, version1)
            v2 = await self.get_version(file_path, version2)
            
            if not v1 or not v2:
                raise ValueError("One or both versions not found")
            
            # Generate diff
            diff_result = await self.diff_engine.compare_text(
                v1.content.decode('utf-8', errors='ignore'),
                v2.content.decode('utf-8', errors='ignore')
            )
            
            return {
                "file_path": file_path,
                "version1": version1,
                "version2": version2,
                "diff": diff_result,
                "version1_info": {
                    "version": v1.version,
                    "created_at": v1.created_at,
                    "content_hash": v1.content_hash,
                    "metadata": v1.metadata
                },
                "version2_info": {
                    "version": v2.version,
                    "created_at": v2.created_at,
                    "content_hash": v2.content_hash,
                    "metadata": v2.metadata
                }
            }
            
        except Exception as e:
            logger.error(f"Error comparing versions for {file_path}: {e}")
            return {"error": str(e)}
    
    async def delete_old_versions(self, file_path: Optional[str] = None):
        """Delete old versions based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=config.versioning.retention_days)
            
            if file_path:
                # Delete versions for specific file
                await self._delete_old_versions_for_file(file_path, cutoff_date)
            else:
                # Get all files with versions
                async with await database_service.get_connection() as db:
                    cursor = await db.execute("""
                        SELECT DISTINCT file_path FROM file_versions 
                        WHERE created_at < ?
                    """, (cutoff_date.isoformat(),))
                    
                    files = await cursor.fetchall()
                    
                    for (file_path,) in files:
                        await self._delete_old_versions_for_file(file_path, cutoff_date)
            
            logger.info("Completed cleanup of old versions")
            
        except Exception as e:
            logger.error(f"Error deleting old versions: {e}")
    
    async def _delete_old_versions_for_file(self, file_path: str, cutoff_date: datetime):
        """Delete old versions for a specific file"""
        try:
            # Get versions to keep (most recent N)
            versions = await self.list_versions(file_path)
            versions.sort(key=lambda v: v.version, reverse=True)
            
            versions_to_keep = versions[:config.versioning.max_versions_per_file]
            keep_versions = {v.version for v in versions_to_keep}
            
            # Delete old versions from database
            async with await database_service.get_connection() as db:
                await db.execute("""
                    DELETE FROM file_versions 
                    WHERE file_path = ? AND created_at < ? AND version NOT IN ({})
                """.format(','.join('?' * len(keep_versions))),
                    [file_path, cutoff_date.isoformat()] + list(keep_versions)
                )
                await db.commit()
            
            # Delete from filesystem if configured
            if config.versioning.storage_backend == "filesystem":
                await self._cleanup_filesystem_versions(file_path, keep_versions)
            
        except Exception as e:
            logger.error(f"Error deleting old versions for {file_path}: {e}")
    
    async def _save_version_to_filesystem(self, version_id: int, file_path: str, content: bytes):
        """Save version content to filesystem"""
        try:
            # Create version file path
            version_dir = self.version_storage / Path(file_path).parent
            version_dir.mkdir(parents=True, exist_ok=True)
            
            version_file = version_dir / f"{Path(file_path).name}.v{version_id}"
            
            async with aiofiles.open(version_file, 'wb') as f:
                await f.write(content)
            
        except Exception as e:
            logger.error(f"Error saving version to filesystem: {e}")
    
    async def _load_version_from_filesystem(self, version_id: int, file_path: str) -> Optional[bytes]:
        """Load version content from filesystem"""
        try:
            version_file = (self.version_storage / Path(file_path).parent / 
                          f"{Path(file_path).name}.v{version_id}")
            
            if not version_file.exists():
                return None
            
            async with aiofiles.open(version_file, 'rb') as f:
                return await f.read()
                
        except Exception as e:
            logger.error(f"Error loading version from filesystem: {e}")
            return None
    
    async def _cleanup_filesystem_versions(self, file_path: str, keep_versions: set):
        """Clean up filesystem versions"""
        try:
            version_dir = self.version_storage / Path(file_path).parent
            if not version_dir.exists():
                return
            
            base_name = Path(file_path).name
            for version_file in version_dir.glob(f"{base_name}.v*"):
                try:
                    version_num = int(version_file.suffix[2:])  # Remove .v prefix
                    if version_num not in keep_versions:
                        version_file.unlink()
                except ValueError:
                    continue  # Skip invalid version files
                    
        except Exception as e:
            logger.error(f"Error cleaning up filesystem versions: {e}")
    
    async def _auto_snapshot_loop(self):
        """Automatic snapshot loop"""
        while self._running:
            try:
                await self._create_auto_snapshot()
                await asyncio.sleep(config.versioning.snapshot_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-snapshot loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _create_auto_snapshot(self):
        """Create automatic snapshot of workspace"""
        try:
            logger.debug("Creating auto-snapshot...")
            
            # Get all files in workspace
            if not self.workspace_root.exists():
                return
            
            snapshot_count = 0
            for file_path in self.workspace_root.rglob("*"):
                if file_path.is_file():
                    try:
                        relative_path = file_path.relative_to(self.workspace_root)
                        await self.create_version(
                            str(relative_path),
                            metadata={"creation_method": "auto_snapshot"}
                        )
                        snapshot_count += 1
                    except Exception as e:
                        logger.warning(f"Error snapshotting {file_path}: {e}")
            
            logger.debug(f"Auto-snapshot completed: {snapshot_count} files")
            
        except Exception as e:
            logger.error(f"Error creating auto-snapshot: {e}")
    
    async def get_version_statistics(self) -> Dict[str, Any]:
        """Get versioning statistics"""
        try:
            async with await database_service.get_connection() as db:
                # Get total versions
                cursor = await db.execute("SELECT COUNT(*) FROM file_versions")
                total_versions = (await cursor.fetchone())[0]
                
                # Get unique files
                cursor = await db.execute("SELECT COUNT(DISTINCT file_path) FROM file_versions")
                unique_files = (await cursor.fetchone())[0]
                
                # Get storage usage
                cursor = await db.execute("SELECT SUM(LENGTH(content)) FROM file_versions WHERE content IS NOT NULL")
                storage_bytes = (await cursor.fetchone())[0] or 0
                
                # Get recent versions
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM file_versions 
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                recent_versions = (await cursor.fetchone())[0]
                
                return {
                    "total_versions": total_versions,
                    "unique_files": unique_files,
                    "storage_bytes": storage_bytes,
                    "storage_mb": storage_bytes / (1024 * 1024),
                    "recent_versions_24h": recent_versions,
                    "storage_backend": config.versioning.storage_backend,
                    "auto_snapshot_enabled": config.versioning.auto_snapshot
                }
                
        except Exception as e:
            logger.error(f"Error getting version statistics: {e}")
            return {}


# Global versioning service instance
versioning_service = VersioningService()
