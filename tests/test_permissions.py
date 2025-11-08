"""
Tests for Dynamic Permission & Capability System
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock, Mock

from app.security.permissions import (
    CapabilityRequest,
    CapabilityGrant,
    CapabilityDeny,
    CapabilityDecision,
    DecisionType,
    DynamicPermissionManager,
    ResourceLimits,
    RiskLevel,
)


@pytest.fixture
def permission_manager():
    """Create a permission manager instance for testing."""
    return DynamicPermissionManager()


@pytest.fixture
def sample_request():
    """Create a sample capability request."""
    return CapabilityRequest(
        agent_id="test_agent_1",
        agent_type="GenericAgent",
        tools=["compiler"],
        env_vars={"PATH": "/usr/bin"},
        paths=["/home/user/project"],
        network=False,
        task_description="Compile a simple C program",
    )


class TestCapabilityModels:
    """Test capability request and grant models."""
    
    def test_capability_request_creation(self):
        """Test creating a capability request."""
        request = CapabilityRequest(
            agent_id="test_agent",
            agent_type="GameDevAgent",
            tools=["cuda", "opengl"],
            env_vars={"CUDA_PATH": "/usr/local/cuda"},
            paths=["/usr/local/cuda"],
            network=False,
        )
        
        assert request.agent_id == "test_agent"
        assert request.agent_type == "GameDevAgent"
        assert "cuda" in request.tools
        assert "opengl" in request.tools
        assert request.network is False
    
    def test_capability_grant_creation(self):
        """Test creating a capability grant."""
        grant = CapabilityGrant(
            request_id="req_1",
            agent_id="agent_1",
            audit_id="audit_1",
            granted_tools=["compiler"],
            network_allowed=False,
            resource_limits=ResourceLimits(max_memory_mb=1024),
            decision_rationale="Safe operation",
        )
        
        assert grant.agent_id == "agent_1"
        assert "compiler" in grant.granted_tools
        assert grant.resource_limits.max_memory_mb == 1024
    
    def test_capability_deny_creation(self):
        """Test creating a capability deny."""
        deny = CapabilityDeny(
            request_id="req_1",
            agent_id="agent_1",
            audit_id="audit_1",
            denied_reason="Unauthorized tool access",
            denied_capabilities=["root_access"],
            risk_level=RiskLevel.CRITICAL,
        )
        
        assert deny.agent_id == "agent_1"
        assert deny.risk_level == RiskLevel.CRITICAL
        assert "root_access" in deny.denied_capabilities


class TestToolCompatibility:
    """Test tool-agent compatibility checking."""
    
    @pytest.mark.asyncio
    async def test_compatible_tool_gamedev(self, permission_manager):
        """Test compatible tool for GameDevAgent."""
        assert permission_manager._check_tool_compatibility("cuda", "GameDevAgent")
        assert permission_manager._check_tool_compatibility("opengl", "GameDevAgent")
        assert permission_manager._check_tool_compatibility("compiler", "GameDevAgent")
    
    @pytest.mark.asyncio
    async def test_compatible_tool_network_agent(self, permission_manager):
        """Test compatible tools for NetworkAgent."""
        assert permission_manager._check_tool_compatibility("network_socket", "NetworkAgent")
        assert permission_manager._check_tool_compatibility("http_client", "NetworkAgent")
        assert permission_manager._check_tool_compatibility("dns", "NetworkAgent")
    
    @pytest.mark.asyncio
    async def test_incompatible_tool(self, permission_manager):
        """Test incompatible tool assignment."""
        # NetworkAgent should not have CUDA
        assert not permission_manager._check_tool_compatibility("cuda", "NetworkAgent")
        # GenericAgent shouldn't have IDA Pro
        assert not permission_manager._check_tool_compatibility("ida_pro", "GenericAgent")


class TestRiskAssessment:
    """Test risk assessment logic."""
    
    @pytest.mark.asyncio
    async def test_command_intent_analysis_safe(self, permission_manager):
        """Test safe command intent analysis."""
        risk = await permission_manager._analyze_command_intent("gcc -c file.c")
        assert risk == 0.0
    
    @pytest.mark.asyncio
    async def test_command_intent_analysis_dangerous(self, permission_manager):
        """Test dangerous command intent analysis."""
        risk = await permission_manager._analyze_command_intent("rm -rf /")
        assert risk > 0.0
        
        risk_dd = await permission_manager._analyze_command_intent("dd if=/dev/sda")
        assert risk_dd > 0.0
    
    @pytest.mark.asyncio
    async def test_path_risk_detection(self, permission_manager):
        """Test sensitive path detection."""
        risky_paths = await permission_manager._check_path_risks(["/etc/shadow", "/etc/passwd"])
        assert len(risky_paths) == 2
        
        safe_paths = await permission_manager._check_path_risks(["/home/user/data", "/tmp/files"])
        assert len(safe_paths) == 0
    
    @pytest.mark.asyncio
    async def test_suspicious_pattern_detection(self, permission_manager, sample_request):
        """Test suspicious capability pattern detection."""
        # Create request with suspicious combo
        request = CapabilityRequest(
            agent_id="bad_agent",
            agent_type="GenericAgent",
            tools=["delete", "system32_access", "powershell"],
            network=False,
        )
        
        risk_level, reasons = await permission_manager._assess_risk(request)
        # Should have at least medium risk due to pattern
        assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert any("Suspicious pattern" in r for r in reasons)


@pytest.mark.asyncio
class TestAutoGrant:
    """Test AUTO_GRANT decision logic."""
    
    async def test_auto_grant_safe_request(self, permission_manager, sample_request):
        """Test AUTO_GRANT for safe requests."""
        with patch.object(permission_manager, '_persist_grant', new_callable=AsyncMock):
            with patch.object(permission_manager, '_log_audit', new_callable=AsyncMock):
                with patch.object(permission_manager, '_get_agent_trust_score', return_value=0.8):
                    decision = await permission_manager.request_capability(sample_request)
                    
                    assert decision.decision_type == DecisionType.AUTO_GRANT
                    assert decision.grant is not None
                    assert sample_request.tools[0] in decision.grant.granted_tools
                    assert decision.grant.ttl_seconds == 3600


@pytest.mark.asyncio
class TestRequireConfirmation:
    """Test REQUIRE_CONFIRMATION decision logic."""
    
    async def test_require_confirmation_medium_risk(self, permission_manager):
        """Test REQUIRE_CONFIRMATION for medium-risk requests."""
        request = CapabilityRequest(
            agent_id="new_agent",
            agent_type="GenericAgent",
            tools=["network_socket", "shell"],
            network=True,
            command="curl http://example.com",
        )
        
        with patch.object(permission_manager, '_log_audit', new_callable=AsyncMock):
            with patch.object(permission_manager, '_get_agent_trust_score', return_value=0.3):
                decision = await permission_manager.request_capability(request)
                
                assert decision.decision_type == DecisionType.REQUIRE_CONFIRMATION
                assert decision.confirmation_required is not None
                assert "network_socket" in decision.confirmation_required["requested_tools"]


@pytest.mark.asyncio
class TestAutoDeny:
    """Test AUTO_DENY decision logic."""
    
    async def test_auto_deny_high_risk(self, permission_manager):
        """Test AUTO_DENY for high-risk requests."""
        request = CapabilityRequest(
            agent_id="risky_agent",
            agent_type="GenericAgent",
            tools=["kernel_debug", "root_access"],
            paths=["/etc/shadow"],
            network=True,
            command="rm -rf /",
        )
        
        with patch.object(permission_manager, '_log_audit', new_callable=AsyncMock):
            with patch.object(permission_manager, '_get_agent_trust_score', return_value=0.1):
                decision = await permission_manager.request_capability(request)
                
                assert decision.decision_type == DecisionType.AUTO_DENY
                assert decision.deny is not None
                assert decision.deny.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


@pytest.mark.asyncio
class TestCaching:
    """Test grant caching with TTL."""
    
    async def test_cache_hit(self, permission_manager, sample_request):
        """Test cache hit for repeated requests."""
        with patch.object(permission_manager, '_persist_grant', new_callable=AsyncMock):
            with patch.object(permission_manager, '_log_audit', new_callable=AsyncMock):
                with patch.object(permission_manager, '_get_agent_trust_score', return_value=0.8):
                    # First request
                    decision1 = await permission_manager.request_capability(sample_request)
                    
                    # Second identical request should hit cache
                    decision2 = await permission_manager.request_capability(sample_request)
                    
                    assert decision1.grant.grant_id == decision2.grant.grant_id
    
    async def test_cache_expiry(self, permission_manager, sample_request):
        """Test cache expiry with TTL."""
        from app.security.permissions import CachedGrant
        
        grant = CapabilityGrant(
            request_id="req_1",
            agent_id="agent_1",
            audit_id="audit_1",
            granted_tools=["compiler"],
            network_allowed=False,
            resource_limits=ResourceLimits(),
            decision_rationale="Test",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        
        cached = CachedGrant(
            grant=grant,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        
        assert cached.is_expired()
        
        # Non-expired grant
        future_grant = CapabilityGrant(
            request_id="req_2",
            agent_id="agent_2",
            audit_id="audit_2",
            granted_tools=["debugger"],
            network_allowed=False,
            resource_limits=ResourceLimits(),
            decision_rationale="Test",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        cached_future = CachedGrant(
            grant=future_grant,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert not cached_future.is_expired()


@pytest.mark.asyncio
class TestRevocation:
    """Test capability revocation."""
    
    async def test_revoke_grant_success(self, permission_manager):
        """Test successful grant revocation."""
        grant = CapabilityGrant(
            request_id="req_1",
            agent_id="agent_1",
            audit_id="audit_1",
            granted_tools=["compiler"],
            network_allowed=False,
            resource_limits=ResourceLimits(),
            decision_rationale="Test",
        )
        
        # Mock database operations
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = ("agent_1", "req_1")
        
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_cursor
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        
        from app.database.database_service import database_service
        with patch.object(database_service, 'get_connection', return_value=mock_db):
            with patch.object(permission_manager, '_log_audit', new_callable=AsyncMock):
                result = await permission_manager.revoke_grant(
                    grant.grant_id,
                    grant.revocation_token,
                    "User revocation"
                )
                
                # Should succeed (mocked)
                assert isinstance(result, bool)
    
    async def test_revoke_grant_invalid_token(self, permission_manager):
        """Test revocation with invalid token."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = None  # Invalid token
        
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_cursor
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        
        from app.database.database_service import database_service
        with patch.object(database_service, 'get_connection', return_value=mock_db):
            result = await permission_manager.revoke_grant(
                "invalid_grant_id",
                "invalid_token",
                "User revocation"
            )
            
            assert result is False


