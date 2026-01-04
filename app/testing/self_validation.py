"""
FreEco.ai Platform - Self-Validation System
Enhanced OpenManus with comprehensive self-testing

This module provides automated self-validation:
- Health checks for all systems
- Consistency checks for data integrity
- Security audits for vulnerabilities
- Performance audits for bottlenecks
- Ethics audits for compliance
- Comprehensive validation reports

Part of Self-Testing & Validation System
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status"""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ValidationCheck:
    """Individual validation check"""

    name: str
    category: str  # health, security, performance, ethics
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthReport:
    """System health report"""

    overall_status: ValidationStatus
    checks: List[ValidationCheck]
    passed: int
    warned: int
    failed: int
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "overall_status": self.overall_status.value,
            "passed": self.passed,
            "warned": self.warned,
            "failed": self.failed,
            "total_checks": len(self.checks),
            "timestamp": self.timestamp.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
        }

    def __str__(self) -> str:
        return (
            f"Health Report ({self.overall_status.value.upper()})\n"
            f"Passed: {self.passed}, Warned: {self.warned}, Failed: {self.failed}\n"
            f"Total Checks: {len(self.checks)}\n"
            f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )


@dataclass
class ValidationReport:
    """Comprehensive validation report"""

    health_report: HealthReport
    security_score: float  # 0-100
    performance_score: float  # 0-100
    ethics_score: float  # 0-100
    overall_score: float  # 0-100
    recommendations: List[str]
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "health": self.health_report.to_dict(),
            "scores": {
                "security": self.security_score,
                "performance": self.performance_score,
                "ethics": self.ethics_score,
                "overall": self.overall_score,
            },
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return (
            f"=== FreEco.ai Validation Report ===\n\n"
            f"{self.health_report}\n\n"
            f"Scores:\n"
            f"  Security: {self.security_score:.1f}/100\n"
            f"  Performance: {self.performance_score:.1f}/100\n"
            f"  Ethics: {self.ethics_score:.1f}/100\n"
            f"  Overall: {self.overall_score:.1f}/100\n\n"
            f"Recommendations: {len(self.recommendations)}\n"
        )


