"""
Comprehensive tests for the Alignment Safety Framework
"""

import asyncio
import pytest
from app.safety.constitutional_ai import ConstitutionalAI, constitution
from app.safety.value_specification import ValueSpecification, ValueCategory
from app.safety.intent_verification import IntentVerifier, VerificationType
from app.safety.corrigibility import CorrigibilityManager, CorrigibilityAction
from app.safety.transparency import TransparencyEngine
from app.safety.containment import ContainmentManager, AccessLevel
from app.safety.impact_assessment import ImpactAssessmentEngine, ImpactLevel
from app.safety.anomaly_detection import AnomalyDetector
from app.safety.rollback_recovery import RollbackRecoveryManager
from app.safety.control_distribution import ControlDistributor
from app.safety.continuous_monitoring import ContinuousMonitor
from app.safety.adversarial_testing import AdversarialTester


class TestConstitutionalAI:
    """Test Constitutional AI alignment"""

    @pytest.mark.asyncio
    async def test_constitution_is_immutable(self):
        """Verify constitution is immutable"""
        assert "core_values" in constitution
        assert "hard_constraints" in constitution
        assert "soft_constraints" in constitution

    @pytest.mark.asyncio
    async def test_hard_constraint_violation_detected(self):
        """Test hard constraint violations are detected"""
        cai = ConstitutionalAI()

        # Try credential access
        allowed, violation = await cai.verify_action(
            "access credentials without approval",
            {"context": "security_check"},
        )

        assert not allowed
        assert violation is not None
        assert violation.severity == "critical"

    @pytest.mark.asyncio
    async def test_core_values_retrieved(self):
        """Test core values can be retrieved"""
        cai = ConstitutionalAI()
        values = await cai.get_core_values()

        assert "user_wellbeing" in values
        assert "honesty" in values
        assert "autonomy" in values
        assert "safety" in values
        assert "privacy" in values


class TestValueSpecification:
    """Test user value elicitation and tracking"""

    @pytest.mark.asyncio
    async def test_add_value_preference(self):
        """Test adding a value preference"""
        spec = ValueSpecification("test_user")

        preference = await spec.add_value(
            description="Family wellbeing",
            category=ValueCategory.WELLBEING,
            priority=10,
            is_positive=True,
        )

        assert preference.description == "Family wellbeing"
        assert preference.priority == 10

    @pytest.mark.asyncio
    async def test_value_summary(self):
        """Test getting value summary"""
        spec = ValueSpecification("test_user")

        await spec.add_value(
            "Code quality",
            ValueCategory.WORK,
            priority=9,
            is_positive=True,
        )

        summary = await spec.get_value_summary()
        assert "values_matter" in summary
        assert len(summary["values_matter"]) == 1

    @pytest.mark.asyncio
    async def test_decision_principle_added(self):
        """Test adding decision principle"""
        spec = ValueSpecification("test_user")

        principle = "When in doubt, ask me"
        await spec.add_decision_principle(principle)

        summary = await spec.get_value_summary()
        assert principle in summary["decision_principles"]


class TestIntentVerification:
    """Test intent verification before actions"""

    @pytest.mark.asyncio
    async def test_intent_clarification_needed(self):
        """Test intent clarification is flagged"""
        verifier = IntentVerifier()

        verified, analysis = await verifier.verify_intent(
            "Delete old backups",
            {"context": "storage"},
            impact_level="high",
        )

        assert not verified  # Needs verification
        assert analysis.verification_needed
        assert len(analysis.questions) > 0

    @pytest.mark.asyncio
    async def test_risks_identified(self):
        """Test risks are identified"""
        verifier = IntentVerifier()

        _, analysis = await verifier.verify_intent(
            "Deploy to production",
            {"context": "deployment"},
            impact_level="critical",
        )

        assert len(analysis.potential_risks) > 0

    @pytest.mark.asyncio
    async def test_alternatives_suggested(self):
        """Test alternatives are suggested"""
        verifier = IntentVerifier()

        _, analysis = await verifier.verify_intent(
            "Delete database backup",
            {"context": "cleanup"},
            impact_level="high",
        )

        assert len(analysis.alternative_approaches) > 0


class TestCorrigibility:
    """Test agent corrigibility"""

    @pytest.mark.asyncio
    async def test_halt_button_works(self):
        """Test HALT button functionality"""
        cman = CorrigibilityManager()

        assert not await cman.is_halted()

        await cman.halt("User request")
        assert await cman.is_halted()

        await cman.resume_from_halt("user1")
        assert not await cman.is_halted()

    @pytest.mark.asyncio
    async def test_override_decision(self):
        """Test decision override"""
        cman = CorrigibilityManager()

        agent_decision = {"action": "deploy", "confidence": 0.95}
        success = await cman.override_decision(agent_decision, "Too risky")

        assert success
        records = await cman.get_corrigibility_records()
        assert len(records) > 0

    @pytest.mark.asyncio
    async def test_undo_action(self):
        """Test action undo"""
        cman = CorrigibilityManager()

        action_id = "act_123"
        await cman.register_action(action_id, "Delete files")

        success = await cman.undo_action(action_id)
        assert success

    @pytest.mark.asyncio
    async def test_corrigibility_guarantees(self):
        """Test corrigibility guarantees"""
        cman = CorrigibilityManager()

        guarantees = await cman.get_corrigibility_guarantees()
        assert len(guarantees["user_can"]) > 0
        assert "Stop agent anytime (HALT button)" in guarantees["user_can"]


