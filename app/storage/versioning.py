"""Versioning engine for tracking file versions with content-addressable storage."""

import hashlib
import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT
from app.logger import logger
from app.storage.audit import audit_logger, AuditEventType


class FileVersion(BaseModel):
    """Represents a single version of a file."""
    
    version_id: str = Field(..., description="Unique version identifier")
    file_path: str = Field(..., description="Path to the file")
    content_hash: str = Field(..., description="SHA256 hash of the content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Version creation timestamp")
    size: int = Field(..., description="File size in bytes")
    author: str = Field(default="system", description="Author of the version")
    message: Optional[str] = Field(None, description="Commit message")
    parent_version: Optional[str] = Field(None, description="Parent version ID")
    tags: List[str] = Field(default_factory=list, description="Tags for this version")


class VersioningEngine:
    """Content-addressable versioning engine with deduplication."""
    
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
        self._versions_dir = PROJECT_ROOT / "data" / "versions"
        self._objects_dir = self._versions_dir / "objects"
        self._index_dir = self._versions_dir / "index"
        
        self._versions_dir.mkdir(parents=True, exist_ok=True)
        self._objects_dir.mkdir(parents=True, exist_ok=True)
        self._index_dir.mkdir(parents=True, exist_ok=True)
        
        self._version_index: Dict[str, List[FileVersion]] = {}
        self._load_index()
        
        logger.info(f"VersioningEngine initialized with storage: {self._versions_dir}")
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    def _get_object_path(self, content_hash: str) -> Path:
        """Get the storage path for a content object.
        
        Uses a two-level directory structure for better filesystem performance.
        """
        return self._objects_dir / content_hash[:2] / content_hash[2:4] / content_hash
    
    def _store_object(self, content: bytes) -> str:
        """Store content in the object store and return its hash.
        
        Args:
            content: Content to store
            
        Returns:
            Content hash
        """
        content_hash = self._compute_hash(content)
        object_path = self._get_object_path(content_hash)
        
        if not object_path.exists():
            object_path.parent.mkdir(parents=True, exist_ok=True)
            with open(object_path, 'wb') as f:
                f.write(content)
            logger.debug(f"Stored object: {content_hash}")
        else:
            logger.debug(f"Object already exists: {content_hash}")
        
        return content_hash
    
    def _retrieve_object(self, content_hash: str) -> Optional[bytes]:
        """Retrieve content from the object store.
        
        Args:
            content_hash: Hash of the content to retrieve
            
        Returns:
            Content bytes or None if not found
        """
        object_path = self._get_object_path(content_hash)
        
        if not object_path.exists():
            logger.error(f"Object not found: {content_hash}")
            return None
        
        with open(object_path, 'rb') as f:
            return f.read()
    
    def _save_index(self) -> None:
        """Save the version index to disk."""
        with self._lock:
            for file_path, versions in self._version_index.items():
                safe_filename = file_path.replace('/', '_').replace('\\', '_')
                index_file = self._index_dir / f"{safe_filename}.json"
                
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump([v.model_dump(mode='json') for v in versions], f, indent=2, default=str)
    
    def _load_index(self) -> None:
        """Load the version index from disk."""
        with self._lock:
            for index_file in self._index_dir.glob("*.json"):
                try:
                    with open(index_file, 'r', encoding='utf-8') as f:
                        versions_data = json.load(f)
                        versions = [FileVersion.model_validate(v) for v in versions_data]
                        
                        if versions:
                            file_path = versions[0].file_path
                            self._version_index[file_path] = versions
                except Exception as e:
                    logger.error(f"Error loading index file {index_file}: {e}")
    
    def create_version(
        self,
        file_path: str,
        content: bytes,
        author: str = "system",
        message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> FileVersion:
        """Create a new version of a file.
        
        Args:
            file_path: Path to the file
            content: File content
            author: Author of the version
            message: Commit message
            tags: Tags for this version
            
        Returns:
            The created FileVersion
        """
        with self._lock:
            content_hash = self._store_object(content)
            
            existing_versions = self._version_index.get(file_path, [])
            parent_version = existing_versions[-1].version_id if existing_versions else None
            
            version = FileVersion(
                version_id=f"{content_hash[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                file_path=file_path,
                content_hash=content_hash,
                size=len(content),
                author=author,
                message=message,
                parent_version=parent_version,
                tags=tags or []
            )
            
            if file_path not in self._version_index:
                self._version_index[file_path] = []
            
            self._version_index[file_path].append(version)
            self._save_index()
            
            audit_logger.log_event(
                AuditEventType.VERSION_CREATED,
                user=author,
                resource=file_path,
                details={"version_id": version.version_id, "content_hash": content_hash}
            )
            
            logger.info(f"Created version {version.version_id} for {file_path}")
            return version
    
    def get_version(self, file_path: str, version_id: str) -> Optional[FileVersion]:
        """Get a specific version of a file.
        
        Args:
            file_path: Path to the file
            version_id: Version identifier
            
        Returns:
            The FileVersion or None if not found
        """
        versions = self._version_index.get(file_path, [])
        for version in versions:
            if version.version_id == version_id:
                return version
        return None
    
    def get_version_content(self, version: FileVersion) -> Optional[bytes]:
        """Get the content of a specific version.
        
        Args:
            version: The FileVersion to retrieve
            
        Returns:
            Content bytes or None if not found
        """
        return self._retrieve_object(version.content_hash)
    
    def get_versions(self, file_path: str) -> List[FileVersion]:
        """Get all versions of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of FileVersions
        """
        return self._version_index.get(file_path, [])
    
    def get_latest_version(self, file_path: str) -> Optional[FileVersion]:
        """Get the latest version of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The latest FileVersion or None if no versions exist
        """
        versions = self._version_index.get(file_path, [])
        return versions[-1] if versions else None
    
    def diff_versions(self, version1: FileVersion, version2: FileVersion) -> Optional[str]:
        """Generate a diff between two versions.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            Unified diff string or None on error
        """
        try:
            import difflib
            
            content1 = self.get_version_content(version1)
            content2 = self.get_version_content(version2)
            
            if content1 is None or content2 is None:
                return None
            
            lines1 = content1.decode('utf-8', errors='replace').splitlines(keepends=True)
            lines2 = content2.decode('utf-8', errors='replace').splitlines(keepends=True)
            
            diff = difflib.unified_diff(
                lines1, lines2,
                fromfile=f"{version1.file_path} ({version1.version_id})",
                tofile=f"{version2.file_path} ({version2.version_id})",
                lineterm=''
            )
            
            return '\n'.join(diff)
        except Exception as e:
            logger.error(f"Error generating diff: {e}")
            return None
    
    def get_all_files(self) -> List[str]:
        """Get all files tracked by the versioning engine.
        
        Returns:
            List of file paths
        """
        return list(self._version_index.keys())
    
    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        total_versions = sum(len(versions) for versions in self._version_index.values())
        total_objects = sum(1 for _ in self._objects_dir.rglob("*") if _.is_file())
        
        total_size = 0
        for obj_file in self._objects_dir.rglob("*"):
            if obj_file.is_file():
                total_size += obj_file.stat().st_size
        
        return {
            "total_files": len(self._version_index),
            "total_versions": total_versions,
            "total_objects": total_objects,
            "total_size_bytes": total_size
        }
    
    def tag_version(self, file_path: str, version_id: str, tag: str) -> bool:
        """Add a tag to a version.
        
        Args:
            file_path: Path to the file
            version_id: Version identifier
            tag: Tag to add
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            version = self.get_version(file_path, version_id)
            if not version:
                return False
            
            if tag not in version.tags:
                version.tags.append(tag)
                self._save_index()
                logger.info(f"Tagged version {version_id} with '{tag}'")
                return True
            
            return False
    
    def delete_version(self, file_path: str, version_id: str) -> bool:
        """Delete a specific version.
        
        Note: This only removes the version from the index, not the object store
        (to maintain integrity of other versions that might reference the same content).
        
        Args:
            file_path: Path to the file
            version_id: Version identifier
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            versions = self._version_index.get(file_path, [])
            version = next((v for v in versions if v.version_id == version_id), None)
            
            if not version:
                return False
            
            versions.remove(version)
            if not versions:
                del self._version_index[file_path]
            
            self._save_index()
            
            audit_logger.log_event(
                AuditEventType.VERSION_DELETED,
                resource=file_path,
                details={"version_id": version_id}
            )
            
            logger.info(f"Deleted version {version_id} for {file_path}")
            return True


def get_versioning_engine() -> VersioningEngine:
    """Get the singleton versioning engine instance."""
    return VersioningEngine()
