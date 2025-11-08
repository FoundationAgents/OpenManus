"""
Snapshot Manager
Manages system snapshots and point-in-time recovery
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel

from app.logger import logger
from app.config import config
from app.versioning.versioning_service import versioning_service


class Snapshot(BaseModel):
    """Represents a system snapshot"""
    id: Optional[int] = None
    name: str
    description: str
    snapshot_type: str  # manual, auto, scheduled
    file_versions: Dict[str, int] = {}  # file_path -> version_id
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None


class SnapshotManager:
    """Manages system snapshots"""
    
    def __init__(self):
        self.snapshot_storage = Path("./data/snapshots")
        self.snapshot_storage.mkdir(parents=True, exist_ok=True)
        self._auto_snapshot_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize snapshot manager"""
        logger.info("Initializing snapshot manager...")
        
        # Start auto-snapshot task if enabled
        if config.versioning.auto_snapshot:
            self._running = True
            self._auto_snapshot_task = asyncio.create_task(self._auto_snapshot_loop())
        
        logger.info("Snapshot manager initialized")
    
    async def stop(self):
        """Stop snapshot manager"""
        logger.info("Stopping snapshot manager...")
        self._running = False
        
        if self._auto_snapshot_task:
            self._auto_snapshot_task.cancel()
            try:
                await self._auto_snapshot_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Snapshot manager stopped")
    
    async def create_snapshot(self, name: str, description: str = "",
                            file_paths: Optional[List[str]] = None,
                            snapshot_type: str = "manual") -> int:
        """Create a system snapshot"""
        try:
            logger.info(f"Creating snapshot: {name}")
            
            # Determine files to snapshot
            if file_paths is None:
                file_paths = await self._get_workspace_files()
            
            # Get current versions for all files
            file_versions = {}
            for file_path in file_paths:
                latest_version = await versioning_service.get_latest_version(file_path)
                if latest_version:
                    file_versions[file_path] = latest_version.version
                else:
                    # Create version if it doesn't exist
                    version_id = await versioning_service.create_version(file_path)
                    file_versions[file_path] = version_id
            
            # Create snapshot metadata
            snapshot = Snapshot(
                name=name,
                description=description,
                snapshot_type=snapshot_type,
                file_versions=file_versions,
                metadata={
                    "total_files": len(file_versions),
                    "created_by": "system",
                    "snapshot_method": "version_links"
                }
            )
            
            # Save snapshot
            snapshot_id = await self._save_snapshot(snapshot)
            
            logger.info(f"Created snapshot {snapshot_id}: {name} ({len(file_versions)} files)")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Error creating snapshot {name}: {e}")
            raise
    
    async def restore_snapshot(self, snapshot_id: int) -> bool:
        """Restore system to a snapshot"""
        try:
            # Load snapshot
            snapshot = await self._load_snapshot(snapshot_id)
            if not snapshot:
                logger.error(f"Snapshot {snapshot_id} not found")
                return False
            
            logger.info(f"Restoring snapshot: {snapshot.name}")
            
            # Restore each file to its snapshot version
            restored_count = 0
            failed_files = []
            
            for file_path, version_id in snapshot.file_versions.items():
                try:
                    success = await versioning_service.restore_version(file_path, version_id)
                    if success:
                        restored_count += 1
                    else:
                        failed_files.append(file_path)
                except Exception as e:
                    logger.error(f"Error restoring {file_path}: {e}")
                    failed_files.append(file_path)
            
            if failed_files:
                logger.warning(f"Failed to restore {len(failed_files)} files: {failed_files}")
            else:
                logger.info(f"Successfully restored snapshot: {snapshot.name} ({restored_count} files)")
            
            return len(failed_files) == 0
            
        except Exception as e:
            logger.error(f"Error restoring snapshot {snapshot_id}: {e}")
            return False
    
    async def list_snapshots(self, snapshot_type: Optional[str] = None) -> List[Snapshot]:
        """List available snapshots"""
        try:
            snapshots = []
            
            for snapshot_file in self.snapshot_storage.glob("*.json"):
                try:
                    with open(snapshot_file, 'r') as f:
                        snapshot_data = json.load(f)
                    
                    snapshot = Snapshot(**snapshot_data)
                    
                    # Filter by type if specified
                    if snapshot_type is None or snapshot.snapshot_type == snapshot_type:
                        snapshots.append(snapshot)
                        
                except Exception as e:
                    logger.error(f"Error loading snapshot {snapshot_file}: {e}")
            
            # Sort by creation date
            snapshots.sort(key=lambda s: s.created_at or datetime.min, reverse=True)
            return snapshots
            
        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
            return []
    
    async def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete a snapshot"""
        try:
            snapshot_file = self.snapshot_storage / f"snapshot_{snapshot_id}.json"
            if snapshot_file.exists():
                snapshot_file.unlink()
                logger.info(f"Deleted snapshot {snapshot_id}")
                return True
            else:
                logger.warning(f"Snapshot {snapshot_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting snapshot {snapshot_id}: {e}")
            return False
    
    async def compare_snapshots(self, snapshot_id1: int, snapshot_id2: int) -> Dict[str, Any]:
        """Compare two snapshots"""
        try:
            # Load both snapshots
            snapshot1 = await self._load_snapshot(snapshot_id1)
            snapshot2 = await self._load_snapshot(snapshot_id2)
            
            if not snapshot1 or not snapshot2:
                return {"error": "One or both snapshots not found"}
            
            # Compare file versions
            files1 = set(snapshot1.file_versions.keys())
            files2 = set(snapshot2.file_versions.keys())
            
            added_files = files2 - files1
            removed_files = files1 - files2
            common_files = files1 & files2
            
            changed_files = []
            for file_path in common_files:
                if snapshot1.file_versions[file_path] != snapshot2.file_versions[file_path]:
                    changed_files.append(file_path)
            
            return {
                "snapshot1": {
                    "id": snapshot_id1,
                    "name": snapshot1.name,
                    "created_at": snapshot1.created_at
                },
                "snapshot2": {
                    "id": snapshot_id2,
                    "name": snapshot2.name,
                    "created_at": snapshot2.created_at
                },
                "differences": {
                    "added_files": list(added_files),
                    "removed_files": list(removed_files),
                    "changed_files": changed_files,
                    "total_changes": len(added_files) + len(removed_files) + len(changed_files)
                }
            }
            
        except Exception as e:
            logger.error(f"Error comparing snapshots: {e}")
            return {"error": str(e)}
    
    async def _get_workspace_files(self) -> List[str]:
        """Get all files in workspace"""
        try:
            workspace_root = Path("./workspace")
            if not workspace_root.exists():
                return []
            
            files = []
            for file_path in workspace_root.rglob("*"):
                if file_path.is_file():
                    # Get relative path
                    relative_path = file_path.relative_to(workspace_root)
                    files.append(str(relative_path))
            
            return files
            
        except Exception as e:
            logger.error(f"Error getting workspace files: {e}")
            return []
    
    async def _save_snapshot(self, snapshot: Snapshot) -> int:
        """Save snapshot to file"""
        try:
            # Generate snapshot ID
            snapshot_id = int(datetime.now().timestamp())
            snapshot.id = snapshot_id
            snapshot.created_at = datetime.now()
            
            # Save to file
            snapshot_file = self.snapshot_storage / f"snapshot_{snapshot_id}.json"
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot.dict(), f, indent=2, default=str)
            
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            raise
    
    async def _load_snapshot(self, snapshot_id: int) -> Optional[Snapshot]:
        """Load snapshot from file"""
        try:
            snapshot_file = self.snapshot_storage / f"snapshot_{snapshot_id}.json"
            if not snapshot_file.exists():
                return None
            
            with open(snapshot_file, 'r') as f:
                snapshot_data = json.load(f)
            
            return Snapshot(**snapshot_data)
            
        except Exception as e:
            logger.error(f"Error loading snapshot {snapshot_id}: {e}")
            return None
    
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
        """Create automatic snapshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"auto_snapshot_{timestamp}"
            description = f"Automatic snapshot created at {datetime.now()}"
            
            await self.create_snapshot(
                name=name,
                description=description,
                snapshot_type="auto"
            )
            
        except Exception as e:
            logger.error(f"Error creating auto-snapshot: {e}")
    
    async def cleanup_old_snapshots(self):
        """Clean up old snapshots based on retention policy"""
        try:
            snapshots = await self.list_snapshots()
            
            # Keep snapshots from last 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            to_delete = []
            for snapshot in snapshots:
                if snapshot.created_at and snapshot.created_at < cutoff_date:
                    # Keep manual snapshots longer
                    if snapshot.snapshot_type == "auto":
                        to_delete.append(snapshot.id)
            
            # Delete old snapshots
            for snapshot_id in to_delete:
                await self.delete_snapshot(snapshot_id)
            
            if to_delete:
                logger.info(f"Cleaned up {len(to_delete)} old snapshots")
            
        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
    
    async def get_snapshot_statistics(self) -> Dict[str, Any]:
        """Get snapshot statistics"""
        try:
            snapshots = await self.list_snapshots()
            
            # Count by type
            type_counts = {}
            for snapshot in snapshots:
                snapshot_type = snapshot.snapshot_type
                type_counts[snapshot_type] = type_counts.get(snapshot_type, 0) + 1
            
            # Recent snapshots
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_snapshots = [
                s for s in snapshots 
                if s.created_at and s.created_at > recent_cutoff
            ]
            
            # Total files across all snapshots
            total_files = sum(len(s.file_versions) for s in snapshots)
            
            return {
                "total_snapshots": len(snapshots),
                "type_distribution": type_counts,
                "recent_snapshots_7d": len(recent_snapshots),
                "total_files": total_files,
                "average_files_per_snapshot": total_files / len(snapshots) if snapshots else 0,
                "oldest_snapshot": min((s.created_at for s in snapshots if s.created_at), default=None),
                "newest_snapshot": max((s.created_at for s in snapshots if s.created_at), default=None)
            }
            
        except Exception as e:
            logger.error(f"Error getting snapshot statistics: {e}")
            return {}


# Global snapshot manager instance
snapshot_manager = SnapshotManager()
