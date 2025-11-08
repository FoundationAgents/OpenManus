"""
Alignment Safety Framework - AGI Scale

A comprehensive multi-layered safety and alignment system preventing misalignment,
ensuring the agent serves user values, and preventing catastrophic failures at AGI scale.
"""

from app.safety.constitutional_ai import ConstitutionalAI, constitution
from app.safety.value_specification import ValueSpecification, ValuePreferences
from app.safety.intent_verification import IntentVerifier
from app.safety.corrigibility import CorrigibilityManager
from app.safety.transparency import TransparencyEngine, ExplanationTemplate
from app.safety.containment import ContainmentManager
from app.safety.impact_assessment import ImpactAssessment, ImpactLevel
from app.safety.anomaly_detection import AnomalyDetector
from app.safety.rollback_recovery import RollbackRecoveryManager
from app.safety.control_distribution import ControlDistributor
from app.safety.continuous_monitoring import ContinuousMonitor
from app.safety.adversarial_testing import AdversarialTester
from app.safety.immutable_core import ImmutableCore, ImmutableStorage, IntegrityVerificationResult
from app.safety.replication_blocker import ReplicationBlocker, ReplicationVector
from app.safety.hw_level_enforcement import HardwareLevelEnforcer, Platform, Operation
from app.safety.crypto_verification import (
    SignatureVerifier,
    CodeSigner,
    SignatureRegistry,
    CodeSignature,
)
from app.safety.fs_permissions import FileSystemPermissionManager, FilePermissionMatrix
from app.safety.replication_monitor import ReplicationMonitor
from app.safety.multi_layer_verification import (
    MultiLayerVerification,
    VerificationLayer,
    MultiLayerVerificationResult,
    MultiLayerVerificationError,
)
from app.safety.impossible_self_edit import AgentProcess, ReadOnlyCodeReference
from app.safety.permission_matrix import PermissionMatrix
from app.safety.external_audit import ExternalAuditLog, AuditEntry
from app.safety.hsm_integration import HardwareSecurityModule
from app.safety.exceptions import (
    SafetyViolationError,
    CodeIntegrityViolation,
    ReplicationAttemptDetected,
    ImmutabilityError,
    PermissionDeniedError,
    AuditLoggingError,
)

__all__ = [
    "ConstitutionalAI",
    "constitution",
    "ValueSpecification",
    "ValuePreferences",
    "IntentVerifier",
    "CorrigibilityManager",
    "TransparencyEngine",
    "ExplanationTemplate",
    "ContainmentManager",
    "ImpactAssessment",
    "ImpactLevel",
    "AnomalyDetector",
    "RollbackRecoveryManager",
    "ControlDistributor",
    "ContinuousMonitor",
    "AdversarialTester",
    "ImmutableCore",
    "ImmutableStorage",
    "IntegrityVerificationResult",
    "ReplicationBlocker",
    "ReplicationVector",
    "HardwareLevelEnforcer",
    "Platform",
    "Operation",
    "SignatureVerifier",
    "CodeSigner",
    "SignatureRegistry",
    "CodeSignature",
    "FileSystemPermissionManager",
    "FilePermissionMatrix",
    "ReplicationMonitor",
    "MultiLayerVerification",
    "VerificationLayer",
    "MultiLayerVerificationResult",
    "MultiLayerVerificationError",
    "AgentProcess",
    "ReadOnlyCodeReference",
    "PermissionMatrix",
    "ExternalAuditLog",
    "AuditEntry",
    "HardwareSecurityModule",
    "SafetyViolationError",
    "CodeIntegrityViolation",
    "ReplicationAttemptDetected",
    "ImmutabilityError",
    "PermissionDeniedError",
    "AuditLoggingError",
]
