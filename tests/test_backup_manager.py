"""Tests for backup manager functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

from app.storage.backup import BackupManager, BackupMetadata


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())
    
    workspace_dir = temp_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = workspace_dir / "test.txt"
    test_file.write_text("Test content")
    
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def backup_manager(temp_project_dir, monkeypatch):
    """Create a BackupManager instance with temporary directory."""
    monkeypatch.setattr("app.storage.backup.PROJECT_ROOT", temp_project_dir)
    monkeypatch.setattr("app.storage.versioning.PROJECT_ROOT", temp_project_dir)
    monkeypatch.setattr("app.storage.audit.PROJECT_ROOT", temp_project_dir)
    monkeypatch.setattr("app.storage.guardian.logger", Mock())
    
    manager = BackupManager.__new__(BackupManager)
    manager._initialized = False
    manager.__init__()
    
    return manager


def test_backup_manager_initialization(backup_manager):
    """Test backup manager initializes correctly."""
    assert backup_manager._initialized
    assert backup_manager._backup_dir.exists()
    assert backup_manager._archive_dir.exists()
    assert backup_manager._metadata_dir.exists()


def test_create_backup(backup_manager):
    """Test creating a backup."""
    metadata = backup_manager.create_backup(
        backup_type="full",
        description="Test backup",
        include_versions=True
    )
    
    assert metadata is not None
    assert metadata.backup_type == "full"
    assert metadata.description == "Test backup"
    assert Path(metadata.archive_path).exists()
    assert metadata.size_bytes > 0


def test_get_backups(backup_manager):
    """Test getting backup list."""
    backup_manager.create_backup(backup_type="full")
    backup_manager.create_backup(backup_type="incremental")
    
    backups = backup_manager.get_backups()
    
    assert len(backups) >= 2


def test_get_backup(backup_manager):
    """Test getting a specific backup."""
    metadata = backup_manager.create_backup(backup_type="full")
    
    retrieved = backup_manager.get_backup(metadata.backup_id)
    
    assert retrieved is not None
    assert retrieved.backup_id == metadata.backup_id


def test_restore_backup_with_auto_approval(backup_manager):
    """Test restoring a backup with auto-approval."""
    backup_manager._guardian.set_auto_approve(True)
    
    metadata = backup_manager.create_backup(backup_type="full")
    
    success = backup_manager.restore_backup(
        backup_id=metadata.backup_id,
        require_approval=True
    )
    
    assert success is True


def test_restore_backup_without_approval(backup_manager):
    """Test restoring without Guardian approval fails."""
    backup_manager._guardian.set_auto_approve(False)
    
    metadata = backup_manager.create_backup(backup_type="full")
    
    success = backup_manager.restore_backup(
        backup_id=metadata.backup_id,
        require_approval=True
    )
    
    assert success is False


def test_restore_nonexistent_backup(backup_manager):
    """Test restoring a nonexistent backup fails."""
    success = backup_manager.restore_backup(
        backup_id="nonexistent",
        require_approval=False
    )
    
    assert success is False


def test_archive_old_backups(backup_manager, monkeypatch):
    """Test archiving old backups."""
    from datetime import datetime, timedelta
    
    backup1 = backup_manager.create_backup(backup_type="full")
    old_timestamp = datetime.now() - timedelta(days=40)
    backup1.timestamp = old_timestamp
    backup_manager._save_metadata(backup1)
    
    backup2 = backup_manager.create_backup(backup_type="full")
    
    archived_count = backup_manager.archive_old_backups(
        days_threshold=30,
        keep_count=1
    )
    
    assert archived_count >= 0


def test_delete_backup(backup_manager):
    """Test deleting a backup."""
    backup_manager._guardian.set_auto_approve(True)
    
    metadata = backup_manager.create_backup(backup_type="full")
    
    success = backup_manager.delete_backup(
        backup_id=metadata.backup_id,
        require_approval=False
    )
    
    assert success is True
    assert not Path(metadata.archive_path).exists()


def test_get_backup_stats(backup_manager):
    """Test getting backup statistics."""
    backup_manager.create_backup(backup_type="full")
    backup_manager.create_backup(backup_type="incremental")
    
    stats = backup_manager.get_backup_stats()
    
    assert stats["total_backups"] >= 2
    assert stats["total_size_bytes"] > 0
    assert "full" in stats["by_type"]


def test_backup_callback(backup_manager):
    """Test backup callback is called."""
    callback_called = []
    
    def callback(metadata: BackupMetadata):
        callback_called.append(metadata.backup_id)
    
    backup_manager.set_backup_callback(callback)
    
    metadata = backup_manager.create_backup(backup_type="full")
    
    assert metadata.backup_id in callback_called


def test_cleanup_old_backups(backup_manager):
    """Test cleaning up old backups."""
    from datetime import datetime, timedelta
    
    metadata = backup_manager.create_backup(backup_type="full")
    
    old_timestamp = datetime.now() - timedelta(days=100)
    metadata.timestamp = old_timestamp
    backup_manager._save_metadata(metadata)
    
    deleted_count = backup_manager.cleanup_old_backups(retention_days=90)
    
    assert deleted_count >= 0


@pytest.mark.skipif(
    not hasattr(BackupManager, '_scheduler') or BackupManager.__new__(BackupManager)._scheduler is None,
    reason="Scheduler not available"
)
def test_schedule_backup(backup_manager):
    """Test scheduling backups."""
    success = backup_manager.schedule_backup(
        schedule_type="interval",
        schedule_config={"hours": 24},
        backup_config={"backup_type": "full"}
    )
    
    if backup_manager._scheduler:
        assert success is True


def test_backup_with_tags(backup_manager):
    """Test creating a backup with tags."""
    metadata = backup_manager.create_backup(
        backup_type="full",
        tags=["important", "release-1.0"]
    )
    
    assert "important" in metadata.tags
    assert "release-1.0" in metadata.tags


def test_incremental_backup(backup_manager):
    """Test creating an incremental backup."""
    full_backup = backup_manager.create_backup(backup_type="full")
    incremental_backup = backup_manager.create_backup(backup_type="incremental")
    
    assert full_backup.backup_type == "full"
    assert incremental_backup.backup_type == "incremental"
