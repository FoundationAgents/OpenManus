"""Capability grant system for adaptive sandbox authorization.

Defines what tools, paths, and environment variables an agent can access
in a sandbox execution context. Includes Guardian validation checkpoints.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.logger import logger


class PathAccessMode(Enum):
    """File system access modes for granted paths."""
    READ_ONLY = "ro"
    READ_WRITE = "rw"


class GrantStatus(Enum):
    """Status of a capability grant."""
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class GrantDecision:
    """Guardian decision for a capability grant request."""
    approved: bool
    grant_id: str
    reason: str
    risk_level: str
    conditions: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None
    

class CapabilityGrant(BaseModel):
    """Defines capabilities granted to an agent for sandbox execution.
    
    A grant specifies:
    - Which tools/executables the agent can use
    - Which file paths the agent can access and how (ro/rw)
    - Which environment variables can be inherited/set
    - Resource limits (CPU %, memory, timeout)
    - Isolation level constraints
    """
    
    grant_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique grant ID")
    agent_id: str = Field(..., description="Agent ID this grant is for")
    status: GrantStatus = Field(default=GrantStatus.APPROVED, description="Current grant status")
    created_at: float = Field(default_factory=time.time, description="Grant creation timestamp")
    expires_at: Optional[float] = Field(None, description="Grant expiration time (None for no expiry)")
    
    # Tool/command access
    allowed_tools: Set[str] = Field(default_factory=set, description="Allowed tools/executables (e.g., python, git, npm)")
    blocked_tools: Set[str] = Field(default_factory=set, description="Explicitly blocked tools")
    
    # File system access: path -> access_mode
    allowed_paths: Dict[str, PathAccessMode] = Field(
        default_factory=dict, 
        description="Allowed file paths with access modes (ro/rw)"
    )
    blocked_paths: List[str] = Field(default_factory=list, description="Blocked path patterns")
    
    # Environment variables
    env_whitelist: Set[str] = Field(
        default_factory=set,
        description="Environment variables to inherit from host (e.g., PATH, HOME)"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Explicit environment variables to set"
    )
    
    # Network access
    network_enabled: bool = Field(False, description="Allow network access")
    allowed_domains: Set[str] = Field(default_factory=set, description="Allowed network domains")
    
    # Resource limits
    cpu_percent: float = Field(80.0, description="CPU limit as percentage of system CPU")
    memory_mb: int = Field(512, description="Memory limit in MB")
    timeout_seconds: int = Field(300, description="Command timeout in seconds")
    
    # Isolation constraints
    min_isolation_level: int = Field(0, description="Minimum isolation level (0=TRUSTED to 4=ISOLATED)")
    max_isolation_level: int = Field(4, description="Maximum isolation level")
    
    # Audit/Guardian metadata
    granted_by: str = Field(default="system", description="Who/what granted this capability")
    grant_reason: str = Field(default="", description="Reason for the grant")
    risk_assessment: Optional[str] = Field(None, description="Guardian risk assessment")
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_valid(self) -> bool:
        """Check if grant is currently valid (not expired or revoked)."""
        if self.status == GrantStatus.REVOKED:
            return False
        if self.status == GrantStatus.EXPIRED:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True
    
    def can_execute_tool(self, tool: str) -> bool:
        """Check if the agent can execute a specific tool."""
        if tool in self.blocked_tools:
            return False
        if self.allowed_tools and tool not in self.allowed_tools:
            return False
        return True
    
    def get_allowed_access_for_path(self, path: str) -> Optional[PathAccessMode]:
        """Check if agent can access a path and in what mode."""
        # Check blocked patterns first
        for blocked in self.blocked_paths:
            if path.startswith(blocked):
                return None
        
        # Check allowed paths
        for allowed_path, mode in self.allowed_paths.items():
            if path.startswith(allowed_path):
                return mode
        
        return None
    
    def get_filtered_environment(self, host_env: Dict[str, str]) -> Dict[str, str]:
        """Get filtered environment variables for sandbox.
        
        Combines host environment (filtered by whitelist) with explicit vars.
        """
        filtered = {}
        
        # Add whitelisted host environment variables
        for var_name in self.env_whitelist:
            if var_name in host_env:
                filtered[var_name] = host_env[var_name]
        
        # Override with explicitly set variables
        filtered.update(self.env_vars)
        
        # Always include sandbox identifiers
        filtered["SANDBOX_MODE"] = "adaptive"
        filtered["GRANT_ID"] = self.grant_id
        
        return filtered
    
    def to_dict(self) -> Dict:
        """Convert grant to dictionary for serialization."""
        return {
            "grant_id": self.grant_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "allowed_tools": list(self.allowed_tools),
            "blocked_tools": list(self.blocked_tools),
            "allowed_paths": {k: v.value for k, v in self.allowed_paths.items()},
            "blocked_paths": self.blocked_paths,
            "env_whitelist": list(self.env_whitelist),
            "env_vars": self.env_vars,
            "network_enabled": self.network_enabled,
            "allowed_domains": list(self.allowed_domains),
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "timeout_seconds": self.timeout_seconds,
            "min_isolation_level": self.min_isolation_level,
            "max_isolation_level": self.max_isolation_level,
            "granted_by": self.granted_by,
            "grant_reason": self.grant_reason,
            "risk_assessment": self.risk_assessment,
        }


class GrantManager:
    """Manages capability grants for agents."""
    
    def __init__(self):
        """Initialize grant manager."""
        self._grants: Dict[str, CapabilityGrant] = {}
        self._checkpoints: Dict[str, List[GrantDecision]] = {}  # agent_id -> decisions
    
    def create_grant(self, grant: CapabilityGrant) -> str:
        """Create and store a new grant."""
        self._grants[grant.grant_id] = grant
        logger.info(f"Created grant {grant.grant_id} for agent {grant.agent_id}")
        return grant.grant_id
    
    def get_grant(self, grant_id: str) -> Optional[CapabilityGrant]:
        """Get a grant by ID."""
        return self._grants.get(grant_id)
    
    def get_agent_grants(self, agent_id: str) -> List[CapabilityGrant]:
        """Get all valid grants for an agent."""
        grants = []
        for grant in self._grants.values():
            if grant.agent_id == agent_id and grant.is_valid():
                grants.append(grant)
        return grants
    
    def revoke_grant(self, grant_id: str) -> bool:
        """Revoke a grant."""
        grant = self._grants.get(grant_id)
        if grant:
            grant.status = GrantStatus.REVOKED
            logger.info(f"Revoked grant {grant_id}")
            return True
        return False
    
    def revoke_agent_grants(self, agent_id: str) -> int:
        """Revoke all grants for an agent."""
        count = 0
        for grant in self._grants.values():
            if grant.agent_id == agent_id and grant.status != GrantStatus.REVOKED:
                grant.status = GrantStatus.REVOKED
                count += 1
        logger.info(f"Revoked {count} grants for agent {agent_id}")
        return count
    
    def record_checkpoint(self, agent_id: str, decision: GrantDecision) -> None:
        """Record a Guardian checkpoint decision."""
        if agent_id not in self._checkpoints:
            self._checkpoints[agent_id] = []
        self._checkpoints[agent_id].append(decision)
        logger.debug(f"Recorded checkpoint for agent {agent_id}: {decision.reason}")
    
    def get_checkpoints(self, agent_id: str) -> List[GrantDecision]:
        """Get all checkpoint decisions for an agent."""
        return self._checkpoints.get(agent_id, [])
    
    def get_grant_stats(self) -> Dict:
        """Get statistics about active grants."""
        active_grants = [g for g in self._grants.values() if g.is_valid()]
        agents = set(g.agent_id for g in active_grants)
        
        return {
            "total_grants": len(self._grants),
            "active_grants": len(active_grants),
            "unique_agents": len(agents),
            "revoked_grants": len([g for g in self._grants.values() if g.status == GrantStatus.REVOKED]),
            "expired_grants": len([g for g in self._grants.values() if g.status == GrantStatus.EXPIRED]),
        }


# Global grant manager
_grant_manager: Optional[GrantManager] = None


def get_grant_manager() -> GrantManager:
    """Get the global grant manager."""
    global _grant_manager
    if _grant_manager is None:
        _grant_manager = GrantManager()
    return _grant_manager
