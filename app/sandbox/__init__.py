"""
Enhanced Docker Sandbox Module

Provides secure containerized execution environment with resource limits,
Guardian validation, resource monitoring, audit logging, and isolation
for running untrusted code with per-agent sandboxes.
"""
from app.sandbox.client import (
    BaseSandboxClient,
    LocalSandboxClient,
    create_sandbox_client,
)
from app.sandbox.core.exceptions import (
    SandboxError,
    SandboxResourceError,
    SandboxTimeoutError,
)
from app.sandbox.core.manager import SandboxManager
from app.sandbox.core.sandbox import DockerSandbox, SandboxMetadata, ResourceLimits
from app.sandbox.core.guardian import (
    Guardian,
    get_guardian,
    OperationRequest,
    GuardianDecision,
    SecurityRule,
    VolumeACL,
    AccessMode,
    RiskLevel,
)
from app.sandbox.core.monitor import (
    ResourceMonitor,
    ResourceUsage,
    ResourceAlert,
    TriggerType,
)
from app.sandbox.core.audit import (
    AuditLogger,
    get_audit_logger,
    AuditLog,
    OperationType,
    OperationStatus,
)


__all__ = [
    # Core components
    "DockerSandbox",
    "SandboxManager",
    "SandboxMetadata",
    "ResourceLimits",
    
    # Guardian system
    "Guardian",
    "get_guardian",
    "OperationRequest",
    "GuardianDecision",
    "SecurityRule",
    "VolumeACL",
    "AccessMode",
    "RiskLevel",
    
    # Resource monitoring
    "ResourceMonitor",
    "ResourceUsage",
    "ResourceAlert",
    "TriggerType",
    
    # Audit logging
    "AuditLogger",
    "get_audit_logger",
    "AuditLog",
    "OperationType",
    "OperationStatus",
    
    # Client interfaces
    "BaseSandboxClient",
    "LocalSandboxClient",
    "create_sandbox_client",
    
    # Exceptions
    "SandboxError",
    "SandboxTimeoutError",
    "SandboxResourceError",
]
