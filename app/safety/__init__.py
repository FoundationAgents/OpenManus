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
]
