"""
Dynamic Permission & Capability System

Manages intelligent capability granting for agents with risk assessment,
TTL-based caching, revocation, and comprehensive audit trails.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field

from app.logger import logger
from app.database.database_service import database_service


class DecisionType(str, Enum):
    """Capability decision types."""
    AUTO_GRANT = "auto_grant"
    REQUIRE_CONFIRMATION = "require_confirmation"
    AUTO_DENY = "auto_deny"


class RiskLevel(str, Enum):
    """Risk assessment levels for capabilities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceLimits(BaseModel):
    """Resource consumption limits for capability grant."""
    max_memory_mb: Optional[int] = Field(None, description="Max memory in MB")
    max_cpu_percent: Optional[float] = Field(None, description="Max CPU percentage")
    max_disk_mb: Optional[int] = Field(None, description="Max disk space in MB")
    max_network_bandwidth_mbps: Optional[float] = Field(None, description="Max network bandwidth")
    timeout_seconds: Optional[int] = Field(None, description="Operation timeout in seconds")


class CapabilityRequest(BaseModel):
    """Request for agent capabilities."""
    
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(..., description="Type of agent (e.g., GameDevAgent, NetworkAgent)")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    # Requested capabilities
    tools: List[str] = Field(default_factory=list, description="Requested tools (e.g., compiler, debugger)")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables needed")
    paths: List[str] = Field(default_factory=list, description="File system paths to access")
    network: bool = Field(default=False, description="Network access required")
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits, description="Resource constraints")
    
    # Context for better decision making
    command: Optional[str] = Field(None, description="Command to be executed (for intent analysis)")
    task_description: Optional[str] = Field(None, description="High-level task description")
    context: Optional[str] = Field(None, description="Additional context for decision making")
    
    class Config:
        arbitrary_types_allowed = True


class CapabilityGrant(BaseModel):
    """Granted capability set for an agent."""
    
    grant_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique grant ID")
    request_id: str = Field(..., description="Reference to capability request")
    agent_id: str = Field(..., description="Agent receiving grant")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Grant timestamp")
    audit_id: str = Field(..., description="Audit trail ID")
    
    # Granted capabilities
    granted_tools: List[str] = Field(default_factory=list, description="Approved tools")
    granted_env_vars: Dict[str, str] = Field(default_factory=dict, description="Approved environment variables")
    granted_paths: List[str] = Field(default_factory=list, description="Approved file system paths")
    network_allowed: bool = Field(default=False, description="Network access granted")
    resource_limits: ResourceLimits = Field(..., description="Enforced resource limits")
    
    # Expiry and revocation
    expires_at: Optional[datetime] = Field(None, description="Grant expiry timestamp")
    ttl_seconds: Optional[int] = Field(None, description="Time-to-live in seconds")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp if revoked")
    revocation_token: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Token for revocation")
    
    decision_rationale: str = Field(..., description="Explanation of the decision")
    trust_score: float = Field(default=0.5, description="Agent trust score (0-1)")
    
    class Config:
        arbitrary_types_allowed = True


class CapabilityDeny(BaseModel):
    """Denied capability request."""
    
    deny_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique deny ID")
    request_id: str = Field(..., description="Reference to capability request")
    agent_id: str = Field(..., description="Agent whose request was denied")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Denial timestamp")
    audit_id: str = Field(..., description="Audit trail ID")
    
    denied_reason: str = Field(..., description="Reason for denial")
    denied_capabilities: List[str] = Field(..., description="Capabilities that were denied")
    risk_level: RiskLevel = Field(..., description="Assessed risk level")
    
    class Config:
        arbitrary_types_allowed = True


class CapabilityDecision(BaseModel):
    """Union-like decision response for capability requests."""
    
    decision_type: DecisionType = Field(..., description="Type of decision")
    grant: Optional[CapabilityGrant] = Field(None, description="Grant if AUTO_GRANT")
    deny: Optional[CapabilityDeny] = Field(None, description="Deny if AUTO_DENY")
    confirmation_required: Optional[Dict[str, Any]] = Field(None, description="Details if REQUIRE_CONFIRMATION")
    
    class Config:
        arbitrary_types_allowed = True