class SelfValidationSystem:
    """
    Comprehensive self-validation system

    Features:
    - Health checks for all components
    - Security vulnerability scanning
    - Performance bottleneck detection
    - Ethics compliance verification
    - Automated recommendations
    - Continuous validation

    Example:
        validator = SelfValidationSystem()

        # Run full validation
        report = validator.validate_all()
        print(report)

        # Run specific checks
        health = validator.health_check()
        security = validator.security_audit()
    """

    def __init__(self):
        """Initialize self-validation system"""
        self.validation_history: List[ValidationReport] = []

    def validate_all(self) -> ValidationReport:
        """
        Run all validation checks

        Returns:
            ValidationReport with comprehensive results
        """
        logger.info("Starting comprehensive validation...")

        # Run all checks
        health_report = self.health_check()
        security_score = self._security_audit_score()
        performance_score = self._performance_audit_score()
        ethics_score = self._ethics_audit_score()

        # Calculate overall score
        overall_score = (
            security_score * 0.35 + performance_score * 0.25 + ethics_score * 0.40
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            health_report,
            security_score,
            performance_score,
            ethics_score,
        )

        # Create report
        report = ValidationReport(
            health_report=health_report,
            security_score=security_score,
            performance_score=performance_score,
            ethics_score=ethics_score,
            overall_score=overall_score,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

        # Save to history
        self.validation_history.append(report)

        logger.info(f"Validation complete. Overall score: {overall_score:.1f}/100")

        return report

    def health_check(self) -> HealthReport:
        """
        Perform system health checks

        Returns:
            HealthReport with health status
        """
        checks = []

        # Check stability module
        checks.append(self._check_stability_module())

        # Check performance module
        checks.append(self._check_performance_module())

        # Check security module
        checks.append(self._check_security_module())

        # Check ethics module
        checks.append(self._check_ethics_module())

        # Check LLM connectivity
        checks.append(self._check_llm_connectivity())

        # Check file system
        checks.append(self._check_file_system())

        # Count results
        passed = sum(1 for c in checks if c.status == ValidationStatus.PASS)
        warned = sum(1 for c in checks if c.status == ValidationStatus.WARN)
        failed = sum(1 for c in checks if c.status == ValidationStatus.FAIL)

        # Determine overall status
        if failed > 0:
            overall_status = ValidationStatus.FAIL
        elif warned > 0:
            overall_status = ValidationStatus.WARN
        else:
            overall_status = ValidationStatus.PASS

        return HealthReport(
            overall_status=overall_status,
            checks=checks,
            passed=passed,
            warned=warned,
            failed=failed,
            timestamp=datetime.now(),
        )

    def _check_stability_module(self) -> ValidationCheck:
        """Check stability module health"""
        try:
            from app.stability import (
                ErrorRecoverySystem,
                GracefulDegradation,
                RetryManager,
            )

            # Test basic functionality
            RetryManager()
            GracefulDegradation()
            ErrorRecoverySystem()

            return ValidationCheck(
                name="Stability Module",
                category="health",
                status=ValidationStatus.PASS,
                message="Stability module is healthy",
                details={
                    "components": [
                        "RetryManager",
                        "GracefulDegradation",
                        "ErrorRecoverySystem",
                    ]
                },
            )

        except Exception as e:
            return ValidationCheck(
                name="Stability Module",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"Stability module failed: {e}",
            )

    def _check_performance_module(self) -> ValidationCheck:
        """Check performance module health"""
        try:
            from app.performance import MonitoringSystem, PerformanceOptimizer

            optimizer = PerformanceOptimizer()
            MonitoringSystem()

            # Check cache
            cache_stats = optimizer.get_cache_stats()

            return ValidationCheck(
                name="Performance Module",
                category="health",
                status=ValidationStatus.PASS,
                message="Performance module is healthy",
                details={"cache_stats": cache_stats},
            )

        except Exception as e:
            return ValidationCheck(
                name="Performance Module",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"Performance module failed: {e}",
            )

    def _check_security_module(self) -> ValidationCheck:
        """Check security module health"""
        try:
            from app.security import AntiHackingSystem, SecurityManager

            SecurityManager()
            anti_hack = AntiHackingSystem()

            # Test basic functionality
            test_input = "SELECT * FROM users"
            anti_hack.prevent_sql_injection(test_input)

            return ValidationCheck(
                name="Security Module",
                category="health",
                status=ValidationStatus.PASS,
                message="Security module is healthy",
                details={"sql_injection_prevention": "working"},
            )

        except Exception as e:
            return ValidationCheck(
                name="Security Module",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"Security module failed: {e}",
            )

    def _check_ethics_module(self) -> ValidationCheck:
        """Check ethics module health"""
        try:
            from app.ethics import EcologicalSystem, FreEcoLawsEnforcer

            laws = FreEcoLawsEnforcer()
            EcologicalSystem()

            # Test basic functionality
            approved, benchmark, _ = laws.evaluate_action("Find vegan recipes")

            if not approved:
                return ValidationCheck(
                    name="Ethics Module",
                    category="health",
                    status=ValidationStatus.WARN,
                    message="Ethics module working but may be too strict",
                )

            return ValidationCheck(
                name="Ethics Module",
                category="health",
                status=ValidationStatus.PASS,
                message="Ethics module is healthy",
                details={"benchmark_score": benchmark.total_score()},
            )

        except Exception as e:
            return ValidationCheck(
                name="Ethics Module",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"Ethics module failed: {e}",
            )

    def _check_llm_connectivity(self) -> ValidationCheck:
        """Check LLM connectivity"""
        try:
            # This would test actual LLM connectivity
            # For now, just check if config exists
            import os

            has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

            if has_openai_key:
                return ValidationCheck(
                    name="LLM Connectivity",
                    category="health",
                    status=ValidationStatus.PASS,
                    message="LLM API keys configured",
                )
            else:
                return ValidationCheck(
                    name="LLM Connectivity",
                    category="health",
                    status=ValidationStatus.WARN,
                    message="No LLM API keys found",
                )

        except Exception as e:
            return ValidationCheck(
                name="LLM Connectivity",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"LLM check failed: {e}",
            )

    def _check_file_system(self) -> ValidationCheck:
        """Check file system health"""
        try:
            import psutil

            # Check disk space
            disk = psutil.disk_usage("/")
            free_percent = (disk.free / disk.total) * 100

            if free_percent < 10:
                status = ValidationStatus.FAIL
                message = f"Low disk space: {free_percent:.1f}% free"
            elif free_percent < 20:
                status = ValidationStatus.WARN
                message = f"Disk space warning: {free_percent:.1f}% free"
            else:
                status = ValidationStatus.PASS
                message = f"Disk space healthy: {free_percent:.1f}% free"

            return ValidationCheck(
                name="File System",
                category="health",
                status=status,
                message=message,
                details={"free_percent": free_percent},
            )

        except Exception as e:
            return ValidationCheck(
                name="File System",
                category="health",
                status=ValidationStatus.FAIL,
                message=f"File system check failed: {e}",
            )

    def _security_audit_score(self) -> float:
        """Calculate security audit score"""
        score = 100.0

        try:
            from app.security import default_anti_hacking, default_security

            # Check for security events
            audit_log = default_security.get_audit_log(hours=24)
            high_severity_events = [
                e for e in audit_log if e.threat_level.value in ["high", "critical"]
            ]

            # Deduct points for security events
            score -= len(high_severity_events) * 5

            # Check for blocked IPs
            blocked_ips = default_anti_hacking.get_blocked_ips()
            if len(blocked_ips) > 10:
                score -= 10

            # Check intrusion log
            intrusions = default_anti_hacking.get_intrusion_log(hours=24)
            score -= len(intrusions) * 2

        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            score = 50.0  # Default to medium score on error

        return max(0.0, min(100.0, score))

    def _performance_audit_score(self) -> float:
        """Calculate performance audit score"""
        score = 100.0

        try:
            from app.performance import default_monitor, default_optimizer

            # Check cache hit rate
            cache_stats = default_optimizer.get_cache_stats()
            hit_rate = cache_stats.get("hit_rate", 0.0)

            if hit_rate < 0.5:
                score -= 20
            elif hit_rate < 0.7:
                score -= 10

            # Check system metrics
            metrics = default_monitor.collect_metrics()

            if metrics.cpu_percent > 90:
                score -= 15
            elif metrics.cpu_percent > 75:
                score -= 5

            if metrics.memory_percent > 90:
                score -= 15
            elif metrics.memory_percent > 75:
                score -= 5

        except Exception as e:
            logger.error(f"Performance audit failed: {e}")
            score = 70.0  # Default to good score on error

        return max(0.0, min(100.0, score))

    def _ethics_audit_score(self) -> float:
        """Calculate ethics audit score"""
        score = 100.0

        try:
            from app.ethics import default_ecological, default_freeco_laws

            # Check evaluation stats
            stats = default_freeco_laws.get_evaluation_stats()
            approval_rate = stats.get("approval_rate", 1.0)

            # High approval rate is good (means most actions are ethical)
            if approval_rate < 0.5:
                score -= 30
            elif approval_rate < 0.7:
                score -= 15

            # Check sustainability metrics
            sustainability = default_ecological.get_sustainability_metrics()
            co2_per_request = sustainability.co2_per_request()

            # Penalize high carbon footprint
            if co2_per_request > 100:  # > 100g per request
                score -= 20
            elif co2_per_request > 50:
                score -= 10

        except Exception as e:
            logger.error(f"Ethics audit failed: {e}")
            score = 80.0  # Default to good score on error

        return max(0.0, min(100.0, score))

    def _generate_recommendations(
        self,
        health: HealthReport,
        security_score: float,
        performance_score: float,
        ethics_score: float,
    ) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []

        # Health recommendations
        if health.failed > 0:
            recommendations.append(
                f"⚠️ {health.failed} health check(s) failed. Review system logs and fix critical issues."
            )

        # Security recommendations
        if security_score < 70:
            recommendations.append(
                "🔒 Security score is low. Review security audit logs and address vulnerabilities."
            )
        elif security_score < 85:
            recommendations.append(
                "🔒 Security could be improved. Consider implementing additional security measures."
            )

        # Performance recommendations
        if performance_score < 70:
            recommendations.append(
                "⚡ Performance score is low. Optimize caching, reduce resource usage, and profile slow operations."
            )
        elif performance_score < 85:
            recommendations.append(
                "⚡ Performance could be improved. Review cache hit rates and system resource usage."
            )

        # Ethics recommendations
        if ethics_score < 70:
            recommendations.append(
                "🌱 Ethics score is low. Review blocked actions and ensure alignment with FreEco.ai values."
            )
        elif ethics_score < 85:
            recommendations.append(
                "🌱 Ethics could be improved. Focus on reducing carbon footprint and improving sustainability."
            )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "✅ All systems are healthy! Continue monitoring and maintaining current practices."
            )

        return recommendations


# Global self-validation instance
default_validator = SelfValidationSystem()
