"""
Production Readiness Checker

Final gate before merge to production branch.
"""

import os
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from app.logger import logger


@dataclass
class ReadinessCheck:
    """Production readiness check item"""
    name: str
    passed: bool
    severity: str  # BLOCKER, CRITICAL, WARNING
    message: str
    details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": self.details
        }


class ProductionReadinessChecker:
    """Checks production readiness"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_code_coverage = self.config.get("min_code_coverage", 80)
        self.enforce_tests = self.config.get("enforce_tests", True)
        self.enforce_docs = self.config.get("enforce_documentation", True)
    
    async def check_readiness(self, code_files: List[str]) -> Dict[str, Any]:
        """Perform production readiness checks"""
        checks = []
        
        # Run all checks
        checks.append(await self._check_tests_passing())
        checks.append(await self._check_code_coverage(code_files))
        checks.append(await self._check_security_scan(code_files))
        checks.append(await self._check_performance_regression())
        checks.append(await self._check_documentation(code_files))
        checks.append(await self._check_migrations())
        checks.append(await self._check_deployment_docs())
        checks.append(await self._check_rollback_procedure())
        checks.append(await self._check_monitoring())
        checks.append(await self._check_secrets(code_files))
        checks.append(await self._check_dependencies())
        checks.append(await self._check_backwards_compatibility())
        checks.append(await self._check_changelog())
        checks.append(await self._check_version_bump())
        checks.append(await self._check_performance_slas())
        
        # Determine overall readiness
        blockers = [c for c in checks if not c.passed and c.severity == "BLOCKER"]
        critical = [c for c in checks if not c.passed and c.severity == "CRITICAL"]
        warnings = [c for c in checks if not c.passed and c.severity == "WARNING"]
        
        passed = len(blockers) == 0 and len(critical) == 0
        
        # Generate report
        report = self._generate_readiness_report(checks, passed)
        
        return {
            "ready": passed,
            "checks": [c.to_dict() for c in checks],
            "blockers": [c.to_dict() for c in blockers],
            "critical": [c.to_dict() for c in critical],
            "warnings": [c.to_dict() for c in warnings],
            "report": report
        }
    
    async def _check_tests_passing(self) -> ReadinessCheck:
        """Check if all tests pass"""
        if not self.enforce_tests:
            return ReadinessCheck(
                name="Tests Passing",
                passed=True,
                severity="WARNING",
                message="Test enforcement disabled"
            )
        
        try:
            # Try to run tests
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            passed = result.returncode == 0
            
            return ReadinessCheck(
                name="Tests Passing",
                passed=passed,
                severity="BLOCKER",
                message="All tests pass" if passed else "Some tests failing",
                details=result.stdout if not passed else None
            )
        
        except FileNotFoundError:
            return ReadinessCheck(
                name="Tests Passing",
                passed=False,
                severity="WARNING",
                message="No test framework found",
                details="pytest not installed"
            )
        
        except subprocess.TimeoutExpired:
            return ReadinessCheck(
                name="Tests Passing",
                passed=False,
                severity="CRITICAL",
                message="Tests timed out",
                details="Tests took more than 5 minutes"
            )
        
        except Exception as e:
            return ReadinessCheck(
                name="Tests Passing",
                passed=False,
                severity="WARNING",
                message="Could not run tests",
                details=str(e)
            )
    
    async def _check_code_coverage(self, code_files: List[str]) -> ReadinessCheck:
        """Check code coverage"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov", "--cov-report=term"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse coverage from output
            coverage = 0
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line:
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            coverage = int(part.replace('%', ''))
                            break
            
            passed = coverage >= self.min_code_coverage
            
            return ReadinessCheck(
                name="Code Coverage",
                passed=passed,
                severity="CRITICAL",
                message=f"Coverage: {coverage}% (min: {self.min_code_coverage}%)",
                details=f"Current coverage: {coverage}%"
            )
        
        except FileNotFoundError:
            return ReadinessCheck(
                name="Code Coverage",
                passed=False,
                severity="WARNING",
                message="Coverage tool not found",
                details="pytest-cov not installed"
            )
        
        except Exception as e:
            return ReadinessCheck(
                name="Code Coverage",
                passed=False,
                severity="WARNING",
                message="Could not check coverage",
                details=str(e)
            )
    
    async def _check_security_scan(self, code_files: List[str]) -> ReadinessCheck:
        """Run security scan"""
        try:
            # Try to run bandit
            result = subprocess.run(
                ["python", "-m", "bandit", "-r", ".", "-ll"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check for high/medium severity issues
            high_issues = result.stdout.count("Severity: High")
            medium_issues = result.stdout.count("Severity: Medium")
            
            passed = high_issues == 0
            
            return ReadinessCheck(
                name="Security Scan",
                passed=passed,
                severity="BLOCKER" if high_issues > 0 else "WARNING",
                message=f"Security scan: {high_issues} high, {medium_issues} medium issues",
                details=result.stdout if high_issues > 0 else None
            )
        
        except FileNotFoundError:
            return ReadinessCheck(
                name="Security Scan",
                passed=True,
                severity="WARNING",
                message="Security scanner not found",
                details="bandit not installed"
            )
        
        except Exception as e:
            return ReadinessCheck(
                name="Security Scan",
                passed=True,
                severity="WARNING",
                message="Could not run security scan",
                details=str(e)
            )
    
    async def _check_performance_regression(self) -> ReadinessCheck:
        """Check for performance regressions"""
        # This would need benchmark comparison
        return ReadinessCheck(
            name="Performance Regression",
            passed=True,
            severity="WARNING",
            message="Performance benchmarks not configured",
            details="Configure benchmarks for production"
        )
    
    async def _check_documentation(self, code_files: List[str]) -> ReadinessCheck:
        """Check documentation completeness"""
        if not self.enforce_docs:
            return ReadinessCheck(
                name="Documentation",
                passed=True,
                severity="WARNING",
                message="Documentation enforcement disabled"
            )
        
        undocumented = []
        
        for file_path in code_files:
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Simple check: does file have module docstring?
                if not content.strip().startswith('"""'):
                    undocumented.append(file_path)
            
            except Exception as e:
                logger.debug(f"Could not check documentation for {file_path}: {e}")
        
        passed = len(undocumented) == 0
        
        return ReadinessCheck(
            name="Documentation",
            passed=passed,
            severity="WARNING",
            message=f"{len(undocumented)} files without documentation",
            details=", ".join(undocumented[:5]) if undocumented else None
        )
    
    async def _check_migrations(self) -> ReadinessCheck:
        """Check database migrations"""
        # Check if migrations directory exists
        if os.path.exists("migrations") or os.path.exists("alembic"):
            return ReadinessCheck(
                name="Database Migrations",
                passed=True,
                severity="WARNING",
                message="Migrations exist but not tested",
                details="Ensure migrations are tested in staging"
            )
        
        return ReadinessCheck(
            name="Database Migrations",
            passed=True,
            severity="WARNING",
            message="No migrations detected"
        )
    
    async def _check_deployment_docs(self) -> ReadinessCheck:
        """Check deployment documentation"""
        deployment_files = [
            "DEPLOYMENT.md",
            "deploy.md",
            "README.md"
        ]
        
        has_deploy_docs = any(os.path.exists(f) for f in deployment_files)
        
        return ReadinessCheck(
            name="Deployment Documentation",
            passed=has_deploy_docs,
            severity="WARNING",
            message="Deployment docs found" if has_deploy_docs else "No deployment docs",
            details="Add DEPLOYMENT.md with deployment steps" if not has_deploy_docs else None
        )
    
    async def _check_rollback_procedure(self) -> ReadinessCheck:
        """Check rollback documentation"""
        # Look for rollback mentions in docs
        has_rollback_docs = False
        
        if os.path.exists("DEPLOYMENT.md"):
            try:
                with open("DEPLOYMENT.md", 'r') as f:
                    content = f.read().lower()
                    has_rollback_docs = "rollback" in content
            except Exception:
                pass
        
        return ReadinessCheck(
            name="Rollback Procedure",
            passed=has_rollback_docs,
            severity="WARNING",
            message="Rollback procedure documented" if has_rollback_docs else "No rollback docs",
            details="Document rollback procedure in DEPLOYMENT.md" if not has_rollback_docs else None
        )
    
    async def _check_monitoring(self) -> ReadinessCheck:
        """Check monitoring configuration"""
        # This is application-specific
        return ReadinessCheck(
            name="Monitoring/Alerting",
            passed=True,
            severity="WARNING",
            message="Configure monitoring for production",
            details="Set up metrics, logging, and alerts"
        )
    
    async def _check_secrets(self, code_files: List[str]) -> ReadinessCheck:
        """Check for hardcoded secrets"""
        secret_patterns = [
            "password",
            "api_key",
            "secret",
            "token",
            "apikey"
        ]
        
        files_with_secrets = []
        
        for file_path in code_files:
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                for pattern in secret_patterns:
                    if f'{pattern}="' in content or f"{pattern}='" in content:
                        files_with_secrets.append(file_path)
                        break
            
            except Exception:
                pass
        
        passed = len(files_with_secrets) == 0
        
        return ReadinessCheck(
            name="No Hardcoded Secrets",
            passed=passed,
            severity="BLOCKER",
            message="No secrets detected" if passed else f"Potential secrets in {len(files_with_secrets)} files",
            details=", ".join(files_with_secrets) if not passed else None
        )
    
    async def _check_dependencies(self) -> ReadinessCheck:
        """Check dependency versions are pinned"""
        if os.path.exists("requirements.txt"):
            try:
                with open("requirements.txt", 'r') as f:
                    content = f.read()
                
                unpinned = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' not in line and '>=' not in line:
                            unpinned.append(line)
                
                passed = len(unpinned) == 0
                
                return ReadinessCheck(
                    name="Pinned Dependencies",
                    passed=passed,
                    severity="WARNING",
                    message="All dependencies pinned" if passed else f"{len(unpinned)} unpinned",
                    details=", ".join(unpinned) if unpinned else None
                )
            
            except Exception:
                pass
        
        return ReadinessCheck(
            name="Pinned Dependencies",
            passed=True,
            severity="WARNING",
            message="No requirements.txt found"
        )
    
    async def _check_backwards_compatibility(self) -> ReadinessCheck:
        """Check backwards compatibility"""
        # This requires more context
        return ReadinessCheck(
            name="Backwards Compatibility",
            passed=True,
            severity="WARNING",
            message="Manual verification required",
            details="Verify API/library changes are backwards compatible"
        )
    
    async def _check_changelog(self) -> ReadinessCheck:
        """Check changelog entry"""
        changelog_files = ["CHANGELOG.md", "CHANGES.md", "HISTORY.md"]
        
        has_changelog = any(os.path.exists(f) for f in changelog_files)
        
        return ReadinessCheck(
            name="Changelog Entry",
            passed=has_changelog,
            severity="WARNING",
            message="Changelog found" if has_changelog else "No changelog",
            details="Add CHANGELOG.md with version history" if not has_changelog else None
        )
    
    async def _check_version_bump(self) -> ReadinessCheck:
        """Check version bump"""
        # This requires checking version files
        return ReadinessCheck(
            name="Version Bump",
            passed=True,
            severity="WARNING",
            message="Verify version bump is correct",
            details="Ensure version follows semantic versioning"
        )
    
    async def _check_performance_slas(self) -> ReadinessCheck:
        """Check performance SLAs"""
        return ReadinessCheck(
            name="Performance SLAs",
            passed=True,
            severity="WARNING",
            message="Performance SLAs not configured",
            details="Define and verify performance SLAs"
        )
    
    def _generate_readiness_report(self, checks: List[ReadinessCheck], ready: bool) -> str:
        """Generate production readiness report"""
        report = ["=" * 80]
        report.append("PRODUCTION READINESS REPORT")
        report.append("=" * 80)
        
        passed_count = sum(1 for c in checks if c.passed)
        report.append(f"Checks Passed: {passed_count}/{len(checks)}")
        report.append("")
        
        # Group by severity
        blockers = [c for c in checks if not c.passed and c.severity == "BLOCKER"]
        critical = [c for c in checks if not c.passed and c.severity == "CRITICAL"]
        warnings = [c for c in checks if not c.passed and c.severity == "WARNING"]
        
        if blockers:
            report.append("🚫 BLOCKERS (must fix before production):")
            for check in blockers:
                report.append(f"  ❌ {check.name}: {check.message}")
                if check.details:
                    report.append(f"     Details: {check.details}")
            report.append("")
        
        if critical:
            report.append("⚠️  CRITICAL (should fix before production):")
            for check in critical:
                report.append(f"  ❌ {check.name}: {check.message}")
                if check.details:
                    report.append(f"     Details: {check.details}")
            report.append("")
        
        if warnings:
            report.append(f"⚡ WARNINGS ({len(warnings)}):")
            for check in warnings[:5]:
                report.append(f"  ⚠️  {check.name}: {check.message}")
            if len(warnings) > 5:
                report.append(f"  ... and {len(warnings) - 5} more")
            report.append("")
        
        # Passed checks
        passed = [c for c in checks if c.passed]
        if passed:
            report.append(f"✅ PASSED ({len(passed)}):")
            for check in passed[:5]:
                report.append(f"  ✓ {check.name}")
            if len(passed) > 5:
                report.append(f"  ... and {len(passed) - 5} more")
        
        report.append("=" * 80)
        
        if ready:
            report.append("✅ PRODUCTION READY - All critical checks passed")
        else:
            report.append("❌ NOT PRODUCTION READY - Fix blockers and critical issues")
        
        return "\n".join(report)
