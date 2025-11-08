"""Security package providing ACL management
"""
Security Module - Dynamic Permissions & Capabilities System

Provides intelligent, risk-based capability granting for agents with
support for TTL caching, revocation, audit trails, and user confirmation.
"""

from app.security.permissions import (
    CapabilityRequest,
    CapabilityGrant,
    CapabilityDeny,
    CapabilityDecision,
    DecisionType,
    DynamicPermissionManager,
    ResourceLimits,
    get_permission_manager,
)

__all__ = [
    "CapabilityRequest",
    "CapabilityGrant",
    "CapabilityDeny",
    "CapabilityDecision",
    "DecisionType",
    "DynamicPermissionManager",
    "ResourceLimits",
    "get_permission_manager",
    "ACLManager", 
    "acl_manager"
]
