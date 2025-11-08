"""
Service layer for integrating versioning with file operations.
Provides hooks for automatic versioning of file changes.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

from app.config import config
from app.logger import logger
from app.storage.versioning import get_versioning_engine


class VersioningService:
    """
    Service layer that integrates versioning with file operations.
    Provides automatic versioning hooks for editors and tools.
    """
    
    def __init__(self):
        self._versioning_engine = None
        self._lock = Lock()
        self._enabled = True
    
    def _get_engine(self):
        """Lazy load the versioning engine."""
        if self._versioning_engine is None:
            with self._lock:
                if self._versioning_engine is None:
                    self._versioning_engine = get_versioning_engine()
        return self._versioning_engine
    
    def is_enabled(self) -> bool:
        """Check if versioning service is enabled."""
        return self._enabled and config.versioning.enable_versioning
    
    def enable(self):
        """Enable versioning service."""
        self._enabled = True
        logger.info("Versioning service enabled")
    
    def disable(self):
        """Disable versioning service."""
        self._enabled = False
        logger.info("Versioning service disabled")
    
    def on_file_save(
        self,
        file_path: str,
        content: str,
        agent: str = "system",
        reason: str = "File saved"
    ) -> Optional[str]:
        """
        Hook called when a file is saved.
        
        Args:
            file_path: Path to the saved file (relative to project root)
            content: File content
            agent: Agent that performed the save
            reason: Reason for the save
            
        Returns:
            Version ID if version was created, None otherwise
        """
        if not self.is_enabled():
            return None
        
        try:
            engine = self._get_engine()
            # Convert to relative path if absolute
            if os.path.isabs(file_path):
                project_root = Path(config.project.project_root)
                try:
                    file_path = str(Path(file_path).relative_to(project_root))
                except ValueError:
                    # File is outside project root, don't version
                    logger.debug(f"File {file_path} is outside project root, skipping versioning")
                    return None
            
            version_id = engine.create_version(file_path, content, agent, reason)
            if version_id:
                logger.debug(f"Created version {version_id} for {file_path}")
            
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to create version for {file_path}: {e}")
            return None
    
    def on_file_edit(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        agent: str = "system",
        reason: str = "File edited"
    ) -> Optional[str]:
        """
        Hook called when a file is edited.
        
        Args:
            file_path: Path to the edited file
            old_content: Previous content
            new_content: New content
            agent: Agent that performed the edit
            reason: Reason for the edit
            
        Returns:
            Version ID if version was created, None otherwise
        """
        # Only create version if content actually changed
        if old_content == new_content:
            return None
        
        return self.on_file_save(file_path, new_content, agent, reason)
    
    def create_snapshot(
        self,
        name: str,
        file_paths: list,
        description: str = "",
        agent: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a snapshot of multiple files.
        
        Args:
            name: Snapshot name
            file_paths: List of file paths to include
            description: Snapshot description
            agent: Agent creating the snapshot
            metadata: Additional metadata
            
        Returns:
            Snapshot ID if created, None otherwise
        """
        if not self.is_enabled():
            return None
        
        try:
            engine = self._get_engine()
            return engine.create_snapshot(name, file_paths, description, agent, metadata)
        except Exception as e:
            logger.error(f"Failed to create snapshot {name}: {e}")
            return None
    
    def rollback_file(
        self,
        file_path: str,
        version_id: str,
        agent: str = "system",
        reason: str = "Rollback operation"
    ) -> bool:
        """
        Rollback a file to a specific version.
        
        Args:
            file_path: Path to the file to rollback
            version_id: Target version ID
            agent: Agent performing the rollback
            reason: Reason for rollback
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            engine = self._get_engine()
            return engine.rollback_to_version(version_id, agent, reason)
        except Exception as e:
            logger.error(f"Failed to rollback {file_path} to version {version_id}: {e}")
            return False
    
    def get_version_history(self, file_path: str, limit: int = 50, offset: int = 0):
        """Get version history for a file."""
        if not self.is_enabled():
            return []
        
        try:
            engine = self._get_engine()
            return engine.get_version_history(file_path, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get version history for {file_path}: {e}")
            return []
    
    def get_file_diff(self, from_version_id: str, to_version_id: Optional[str] = None) -> str:
        """Get diff between two versions."""
        if not self.is_enabled():
            return ""
        
        try:
            engine = self._get_engine()
            return engine.generate_diff(from_version_id, to_version_id)
        except Exception as e:
            logger.error(f"Failed to generate diff: {e}")
            return ""
    
    def get_version_content(self, version_id: str) -> Optional[str]:
        """Get content for a specific version."""
        if not self.is_enabled():
            return None
        
        try:
            engine = self._get_engine()
            return engine.get_version_content(version_id)
        except Exception as e:
            logger.error(f"Failed to get content for version {version_id}: {e}")
            return None


# Global service instance
_versioning_service: Optional[VersioningService] = None
_service_lock = Lock()


def get_versioning_service() -> VersioningService:
    """Get the global versioning service instance."""
    global _versioning_service
    
    if _versioning_service is None:
        with _service_lock:
            if _versioning_service is None:
                _versioning_service = VersioningService()
    
    return _versioning_service