"""
Versioning Engine for tracking file changes with SQLite backend.
Provides content-addressable storage, deduplication, snapshots, and rollback support.
"""

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from difflib import unified_diff
from dataclasses import dataclass, asdict
import tempfile
import shutil
import fnmatch
import glob

from app.config import config, PROJECT_ROOT
from app.logger import logger


@dataclass
class VersionMetadata:
    """Metadata for a file version."""
    file_path: str
    version_id: str
    content_hash: str
    timestamp: datetime
    agent: str
    reason: str
    size: int
    is_snapshot: bool = False
    snapshot_id: Optional[str] = None


@dataclass
class SnapshotMetadata:
    """Metadata for a workflow snapshot."""
    snapshot_id: str
    name: str
    description: str
    timestamp: datetime
    agent: str
    file_versions: List[str]  # List of version_ids
    metadata: Dict[str, Any]


class VersioningEngine:
    """
    SQLite-backed versioning engine with content-addressable storage.
    
    Features:
    - Automatic version creation on file changes
    - Content deduplication via SHA-256 hashing
    - Snapshot support for workflow states
    - Rollback capabilities with diff generation
    - Configurable retention policies
    """
    
    def __init__(self, db_path: Optional[Path] = None, storage_path: Optional[Path] = None):
        """
        Initialize the versioning engine.
        
        Args:
            db_path: Path to SQLite database (default: from config)
            storage_path: Path to content storage directory (default: from config)
        """
        self.project_root = Path(PROJECT_ROOT)
        self.settings = config.versioning
        
        # Use configured paths or defaults
        if db_path is None:
            db_path = self.project_root / self.settings.database_path
        if storage_path is None:
            storage_path = self.project_root / self.settings.storage_path
            
        self.db_path = Path(db_path)
        self.storage_path = Path(storage_path)
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"VersioningEngine initialized with DB: {self.db_path}, Storage: {self.storage_path}")
    
    def _should_track_file(self, file_path: str) -> bool:
        """
        Check if a file should be tracked based on configuration patterns.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if file should be tracked, False otherwise
        """
        # Check exclude patterns first
        for pattern in self.settings.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern) or glob.fnmatch.fnmatch(file_path, pattern):
                return False
        
        # Check include patterns
        for pattern in self.settings.track_file_patterns:
            if fnmatch.fnmatch(file_path, pattern) or glob.fnmatch.fnmatch(file_path, pattern):
                return True
        
        # Default to not tracking if no patterns match
        return False
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS file_blobs (
                    content_hash TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    storage_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS versions (
                    version_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    agent TEXT NOT NULL,
                    reason TEXT,
                    is_snapshot BOOLEAN DEFAULT FALSE,
                    snapshot_id TEXT,
                    FOREIGN KEY (content_hash) REFERENCES file_blobs(content_hash)
                );
                
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    agent TEXT NOT NULL,
                    metadata TEXT  -- JSON metadata
                );
                
                CREATE TABLE IF NOT EXISTS snapshot_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id),
                    FOREIGN KEY (version_id) REFERENCES versions(version_id),
                    UNIQUE(snapshot_id, version_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_versions_file_path ON versions(file_path);
                CREATE INDEX IF NOT EXISTS idx_versions_timestamp ON versions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_versions_content_hash ON versions(content_hash);
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp);
            """)
            conn.commit()
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _store_content(self, content: str, content_hash: str) -> str:
        """
        Store content in content-addressable storage.
        
        Args:
            content: Content to store
            content_hash: Pre-calculated hash
            
        Returns:
            Path to stored content
        """
        storage_file = self.storage_path / content_hash
        
        # Only store if not already exists (deduplication)
        if not storage_file.exists():
            # Ensure storage directory exists
            self.storage_path.mkdir(parents=True, exist_ok=True)
            with open(storage_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return str(storage_file)
    
    def _load_content(self, content_hash: str) -> str:
        """
        Load content from storage by hash.
        
        Args:
            content_hash: Hash of content to load
            
        Returns:
            Content string
            
        Raises:
            FileNotFoundError: If content hash not found
        """
        storage_file = self.storage_path / content_hash
        if not storage_file.exists():
            raise FileNotFoundError(f"Content with hash {content_hash} not found")
        
        with open(storage_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def create_version(
        self,
        file_path: str,
        content: str,
        agent: str = "system",
        reason: str = "File saved"
    ) -> Optional[str]:
        """
        Create a new version for a file.
        
        Args:
            file_path: Path to the file (relative to project root)
            content: File content
            agent: Agent making the change
            reason: Reason for the change
            
        Returns:
            Version ID if created, None if skipped
        """
        # Check if versioning is enabled
        if not self.settings.enable_versioning:
            return None
        
        # Check if file should be tracked
        if not self._should_track_file(file_path):
            logger.debug(f"File {file_path} not tracked by versioning patterns")
            return None
        
        with self._lock:
            content_hash = self._calculate_hash(content)
            timestamp = datetime.now()
            version_id = f"{file_path.replace('/', '_')}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Store content if not already exists
            storage_path = self._store_content(content, content_hash)
            
            # Check if this is a duplicate version (same content as latest)
            latest_version = self.get_latest_version(file_path)
            if latest_version and latest_version.content_hash == content_hash:
                logger.debug(f"Skipping duplicate version for {file_path} (hash: {content_hash})")
                return latest_version.version_id
            
            with sqlite3.connect(self.db_path) as conn:
                # Insert blob if not exists
                conn.execute(
                    "INSERT OR IGNORE INTO file_blobs (content_hash, size, storage_path) VALUES (?, ?, ?)",
                    (content_hash, len(content), storage_path)
                )
                
                # Insert version
                conn.execute(
                    """
                    INSERT INTO versions (version_id, file_path, content_hash, timestamp, agent, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (version_id, file_path, content_hash, timestamp, agent, reason)
                )
                conn.commit()
            
            logger.info(f"Created version {version_id} for {file_path} by {agent}")
            return version_id
    
    def get_version(self, version_id: str) -> Optional[VersionMetadata]:
        """Get version metadata by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT v.*, fb.size 
                FROM versions v
                JOIN file_blobs fb ON v.content_hash = fb.content_hash
                WHERE v.version_id = ?
                """,
                (version_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return VersionMetadata(
                    file_path=row['file_path'],
                    version_id=row['version_id'],
                    content_hash=row['content_hash'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    agent=row['agent'],
                    reason=row['reason'] or "",
                    size=row['size'],
                    is_snapshot=bool(row['is_snapshot']),
                    snapshot_id=row['snapshot_id']
                )
        return None
    
    def get_version_content(self, version_id: str) -> Optional[str]:
        """Get content for a specific version."""
        version = self.get_version(version_id)
        if not version:
            return None
        
        try:
            return self._load_content(version.content_hash)
        except FileNotFoundError:
            logger.error(f"Content not found for version {version_id}")
            return None
    
    def get_latest_version(self, file_path: str) -> Optional[VersionMetadata]:
        """Get the latest version for a file."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT v.*, fb.size 
                FROM versions v
                JOIN file_blobs fb ON v.content_hash = fb.content_hash
                WHERE v.file_path = ?
                ORDER BY v.timestamp DESC
                LIMIT 1
                """,
                (file_path,)
            )
            row = cursor.fetchone()
            
            if row:
                return VersionMetadata(
                    file_path=row['file_path'],
                    version_id=row['version_id'],
                    content_hash=row['content_hash'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    agent=row['agent'],
                    reason=row['reason'] or "",
                    size=row['size'],
                    is_snapshot=bool(row['is_snapshot']),
                    snapshot_id=row['snapshot_id']
                )
        return None
    
    def get_version_history(
        self,
        file_path: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        """Get version history for a file."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT v.*, fb.size 
                FROM versions v
                JOIN file_blobs fb ON v.content_hash = fb.content_hash
                WHERE v.file_path = ?
                ORDER BY v.timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (file_path, limit, offset)
            )
            
            return [
                VersionMetadata(
                    file_path=row['file_path'],
                    version_id=row['version_id'],
                    content_hash=row['content_hash'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    agent=row['agent'],
                    reason=row['reason'] or "",
                    size=row['size'],
                    is_snapshot=bool(row['is_snapshot']),
                    snapshot_id=row['snapshot_id']
                )
                for row in cursor.fetchall()
            ]
    
    def generate_diff(
        self,
        from_version_id: str,
        to_version_id: Optional[str] = None,
        file_path: Optional[str] = None,
        context_lines: int = 3
    ) -> str:
        """
        Generate unified diff between two versions.
        
        Args:
            from_version_id: Source version ID
            to_version_id: Target version ID (None for latest)
            file_path: File path for context
            context_lines: Number of context lines in diff
            
        Returns:
            Unified diff string
        """
        from_content = self.get_version_content(from_version_id)
        if from_content is None:
            raise ValueError(f"Version {from_version_id} not found")
        
        if to_version_id:
            to_content = self.get_version_content(to_version_id)
            if to_content is None:
                raise ValueError(f"Version {to_version_id} not found")
        else:
            # Get latest version of the same file
            from_version = self.get_version(from_version_id)
            if not from_version:
                raise ValueError(f"Version {from_version_id} not found")
            
            latest_version = self.get_latest_version(from_version.file_path)
            if latest_version:
                to_content = self.get_version_content(latest_version.version_id)
                to_version_id = latest_version.version_id
            else:
                to_content = ""
        
        from_lines = from_content.splitlines(keepends=True)
        to_lines = to_content.splitlines(keepends=True)
        
        from_version = self.get_version(from_version_id)
        to_version = self.get_version(to_version_id) if to_version_id else None
        
        from_file = file_path or (from_version.file_path if from_version else "from_file")
        to_file = file_path or (to_version.file_path if to_version else "to_file")
        
        from_timestamp = from_version.timestamp.strftime("%Y-%m-%d %H:%M:%S") if from_version else ""
        to_timestamp = to_version.timestamp.strftime("%Y-%m-%d %H:%M:%S") if to_version else ""
        
        diff = unified_diff(
            from_lines,
            to_lines,
            fromfile=f"{from_file} ({from_timestamp})",
            tofile=f"{to_file} ({to_timestamp})",
            n=context_lines
        )
        
        return "".join(diff)
    
    def rollback_to_version(self, version_id: str, agent: str = "system", reason: str = "Rollback operation") -> bool:
        """
        Rollback a file to a specific version.
        
        Args:
            version_id: Target version ID to rollback to
            agent: Agent performing the rollback
            reason: Reason for rollback
            
        Returns:
            True if successful, False otherwise
        """
        version = self.get_version(version_id)
        if not version:
            logger.error(f"Version {version_id} not found")
            return False
        
        content = self.get_version_content(version_id)
        if content is None:
            logger.error(f"Content not found for version {version_id}")
            return False
        
        # Guardian checks if enabled
        if self.settings.enable_guardian_checks:
            if not self._perform_guardian_checks(version, agent, reason):
                logger.warning(f"Guardian checks failed for rollback of {version.file_path} to version {version_id}")
                return False
        
        # Write content back to file
        file_full_path = self.project_root / version.file_path
        try:
            # Ensure directory exists
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create a new version for the rollback
            self.create_version(
                version.file_path,
                content,
                agent=agent,
                reason=f"Rollback to {version_id}: {reason}"
            )
            
            logger.info(f"Rolled back {version.file_path} to version {version_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback {version.file_path} to version {version_id}: {e}")
            return False
    
    def _perform_guardian_checks(self, version: VersionMetadata, agent: str, reason: str) -> bool:
        """
        Perform Guardian security checks before rollback operations.
        
        Args:
            version: Version metadata to rollback to
            agent: Agent performing the rollback
            reason: Reason for rollback
            
        Returns:
            True if checks pass, False otherwise
        """
        # For now, implement basic checks
        # This could be extended to integrate with the actual Guardian system
        
        # Check if agent is allowed to perform rollbacks
        allowed_agents = ["system", "admin", "developer"]
        if agent not in allowed_agents:
            logger.warning(f"Agent {agent} not authorized to perform rollbacks")
            return False
        
        # Check if rollback reason is provided
        if not reason or reason.strip() == "":
            logger.warning("Rollback reason not provided")
            return False
        
        # Check if version is too old (basic retention check)
        days_old = (datetime.now() - version.timestamp).days
        if days_old > self.settings.retention_days:
            logger.warning(f"Version {version.version_id} is {days_old} days old, exceeding retention policy")
            return False
        
        return True
    
    def create_snapshot(
        self,
        name: str,
        file_paths: List[str],
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
            Snapshot ID if created, None if skipped
        """
        # Check if snapshots are enabled
        if not self.settings.enable_snapshots:
            return None
        
        with self._lock:
            timestamp = datetime.now()
            snapshot_id = f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get current versions of all files
            version_ids = []
            for file_path in file_paths:
                latest_version = self.get_latest_version(file_path)
                if latest_version:
                    version_ids.append(latest_version.version_id)
                else:
                    logger.warning(f"No version found for file {file_path} in snapshot creation")
            
            with sqlite3.connect(self.db_path) as conn:
                # Insert snapshot
                conn.execute(
                    """
                    INSERT INTO snapshots (snapshot_id, name, description, timestamp, agent, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        name,
                        description,
                        timestamp,
                        agent,
                        json.dumps(metadata or {})
                    )
                )
                
                # Link snapshot to file versions
                for version_id in version_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO snapshot_files (snapshot_id, version_id) VALUES (?, ?)",
                        (snapshot_id, version_id)
                    )
                
                conn.commit()
            
            logger.info(f"Created snapshot {snapshot_id} with {len(version_ids)} files")
            return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot metadata by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT s.*, GROUP_CONCAT(sf.version_id) as version_ids
                FROM snapshots s
                LEFT JOIN snapshot_files sf ON s.snapshot_id = sf.snapshot_id
                WHERE s.snapshot_id = ?
                GROUP BY s.snapshot_id
                """,
                (snapshot_id,)
            )
            row = cursor.fetchone()
            
            if row:
                version_ids = row['version_ids'].split(',') if row['version_ids'] else []
                return SnapshotMetadata(
                    snapshot_id=row['snapshot_id'],
                    name=row['name'],
                    description=row['description'] or "",
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    agent=row['agent'],
                    file_versions=version_ids,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
        return None
    
    def restore_snapshot(self, snapshot_id: str, agent: str = "system", reason: str = "Snapshot restore") -> bool:
        """
        Restore all files in a snapshot to their saved versions.
        
        Args:
            snapshot_id: Snapshot ID to restore
            agent: Agent performing the restore
            reason: Reason for restore
            
        Returns:
            True if successful, False otherwise
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            logger.error(f"Snapshot {snapshot_id} not found")
            return False
        
        success = True
        for version_id in snapshot.file_versions:
            if not self.rollback_to_version(version_id, agent, f"Restore snapshot {snapshot_id}: {reason}"):
                success = False
                logger.error(f"Failed to restore version {version_id} from snapshot {snapshot_id}")
        
        if success:
            logger.info(f"Successfully restored snapshot {snapshot_id}")
        else:
            logger.warning(f"Partially restored snapshot {snapshot_id}")
        
        return success
    
    def list_snapshots(self, limit: int = 50, offset: int = 0) -> List[SnapshotMetadata]:
        """List all snapshots."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT s.*, GROUP_CONCAT(sf.version_id) as version_ids
                FROM snapshots s
                LEFT JOIN snapshot_files sf ON s.snapshot_id = sf.snapshot_id
                GROUP BY s.snapshot_id
                ORDER BY s.timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            
            return [
                SnapshotMetadata(
                    snapshot_id=row['snapshot_id'],
                    name=row['name'],
                    description=row['description'] or "",
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    agent=row['agent'],
                    file_versions=row['version_ids'].split(',') if row['version_ids'] else [],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                for row in cursor.fetchall()
            ]
    
    def cleanup_old_versions(self, days: int = 30, agent: Optional[str] = None) -> int:
        """
        Clean up old versions based on retention policy.
        
        Args:
            days: Delete versions older than this many days
            agent: Only delete versions by this agent (None for all)
            
        Returns:
            Number of versions deleted
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            query = "DELETE FROM versions WHERE timestamp < ?"
            params = [cutoff_date]
            
            if agent:
                query += " AND agent = ?"
                params.append(agent)
            
            cursor = conn.execute(query, params)
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} old versions (older than {days} days)")
        return deleted_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Count versions
            version_count = conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            
            # Count unique content blobs
            blob_count = conn.execute("SELECT COUNT(*) FROM file_blobs").fetchone()[0]
            
            # Total storage size
            total_size = conn.execute("SELECT SUM(size) FROM file_blobs").fetchone()[0] or 0
            
            # Count snapshots
            snapshot_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        
        # Calculate actual disk usage
        disk_usage = 0
        if self.storage_path.exists():
            for file_path in self.storage_path.iterdir():
                if file_path.is_file():
                    disk_usage += file_path.stat().st_size
        
        return {
            "version_count": version_count,
            "blob_count": blob_count,
            "total_size_bytes": total_size,
            "disk_usage_bytes": disk_usage,
            "snapshot_count": snapshot_count,
            "deduplication_ratio": total_size / disk_usage if disk_usage > 0 else 1.0,
            "storage_path": str(self.storage_path),
            "database_path": str(self.db_path)
        }


# Global instance
_versioning_engine: Optional[VersioningEngine] = None
_engine_lock = threading.Lock()


def get_versioning_engine() -> VersioningEngine:
    """Get the global versioning engine instance."""
    global _versioning_engine
    
    if _versioning_engine is None:
        with _engine_lock:
            if _versioning_engine is None:
                _versioning_engine = VersioningEngine()
    
    return _versioning_engine