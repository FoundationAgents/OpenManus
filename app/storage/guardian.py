"""Guardian service for validating and approving destructive operations."""

import threading
from enum import Enum
from typing import Callable, Optional

from pydantic import BaseModel, Field

from app.logger import logger
from app.storage.audit import audit_logger, AuditEventType


class GuardianDecision(str, Enum):
    """Guardian decision outcomes."""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class GuardianRequest(BaseModel):
    """Represents a request for Guardian approval."""
    
    request_id: str = Field(..., description="Unique request identifier")
    operation: str = Field(..., description="Operation being requested")
    resource: str = Field(..., description="Resource affected by the operation")
    reason: str = Field(..., description="Reason for the operation")
    user: str = Field(default="system", description="User requesting the operation")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, high, critical")
    decision: GuardianDecision = Field(default=GuardianDecision.PENDING, description="Decision status")
    details: dict = Field(default_factory=dict, description="Additional details")


class Guardian:
    """Guardian service for approving destructive operations."""
    
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
        self._approval_callback: Optional[Callable[[GuardianRequest], bool]] = None
        self._auto_approve = False
        self._request_counter = 0
        
        logger.info("Guardian service initialized")
    
    def set_approval_callback(self, callback: Callable[[GuardianRequest], bool]) -> None:
        """Set the callback function for approval requests.
        
        The callback should display a UI dialog and return True for approval, False for rejection.
        
        Args:
            callback: Function that takes a GuardianRequest and returns approval decision
        """
        with self._lock:
            self._approval_callback = callback
            logger.info("Guardian approval callback registered")
    
    def set_auto_approve(self, auto_approve: bool) -> None:
        """Set whether to automatically approve all requests (for testing).
        
        Args:
            auto_approve: If True, all requests are automatically approved
        """
        with self._lock:
            self._auto_approve = auto_approve
            logger.warning(f"Guardian auto-approve set to: {auto_approve}")
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        with self._lock:
            self._request_counter += 1
            return f"guardian_req_{self._request_counter:06d}"
    
    def request_approval(
        self,
        operation: str,
        resource: str,
        reason: str,
        user: str = "system",
        risk_level: str = "medium",
        details: Optional[dict] = None
    ) -> bool:
        """Request approval for a destructive operation.
        
        Args:
            operation: Operation being requested (e.g., "restore", "delete")
            resource: Resource affected by the operation
            reason: Reason for the operation
            user: User requesting the operation
            risk_level: Risk level (low, medium, high, critical)
            details: Additional details
            
        Returns:
            True if approved, False if rejected
        """
        request = GuardianRequest(
            request_id=self._generate_request_id(),
            operation=operation,
            resource=resource,
            reason=reason,
            user=user,
            risk_level=risk_level,
            details=details or {}
        )
        
        logger.info(f"Guardian approval requested: {operation} on {resource} (risk: {risk_level})")
        
        with self._lock:
            if self._auto_approve:
                request.decision = GuardianDecision.APPROVED
                approved = True
                logger.warning(f"Auto-approved request: {request.request_id}")
            elif self._approval_callback:
                try:
                    approved = self._approval_callback(request)
                    request.decision = GuardianDecision.APPROVED if approved else GuardianDecision.REJECTED
                except Exception as e:
                    logger.error(f"Error in approval callback: {e}")
                    request.decision = GuardianDecision.REJECTED
                    approved = False
            else:
                logger.warning("No approval callback registered, defaulting to rejection")
                request.decision = GuardianDecision.REJECTED
                approved = False
        
        audit_event_type = AuditEventType.GUARDIAN_APPROVAL if approved else AuditEventType.GUARDIAN_REJECTION
        audit_logger.log_event(
            audit_event_type,
            user=user,
            resource=resource,
            details={
                "request_id": request.request_id,
                "operation": operation,
                "risk_level": risk_level,
                "reason": reason
            }
        )
        
        logger.info(f"Guardian decision: {request.decision.value} for {request.request_id}")
        return approved
    
    def validate_restore_operation(
        self,
        backup_id: str,
        target_path: str,
        user: str = "system"
    ) -> bool:
        """Validate a restore operation.
        
        Args:
            backup_id: ID of the backup to restore
            target_path: Path where files will be restored
            user: User performing the restore
            
        Returns:
            True if approved, False if rejected
        """
        return self.request_approval(
            operation="restore_backup",
            resource=target_path,
            reason=f"Restore backup {backup_id} to {target_path}",
            user=user,
            risk_level="high",
            details={"backup_id": backup_id, "target_path": target_path}
        )
    
    def validate_delete_operation(
        self,
        resource: str,
        user: str = "system"
    ) -> bool:
        """Validate a delete operation.
        
        Args:
            resource: Resource to be deleted
            user: User performing the delete
            
        Returns:
            True if approved, False if rejected
        """
        return self.request_approval(
            operation="delete",
            resource=resource,
            reason=f"Delete {resource}",
            user=user,
            risk_level="high",
            details={"resource": resource}
        )


def get_guardian() -> Guardian:
    """Get the singleton Guardian instance."""
    return Guardian()
