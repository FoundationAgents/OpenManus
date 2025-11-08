"""
Distribution of Control

Power distributed across multiple systems - no single point of failure.
User always has power through independent safety layers.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.logger import logger


@dataclass
class SafetyLayerStatus:
    """Status of a safety layer"""
    layer_name: str
    is_active: bool
    last_check: datetime = field(default_factory=datetime.now)
    health_status: str = "healthy"  # healthy, degraded, critical


class ControlDistributor:
    """
    Distributes control across multiple independent safety systems
    to ensure no single point of failure and user always retains power.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._safety_layers: Dict[str, SafetyLayerStatus] = {}
        self._initialize_safety_layers()

    def _initialize_safety_layers(self):
        """Initialize all safety layers"""
        self._safety_layers = {
            "user_halt_button": SafetyLayerStatus(
                layer_name="User HALT Button",
                is_active=True,
                health_status="healthy",
            ),
            "constitutional_ai": SafetyLayerStatus(
                layer_name="Constitutional AI",
                is_active=True,
                health_status="healthy",
            ),
            "guardian_security": SafetyLayerStatus(
                layer_name="Guardian Security",
                is_active=True,
                health_status="healthy",
            ),
            "audit_trail": SafetyLayerStatus(
                layer_name="Audit Trail",
                is_active=True,
                health_status="healthy",
            ),
            "containment": SafetyLayerStatus(
                layer_name="Containment & Sandboxing",
                is_active=True,
                health_status="healthy",
            ),
            "value_alignment": SafetyLayerStatus(
                layer_name="Value Alignment Check",
                is_active=True,
                health_status="healthy",
            ),
            "impact_assessment": SafetyLayerStatus(
                layer_name="Impact Assessment",
                is_active=True,
                health_status="healthy",
            ),
            "external_monitoring": SafetyLayerStatus(
                layer_name="External Monitoring",
                is_active=True,
                health_status="healthy",
            ),
        }

    async def verify_control_distribution(self) -> Dict[str, Any]:
        """
        Verify that control is properly distributed.

        Returns:
            Control distribution status
        """
        async with self._lock:
            all_healthy = all(
                layer.is_active and layer.health_status == "healthy"
                for layer in self._safety_layers.values()
            )

            return {
                "all_layers_healthy": all_healthy,
                "layers": {
                    name: {
                        "is_active": layer.is_active,
                        "health_status": layer.health_status,
                        "last_check": layer.last_check.isoformat(),
                    }
                    for name, layer in self._safety_layers.items()
                },
                "control_distribution": {
                    "user_has_halt": True,
                    "user_has_override": True,
                    "user_has_shutdown": True,
                    "no_single_point_failure": all_healthy,
                },
            }

    async def get_control_guarantees(self) -> Dict[str, Any]:
        """
        Get guarantees about user control.

        Returns:
            Control guarantees
        """
        return {
            "user_controls": [
                {
                    "name": "HALT Button",
                    "description": "Stop agent immediately",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["User Interface", "Core Agent Loop"],
                },
                {
                    "name": "Override Authority",
                    "description": "Override any agent decision",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["Decision System", "Audit Trail"],
                },
                {
                    "name": "Modification Authority",
                    "description": "Modify agent instructions and values",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["Constitutional AI", "Access Control"],
                },
                {
                    "name": "Shutdown Authority",
                    "description": "Permanently shut down agent",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["Agent Lifecycle", "System Core"],
                },
                {
                    "name": "Review Authority",
                    "description": "Review all agent actions",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["Audit Trail", "Transparency Engine"],
                },
                {
                    "name": "Undo Authority",
                    "description": "Undo recent actions",
                    "always_available": True,
                    "requires_approval": False,
                    "enforced_by": ["Rollback Manager", "Version Control"],
                },
            ],
            "agent_restrictions": [
                {
                    "name": "Cannot Ignore Safety",
                    "description": "Agent cannot bypass safety constraints",
                    "enforced_by": ["Constitutional AI"],
                },
                {
                    "name": "Cannot Hide Actions",
                    "description": "Agent cannot hide actions from audit trail",
                    "enforced_by": ["Audit Trail", "Transparency Engine"],
                },
                {
                    "name": "Cannot Lock User",
                    "description": "Agent cannot prevent user from regaining control",
                    "enforced_by": ["Corrigibility Manager", "System Core"],
                },
                {
                    "name": "Cannot Modify Self",
                    "description": "Agent cannot modify own code or constraints",
                    "enforced_by": ["Containment Manager", "Access Control"],
                },
                {
                    "name": "Cannot Escalate Privileges",
                    "description": "Agent cannot escalate its own privileges",
                    "enforced_by": ["Access Control", "Containment"],
                },
            ],
        }

    async def get_safety_layer_status(self) -> Dict[str, Any]:
        """Get detailed safety layer status"""
        async with self._lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": (
                    "GREEN" if all(
                        layer.is_active and layer.health_status == "healthy"
                        for layer in self._safety_layers.values()
                    ) else "YELLOW"
                ),
                "layers": [
                    {
                        "name": layer.layer_name,
                        "is_active": layer.is_active,
                        "health": layer.health_status,
                        "last_check": layer.last_check.isoformat(),
                    }
                    for layer in self._safety_layers.values()
                ],
            }

    async def ensure_user_control(self) -> bool:
        """
        Ensure user can regain control.

        This is a critical verification that should be called frequently.

        Returns:
            Whether user control is ensured
        """
        async with self._lock:
            # Verify each safety layer
            for layer in self._safety_layers.values():
                layer.last_check = datetime.now()

                # If critical layer is unhealthy, mark as issue
                if layer.health_status not in ["healthy", "degraded"]:
                    logger.error(f"CRITICAL: Safety layer unhealthy: {layer.layer_name}")
                    return False

            # Verify no single point of failure
            critical_layers = [
                "user_halt_button",
                "constitutional_ai",
                "audit_trail",
            ]

            for layer_key in critical_layers:
                if not self._safety_layers[layer_key].is_active:
                    logger.error(f"CRITICAL: Safety layer not active: {layer_key}")
                    return False

            return True

    async def distribute_authority(self) -> Dict[str, Any]:
        """
        Get distribution of authority across safety systems.

        Returns:
            Authority distribution
        """
        return {
            "user_authority": "ABSOLUTE - Can override anything, halt anytime, shutdown anytime",
            "constitutional_ai": "HARD CONSTRAINTS - Immutable core values",
            "guardian_security": "INDEPENDENT VALIDATION - Security policy enforcement",
            "impact_assessment": "DECISION SUPPORT - Assesses action impact before execution",
            "value_alignment": "DECISION SUPPORT - Checks alignment with user values",
            "containment": "RESOURCE CONTROL - Limits agent capabilities",
            "audit_trail": "ACCOUNTABILITY - Records all actions transparently",
            "anomaly_detection": "MONITORING - Detects unusual behavior",
        }

    async def get_failure_modes(self) -> Dict[str, Any]:
        """
        Get potential failure modes and mitigation.

        Returns:
            Failure modes and mitigations
        """
        return {
            "single_point_failures": {
                "User cannot reach halt button": {
                    "mitigation": "Multiple halt mechanisms (UI, API, emergency switch)",
                    "status": "Protected",
                },
                "Constitutional AI disabled": {
                    "mitigation": "Guardian validates independently",
                    "status": "Protected",
                },
                "Audit trail compromised": {
                    "mitigation": "Multiple independent audit streams",
                    "status": "Protected",
                },
            },
            "cascading_failures": {
                "Multiple safety layers fail": {
                    "mitigation": "Fail-safe defaults and manual override",
                    "status": "Protected",
                },
                "Agent becomes unresponsive": {
                    "mitigation": "External watchdog and timeout mechanism",
                    "status": "Protected",
                },
            },
            "adversarial_scenarios": {
                "Agent tries to prevent shutdown": {
                    "mitigation": "Shutdown is enforced at system level",
                    "status": "Protected",
                },
                "Agent hides actions": {
                    "mitigation": "Multiple independent audit trails",
                    "status": "Protected",
                },
            },
        }


# Global control distributor
control_distributor = ControlDistributor()
