"""Tests for Guardian approval system."""

import pytest
from app.storage.guardian import Guardian, GuardianDecision, GuardianRequest


@pytest.fixture
def guardian():
    """Create a Guardian instance."""
    g = Guardian.__new__(Guardian)
    g._initialized = False
    g.__init__()
    return g


def test_guardian_initialization(guardian):
    """Test Guardian initializes correctly."""
    assert guardian._initialized
    assert guardian._approval_callback is None
    assert guardian._auto_approve is False


def test_auto_approve_mode(guardian):
    """Test auto-approve mode."""
    guardian.set_auto_approve(True)
    
    approved = guardian.request_approval(
        operation="test_operation",
        resource="test_resource",
        reason="Test reason"
    )
    
    assert approved is True


def test_approval_callback(guardian):
    """Test approval callback."""
    approved_operations = []
    
    def mock_callback(request: GuardianRequest) -> bool:
        approved_operations.append(request.operation)
        return request.operation == "approve_me"
    
    guardian.set_approval_callback(mock_callback)
    
    result1 = guardian.request_approval(
        operation="approve_me",
        resource="resource1",
        reason="Test"
    )
    
    result2 = guardian.request_approval(
        operation="reject_me",
        resource="resource2",
        reason="Test"
    )
    
    assert result1 is True
    assert result2 is False
    assert "approve_me" in approved_operations
    assert "reject_me" in approved_operations


def test_no_callback_defaults_to_rejection(guardian):
    """Test that without callback, operations are rejected."""
    approved = guardian.request_approval(
        operation="test_operation",
        resource="test_resource",
        reason="Test reason"
    )
    
    assert approved is False


def test_validate_restore_operation(guardian):
    """Test restore operation validation."""
    guardian.set_auto_approve(True)
    
    approved = guardian.validate_restore_operation(
        backup_id="backup_123",
        target_path="/test/path",
        user="test_user"
    )
    
    assert approved is True


def test_validate_delete_operation(guardian):
    """Test delete operation validation."""
    guardian.set_auto_approve(True)
    
    approved = guardian.validate_delete_operation(
        resource="test_resource",
        user="test_user"
    )
    
    assert approved is True


def test_risk_levels(guardian):
    """Test different risk levels."""
    guardian.set_auto_approve(True)
    
    for risk_level in ["low", "medium", "high", "critical"]:
        approved = guardian.request_approval(
            operation="test",
            resource="resource",
            reason="Test",
            risk_level=risk_level
        )
        assert approved is True


def test_request_id_generation(guardian):
    """Test that request IDs are unique."""
    guardian.set_auto_approve(True)
    
    guardian.request_approval(
        operation="test1",
        resource="resource1",
        reason="Test"
    )
    
    guardian.request_approval(
        operation="test2",
        resource="resource2",
        reason="Test"
    )
    
    assert guardian._request_counter >= 2


def test_callback_exception_handling(guardian):
    """Test that callback exceptions are handled gracefully."""
    def failing_callback(request: GuardianRequest) -> bool:
        raise Exception("Callback error")
    
    guardian.set_approval_callback(failing_callback)
    
    approved = guardian.request_approval(
        operation="test",
        resource="resource",
        reason="Test"
    )
    
    assert approved is False
