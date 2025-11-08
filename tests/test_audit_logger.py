"""Tests for audit logging functionality."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from app.storage.audit import AuditLogger, AuditEvent, AuditEventType


@pytest.fixture
def temp_audit_dir():
    """Create a temporary directory for audit logs."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def audit_logger(temp_audit_dir, monkeypatch):
    """Create an AuditLogger instance with temporary directory."""
    from app.config import PROJECT_ROOT
    
    audit_dir = temp_audit_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setattr("app.storage.audit.PROJECT_ROOT", temp_audit_dir)
    
    logger = AuditLogger.__new__(AuditLogger)
    logger._initialized = False
    logger.__init__()
    
    return logger


def test_audit_logger_initialization(audit_logger):
    """Test audit logger initializes correctly."""
    assert audit_logger._initialized
    assert audit_logger._audit_dir.exists()


def test_log_event(audit_logger):
    """Test logging an audit event."""
    event = audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="test_user",
        resource="test_backup",
        details={"key": "value"}
    )
    
    assert event.event_type == AuditEventType.BACKUP_STARTED
    assert event.user == "test_user"
    assert event.resource == "test_backup"
    assert event.details["key"] == "value"
    assert event.success is True


def test_log_failed_event(audit_logger):
    """Test logging a failed event."""
    event = audit_logger.log_event(
        event_type=AuditEventType.BACKUP_FAILED,
        user="test_user",
        resource="test_backup",
        success=False,
        error_message="Test error"
    )
    
    assert event.success is False
    assert event.error_message == "Test error"


def test_get_events(audit_logger):
    """Test querying audit events."""
    audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="user1",
        resource="backup1"
    )
    audit_logger.log_event(
        event_type=AuditEventType.BACKUP_COMPLETED,
        user="user1",
        resource="backup1"
    )
    audit_logger.log_event(
        event_type=AuditEventType.RESTORE_STARTED,
        user="user2",
        resource="backup2"
    )
    
    all_events = audit_logger.get_events()
    assert len(all_events) >= 3
    
    backup_events = audit_logger.get_events(event_type=AuditEventType.BACKUP_STARTED)
    assert len(backup_events) >= 1
    assert all(e.event_type == AuditEventType.BACKUP_STARTED for e in backup_events)
    
    user1_events = audit_logger.get_events(user="user1")
    assert len(user1_events) >= 2
    assert all(e.user == "user1" for e in user1_events)


def test_get_events_with_limit(audit_logger):
    """Test querying events with limit."""
    for i in range(10):
        audit_logger.log_event(
            event_type=AuditEventType.BACKUP_STARTED,
            user="test_user",
            resource=f"backup_{i}"
        )
    
    events = audit_logger.get_events(limit=5)
    assert len(events) <= 5


def test_get_event_summary(audit_logger):
    """Test getting event summary."""
    audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="test_user"
    )
    audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="test_user"
    )
    audit_logger.log_event(
        event_type=AuditEventType.RESTORE_STARTED,
        user="test_user"
    )
    
    summary = audit_logger.get_event_summary()
    
    assert summary.get("backup_started", 0) >= 2
    assert summary.get("restore_started", 0) >= 1


def test_event_id_uniqueness(audit_logger):
    """Test that event IDs are unique."""
    event1 = audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="test_user"
    )
    event2 = audit_logger.log_event(
        event_type=AuditEventType.BACKUP_STARTED,
        user="test_user"
    )
    
    assert event1.event_id != event2.event_id
