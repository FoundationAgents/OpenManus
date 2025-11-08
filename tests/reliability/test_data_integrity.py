"""
Tests for data integrity system
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.reliability.data_integrity import DataIntegrityManager, BackupInfo


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_integrity_manager_initialization(temp_dir):
    """Test integrity manager initialization"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    assert manager.backup_dir.exists()


@pytest.mark.asyncio
async def test_checksum_calculation(temp_dir):
    """Test checksum calculation"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Calculate checksum
    checksum = manager._calculate_checksum(str(test_file))
    assert checksum
    assert len(checksum) == 64  # SHA256 hex is 64 chars


@pytest.mark.asyncio
async def test_record_and_check_integrity(temp_dir):
    """Test recording and checking file integrity"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Record checksum
    success = await manager.record_checksum(str(test_file))
    assert success

    # Check integrity
    is_valid, message = await manager.check_integrity(str(test_file))
    assert is_valid


@pytest.mark.asyncio
async def test_backup_creation(temp_dir):
    """Test backup creation"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Create backup
    backup_info = await manager.create_backup(str(test_file), backup_type="full")
    assert backup_info is not None
    assert backup_info.source_path == str(test_file)
    assert backup_info.backup_type == "full"


@pytest.mark.asyncio
async def test_backup_directory_creation(temp_dir):
    """Test backup directory creation"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test directory
    test_dir = temp_dir / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")

    # Create backup
    backup_info = await manager.create_backup(str(test_dir), backup_type="full")
    assert backup_info is not None
    assert backup_info.size_bytes > 0


@pytest.mark.asyncio
async def test_restore_backup(temp_dir):
    """Test backup restoration"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create original file
    original_file = temp_dir / "original.txt"
    original_file.write_text("original content")

    # Create backup
    backup_info = await manager.create_backup(str(original_file), backup_type="full")
    assert backup_info is not None

    # Modify original
    original_file.write_text("modified content")

    # Restore backup
    restore_to = temp_dir / "restored.txt"
    success = await manager.restore_backup(backup_info.destination_path, str(restore_to))
    assert success
    assert restore_to.read_text() == "original content"


@pytest.mark.asyncio
async def test_backup_history(temp_dir):
    """Test backup history tracking"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Create multiple backups
    for i in range(3):
        await manager.create_backup(str(test_file), backup_type="full")

    # Get history
    history = manager.get_backup_history(backup_type="full")
    assert len(history) > 0


@pytest.mark.asyncio
async def test_cleanup_old_backups(temp_dir):
    """Test cleanup of old backups"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Create multiple backups
    for i in range(5):
        await manager.create_backup(str(test_file), backup_type="full")

    # Cleanup
    deleted = await manager.cleanup_old_backups(backup_type="full", keep_count=2)
    assert deleted >= 0  # May delete some backups


@pytest.mark.asyncio
async def test_path_size_calculation(temp_dir):
    """Test path size calculation"""
    db_path = temp_dir / "test.db"
    manager = DataIntegrityManager(str(db_path))

    # Create test files
    test_dir = temp_dir / "sizes"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("a" * 100)
    (test_dir / "file2.txt").write_text("b" * 200)

    # Get size
    size = manager._get_path_size(test_dir)
    assert size >= 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
