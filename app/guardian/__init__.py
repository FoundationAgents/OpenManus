"""
Unified Guardian Security System

This module provides consolidated security and policy enforcement across:
- Network operations
- Storage operations
- Sandbox execution
- Security monitoring

The unified interface allows consistent Guardian access regardless of domain.

Core Components:
    - GuardianService: Central security monitoring service
    - UnifiedGuardian: Domain-agnostic unified interface
    - ThreatDetector: Threat detection and analysis
    - SecurityRules: Security policy definitions
"""

# Central service implementations
from .guardian_service import GuardianService
from .threat_detector import ThreatDetector
from .security_rules import SecurityRules

# Unified interface
from .unified import (
    UnifiedGuardian,
    UnifiedGuardianDecision,
    GuardianDomain,
    UnifiedRiskLevel,
    get_unified_guardian,
)

__all__ = [
    # Service implementations
    "GuardianService",
    "ThreatDetector",
    "SecurityRules",
    # Unified interface
    "UnifiedGuardian",
    "UnifiedGuardianDecision",
    "GuardianDomain",
    "UnifiedRiskLevel",
    "get_unified_guardian",
]
