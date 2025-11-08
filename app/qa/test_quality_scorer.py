"""
Test Quality Scoring

Rates individual test quality based on:
- Clarity of assertions
- Setup/teardown
- Test isolation
- Determinism
- Edge case coverage
- Performance
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from app.logger import logger


@dataclass
class TestQualityMetrics:
    """Metrics for a single test"""
    test_name: str
    file_path: str
    line_number: int
    has_clear_assertion: bool = False
    has_setup: bool = False
    has_teardown: bool = False
    is_isolated: bool = False
    is_deterministic: bool = False
    covers_edge_cases: bool = False
    performance_ok: bool = False  # runs in < 1s
    maintainability_score: float = 0.0  # 0-100
    clarity_score: float = 0.0  # 0-100
    overall_score: float = 0.0  # 0-100
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "metrics": {
                "has_clear_assertion": self.has_clear_assertion,
                "has_setup": self.has_setup,
                "has_teardown": self.has_teardown,
                "is_isolated": self.is_isolated,
                "is_deterministic": self.is_deterministic,
                "covers_edge_cases": self.covers_edge_cases,
                "performance_ok": self.performance_ok,
            },
            "scores": {
                "maintainability": self.maintainability_score,
                "clarity": self.clarity_score,
                "overall": self.overall_score,
            },
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


class TestQualityScorer:
    """Score individual test quality"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.test_scores: Dict[str, TestQualityMetrics] = {}
        self.min_quality_score = self.config.get("min_test_quality_score", 70)
    
    async def score_test_file(self, file_path: str) -> Dict[str, TestQualityMetrics]:
        """Score all tests in a file"""
        try:
            with open(file_path) as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    score = self._score_test_function(node, file_path, source)
                    self.test_scores[f"{file_path}::{node.name}"] = score
            
            return self.test_scores
        
        except Exception as e:
            logger.error(f"Failed to score test file {file_path}: {e}")
            return {}
    
    def _score_test_function(self, node: ast.FunctionDef, file_path: str, source: str) -> TestQualityMetrics:
        """Score a single test function"""
        source_lines = source.split("\n")
        
        # Extract function source
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        function_lines = source_lines[start_line - 1:end_line]
        function_source = "\n".join(function_lines)
        
        metrics = TestQualityMetrics(
            test_name=node.name,
            file_path=file_path,
            line_number=start_line,
            has_clear_assertion=self._check_clear_assertion(node),
            has_setup=self._check_setup(node),
            has_teardown=self._check_teardown(node),
            is_isolated=self._check_isolation(node),
            is_deterministic=self._check_determinism(function_source),
            covers_edge_cases=self._check_edge_cases(function_source),
            performance_ok=self._check_performance(node),
        )
        
        # Calculate scores
        metrics.maintainability_score = self._calculate_maintainability_score(metrics, function_lines)
        metrics.clarity_score = self._calculate_clarity_score(metrics, function_lines)
        metrics.overall_score = (metrics.maintainability_score + metrics.clarity_score) / 2
        
        # Generate issues and recommendations
        metrics.issues = self._generate_issues(metrics)
        metrics.recommendations = self._generate_recommendations(metrics)
        
        return metrics
    
    def _check_clear_assertion(self, node: ast.FunctionDef) -> bool:
        """Check if test has clear assertions"""
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ["assert_equal", "assert_true", "assert_false", "assert_raises"]:
                        return True
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id == "assert_" or "assert" in child.func.attr:
                            return True
        return False
    
    def _check_setup(self, node: ast.FunctionDef) -> bool:
        """Check if test has setup"""
        # Look for setUp, setup, arrange pattern
        source = ast.unparse(node)
        return any(pattern in source for pattern in ["setUp", "setup", "# Arrange", "arrange"])
    
    def _check_teardown(self, node: ast.FunctionDef) -> bool:
        """Check if test has teardown"""
        # Look for tearDown, cleanup, finally, context manager
        has_try_finally = False
        has_context_manager = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                has_try_finally = True
            if isinstance(child, ast.With):
                has_context_manager = True
        
        return has_try_finally or has_context_manager
    
    def _check_isolation(self, node: ast.FunctionDef) -> bool:
        """Check if test is isolated (no external dependencies)"""
        source = ast.unparse(node)
        
        # Red flags for non-isolated tests
        red_flags = [
            "global ",
            "import ",
            ".connect(",
            ".open(",
            "requests.get",
            "http",
            "database",
            "static variable",
        ]
        
        for flag in red_flags:
            if flag in source.lower():
                return False
        
        return True
    
    def _check_determinism(self, source: str) -> bool:
        """Check if test is deterministic"""
        # Red flags for non-deterministic tests
        red_flags = [
            "random.",
            "randint",
            "sleep(",
            "time.time()",
            "datetime.now()",
            "uuid",
        ]
        
        for flag in red_flags:
            if flag in source.lower():
                return False
        
        return True
    
    def _check_edge_cases(self, source: str) -> bool:
        """Check if test covers edge cases"""
        edge_case_patterns = [
            "None",
            "empty",
            "[]",
            "0",
            "-1",
            "max",
            "min",
            "boundary",
            "limit",
        ]
        
        matches = sum(1 for pattern in edge_case_patterns if pattern.lower() in source.lower())
        return matches >= 2  # Should have at least 2 edge case indicators
    
    def _check_performance(self, node: ast.FunctionDef) -> bool:
        """Check if test is performant (no very slow operations)"""
        # Look for performance anti-patterns
        source = ast.unparse(node)
        
        slow_patterns = [
            "time.sleep()",
            "sleep(10",
            "sleep(60",
        ]
        
        for pattern in slow_patterns:
            if pattern in source:
                return False
        
        return True
    
    def _calculate_maintainability_score(self, metrics: TestQualityMetrics, lines: List[str]) -> float:
        """Calculate maintainability score"""
        score = 50.0  # Base score
        
        # Clarity
        if metrics.has_clear_assertion:
            score += 10
        if metrics.is_isolated:
            score += 10
        if metrics.is_deterministic:
            score += 10
        
        # Complexity
        function_length = len(lines)
        if function_length < 10:
            score += 5
        elif function_length > 50:
            score -= 10
        
        return min(100.0, max(0.0, score))
    
    def _calculate_clarity_score(self, metrics: TestQualityMetrics, lines: List[str]) -> float:
        """Calculate clarity score"""
        score = 50.0  # Base score
        
        if metrics.has_setup:
            score += 10
        if metrics.has_teardown:
            score += 10
        if metrics.covers_edge_cases:
            score += 10
        if metrics.performance_ok:
            score += 10
        
        return min(100.0, max(0.0, score))
    
    def _generate_issues(self, metrics: TestQualityMetrics) -> List[str]:
        """Generate quality issues"""
        issues = []
        
        if not metrics.has_clear_assertion:
            issues.append("No clear assertion found")
        if not metrics.has_setup:
            issues.append("Missing setup/arrange section")
        if not metrics.has_teardown:
            issues.append("Missing teardown/cleanup")
        if not metrics.is_isolated:
            issues.append("Test has external dependencies")
        if not metrics.is_deterministic:
            issues.append("Test may be non-deterministic")
        if not metrics.covers_edge_cases:
            issues.append("Missing edge case testing")
        if not metrics.performance_ok:
            issues.append("Test may be too slow")
        
        return issues
    
    def _generate_recommendations(self, metrics: TestQualityMetrics) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if not metrics.has_clear_assertion:
            recommendations.append("Add explicit assertions: assert expected == actual")
        if not metrics.has_setup:
            recommendations.append("Add setup phase to initialize test fixtures")
        if not metrics.is_isolated:
            recommendations.append("Use mocks/patches for external dependencies")
        if not metrics.is_deterministic:
            recommendations.append("Avoid non-deterministic operations (random, datetime, sleep)")
        if not metrics.covers_edge_cases:
            recommendations.append("Add tests for edge cases (empty, None, zero, negative)")
        if metrics.overall_score < self.min_quality_score:
            recommendations.append(f"Overall quality score ({metrics.overall_score:.0f}) below minimum ({self.min_quality_score})")
        
        return recommendations
    
    def get_failed_quality_tests(self) -> List[TestQualityMetrics]:
        """Get tests that fail quality threshold"""
        return [
            metrics for metrics in self.test_scores.values()
            if metrics.overall_score < self.min_quality_score
        ]
    
    def export_report(self, format: str = "json") -> str:
        """Export quality scores"""
        if format == "json":
            data = {
                test_id: metrics.to_dict()
                for test_id, metrics in self.test_scores.items()
            }
            return json.dumps(data, indent=2)
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        report = ["=" * 80]
        report.append("TEST QUALITY REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        total_tests = len(self.test_scores)
        failed_quality = len(self.get_failed_quality_tests())
        avg_score = sum(m.overall_score for m in self.test_scores.values()) / total_tests if total_tests > 0 else 0
        
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Average Quality Score: {avg_score:.1f}/100")
        report.append(f"Tests Below Threshold: {failed_quality}")
        report.append("")
        
        # Low quality tests
        if failed_quality > 0:
            report.append("TESTS BELOW QUALITY THRESHOLD:")
            for test_id, metrics in sorted(
                self.test_scores.items(),
                key=lambda x: x[1].overall_score
            ):
                if metrics.overall_score < self.min_quality_score:
                    report.append(f"  {metrics.test_name}: {metrics.overall_score:.1f}/100")
                    for issue in metrics.issues:
                        report.append(f"    - {issue}")
            report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
