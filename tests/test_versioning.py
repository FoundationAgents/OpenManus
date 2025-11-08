"""
Unit tests for the versioning engine.
"""

import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pytest
import sqlite3

from app.storage.versioning import VersioningEngine, VersionMetadata, SnapshotMetadata
from app.storage.service import VersioningService, get_versioning_service
from app.config import config


class TestVersioningEngine:
    """Test cases for VersioningEngine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def versioning_engine(self, temp_dir):
        """Create a versioning engine with temporary storage."""
        db_path = temp_dir / "test.db"
        storage_path = temp_dir / "storage"
        return VersioningEngine(db_path, storage_path)
    
    def test_init_database(self, versioning_engine):
        """Test database initialization."""
        assert versioning_engine.db_path.exists()
        assert versioning_engine.storage_path.exists()
        
        # Check tables exist
        with sqlite3.connect(versioning_engine.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['file_blobs', 'versions', 'snapshots', 'snapshot_files']
            for table in expected_tables:
                assert table in tables
    
    def test_create_version(self, versioning_engine):
        """Test creating a version."""
        file_path = "test_file.py"
        content = "print('Hello, World!')"
        
        version_id = versioning_engine.create_version(
            file_path, content, agent="test_agent", reason="Test version"
        )
        
        assert version_id is not None
        assert file_path.replace('/', '_') in version_id
        
        # Check version metadata
        version = versioning_engine.get_version(version_id)
        assert version is not None
        assert version.file_path == file_path
        assert version.agent == "test_agent"
        assert version.reason == "Test version"
        assert version.size == len(content)
    
    def test_duplicate_version(self, versioning_engine):
        """Test that duplicate versions are not created."""
        file_path = "test_file.py"
        content = "print('Hello, World!')"
        
        # Create first version
        version_id1 = versioning_engine.create_version(file_path, content)
        
        # Create duplicate version
        version_id2 = versioning_engine.create_version(file_path, content)
        
        # Should return the same version ID
        assert version_id1 == version_id2
        
        # Check only one version exists
        history = versioning_engine.get_version_history(file_path)
        assert len(history) == 1
    
    def test_content_deduplication(self, versioning_engine):
        """Test content deduplication."""
        content = "shared content"
        
        # Create versions for different files with same content
        version_id1 = versioning_engine.create_version("file1.py", content)
        version_id2 = versioning_engine.create_version("file2.py", content)
        
        # Get content hashes
        version1 = versioning_engine.get_version(version_id1)
        version2 = versioning_engine.get_version(version_id2)
        
        assert version1.content_hash == version2.content_hash
        
        # Check only one blob stored
        with sqlite3.connect(versioning_engine.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM file_blobs").fetchone()[0]
            assert count == 1
    
    def test_get_version_content(self, versioning_engine):
        """Test retrieving version content."""
        file_path = "test_file.py"
        content = "print('Hello, World!')"
        
        version_id = versioning_engine.create_version(file_path, content)
        retrieved_content = versioning_engine.get_version_content(version_id)
        
        assert retrieved_content == content
    
    def test_get_latest_version(self, versioning_engine):
        """Test getting latest version."""
        file_path = "test_file.py"
        
        # Create multiple versions
        version_id1 = versioning_engine.create_version(file_path, "content1")
        version_id2 = versioning_engine.create_version(file_path, "content2")
        
        latest = versioning_engine.get_latest_version(file_path)
        assert latest is not None
        assert latest.version_id == version_id2
        assert latest.content_hash != versioning_engine.get_version(version_id1).content_hash
    
    def test_version_history(self, versioning_engine):
        """Test getting version history."""
        file_path = "test_file.py"
        
        # Create multiple versions
        version_ids = []
        for i in range(3):
            content = f"content{i}"
            version_id = versioning_engine.create_version(file_path, content)
            version_ids.append(version_id)
        
        # Get history
        history = versioning_engine.get_version_history(file_path)
        assert len(history) == 3
        
        # Should be in reverse chronological order
        assert history[0].version_id == version_ids[2]
        assert history[1].version_id == version_ids[1]
        assert history[2].version_id == version_ids[0]
    
    def test_generate_diff(self, versioning_engine):
        """Test generating diffs."""
        file_path = "test_file.py"
        
        # Create two versions
        version_id1 = versioning_engine.create_version(file_path, "line1\nline2\nline3")
        version_id2 = versioning_engine.create_version(file_path, "line1\nmodified\nline3")
        
        # Generate diff
        diff = versioning_engine.generate_diff(version_id1, version_id2)
        
        assert "---" in diff
        assert "+++" in diff
        assert "-line2" in diff
        assert "+modified" in diff
    
    def test_rollback(self, versioning_engine, temp_dir):
        """Test rolling back to a previous version."""
        file_path = "test_file.py"
        original_content = "original content"
        modified_content = "modified content"
        
        # Create versions
        version_id1 = versioning_engine.create_version(file_path, original_content)
        version_id2 = versioning_engine.create_version(file_path, modified_content)
        
        # Rollback to first version
        success = versioning_engine.rollback_to_version(version_id1)
        assert success
        
        # Check file content (simulate file rollback by checking new version)
        latest = versioning_engine.get_latest_version(file_path)
        latest_content = versioning_engine.get_version_content(latest.version_id)
        assert latest_content == original_content
    
    def test_create_snapshot(self, versioning_engine):
        """Test creating snapshots."""
        # Create versions for multiple files
        version_id1 = versioning_engine.create_version("file1.py", "content1")
        version_id2 = versioning_engine.create_version("file2.py", "content2")
        
        # Create snapshot
        snapshot_id = versioning_engine.create_snapshot(
            "test_snapshot",
            ["file1.py", "file2.py"],
            description="Test snapshot",
            agent="test_agent"
        )
        
        assert snapshot_id is not None
        assert "snapshot_" in snapshot_id
        
        # Check snapshot metadata
        snapshot = versioning_engine.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.name == "test_snapshot"
        assert snapshot.description == "Test snapshot"
        assert snapshot.agent == "test_agent"
        assert set(snapshot.file_versions) == {version_id1, version_id2}
    
    def test_list_snapshots(self, versioning_engine):
        """Test listing snapshots."""
        # Create multiple snapshots
        snapshot_id1 = versioning_engine.create_snapshot("snapshot1", ["file1.py"])
        snapshot_id2 = versioning_engine.create_snapshot("snapshot2", ["file2.py"])
        
        # List snapshots
        snapshots = versioning_engine.list_snapshots()
        assert len(snapshots) >= 2
        
        # Should be in reverse chronological order
        snapshot_names = [s.name for s in snapshots]
        assert "snapshot1" in snapshot_names
        assert "snapshot2" in snapshot_names
    
    def test_cleanup_old_versions(self, versioning_engine):
        """Test cleaning up old versions."""
        file_path = "test_file.py"
        
        # Create a version
        version_id = versioning_engine.create_version(file_path, "content")
        
        # Manually update timestamp to simulate old version
        old_timestamp = datetime.now().timestamp() - (31 * 24 * 3600)  # 31 days ago
        with sqlite3.connect(versioning_engine.db_path) as conn:
            conn.execute(
                "UPDATE versions SET timestamp = ? WHERE version_id = ?",
                (old_timestamp, version_id)
            )
            conn.commit()
        
        # Clean up versions older than 30 days
        deleted_count = versioning_engine.cleanup_old_versions(days=30)
        assert deleted_count == 1
        
        # Version should be deleted
        version = versioning_engine.get_version(version_id)
        assert version is None
    
    def test_storage_stats(self, versioning_engine):
        """Test getting storage statistics."""
        # Create some versions
        versioning_engine.create_version("file1.py", "content1")
        versioning_engine.create_version("file2.py", "content2")
        
        # Get stats
        stats = versioning_engine.get_storage_stats()
        
        assert "version_count" in stats
        assert "blob_count" in stats
        assert "total_size_bytes" in stats
        assert "disk_usage_bytes" in stats
        assert "snapshot_count" in stats
        assert stats["version_count"] >= 2
        assert stats["blob_count"] >= 2


class TestVersioningService:
    """Test cases for VersioningService."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def versioning_service(self, temp_dir, monkeypatch):
        """Create a versioning service with temporary storage."""
        # Mock config to use temp directory
        db_path = temp_dir / "test.db"
        storage_path = temp_dir / "storage"
        
        monkeypatch.setattr(config.versioning, 'database_path', str(db_path))
        monkeypatch.setattr(config.versioning, 'storage_path', str(storage_path))
        monkeypatch.setattr(config.versioning, 'enable_versioning', True)
        
        # Reset global instance and force reinitialization
        import app.storage.service
        import app.storage.versioning
        app.storage.service._versioning_service = None
        app.storage.versioning._versioning_engine = None
        
        service = get_versioning_service()
        # Force database initialization
        service._get_engine()._init_database()
        
        return service
    
    def test_file_save_hook(self, versioning_service):
        """Test file save hook creates version."""
        file_path = "test_file.py"
        content = "print('test')"
        
        version_id = versioning_service.on_file_save(
            file_path, content, agent="test_agent", reason="Test save"
        )
        
        assert version_id is not None
        
        # Check version was created
        history = versioning_service.get_version_history(file_path)
        assert len(history) == 1
        assert history[0].agent == "test_agent"
        assert history[0].reason == "Test save"
    
    def test_file_edit_hook_no_change(self, versioning_service):
        """Test file edit hook with no content change."""
        file_path = "test_file.py"
        content = "print('test')"
        
        # Create initial version
        version_id1 = versioning_service.on_file_save(file_path, content)
        
        # Edit with same content
        version_id2 = versioning_service.on_file_edit(file_path, content, content)
        
        # Should not create new version
        assert version_id2 is None
        
        # Only one version should exist
        history = versioning_service.get_version_history(file_path)
        assert len(history) == 1
    
    def test_file_edit_hook_with_change(self, versioning_service):
        """Test file edit hook with content change."""
        file_path = "test_file.py"
        old_content = "print('old')"
        new_content = "print('new')"
        
        # Create initial version
        version_id1 = versioning_service.on_file_save(file_path, old_content)
        
        # Edit with different content
        version_id2 = versioning_service.on_file_edit(file_path, old_content, new_content)
        
        # Should create new version
        assert version_id2 is not None
        assert version_id2 != version_id1
        
        # Two versions should exist
        history = versioning_service.get_version_history(file_path)
        assert len(history) == 2
    
    def test_snapshot_creation(self, versioning_service):
        """Test snapshot creation through service."""
        # Create some file versions
        versioning_service.on_file_save("file1.py", "content1")
        versioning_service.on_file_save("file2.py", "content2")
        
        # Create snapshot
        snapshot_id = versioning_service.create_snapshot(
            "test_snapshot",
            ["file1.py", "file2.py"],
            description="Test snapshot"
        )
        
        assert snapshot_id is not None
    
    def test_enable_disable(self, versioning_service):
        """Test enabling and disabling service."""
        # Should be enabled by default
        assert versioning_service.is_enabled()
        
        # Test save when enabled
        version_id = versioning_service.on_file_save("test.py", "content")
        assert version_id is not None
        
        # Disable service
        versioning_service.disable()
        assert not versioning_service.is_enabled()
        
        # Test save when disabled
        version_id = versioning_service.on_file_save("test2.py", "content")
        assert version_id is None
        
        # Re-enable service
        versioning_service.enable()
        assert versioning_service.is_enabled()


if __name__ == "__main__":
    pytest.main([__file__])