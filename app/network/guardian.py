"""
Guardian security and policy enforcement system for network operations.

Provides risk assessment, policy validation, and approval workflows for
network requests, WebSocket connections, and diagnostic operations.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime

from app.utils.logger import logger


class RiskLevel(str, Enum):
    """Risk levels for network operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationType(str, Enum):
    """Types of network operations."""
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    HTTP_PUT = "http_put"
    HTTP_DELETE = "http_delete"
    WEBSOCKET = "websocket"
    DNS_LOOKUP = "dns_lookup"
    ICMP_PING = "icmp_ping"
    ICMP_TRACEROUTE = "icmp_traceroute"
    API_CALL = "api_call"


class RiskAssessment(BaseModel):
    """Result of a Guardian risk assessment."""
    
    level: RiskLevel
    approved: bool
    reasons: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class NetworkPolicy(BaseModel):
    """Policy configuration for network operations."""
    
    name: str
    description: str
    allowed_operations: Set[OperationType] = Field(default_factory=set)
    blocked_hosts: List[str] = Field(default_factory=list)
    allowed_hosts: List[str] = Field(default_factory=list)
    blocked_ports: List[int] = Field(default_factory=list)
    allowed_ports: List[int] = Field(default_factory=list)
    max_request_size: Optional[int] = None  # bytes
    require_confirmation: List[OperationType] = Field(default_factory=list)
    enable_logging: bool = True
    
    class Config:
        arbitrary_types_allowed = True


