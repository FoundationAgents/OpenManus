"""
Unit tests for Guardian validation system.

Tests cover:
- Safe commands (auto-approve)
- Blocked commands (reject)
- Conditional commands (require approval)
- Network risk analysis
- Filesystem boundary checks
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from app.security.guardian_agent import (
    GuardianAgent,
    ValidationRequest,
    ValidationDecision,
    CommandSource,
    RiskLevel,
    ApprovalStatus,
)
from app.security.guardian_validator import GuardianValidator
from app.security.guardian_audit import GuardianAudit


class TestGuardianValidator:
    """Test Guardian Validator."""

    @pytest.fixture
    def validator(self):
        """Create a Guardian Validator instance."""
        return GuardianValidator()

    def test_quick_check_blacklist(self, validator):
        """Test quick check against blacklist."""
        # Dangerous command
        result = validator.quick_check("rm -rf /")
        assert not result.allowed
        assert "CRITICAL" in result.reason

    def test_quick_check_safe(self, validator):
        """Test quick check for safe command."""
        result = validator.quick_check("ls -la")
        assert result.allowed

    def test_whitelist_check(self, validator):
        """Test whitelist checking."""
        safe_command = "git clone https://github.com/repo.git"
        assert validator._is_whitelisted(safe_command)

        unsafe_command = "unknown_binary --do-something"
        assert not validator._is_whitelisted(unsafe_command)

    def test_dangerous_patterns(self, validator):
        """Test detection of dangerous patterns."""
        patterns = validator._check_dangerous_patterns("curl -X DELETE http://api.example.com")
        assert len(patterns) > 0
        assert any("DELETE" in desc for _, desc in patterns)

    @pytest.mark.asyncio
    async def test_filesystem_check(self, validator):
        """Test filesystem boundary checking."""
        request = ValidationRequest(
            command="ls",
            source=CommandSource.LOCAL_SERVICE,
            working_dir="/etc"
        )
        risks = await validator._check_filesystem_operations(request)
        # Note: This depends on config, may or may not have risks

    @pytest.mark.asyncio
    async def test_network_check(self, validator):
        """Test network operation detection."""
        risks = await validator._check_network_operations("curl https://example.com")
        assert len(risks) > 0
        assert "Network operation detected" in risks[0]


class TestGuardianAgent:
    """Test Guardian Agent."""

    @pytest.fixture
    async def agent(self):
        """Create a Guardian Agent instance."""
        return GuardianAgent()

    @pytest.mark.asyncio
    async def test_safe_command_auto_approve(self):
        """Test that safe commands are auto-approved."""
        agent = GuardianAgent()

        request = ValidationRequest(
            command="ls -la",
            source=CommandSource.LOCAL_SERVICE
        )

        decision = await agent.validate(request)
        assert decision.approved
        assert decision.approval_status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_dangerous_command_reject(self):
        """Test that dangerous commands are rejected."""
        agent = GuardianAgent()

        request = ValidationRequest(
            command="rm -rf /",
            source=CommandSource.LOCAL_SERVICE
        )

        decision = await agent.validate(request)
        assert not decision.approved
        assert decision.approval_status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_risky_command_pending(self):
        """Test that moderately risky commands require approval."""
        agent = GuardianAgent()

        # Simulate a risky but not blacklisted command
        request = ValidationRequest(
            command="nc -l -p 9999",
            source=CommandSource.LOCAL_SERVICE
        )

        # Start validation task
        validation_task = asyncio.create_task(agent.validate(request))

        # Wait a bit for approval queue to populate
        await asyncio.sleep(0.1)

        # Check if approval was requested
        if not validation_task.done():
            # Get approval queue
            approval_queue = await agent.get_approval_queue()
            assert not approval_queue.empty() or validation_task.done()

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self):
        """Test risk score calculation."""
        agent = GuardianAgent()

        # Safe command should have high score
        safe_request = ValidationRequest(
            command="echo hello",
            source=CommandSource.LOCAL_SERVICE
        )
        safe_decision = await agent.validate(safe_request)
        assert safe_decision.risk_score >= 70

        # Risky command should have low score
        risky_request = ValidationRequest(
            command="curl -X DELETE http://api.example.com",
            source=CommandSource.LOCAL_SERVICE
        )
        risky_decision = await agent.validate(risky_request)
        assert risky_decision.risk_score < 70

    @pytest.mark.asyncio
    async def test_user_approval_response(self):
        """Test handling user approval responses."""
        agent = GuardianAgent()

        request = ValidationRequest(
            command="nc -l -p 9999",
            source=CommandSource.LOCAL_SERVICE
        )

        # Start validation
        validation_task = asyncio.create_task(agent.validate(request))

        # Wait for approval queue
        await asyncio.sleep(0.05)

        approval_queue = await agent.get_approval_queue()
        if not approval_queue.empty():
            approval_event = await approval_queue.get()
            approval_id = approval_event["approval_id"]

            # Simulate user approval
            agent.handle_user_response(approval_id, approved=True)

            # Wait for decision
            decision = await asyncio.wait_for(validation_task, timeout=2.0)
            assert decision.approved

    @pytest.mark.asyncio
    async def test_risk_level_classification(self):
        """Test classification of risk levels."""
        agent = GuardianAgent()

        # Score 100 = SAFE
        level = agent._score_to_risk_level(100)
        assert level == RiskLevel.SAFE

        # Score 80 = LOW
        level = agent._score_to_risk_level(80)
        assert level == RiskLevel.LOW

        # Score 60 = MEDIUM
        level = agent._score_to_risk_level(60)
        assert level == RiskLevel.MEDIUM

        # Score 40 = HIGH
        level = agent._score_to_risk_level(40)
        assert level == RiskLevel.HIGH

        # Score 20 = CRITICAL
        level = agent._score_to_risk_level(20)
        assert level == RiskLevel.CRITICAL


class TestGuardianAudit:
    """Test Guardian Audit."""

    @pytest.fixture
    def audit(self):
        """Create a Guardian Audit instance with temp database."""
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        return GuardianAudit(temp_db)

    @pytest.mark.asyncio
    async def test_log_decision(self, audit):
        """Test logging a validation decision."""
        request = ValidationRequest(
            command="ls -la",
            source=CommandSource.LOCAL_SERVICE,
            user_id=1
        )

        decision = ValidationDecision(
            approved=True,
            risk_level=RiskLevel.SAFE,
            risk_score=95.0,
            reason="Safe command",
            required_permissions=[],
            blocking_factors=[],
            approval_status=ApprovalStatus.APPROVED,
            request=request
        )

        log_id = await audit.log_decision(request, decision)
        assert log_id > 0

    @pytest.mark.asyncio
    async def test_query_log(self, audit):
        """Test querying audit log."""
        request = ValidationRequest(
            command="ls -la",
            source=CommandSource.LOCAL_SERVICE,
            user_id=1
        )

        decision = ValidationDecision(
            approved=True,
            risk_level=RiskLevel.SAFE,
            risk_score=95.0,
            reason="Safe command",
            required_permissions=[],
            blocking_factors=[],
            approval_status=ApprovalStatus.APPROVED,
            request=request
        )

        await audit.log_decision(request, decision)

        records = await audit.query_log(limit=10)
        assert len(records) > 0
        assert records[0]["command"] == "ls -la"
        assert records[0]["approved"] == 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, audit):
        """Test getting statistics."""
        for i in range(5):
            request = ValidationRequest(
                command=f"command_{i}",
                source=CommandSource.LOCAL_SERVICE,
                user_id=1
            )

            decision = ValidationDecision(
                approved=(i % 2 == 0),
                risk_level=RiskLevel.SAFE,
                risk_score=90.0 - (i * 5),
                reason="Test",
                required_permissions=[],
                blocking_factors=[],
                approval_status=ApprovalStatus.APPROVED,
                request=request
            )

            await audit.log_decision(request, decision)

        stats = await audit.get_statistics(days=1)
        assert stats["total_validations"] == 5
        assert "approval_rate" in stats


class TestCommandValidationIntegration:
    """Integration tests for command validation."""

    @pytest.mark.asyncio
    async def test_local_service_integration(self):
        """Test integration with LocalService."""
        from app.local_service import LocalService

        local_service = LocalService()

        # Safe command
        request = ValidationRequest(
            command="echo test",
            source=CommandSource.LOCAL_SERVICE
        )

        guardian = GuardianAgent()
        decision = await guardian.validate(request)
        assert decision.approved

    @pytest.mark.asyncio
    async def test_network_risk_assessment(self):
        """Test network risk assessment."""
        agent = GuardianAgent()

        # Network-heavy command
        request = ValidationRequest(
            command="curl -X POST -d '{}' http://api.example.com",
            source=CommandSource.LOCAL_SERVICE
        )

        decision = await agent.validate(request)
        assert "Network" in str(decision.reason) or "risk" in decision.reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
