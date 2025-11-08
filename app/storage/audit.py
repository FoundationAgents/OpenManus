"""Audit logging for tracking all backup and restore operations."""

import json
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT
from app.logger import logger


class AuditEventType(str, Enum):
    """Types of audit events."""
    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    BACKUP_FAILED = "backup_failed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    ARCHIVE_CREATED = "archive_created"
    ARCHIVE_DELETED = "archive_deleted"
    GUARDIAN_APPROVAL = "guardian_approval"
    GUARDIAN_REJECTION = "guardian_rejection"
    VERSION_CREATED = "version_created"
    VERSION_DELETED = "version_deleted"


class AuditEvent(BaseModel):
    """Represents a single audit event."""
    
    event_id: str = Field(..., description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    user: str = Field(default="system", description="User who initiated the event")
    resource: Optional[str] = Field(None, description="Resource affected by the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")
    success: bool = Field(True, description="Whether the operation was successful")
    error_message: Optional[str] = Field(None, description="Error message if operation failed")


class AuditLogger:
    """Centralized audit logging system."""
    
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
        self._audit_dir = PROJECT_ROOT / "data" / "audit"
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._event_counter = 0
        
        logger.info(f"AuditLogger initialized with audit directory: {self._audit_dir}")
    
    def _get_event_id(self) -> str:
        """Generate a unique event ID."""
        with self._lock:
            self._event_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"audit_{timestamp}_{self._event_counter:06d}"
    
    def log_event(
        self,
        event_type: AuditEventType,
        user: str = "system",
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditEvent:
        """Log an audit event.
        
        Args:
            event_type: Type of event to log
            user: User who initiated the event
            resource: Resource affected by the event
            details: Additional event details
            success: Whether the operation was successful
            error_message: Error message if operation failed
            
        Returns:
            The created AuditEvent
        """
        event = AuditEvent(
            event_id=self._get_event_id(),
            event_type=event_type,
            user=user,
            resource=resource,
            details=details or {},
            success=success,
            error_message=error_message
        )
        
        try:
            self._write_event(event)
            logger.info(f"Audit event logged: {event.event_type} - {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
        
        return event
    
    def _write_event(self, event: AuditEvent) -> None:
        """Write an event to the audit log file."""
        with self._lock:
            log_file = self._audit_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(event.model_dump_json() + '\n')
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user: Optional[str] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Query audit events.
        
        Args:
            event_type: Filter by event type
            user: Filter by user
            resource: Filter by resource
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return
            
        Returns:
            List of matching audit events
        """
        events = []
        
        try:
            with self._lock:
                for log_file in sorted(self._audit_dir.glob("audit_*.jsonl"), reverse=True):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                event = AuditEvent.model_validate_json(line.strip())
                                
                                if event_type and event.event_type != event_type:
                                    continue
                                if user and event.user != user:
                                    continue
                                if resource and event.resource != resource:
                                    continue
                                if start_date and event.timestamp < start_date:
                                    continue
                                if end_date and event.timestamp > end_date:
                                    continue
                                
                                events.append(event)
                                
                                if limit and len(events) >= limit:
                                    return events
                            except Exception as e:
                                logger.error(f"Error parsing audit event: {e}")
                                continue
        except Exception as e:
            logger.error(f"Error querying audit events: {e}")
        
        return events
    
    def get_event_summary(self) -> Dict[str, int]:
        """Get a summary of event counts by type.
        
        Returns:
            Dictionary mapping event types to counts
        """
        summary = {}
        
        try:
            events = self.get_events()
            for event in events:
                event_type = event.event_type.value
                summary[event_type] = summary.get(event_type, 0) + 1
        except Exception as e:
            logger.error(f"Error generating event summary: {e}")
        
        return summary
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> None:
        """Remove audit logs older than the specified number of days.
        
        Args:
            days_to_keep: Number of days of logs to retain
        """
        try:
            with self._lock:
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                for i in range(days_to_keep + 1, 365):
                    old_date = cutoff_date.replace(day=cutoff_date.day - i)
                    log_file = self._audit_dir / f"audit_{old_date.strftime('%Y%m%d')}.jsonl"
                    
                    if log_file.exists():
                        log_file.unlink()
                        logger.info(f"Deleted old audit log: {log_file}")
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")


audit_logger = AuditLogger()
