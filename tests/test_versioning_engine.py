"""Tests for versioning engine functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil

from app.storage.versioning import VersioningEngine, FileVersion


@pytest.fixture
def temp_versions_dir():
    """Create a temporary directory for versions."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def versioning_engine(temp_versions_dir, monkeypatch):
    """Create a VersioningEngine instance with temporary directory."""
    monkeypatch.setattr("app.storage.versioning.PROJECT_ROOT", temp_versions_dir)
    
    engine = VersioningEngine.__new__(VersioningEngine)
    engine._initialized = False
    engine.__init__()
    
    return engine


def test_versioning_engine_initialization(versioning_engine):
    """Test versioning engine initializes correctly."""
    assert versioning_engine._initialized
    assert versioning_engine._versions_dir.exists()
    assert versioning_engine._objects_dir.exists()
    assert versioning_engine._index_dir.exists()


def test_create_version(versioning_engine):
    """Test creating a file version."""
    content = b"Hello, World!"
    version = versioning_engine.create_version(
        file_path="/test/file.txt",
        content=content,
        author="test_user",
        message="Initial commit"
    )
    
    assert version.file_path == "/test/file.txt"
    assert version.size == len(content)
    assert version.author == "test_user"
    assert version.message == "Initial commit"
    assert version.content_hash is not None


def test_get_version(versioning_engine):
    """Test retrieving a specific version."""
    content = b"Test content"
    version = versioning_engine.create_version(
        file_path="/test/file.txt",
        content=content
    )
    
    retrieved = versioning_engine.get_version("/test/file.txt", version.version_id)
    
    assert retrieved is not None
    assert retrieved.version_id == version.version_id
    assert retrieved.content_hash == version.content_hash


def test_get_version_content(versioning_engine):
    """Test retrieving version content."""
    content = b"Test content"
    version = versioning_engine.create_version(
        file_path="/test/file.txt",
        content=content
    )
    
    retrieved_content = versioning_engine.get_version_content(version)
    
    assert retrieved_content == content


def test_get_versions(versioning_engine):
    """Test getting all versions of a file."""
    file_path = "/test/file.txt"
    
    versioning_engine.create_version(file_path, b"Version 1")
    versioning_engine.create_version(file_path, b"Version 2")
    versioning_engine.create_version(file_path, b"Version 3")
    
    versions = versioning_engine.get_versions(file_path)
    
    assert len(versions) == 3


def test_get_latest_version(versioning_engine):
    """Test getting the latest version."""
    file_path = "/test/file.txt"
    
    v1 = versioning_engine.create_version(file_path, b"Version 1")
    v2 = versioning_engine.create_version(file_path, b"Version 2")
    v3 = versioning_engine.create_version(file_path, b"Version 3")
    
    latest = versioning_engine.get_latest_version(file_path)
    
    assert latest is not None
    assert latest.version_id == v3.version_id


def test_content_deduplication(versioning_engine):
    """Test that identical content is deduplicated."""
    content = b"Same content"
    
    v1 = versioning_engine.create_version("/file1.txt", content)
    v2 = versioning_engine.create_version("/file2.txt", content)
    
    assert v1.content_hash == v2.content_hash
    
    object_path = versioning_engine._get_object_path(v1.content_hash)
    assert object_path.exists()


def test_diff_versions(versioning_engine):
    """Test generating diff between versions."""
    file_path = "/test/file.txt"
    
    v1 = versioning_engine.create_version(file_path, b"Line 1\nLine 2\nLine 3\n")
    v2 = versioning_engine.create_version(file_path, b"Line 1\nModified Line 2\nLine 3\nLine 4\n")
    
    diff = versioning_engine.diff_versions(v1, v2)
    
    assert diff is not None
    assert "Modified Line 2" in diff


def test_tag_version(versioning_engine):
    """Test tagging a version."""
    version = versioning_engine.create_version(
        file_path="/test/file.txt",
        content=b"Test content"
    )
    
    success = versioning_engine.tag_version(
        file_path="/test/file.txt",
        version_id=version.version_id,
        tag="release-1.0"
    )
    
    assert success is True
    
    retrieved = versioning_engine.get_version("/test/file.txt", version.version_id)
    assert "release-1.0" in retrieved.tags


def test_delete_version(versioning_engine):
    """Test deleting a version."""
    file_path = "/test/file.txt"
    
    v1 = versioning_engine.create_version(file_path, b"Version 1")
    v2 = versioning_engine.create_version(file_path, b"Version 2")
    
    success = versioning_engine.delete_version(file_path, v1.version_id)
    
    assert success is True
    
    versions = versioning_engine.get_versions(file_path)
    assert len(versions) == 1
    assert versions[0].version_id == v2.version_id


def test_get_all_files(versioning_engine):
    """Test getting all tracked files."""
    versioning_engine.create_version("/file1.txt", b"Content 1")
    versioning_engine.create_version("/file2.txt", b"Content 2")
    versioning_engine.create_version("/file3.txt", b"Content 3")
    
    files = versioning_engine.get_all_files()
    
    assert len(files) == 3
    assert "/file1.txt" in files
    assert "/file2.txt" in files
    assert "/file3.txt" in files


def test_get_storage_stats(versioning_engine):
    """Test getting storage statistics."""
    versioning_engine.create_version("/file1.txt", b"Content 1")
    versioning_engine.create_version("/file2.txt", b"Content 2")
    
    stats = versioning_engine.get_storage_stats()
    
    assert stats["total_files"] == 2
    assert stats["total_versions"] == 2
    assert stats["total_size_bytes"] > 0


def test_parent_version_tracking(versioning_engine):
    """Test that parent versions are tracked correctly."""
    file_path = "/test/file.txt"
    
    v1 = versioning_engine.create_version(file_path, b"Version 1")
    v2 = versioning_engine.create_version(file_path, b"Version 2")
    
    assert v1.parent_version is None
    assert v2.parent_version == v1.version_id