class Guardian:
    """
    Guardian system for network security and policy enforcement.
    
    Assesses risk levels, validates operations against policies,
    and manages approval workflows for network activities.
    """
    
    # Default blocked patterns
    DANGEROUS_PATTERNS = [
        r"localhost",
        r"127\.0\.0\.\d+",
        r"0\.0\.0\.0",
        r"192\.168\.\d+\.\d+",
        r"10\.\d+\.\d+\.\d+",
        r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
        r"::1",
        r"169\.254\.\d+\.\d+",  # Link-local
    ]
    
    # Sensitive ports
    SENSITIVE_PORTS = {
        22,    # SSH
        23,    # Telnet
        25,    # SMTP
        135,   # Windows RPC
        139,   # NetBIOS
        445,   # SMB
        1433,  # MSSQL
        3306,  # MySQL
        3389,  # RDP
        5432,  # PostgreSQL
        6379,  # Redis
        27017, # MongoDB
    }
    
    def __init__(self, policy: Optional[NetworkPolicy] = None):
        """
        Initialize Guardian with a network policy.
        
        Args:
            policy: Network policy configuration, uses default if None
        """
        self.policy = policy or self._create_default_policy()
        self._approval_cache: Dict[str, bool] = {}
        logger.info(f"Guardian initialized with policy: {self.policy.name}")
    
    @staticmethod
    def _create_default_policy() -> NetworkPolicy:
        """Create a default permissive policy."""
        return NetworkPolicy(
            name="default",
            description="Default network policy with basic security",
            allowed_operations=set(OperationType),
            blocked_ports=list(Guardian.SENSITIVE_PORTS),
            require_confirmation=[
                OperationType.HTTP_POST,
                OperationType.HTTP_PUT,
                OperationType.HTTP_DELETE,
            ],
            enable_logging=True
        )
    
    def assess_risk(
        self,
        operation: OperationType,
        host: str,
        port: Optional[int] = None,
        data_size: Optional[int] = None,
        **kwargs
    ) -> RiskAssessment:
        """
        Assess the risk level of a network operation.
        
        Args:
            operation: Type of network operation
            host: Target hostname or IP address
            port: Target port (if applicable)
            data_size: Size of data being sent (if applicable)
            **kwargs: Additional metadata for assessment
            
        Returns:
            RiskAssessment with level, approval status, and reasons
        """
        reasons = []
        risk_score = 0
        
        # Check if operation is allowed
        if operation not in self.policy.allowed_operations:
            reasons.append(f"Operation {operation.value} not allowed by policy")
            risk_score += 100
        
        # Check host blocklist
        if self._is_host_blocked(host):
            reasons.append(f"Host {host} is in blocklist")
            risk_score += 50
        
        # Check if host is in allowlist (if allowlist is defined)
        if self.policy.allowed_hosts and not self._is_host_allowed(host):
            reasons.append(f"Host {host} not in allowlist")
            risk_score += 30
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.match(pattern, host, re.IGNORECASE):
                reasons.append(f"Host matches dangerous pattern: {pattern}")
                risk_score += 40
        
        # Check port restrictions
        if port:
            if self.policy.blocked_ports and port in self.policy.blocked_ports:
                reasons.append(f"Port {port} is blocked")
                risk_score += 50
            
            if self.policy.allowed_ports and port not in self.policy.allowed_ports:
                reasons.append(f"Port {port} not in allowed list")
                risk_score += 30
            
            if port in self.SENSITIVE_PORTS:
                reasons.append(f"Port {port} is sensitive")
                risk_score += 25
        
        # Check data size
        if data_size and self.policy.max_request_size:
            if data_size > self.policy.max_request_size:
                reasons.append(f"Data size {data_size} exceeds limit {self.policy.max_request_size}")
                risk_score += 20
        
        # Determine risk level
        if risk_score >= 100:
            level = RiskLevel.CRITICAL
            approved = False
        elif risk_score >= 50:
            level = RiskLevel.HIGH
            approved = False
        elif risk_score >= 25:
            level = RiskLevel.MEDIUM
            approved = True
        else:
            level = RiskLevel.LOW
            approved = True
        
        # Check if confirmation is required
        requires_confirmation = (
            operation in self.policy.require_confirmation or
            level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        assessment = RiskAssessment(
            level=level,
            approved=approved and risk_score < 100,
            reasons=reasons if reasons else ["No security concerns detected"],
            requires_confirmation=requires_confirmation,
            metadata={
                "operation": operation.value,
                "host": host,
                "port": port,
                "risk_score": risk_score,
                **kwargs
            }
        )
        
        logger.info(
            f"Risk assessment: {operation.value} to {host}:{port or 'N/A'} "
            f"- Level: {level.value}, Approved: {approved}"
        )
        
        return assessment
    
    def _is_host_blocked(self, host: str) -> bool:
        """Check if host is in blocklist."""
        for pattern in self.policy.blocked_hosts:
            if re.match(pattern, host, re.IGNORECASE):
                return True
        return False
    
    def _is_host_allowed(self, host: str) -> bool:
        """Check if host is in allowlist."""
        if not self.policy.allowed_hosts:
            return True
        for pattern in self.policy.allowed_hosts:
            if re.match(pattern, host, re.IGNORECASE):
                return True
        return False
    
    def approve_operation(
        self,
        operation: OperationType,
        host: str,
        port: Optional[int] = None
    ) -> bool:
        """
        Manually approve a network operation.
        
        Args:
            operation: Type of operation
            host: Target host
            port: Target port
            
        Returns:
            True if approved
        """
        key = f"{operation.value}:{host}:{port or 0}"
        self._approval_cache[key] = True
        logger.info(f"Operation approved: {key}")
        return True
    
    def is_approved(
        self,
        operation: OperationType,
        host: str,
        port: Optional[int] = None
    ) -> bool:
        """
        Check if an operation was manually approved.
        
        Args:
            operation: Type of operation
            host: Target host
            port: Target port
            
        Returns:
            True if previously approved
        """
        key = f"{operation.value}:{host}:{port or 0}"
        return self._approval_cache.get(key, False)
    
    def clear_approvals(self):
        """Clear all cached approvals."""
        self._approval_cache.clear()
        logger.info("Cleared all approval cache")
    
    def update_policy(self, policy: NetworkPolicy):
        """
        Update the active network policy.
        
        Args:
            policy: New policy configuration
        """
        self.policy = policy
        self.clear_approvals()
        logger.info(f"Policy updated to: {policy.name}")


# Global Guardian instance
_guardian_instance: Optional[Guardian] = None


def get_guardian(policy: Optional[NetworkPolicy] = None) -> Guardian:
    """
    Get or create the global Guardian instance.
    
    Args:
        policy: Optional policy to use for initialization
        
    Returns:
        Guardian instance
    """
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = Guardian(policy)
    return _guardian_instance


def set_guardian_policy(policy: NetworkPolicy):
    """
    Set the policy for the global Guardian instance.
    
    Args:
        policy: New network policy
    """
    guardian = get_guardian()
    guardian.update_policy(policy)