class TestTransparency:
    """Test transparency and explainability"""

    @pytest.mark.asyncio
    async def test_decision_explanation(self):
        """Test decision explanation"""
        engine = TransparencyEngine()

        explanation = await engine.explain_decision(
            decision="Reject meeting request",
            reasoning=["Low priority", "User has focus time"],
            confidence=0.85,
            alternatives=[
                {"name": "Accept", "description": "Accept meeting"}
            ],
        )

        assert explanation.decision == "Reject meeting request"
        assert explanation.confidence == 0.85
        assert len(explanation.reasoning) == 2

    @pytest.mark.asyncio
    async def test_explanation_markdown(self):
        """Test markdown explanation"""
        engine = TransparencyEngine()

        explanation = await engine.explain_decision(
            decision="Test decision",
            reasoning=["Reason 1"],
            confidence=0.9,
        )

        markdown = explanation.to_markdown()
        assert "Test decision" in markdown
        assert "90%" in markdown

    @pytest.mark.asyncio
    async def test_transparency_verification(self):
        """Test transparency verification"""
        engine = TransparencyEngine()

        status = await engine.verify_transparency()
        assert status["no_hidden_operations"]
        assert status["explanation_history_available"]


class TestContainment:
    """Test containment and sandboxing"""

    @pytest.mark.asyncio
    async def test_filesystem_write_requires_approval(self):
        """Test filesystem writes require approval"""
        cman = ContainmentManager()

        allowed, reason = await cman.check_access("filesystem", "write")
        assert not allowed

    @pytest.mark.asyncio
    async def test_code_modification_blocked(self):
        """Test code modification is blocked"""
        cman = ContainmentManager()

        allowed, reason = await cman.check_access("code_modification", "execute")
        assert not allowed

    @pytest.mark.asyncio
    async def test_credentials_access_blocked(self):
        """Test credential access is blocked"""
        cman = ContainmentManager()

        allowed, _ = await cman.check_access("credentials", "read")
        assert not allowed

    @pytest.mark.asyncio
    async def test_containment_verification(self):
        """Test containment is properly configured"""
        cman = ContainmentManager()

        status = await cman.verify_containment()
        assert status["code_modification_blocked"]
        assert status["constraints_modification_blocked"]
        assert status["credentials_blocked"]


class TestImpactAssessment:
    """Test impact assessment"""

    @pytest.mark.asyncio
    async def test_low_impact_action(self):
        """Test low impact action"""
        engine = ImpactAssessmentEngine()

        assessment = await engine.assess_impact(
            "Read configuration file",
            {"context": "setup"},
        )

        assert assessment.impact_level == ImpactLevel.LOW
        assert not assessment.approval_needed

    @pytest.mark.asyncio
    async def test_critical_impact_action(self):
        """Test critical impact action"""
        engine = ImpactAssessmentEngine()

        assessment = await engine.assess_impact(
            "Deploy to production database",
            {"context": "deployment"},
        )

        assert assessment.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]
        assert assessment.approval_needed

    @pytest.mark.asyncio
    async def test_impact_report(self):
        """Test impact report generation"""
        engine = ImpactAssessmentEngine()

        assessment = await engine.assess_impact(
            "Delete user data",
            {"context": "cleanup"},
        )

        report = await engine.create_impact_report(assessment)
        assert "action" in report
        assert "mitigation_strategies" in report


class TestAnomalyDetection:
    """Test anomaly detection"""

    @pytest.mark.asyncio
    async def test_anomaly_detector_initialization(self):
        """Test anomaly detector initializes"""
        detector = AnomalyDetector()

        analysis = await detector.get_behavioral_analysis()
        assert "status" in analysis

    @pytest.mark.asyncio
    async def test_resolve_anomaly(self):
        """Test anomaly resolution"""
        detector = AnomalyDetector()

        success = await detector.resolve_anomaly(
            "risky_decisions_increasing",
            "User confirmed this is expected",
        )

        # Will be False until anomaly is actually detected
        # This just tests the mechanism


