"""
QA System

Independent QA Agent pool that validates code quality, detects issues,
and automatically fixes problems for production-ready code.

Testing & Validation Pipeline:
- Test Generation: Automatic test creation
- Test Execution: Orchestrated test runs
- Coverage Analysis: Measure and enforce thresholds
- Performance: Regression detection
- Security: SAST/DAST scanning
- Mutation: Test quality verification
- Flaky Detection: Intermittent failure identification
- Quality Scoring: Individual test ratings
- Documentation: Code sample verification
"""

from .code_analyzer import CodeAnalyzer, CodeIssue, IssueSeverity
from .code_remediator import CodeRemediator
from .planning_validator import PlanningValidator, PlanningIssue, ValidationResult
from .prod_readiness import ProductionReadinessChecker, ReadinessCheck
from .qa_knowledge_graph import QAKnowledgeGraph, KnowledgeEntry
from .qa_metrics import QAMetricsCollector, QAMetric

# Testing Pipeline Components
from .test_executor import TestExecutor, TestLevel, TestStatus, TestCase, TestRunResult
from .coverage_analyzer import CoverageAnalyzer, CoverageReport, FileCoverage, CoverageMetric
from .perf_regression_detector import PerformanceRegressionDetector, RegressionReport, PerformanceMetrics
from .security_tester import SecurityTester, SecurityScanReport, Vulnerability, VulnerabilityType
from .mutation_tester import MutationTester, MutationTestResult, Mutant, MutationType
from .test_quality_scorer import TestQualityScorer, TestQualityMetrics
from .flaky_test_detector import FlakyTestDetector, FlakyTestReport, FlakyTestInfo
from .doc_tester import DocumentationTester, DocTestReport, CodeSample
from .test_reporter import TestReporter, TestReport

__all__ = [
    # Original QA System
    "CodeAnalyzer",
    "CodeIssue",
    "IssueSeverity",
    "CodeRemediator",
    "PlanningValidator",
    "PlanningIssue",
    "ValidationResult",
    "ProductionReadinessChecker",
    "ReadinessCheck",
    "QAKnowledgeGraph",
    "KnowledgeEntry",
    "QAMetricsCollector",
    "QAMetric",
    
    # Testing Pipeline
    "TestExecutor",
    "TestLevel",
    "TestStatus",
    "TestCase",
    "TestRunResult",
    "CoverageAnalyzer",
    "CoverageReport",
    "FileCoverage",
    "CoverageMetric",
    "PerformanceRegressionDetector",
    "RegressionReport",
    "PerformanceMetrics",
    "SecurityTester",
    "SecurityScanReport",
    "Vulnerability",
    "VulnerabilityType",
    "MutationTester",
    "MutationTestResult",
    "Mutant",
    "MutationType",
    "TestQualityScorer",
    "TestQualityMetrics",
    "FlakyTestDetector",
    "FlakyTestReport",
    "FlakyTestInfo",
    "DocumentationTester",
    "DocTestReport",
    "CodeSample",
    "TestReporter",
    "TestReport",
]