@dataclass
class CachedGrant:
    """Cached grant with expiry tracking."""
    grant: CapabilityGrant
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))
    
    def is_expired(self) -> bool:
        """Check if grant has expired."""
        return datetime.utcnow() > self.expires_at


class DynamicPermissionManager:
    """
    Manages dynamic capability granting with intelligent risk assessment,
    TTL-based caching, revocation support, and audit trails.
    """
    
    # Tool-to-agent compatibility matrix
    TOOL_AGENT_COMPATIBILITY = {
        "compiler": {"GameDevAgent", "GenericAgent", "SWEAgent"},
        "debugger": {"GameDevAgent", "GenericAgent", "SWEAgent"},
        "cuda": {"GameDevAgent"},
        "opengl": {"GameDevAgent"},
        "network_socket": {"NetworkAgent", "GenericAgent"},
        "http_client": {"NetworkAgent", "GenericAgent"},
        "dns": {"NetworkAgent", "GenericAgent"},
        "file_system": {"GenericAgent", "SWEAgent", "GameDevAgent"},
        "database": {"GenericAgent", "SWEAgent"},
        "shell": {"GenericAgent", "SWEAgent"},
        "docker": {"GenericAgent", "SWEAgent"},
        "ida_pro": {"SecurityAgent"},
        "radare2": {"SecurityAgent", "GenericAgent"},
        "kernel_debug": {"SecurityAgent"},
    }
    
    # Suspicious capability combinations
    SUSPICIOUS_PATTERNS = [
        {"delete", "system32_access", "powershell"},
        {"network", "shell", "system_access"},
        {"root_access", "network", "kernel_debug"},
        {"db_access", "shell", "file_delete"},
    ]
    
    # Default resource limits by agent type
    DEFAULT_LIMITS_BY_AGENT_TYPE = {
        "GameDevAgent": ResourceLimits(max_memory_mb=4096, max_cpu_percent=75, timeout_seconds=300),
        "NetworkAgent": ResourceLimits(max_network_bandwidth_mbps=100, timeout_seconds=60),
        "SWEAgent": ResourceLimits(max_memory_mb=2048, max_cpu_percent=50, timeout_seconds=600),
        "SecurityAgent": ResourceLimits(max_memory_mb=2048, max_cpu_percent=60, timeout_seconds=120),
        "GenericAgent": ResourceLimits(max_memory_mb=1024, max_cpu_percent=30, timeout_seconds=300),
    }
    
    def __init__(self):
        """Initialize the permission manager."""
        self._grant_cache: Dict[str, CachedGrant] = {}
        self._lock = asyncio.Lock()
        self._agent_trust_scores: Dict[str, float] = {}
        self._agent_error_rates: Dict[str, float] = {}
        logger.info("DynamicPermissionManager initialized")
    
    async def request_capability(self, request: CapabilityRequest) -> CapabilityDecision:
        """
        Process a capability request and return a decision.
        
        Args:
            request: Capability request from an agent
            
        Returns:
            CapabilityDecision with grant, deny, or confirmation required
        """
        async with self._lock:
            # Check cache first
            cached = await self._check_cache(request)
            if cached:
                logger.info(f"Cache hit for request {request.request_id}")
                return cached
            
            # Create audit trail
            audit_id = str(uuid.uuid4())
            await self._log_audit("request", request.agent_id, request.request_id, audit_id, {
                "tools": request.tools,
                "network": request.network,
                "paths": request.paths,
            })
            
            # Assess risk
            risk_level, risk_reasons = await self._assess_risk(request)
            
            # Make decision based on risk level
            if risk_level == RiskLevel.LOW:
                return await self._auto_grant(request, audit_id, risk_reasons)
            elif risk_level == RiskLevel.MEDIUM:
                return await self._require_confirmation(request, audit_id, risk_reasons)
            else:  # HIGH or CRITICAL
                return await self._auto_deny(request, audit_id, risk_reasons, risk_level)
    
    async def _assess_risk(self, request: CapabilityRequest) -> Tuple[RiskLevel, List[str]]:
        """
        Assess risk level of a capability request.
        
        Evaluates:
        - Tool compatibility with agent type
        - Historical context and trust score
        - Capability combinations
        - Command intent
        - Resource consumption validity
        
        Returns:
            Tuple of (RiskLevel, list of reasons)
        """
        reasons = []
        risk_score = 0.0  # 0.0 = safe, 1.0 = critical
        
        # 1. Check tool compatibility
        for tool in request.tools:
            compatible = self._check_tool_compatibility(tool, request.agent_type)
            if not compatible:
                reasons.append(f"Tool '{tool}' not compatible with {request.agent_type}")
                risk_score += 0.25
        
        # 2. Check historical context
        trust_score = await self._get_agent_trust_score(request.agent_id)
        if trust_score < 0.3:
            reasons.append(f"Low trust score for agent {request.agent_id}: {trust_score:.2f}")
            risk_score += 0.20
        
        # 3. Check for suspicious capability combinations
        requested_caps = set(request.tools + (["network"] if request.network else []))
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.issubset(requested_caps):
                reasons.append(f"Suspicious pattern detected: {pattern}")
                risk_score += 0.30
        
        # 4. Analyze command intent if provided
        if request.command:
            intent_risk = await self._analyze_command_intent(request.command)
            if intent_risk > 0:
                reasons.append(f"Command intent detected as potentially dangerous")
                risk_score += intent_risk
        
        # 5. Check resource limits validity
        if request.resource_limits.max_memory_mb and request.resource_limits.max_memory_mb > 16000:
            reasons.append("Unreasonably high memory request")
            risk_score += 0.15
        
        # 6. Check for path access risks
        dangerous_paths = await self._check_path_risks(request.paths)
        if dangerous_paths:
            reasons.append(f"Access to sensitive paths: {dangerous_paths}")
            risk_score += 0.20
        
        # Convert score to risk level
        if risk_score >= 0.7:
            return RiskLevel.CRITICAL, reasons
        elif risk_score >= 0.5:
            return RiskLevel.HIGH, reasons
        elif risk_score >= 0.2:
            return RiskLevel.MEDIUM, reasons
        else:
            return RiskLevel.LOW, reasons
    
    def _check_tool_compatibility(self, tool: str, agent_type: str) -> bool:
        """Check if tool is compatible with agent type."""
        compatible_agents = self.TOOL_AGENT_COMPATIBILITY.get(tool, set())
        return agent_type in compatible_agents
    
    async def _get_agent_trust_score(self, agent_id: str) -> float:
        """Get agent trust score from historical data."""
        # Check memory cache
        if agent_id in self._agent_trust_scores:
            return self._agent_trust_scores[agent_id]
        
        # Query from database for historical metrics
        trust_score = await self._query_agent_trust_from_db(agent_id)
        self._agent_trust_scores[agent_id] = trust_score
        return trust_score
    
    async def _query_agent_trust_from_db(self, agent_id: str) -> float:
        """Query database for agent trust metrics."""
        try:
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT AVG(CASE WHEN action = 'grant' THEN 1.0 ELSE 0.5 END) as success_rate
                    FROM permissions_audit
                    WHERE agent_id = ?
                    AND created_at > datetime('now', '-30 days')
                """, (agent_id,))
                row = await cursor.fetchone()
                if row and row[0] is not None:
                    return float(row[0])
                return 0.5  # Default neutral score for new agents
        except Exception as e:
            logger.debug(f"Could not query agent trust (expected during initialization): {e}")
            return 0.5
    
    async def _analyze_command_intent(self, command: str) -> float:
        """
        Analyze command intent for danger signals.
        Returns risk score (0.0-0.5).
        """
        dangerous_keywords = {
            "rm -rf": 0.4,
            "format": 0.3,
            "dd": 0.3,
            "mkfs": 0.3,
            "destroy": 0.2,
            "delete": 0.15,
            "drop": 0.1,
        }
        
        for keyword, risk in dangerous_keywords.items():
            if keyword in command.lower():
                return risk
        
        return 0.0
    
    async def _check_path_risks(self, paths: List[str]) -> List[str]:
        """Check for access to sensitive paths."""
        sensitive_paths = {
            "/etc/shadow",
            "/etc/passwd",
            "/root",
            "C:\\Windows\\System32",
            "C:\\Windows\\System",
        }
        
        risky = []
        for path in paths:
            for sensitive in sensitive_paths:
                if sensitive in path:
                    risky.append(path)
                    break
        
        return risky
    
    async def _auto_grant(self, request: CapabilityRequest, audit_id: str, 
                         risk_reasons: List[str]) -> CapabilityDecision:
        """Create and return an AUTO_GRANT decision."""
        trust_score = await self._get_agent_trust_score(request.agent_id)
        
        grant = CapabilityGrant(
            request_id=request.request_id,
            agent_id=request.agent_id,
            audit_id=audit_id,
            granted_tools=request.tools,
            granted_env_vars=request.env_vars,
            granted_paths=request.paths,
            network_allowed=request.network,
            resource_limits=self._apply_default_limits(request),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            ttl_seconds=3600,
            decision_rationale="; ".join(risk_reasons) if risk_reasons else "Low risk capability request",
            trust_score=trust_score,
        )
        
        # Cache the grant
        self._grant_cache[request.request_id] = CachedGrant(
            grant=grant,
            expires_at=grant.expires_at
        )
        
        # Persist to database
        await self._persist_grant(grant)
        await self._log_audit("grant", request.agent_id, request.request_id, audit_id, {
            "granted_tools": grant.granted_tools,
            "network_allowed": grant.network_allowed,
            "ttl_seconds": grant.ttl_seconds,
        })
        
        logger.info(f"AUTO_GRANT for {request.agent_id}: {request.tools}")
        
        return CapabilityDecision(
            decision_type=DecisionType.AUTO_GRANT,
            grant=grant,
        )
    
    async def _require_confirmation(self, request: CapabilityRequest, audit_id: str,
                                   risk_reasons: List[str]) -> CapabilityDecision:
        """Create and return REQUIRE_CONFIRMATION decision."""
        trust_score = await self._get_agent_trust_score(request.agent_id)
        
        confirmation_details = {
            "agent_id": request.agent_id,
            "agent_type": request.agent_type,
            "request_id": request.request_id,
            "audit_id": audit_id,
            "requested_tools": request.tools,
            "network_access": request.network,
            "file_paths": request.paths,
            "resource_limits": asdict(request.resource_limits),
            "risk_reasons": risk_reasons,
            "task_description": request.task_description,
            "trust_score": trust_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self._log_audit("confirmation_required", request.agent_id, request.request_id, audit_id, {
            "risk_reasons": risk_reasons,
            "tools": request.tools,
        })
        
        logger.info(f"REQUIRE_CONFIRMATION for {request.agent_id}: {request.tools}")
        
        return CapabilityDecision(
            decision_type=DecisionType.REQUIRE_CONFIRMATION,
            confirmation_required=confirmation_details,
        )
    
    async def _auto_deny(self, request: CapabilityRequest, audit_id: str,
                        risk_reasons: List[str], risk_level: RiskLevel) -> CapabilityDecision:
        """Create and return AUTO_DENY decision."""
        deny = CapabilityDeny(
            request_id=request.request_id,
            agent_id=request.agent_id,
            audit_id=audit_id,
            denied_reason="; ".join(risk_reasons),
            denied_capabilities=request.tools,
            risk_level=risk_level,
        )
        
        await self._log_audit("deny", request.agent_id, request.request_id, audit_id, {
            "risk_level": risk_level.value,
            "denied_tools": request.tools,
            "reasons": risk_reasons,
        })
        
        logger.warning(f"AUTO_DENY for {request.agent_id}: {request.tools} - Risk: {risk_level.value}")
        
        return CapabilityDecision(
            decision_type=DecisionType.AUTO_DENY,
            deny=deny,
        )
    
    def _apply_default_limits(self, request: CapabilityRequest) -> ResourceLimits:
        """Apply default resource limits based on agent type."""
        defaults = self.DEFAULT_LIMITS_BY_AGENT_TYPE.get(
            request.agent_type,
            self.DEFAULT_LIMITS_BY_AGENT_TYPE["GenericAgent"]
        )
        
        # Merge with requested limits (request takes precedence if more restrictive)
        def min_or_default(requested, default_val, infinity_val):
            """Helper to get minimum of requested and default, handling None values."""
            if requested is None and default_val is None:
                return None
            if requested is None:
                return default_val
            if default_val is None:
                return requested
            return min(requested, default_val)
        
        return ResourceLimits(
            max_memory_mb=min_or_default(
                request.resource_limits.max_memory_mb,
                defaults.max_memory_mb,
                float('inf')
            ),
            max_cpu_percent=min_or_default(
                request.resource_limits.max_cpu_percent,
                defaults.max_cpu_percent,
                100
            ),
            max_disk_mb=request.resource_limits.max_disk_mb,
            max_network_bandwidth_mbps=min_or_default(
                request.resource_limits.max_network_bandwidth_mbps,
                defaults.max_network_bandwidth_mbps,
                float('inf')
            ),
            timeout_seconds=request.resource_limits.timeout_seconds or defaults.timeout_seconds,
        )
    
    async def _check_cache(self, request: CapabilityRequest) -> Optional[CapabilityDecision]:
        """Check if request is in cache and not expired."""
        if request.request_id not in self._grant_cache:
            return None
        
        cached = self._grant_cache[request.request_id]
        if cached.is_expired():
            del self._grant_cache[request.request_id]
            return None
        
        # Return cached grant decision
        return CapabilityDecision(
            decision_type=DecisionType.AUTO_GRANT,
            grant=cached.grant,
        )
    
    async def _persist_grant(self, grant: CapabilityGrant) -> None:
        """Persist grant to database."""
        try:
            async with await database_service.get_connection() as db:
                await db.execute("""
                    INSERT INTO permissions_grants
                    (grant_id, request_id, agent_id, granted_tools, network_allowed, 
                     ttl_seconds, expires_at, revocation_token, audit_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    grant.grant_id,
                    grant.request_id,
                    grant.agent_id,
                    json.dumps(grant.granted_tools),
                    grant.network_allowed,
                    grant.ttl_seconds,
                    grant.expires_at.isoformat() if grant.expires_at else None,
                    grant.revocation_token,
                    grant.audit_id,
                    datetime.utcnow().isoformat(),
                ))
                await db.commit()
        except Exception as e:
            logger.debug(f"Could not persist grant (database may not be initialized): {e}")
    
    async def _log_audit(self, action: str, agent_id: str, request_id: str, 
                        audit_id: str, metadata: Dict[str, Any]) -> None:
        """Log audit trail entry."""
        try:
            async with await database_service.get_connection() as db:
                await db.execute("""
                    INSERT INTO permissions_audit
                    (audit_id, action, agent_id, request_id, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    audit_id,
                    action,
                    agent_id,
                    request_id,
                    json.dumps(metadata),
                    datetime.utcnow().isoformat(),
                ))
                await db.commit()
        except Exception as e:
            logger.debug(f"Could not log audit (database may not be initialized): {e}")
    
    async def revoke_grant(self, grant_id: str, revocation_token: str, 
                          reason: str = "User revocation") -> bool:
        """
        Revoke a capability grant.
        
        Args:
            grant_id: ID of grant to revoke
            revocation_token: Token required for revocation
            reason: Reason for revocation
            
        Returns:
            True if revocation successful, False otherwise
        """
        try:
            async with self._lock:
                # Verify token and revoke
                async with await database_service.get_connection() as db:
                    cursor = await db.execute("""
                        SELECT agent_id, request_id FROM permissions_grants
                        WHERE grant_id = ? AND revocation_token = ?
                    """, (grant_id, revocation_token))
                    row = await cursor.fetchone()
                    
                    if not row:
                        logger.debug(f"Invalid revocation attempt for grant {grant_id}")
                        return False
                    
                    agent_id, request_id = row
                    
                    # Mark as revoked
                    await db.execute("""
                        UPDATE permissions_grants
                        SET revoked_at = ?, revoked_reason = ?
                        WHERE grant_id = ?
                    """, (datetime.utcnow().isoformat(), reason, grant_id))
                    await db.commit()
                    
                    # Remove from cache
                    if request_id in self._grant_cache:
                        del self._grant_cache[request_id]
                    
                    # Audit the revocation
                    audit_id = str(uuid.uuid4())
                    await self._log_audit("revoke", agent_id, request_id, audit_id, {
                        "grant_id": grant_id,
                        "reason": reason,
                    })
                    
                    logger.info(f"Revoked grant {grant_id} for agent {agent_id}")
                    return True
                    
        except Exception as e:
            logger.debug(f"Error revoking grant (database may not be initialized): {e}")
            return False
    
    async def get_active_grants(self, agent_id: str) -> List[CapabilityGrant]:
        """Get all active (non-revoked, non-expired) grants for an agent."""
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = __import__('aiosqlite').Row
                cursor = await db.execute("""
                    SELECT grant_id, request_id, agent_id, granted_tools, network_allowed,
                           ttl_seconds, expires_at, revocation_token, audit_id, created_at
                    FROM permissions_grants
                    WHERE agent_id = ? AND revoked_at IS NULL
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY created_at DESC
                """, (agent_id, datetime.utcnow().isoformat()))
                rows = await cursor.fetchall()
                
                grants = []
                for row in rows:
                    grant = CapabilityGrant(
                        grant_id=row["grant_id"],
                        request_id=row["request_id"],
                        agent_id=row["agent_id"],
                        audit_id=row["audit_id"],
                        granted_tools=json.loads(row["granted_tools"]),
                        network_allowed=bool(row["network_allowed"]),
                        ttl_seconds=row["ttl_seconds"],
                        expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                        revocation_token=row["revocation_token"],
                    )
                    grants.append(grant)
                
                return grants
        except Exception as e:
            logger.debug(f"Could not fetch active grants (database may not be initialized): {e}")
            return []
    
    async def get_audit_log(self, agent_id: Optional[str] = None, 
                           action: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit log entries.
        
        Args:
            agent_id: Filter by agent ID
            action: Filter by action type
            limit: Maximum entries to return
            
        Returns:
            List of audit log entries
        """
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = __import__('aiosqlite').Row
                
                query = "SELECT * FROM permissions_audit WHERE 1=1"
                params = []
                
                if agent_id:
                    query += " AND agent_id = ?"
                    params.append(agent_id)
                
                if action:
                    query += " AND action = ?"
                    params.append(action)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        "audit_id": row["audit_id"],
                        "action": row["action"],
                        "agent_id": row["agent_id"],
                        "request_id": row["request_id"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"],
                    })
                
                return results
        except Exception as e:
            logger.debug(f"Could not fetch audit log (database may not be initialized): {e}")
            return []


# Global singleton instance
_permission_manager: Optional[DynamicPermissionManager] = None


def get_permission_manager() -> DynamicPermissionManager:
    """Get or create the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = DynamicPermissionManager()
    return _permission_manager