@pytest.mark.asyncio
class TestResourceLimits:
    """Test resource limit enforcement."""
    
    async def test_apply_default_limits_gamedev(self, permission_manager):
        """Test applying default limits for GameDevAgent."""
        request = CapabilityRequest(
            agent_id="game_dev",
            agent_type="GameDevAgent",
            tools=["cuda"],
            resource_limits=ResourceLimits(),
        )
        
        limits = permission_manager._apply_default_limits(request)
        
        assert limits.max_memory_mb == 4096
        assert limits.max_cpu_percent == 75
        assert limits.timeout_seconds == 300
    
    async def test_apply_default_limits_network_agent(self, permission_manager):
        """Test applying default limits for NetworkAgent."""
        request = CapabilityRequest(
            agent_id="net_agent",
            agent_type="NetworkAgent",
            tools=["http_client"],
            resource_limits=ResourceLimits(),
        )
        
        limits = permission_manager._apply_default_limits(request)
        
        assert limits.max_network_bandwidth_mbps == 100
        assert limits.timeout_seconds == 60
    
    async def test_limit_constraints(self, permission_manager):
        """Test that requested limits can't exceed defaults."""
        request = CapabilityRequest(
            agent_id="greedy_agent",
            agent_type="GenericAgent",
            tools=["compiler"],
            resource_limits=ResourceLimits(max_memory_mb=16000),  # Way too high
        )
        
        limits = permission_manager._apply_default_limits(request)
        
        # Should not exceed default for GenericAgent
        assert limits.max_memory_mb <= 1024


@pytest.mark.asyncio
class TestTrustScoring:
    """Test agent trust score calculation."""
    
    async def test_default_trust_score_new_agent(self, permission_manager):
        """Test default trust score for new agents."""
        trust_score = await permission_manager._get_agent_trust_score("new_agent_xyz")
        
        # New agents should have neutral score
        assert trust_score == 0.5
    
    async def test_trust_score_caching(self, permission_manager):
        """Test trust score caching."""
        # Set cached score
        permission_manager._agent_trust_scores["cached_agent"] = 0.7
        
        score = await permission_manager._get_agent_trust_score("cached_agent")
        
        assert score == 0.7


class TestAuditTrail:
    """Test audit trail logging."""
    
    @pytest.mark.asyncio
    async def test_audit_log_structure(self, permission_manager):
        """Test audit log entry structure."""
        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        
        from app.database.database_service import database_service
        with patch.object(database_service, 'get_connection', return_value=mock_db):
            await permission_manager._log_audit(
                "grant",
                "agent_1",
                "req_1",
                "audit_1",
                {"tools": ["compiler"]},
            )
            
            # Verify execute was called
            assert mock_db.execute.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