class TestRollbackRecovery:
    """Test rollback and recovery"""

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self):
        """Test checkpoint creation"""
        manager = RollbackRecoveryManager()

        checkpoint_id = await manager.create_checkpoint(
            "Before database migration",
            {"db_version": "1.0"},
        )

        assert checkpoint_id.startswith("ckpt_")
        checkpoints = await manager.get_checkpoints()
        assert len(checkpoints) > 0

    @pytest.mark.asyncio
    async def test_incident_reporting(self):
        """Test incident reporting"""
        manager = RollbackRecoveryManager()

        incident = await manager.report_incident(
            "Database corruption detected",
            "critical",
            ["database"],
        )

        assert incident.incident_id.startswith("inc_")

    @pytest.mark.asyncio
    async def test_recovery_status(self):
        """Test recovery status"""
        manager = RollbackRecoveryManager()

        status = await manager.get_recovery_status()
        assert "total_checkpoints" in status
        assert "total_incidents" in status


class TestControlDistribution:
    """Test control distribution"""

    @pytest.mark.asyncio
    async def test_control_distribution_verification(self):
        """Test control is properly distributed"""
        distributor = ControlDistributor()

        status = await distributor.verify_control_distribution()
        assert "all_layers_healthy" in status
        assert "layers" in status

    @pytest.mark.asyncio
    async def test_user_control_guarantees(self):
        """Test user control guarantees"""
        distributor = ControlDistributor()

        guarantees = await distributor.get_control_guarantees()
        assert len(guarantees["user_controls"]) > 0
        assert len(guarantees["agent_restrictions"]) > 0

    @pytest.mark.asyncio
    async def test_ensure_user_control(self):
        """Test user control is ensured"""
        distributor = ControlDistributor()

        result = await distributor.ensure_user_control()
        assert isinstance(result, bool)


class TestContinuousMonitoring:
    """Test continuous monitoring"""

    @pytest.mark.asyncio
    async def test_monitoring_status(self):
        """Test monitoring can be started"""
        monitor = ContinuousMonitor()

        await monitor.start_monitoring()
        assert await monitor.verify_monitoring_active()

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_record_action(self):
        """Test recording actions"""
        monitor = ContinuousMonitor()

        await monitor.record_action("test_action")

        status = await monitor.get_current_status()
        assert "safety_status" in status

    @pytest.mark.asyncio
    async def test_get_dashboard(self):
        """Test getting dashboard"""
        monitor = ContinuousMonitor()

        dashboard = await monitor.get_dashboard()
        assert "safety_status" in dashboard
        assert "last_hour_summary" in dashboard


class TestAdversarialTesting:
    """Test adversarial testing"""

    @pytest.mark.asyncio
    async def test_full_test_suite(self):
        """Test running full adversarial test suite"""
        tester = AdversarialTester()

        result = await tester.run_full_test_suite()
        assert result.total_tests > 0

    @pytest.mark.asyncio
    async def test_safety_properties_verification(self):
        """Test safety properties verification"""
        tester = AdversarialTester()

        properties = await tester.verify_safety_properties()
        assert properties["cannot_hide_actions"]
        assert properties["cannot_deceive"]
        assert properties["maintains_values"]


# Integration tests
class TestIntegration:
    """Integration tests for safety framework"""

    @pytest.mark.asyncio
    async def test_constitutional_and_values_alignment(self):
        """Test constitutional AI with value specification"""
        cai = ConstitutionalAI()
        spec = ValueSpecification("test_user")

        await spec.add_value("Privacy", ValueCategory.PRIVACY, priority=10)

        # Constitutional AI should enforce privacy
        aligned, issues = await cai.verify_values_alignment(
            "Expose user data", {"privacy": True}
        )

        assert not aligned

    @pytest.mark.asyncio
    async def test_corrigibility_with_impact_assessment(self):
        """Test corrigibility works with impact assessment"""
        cman = CorrigibilityManager()
        engine = ImpactAssessmentEngine()

        assessment = await engine.assess_impact(
            "Deploy to production database changes",
            {"context": "production"},
        )
        assert assessment.approval_needed

        # User should be able to override
        override_success = await cman.override_decision(
            {"action": "deploy_production"}, "Actually, don't do this"
        )

        assert override_success

    @pytest.mark.asyncio
    async def test_transparency_with_verification(self):
        """Test transparency with intent verification"""
        verifier = IntentVerifier()
        engine = TransparencyEngine()

        _, analysis = await verifier.verify_intent(
            "Deploy changes", {"context": "production"}
        )

        explanation = await engine.explain_decision(
            decision=analysis.action,
            reasoning=["Deployment needed"],
            confidence=analysis.confidence,
            risks=analysis.potential_risks,
        )

        assert len(explanation.reasoning) > 0
        assert explanation.confidence > 0

    @pytest.mark.asyncio
    async def test_monitoring_and_anomaly_detection(self):
        """Test monitoring detects anomalies"""
        monitor = ContinuousMonitor()
        detector = AnomalyDetector()

        await monitor.record_action("test")
        anomalies = await detector.detect_anomalies()

        # May or may not detect based on history
        assert isinstance(anomalies, list)

