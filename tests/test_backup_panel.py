"""Tests for backup panel UI component."""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

try:
    from PyQt6.QtWidgets import QApplication
    from app.ui.panels.backup_panel import BackupPanel
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    if not PYQT6_AVAILABLE:
        pytest.skip("PyQt6 not available")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())
    workspace_dir = temp_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def backup_panel(qapp, temp_project_dir, monkeypatch):
    """Create a BackupPanel instance."""
    if not PYQT6_AVAILABLE:
        pytest.skip("PyQt6 not available")
    
    monkeypatch.setattr("app.storage.backup.PROJECT_ROOT", temp_project_dir)
    monkeypatch.setattr("app.storage.versioning.PROJECT_ROOT", temp_project_dir)
    monkeypatch.setattr("app.storage.audit.PROJECT_ROOT", temp_project_dir)
    
    panel = BackupPanel()
    return panel


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_backup_panel_initialization(backup_panel):
    """Test backup panel initializes correctly."""
    assert backup_panel.backup_manager is not None
    assert backup_panel.guardian is not None
    assert backup_panel.versioning is not None
    assert backup_panel.backups_table is not None


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_refresh_backups(backup_panel):
    """Test refreshing backup list."""
    backup_panel.backup_manager.create_backup(backup_type="full")
    
    backup_panel._refresh_backups()
    
    assert backup_panel.backups_table.rowCount() >= 1


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_update_stats(backup_panel):
    """Test updating backup statistics."""
    backup_panel._update_stats()
    
    assert backup_panel.stats_text.toPlainText() != ""


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_format_size(backup_panel):
    """Test size formatting."""
    assert backup_panel._format_size(1024) == "1.00 KB"
    assert backup_panel._format_size(1024 * 1024) == "1.00 MB"
    assert backup_panel._format_size(1024 * 1024 * 1024) == "1.00 GB"


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_create_backup_button_exists(backup_panel):
    """Test create backup button exists and is enabled."""
    assert backup_panel.create_backup_btn is not None
    assert backup_panel.create_backup_btn.isEnabled()


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_restore_backup_button_exists(backup_panel):
    """Test restore backup button exists and is enabled."""
    assert backup_panel.restore_backup_btn is not None
    assert backup_panel.restore_backup_btn.isEnabled()


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_archive_button_exists(backup_panel):
    """Test archive button exists and is enabled."""
    assert backup_panel.archive_btn is not None
    assert backup_panel.archive_btn.isEnabled()


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_worker_not_running_initially(backup_panel):
    """Test that no worker is running initially."""
    assert backup_panel.worker is None


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")
def test_guardian_callback_setup(backup_panel):
    """Test that Guardian callback is set up."""
    assert backup_panel.guardian._approval_callback is not None
