"""Tests for the SQLite-backed VersioningEngine."""

import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.storage.versioning import SnapshotMetadata, VersionMetadata, VersioningEngine


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for versioning artifacts."""
    directory = Path(tempfile.mkdtemp())
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


@pytest.fixture
def engine(temp_dir, monkeypatch):
    """Create an isolated VersioningEngine instance for testing."""
    db_path = temp_dir / "versions.db"
    storage_path = temp_dir / "storage"

    # Ensure files are always tracked during tests
    monkeypatch.setattr(
        VersioningEngine,
        "_should_track_file",
        lambda self, file_path: True,
    )

    eng = VersioningEngine(db_path=db_path, storage_path=storage_path)
    # Disable guardian checks to keep rollback simple in tests
    if hasattr(eng.settings, "enable_guardian_checks"):
        eng.settings.enable_guardian_checks = False
    return eng


def test_initialization(engine: VersioningEngine):
    """Engine should create storage directories and database on init."""
    assert engine.db_path.exists()
    assert engine.storage_path.exists()


def test_create_and_get_version(engine: VersioningEngine):
    """Creating a version should persist metadata retrievable via get_version."""
    content = "print('hello')\n"
    version_id = engine.create_version("src/example.py", content, agent="tester")

    metadata = engine.get_version(version_id)
    assert isinstance(metadata, VersionMetadata)
    assert metadata.file_path == "src/example.py"
    assert metadata.agent == "tester"
    assert metadata.size == len(content)


def test_duplicate_version_returns_existing_id(engine: VersioningEngine):
    """Creating identical content twice should return the same version id."""
    version_id = engine.create_version("duplicate.py", "same content")
    same_id = engine.create_version("duplicate.py", "same content")

    assert same_id == version_id
    history = engine.get_version_history("duplicate.py")
    assert len(history) == 1


def test_generate_diff(engine: VersioningEngine):
    """Diff generation should highlight modified lines between versions."""
    v1 = engine.create_version("diff.py", "line1\nline2\n")
    v2 = engine.create_version("diff.py", "line1\nmodified\n")

    diff = engine.generate_diff(v1, v2)
    assert "-line2" in diff
    assert "+modified" in diff


def test_cleanup_old_versions(engine: VersioningEngine):
    """Old versions should be removed when cleanup is invoked."""
    version_id = engine.create_version("old.py", "stale")

    old_timestamp = datetime.now().timestamp() - (35 * 24 * 3600)
    with sqlite3.connect(engine.db_path) as conn:
        conn.execute(
            "UPDATE versions SET timestamp = ? WHERE version_id = ?",
            (old_timestamp, version_id),
        )
        conn.commit()

    deleted = engine.cleanup_old_versions(days=30)
    assert deleted == 1
    assert engine.get_version(version_id) is None


def test_snapshot_creation(engine: VersioningEngine):
    """Snapshots should capture the latest versions of requested files."""
    engine.create_version("snap1.py", "content1")
    engine.create_version("snap2.py", "content2")

    snapshot_id = engine.create_snapshot(
        "snapshot-test",
        ["snap1.py", "snap2.py"],
        description="test snapshot",
        agent="tester",
    )

    assert snapshot_id is not None
    snapshot = engine.get_snapshot(snapshot_id)
    assert isinstance(snapshot, SnapshotMetadata)
    assert snapshot.agent == "tester"

    latest_ids = {
        engine.get_latest_version("snap1.py").version_id,
        engine.get_latest_version("snap2.py").version_id,
    }
    assert set(snapshot.file_versions) == latest_ids
