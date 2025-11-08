"""
QA Agent Specialization

Independent QA Agent that validates code written by dev agents,
detecting and automatically fixing quality issues.
"""

import time
from typing import Dict, List, Optional, Any
from enum import Enum
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class QALevel(str, Enum):
    """QA verification levels"""
    BASIC = "basic"  # Syntax, imports, basic linting
    STANDARD = "standard"  # + Code smells, naming, error handling
    STRICT = "strict"  # + Performance, security, architecture
    PARANOID = "paranoid"  # + Style nitpicks, docs, test coverage


class QAAgent(SpecializedAgent):
    """QA Specialist that validates code quality and production readiness"""
    
    def __init__(self, agent_id: str, blackboard, qa_level: QALevel = QALevel.STANDARD, **kwargs):
        # Add QA role if not in AgentRole enum yet
        super().__init__(AgentRole.CODE_REVIEWER, blackboard, name=agent_id, **kwargs)
        
        self.qa_level = qa_level
        self.code_reviewed_count = 0
        self.issues_found_count = 0
        self.auto_fixes_applied = 0
        
        # QA-specific knowledge base
        self.quality_checks = {
            QALevel.BASIC: [
                "syntax_validation",
                "import_check",
                "basic_linting"
            ],
            QALevel.STANDARD: [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation"
            ],
            QALevel.STRICT: [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation",
                "performance_analysis",
                "security_scan",
                "architectural_pattern_check"
            ],
            QALevel.PARANOID: [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation",
                "performance_analysis",
                "security_scan",
                "architectural_pattern_check",
                "style_nitpick_check",
                "documentation_completeness",
                "test_coverage_check"
            ]
        }
        
        # Anti-patterns and code smells
        self.anti_patterns = {
            "stub_detection": {
                "patterns": ["pass", "...", "TODO", "FIXME", "NotImplemented", "raise NotImplementedError"],
                "severity": "HIGH"
            },
            "hack_detection": {
                "patterns": ["# HACK:", "# FIXME:", "while True: break", "# XXX"],
                "severity": "HIGH"
            },
            "magic_numbers": {
                "patterns": ["\\b\\d{2,}\\b"],  # Numbers with 2+ digits without const
                "severity": "MEDIUM"
            },
            "deep_nesting": {
                "threshold": 4,
                "severity": "MEDIUM"
            },
            "long_function": {
                "threshold": 50,  # lines
                "severity": "MEDIUM"
            },
            "god_class": {
                "threshold": 500,  # lines
                "severity": "HIGH"
            },
            "missing_error_handling": {
                "patterns": ["open(", "requests.get", "json.loads"],
                "severity": "HIGH"
            },
            "sql_injection": {
                "patterns": ["f\"SELECT", "f'SELECT", ".format(", "% ("],
                "severity": "CRITICAL"
            },
            "hardcoded_secrets": {
                "patterns": ["password", "api_key", "secret", "token"],
                "severity": "CRITICAL"
            }
        }
        
        # Auto-fixable issues
        self.auto_fixable = [
            "import_organization",
            "formatting",
            "naming_convention",
            "add_type_hints",
            "add_docstrings",
            "extract_magic_numbers",
            "add_logging"
        ]
        
        # Allowed tools for QA agent
        self.allowed_tools = [
            "bash",
            "python_execute",
            "str_replace_editor",
            "file_read",
            "file_write",
            "web_search"
        ]
        
        # QA metrics
        self.metrics = {
            "total_reviews": 0,
            "issues_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "auto_fixes_applied": 0,
            "manual_review_required": 0,
            "false_positives": 0,
            "average_review_time": 0.0
        }
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute QA-specific tasks"""
        start_time = time.time()
        
        try:
            # Extract code to review from task
            code_to_review = task.requirements.get("code_files", [])
            task_type = task.requirements.get("type", "code_review")
            
            if task_type == "code_review":
                result = await self._perform_code_review(code_to_review, task)
            elif task_type == "planning_validation":
                result = await self._validate_planning(task)
            elif task_type == "prod_readiness_check":
                result = await self._check_prod_readiness(task)
            else:
                result = f"Unknown QA task type: {task_type}"
            
            # Update metrics
            review_time = time.time() - start_time
            self.metrics["total_reviews"] += 1
            self.metrics["average_review_time"] = (
                (self.metrics["average_review_time"] * (self.metrics["total_reviews"] - 1) + review_time)
                / self.metrics["total_reviews"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"QA Agent error: {e}")
            return f"QA review failed: {str(e)}"
    
    async def _perform_code_review(self, code_files: List[str], task: DevelopmentTask) -> str:
        """Perform comprehensive code review"""
        from app.qa.code_analyzer import CodeAnalyzer
        from app.qa.code_remediator import CodeRemediator
        
        self.code_reviewed_count += 1
        
        # Get checks for current QA level
        checks = self.quality_checks.get(self.qa_level, self.quality_checks[QALevel.STANDARD])
        
        # Initialize analyzer
        analyzer = CodeAnalyzer(qa_level=self.qa_level)
        
        # Analyze all files
        all_issues = []
        for file_path in code_files:
            issues = await analyzer.analyze_file(file_path, checks)
            all_issues.extend(issues)
        
        self.issues_found_count += len(all_issues)
        
        # Count by severity
        for issue in all_issues:
            severity = issue.get("severity", "MEDIUM")
            self.metrics["issues_by_severity"][severity] = self.metrics["issues_by_severity"].get(severity, 0) + 1
        
        # Auto-fix if enabled
        remediator = CodeRemediator()
        auto_fixed = []
        manual_required = []
        
        for issue in all_issues:
            if issue.get("auto_fixable", False):
                fix_result = await remediator.apply_fix(issue)
                if fix_result.get("success"):
                    auto_fixed.append(issue)
                    self.auto_fixes_applied += 1
                    self.metrics["auto_fixes_applied"] += 1
                else:
                    manual_required.append(issue)
            else:
                manual_required.append(issue)
                self.metrics["manual_review_required"] += 1
        
        # Generate report
        report = self._generate_qa_report(all_issues, auto_fixed, manual_required)
        
        # Determine approval status
        critical_issues = [i for i in manual_required if i.get("severity") == "CRITICAL"]
        high_issues = [i for i in manual_required if i.get("severity") == "HIGH"]
        
        if critical_issues:
            approval = "BLOCKED - Critical issues must be fixed"
        elif high_issues:
            approval = "BLOCKED - High priority issues must be fixed"
        elif manual_required:
            approval = "APPROVED WITH RECOMMENDATIONS"
        else:
            approval = "APPROVED"
        
        return f"{report}\n\nQA APPROVAL STATUS: {approval}"
    
    async def _validate_planning(self, task: DevelopmentTask) -> str:
        """Validate task planning and decomposition"""
        from app.qa.planning_validator import PlanningValidator
        
        validator = PlanningValidator()
        plan_data = task.requirements.get("plan", {})
        
        validation_result = await validator.validate(plan_data)
        
        return validation_result.get("report", "Planning validation completed")
    
    async def _check_prod_readiness(self, task: DevelopmentTask) -> str:
        """Check production readiness"""
        from app.qa.prod_readiness import ProductionReadinessChecker
        
        checker = ProductionReadinessChecker()
        code_files = task.requirements.get("code_files", [])
        
        readiness_result = await checker.check_readiness(code_files)
        
        return readiness_result.get("report", "Production readiness check completed")
    
    def _generate_qa_report(
        self,
        all_issues: List[Dict[str, Any]],
        auto_fixed: List[Dict[str, Any]],
        manual_required: List[Dict[str, Any]]
    ) -> str:
        """Generate comprehensive QA report"""
        report = ["=" * 80]
        report.append("QA REVIEW REPORT")
        report.append("=" * 80)
        report.append(f"QA Level: {self.qa_level.value.upper()}")
        report.append(f"Total Issues Found: {len(all_issues)}")
        report.append(f"Auto-Fixed: {len(auto_fixed)}")
        report.append(f"Manual Review Required: {len(manual_required)}")
        report.append("")
        
        # Issues by severity
        severity_counts = {}
        for issue in all_issues:
            severity = issue.get("severity", "MEDIUM")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        report.append("Issues by Severity:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                report.append(f"  {severity}: {count}")
        report.append("")
        
        # Auto-fixed issues
        if auto_fixed:
            report.append("Auto-Fixed Issues:")
            for issue in auto_fixed[:5]:  # Show first 5
                report.append(f"  ✓ {issue.get('type', 'Unknown')}: {issue.get('message', 'N/A')}")
            if len(auto_fixed) > 5:
                report.append(f"  ... and {len(auto_fixed) - 5} more")
            report.append("")
        
        # Manual review required
        if manual_required:
            report.append("Manual Review Required:")
            for issue in manual_required[:10]:  # Show first 10
                severity = issue.get("severity", "MEDIUM")
                issue_type = issue.get("type", "Unknown")
                message = issue.get("message", "N/A")
                location = issue.get("location", "Unknown")
                report.append(f"  [{severity}] {issue_type} at {location}")
                report.append(f"    → {message}")
                if "suggestion" in issue:
                    report.append(f"    💡 Suggestion: {issue['suggestion']}")
            if len(manual_required) > 10:
                report.append(f"  ... and {len(manual_required) - 10} more issues")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get QA metrics"""
        return {
            **self.metrics,
            "qa_level": self.qa_level.value,
            "code_reviewed": self.code_reviewed_count,
            "issues_found": self.issues_found_count,
            "auto_fixes_applied": self.auto_fixes_applied
        }
