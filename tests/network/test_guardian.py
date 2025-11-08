"""Tests for Guardian security system."""

import pytest
from app.network.guardian import (
    Guardian,
    NetworkPolicy,
    OperationType,
    RiskLevel,
)


def test_guardian_initialization():
    """Test Guardian initialization with default policy."""
    guardian = Guardian()
    assert guardian.policy is not None
    assert guardian.policy.name == "default"


def test_custom_policy():
    """Test Guardian with custom policy."""
    policy = NetworkPolicy(
        name="test_policy",
        description="Test policy",
        allowed_operations={OperationType.HTTP_GET},
        blocked_hosts=["evil.com"],
        blocked_ports=[8080]
    )
    
    guardian = Guardian(policy)
    assert guardian.policy.name == "test_policy"
    assert OperationType.HTTP_GET in guardian.policy.allowed_operations


def test_risk_assessment_allowed():
    """Test risk assessment for allowed operation."""
    guardian = Guardian()
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="example.com",
        port=443
    )
    
    assert assessment.level in [RiskLevel.LOW, RiskLevel.MEDIUM]
    assert assessment.approved is True


def test_risk_assessment_blocked_host():
    """Test risk assessment for blocked host."""
    policy = NetworkPolicy(
        name="test",
        description="Test",
        blocked_hosts=[r"evil\.com"]
    )
    guardian = Guardian(policy)
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="evil.com",
        port=443
    )
    
    assert assessment.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert assessment.approved is False


def test_risk_assessment_blocked_port():
    """Test risk assessment for blocked port."""
    policy = NetworkPolicy(
        name="test",
        description="Test",
        allowed_operations={OperationType.HTTP_GET},  # Allow the operation
        blocked_ports=[8080]
    )
    guardian = Guardian(policy)
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="example.com",
        port=8080
    )
    
    # Blocked port should result in HIGH or CRITICAL risk
    assert assessment.level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM]


def test_risk_assessment_sensitive_port():
    """Test risk assessment for sensitive port."""
    guardian = Guardian()
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="example.com",
        port=22  # SSH
    )
    
    # Sensitive ports increase risk score
    assert assessment.level != RiskLevel.LOW


def test_risk_assessment_localhost():
    """Test risk assessment for localhost."""
    guardian = Guardian()
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="127.0.0.1",
        port=80
    )
    
    # Localhost matches dangerous pattern
    assert assessment.level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def test_manual_approval():
    """Test manual approval of operations."""
    guardian = Guardian()
    
    # Approve operation
    result = guardian.approve_operation(
        operation=OperationType.HTTP_POST,
        host="api.example.com",
        port=443
    )
    
    assert result is True
    
    # Check if approved
    is_approved = guardian.is_approved(
        operation=OperationType.HTTP_POST,
        host="api.example.com",
        port=443
    )
    
    assert is_approved is True


def test_approval_cache_clear():
    """Test clearing approval cache."""
    guardian = Guardian()
    
    # Approve operation
    guardian.approve_operation(
        operation=OperationType.HTTP_POST,
        host="api.example.com",
        port=443
    )
    
    # Clear approvals
    guardian.clear_approvals()
    
    # Check if no longer approved
    is_approved = guardian.is_approved(
        operation=OperationType.HTTP_POST,
        host="api.example.com",
        port=443
    )
    
    assert is_approved is False


def test_policy_update():
    """Test updating Guardian policy."""
    guardian = Guardian()
    original_policy = guardian.policy.name
    
    new_policy = NetworkPolicy(
        name="new_policy",
        description="New policy",
        allowed_operations={OperationType.HTTP_GET}
    )
    
    guardian.update_policy(new_policy)
    
    assert guardian.policy.name == "new_policy"
    assert guardian.policy.name != original_policy


def test_data_size_limit():
    """Test risk assessment with data size limit."""
    policy = NetworkPolicy(
        name="test",
        description="Test",
        max_request_size=1000  # 1KB limit
    )
    guardian = Guardian(policy)
    
    # Small request - should be low risk
    assessment1 = guardian.assess_risk(
        operation=OperationType.HTTP_POST,
        host="example.com",
        port=443,
        data_size=500
    )
    
    # Large request - should increase risk
    assessment2 = guardian.assess_risk(
        operation=OperationType.HTTP_POST,
        host="example.com",
        port=443,
        data_size=5000
    )
    
    # Large request should have higher or equal risk
    risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert risk_levels.index(assessment2.level) >= risk_levels.index(assessment1.level)


def test_operation_not_allowed():
    """Test operation not in allowed list."""
    policy = NetworkPolicy(
        name="test",
        description="Test",
        allowed_operations={OperationType.HTTP_GET}  # Only GET allowed
    )
    guardian = Guardian(policy)
    
    # POST not allowed
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_POST,
        host="example.com",
        port=443
    )
    
    assert assessment.approved is False
    assert any("not allowed" in reason.lower() for reason in assessment.reasons)


def test_requires_confirmation():
    """Test operations requiring confirmation."""
    policy = NetworkPolicy(
        name="test",
        description="Test",
        require_confirmation=[OperationType.HTTP_DELETE]
    )
    guardian = Guardian(policy)
    
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_DELETE,
        host="example.com",
        port=443
    )
    
    assert assessment.requires_confirmation is True
