"""
Comprehensive tests for the Testing & Validation Pipeline

Tests all components:
- Test Executor
- Coverage Analyzer
- Performance Regression Detector
- Security Tester
- Mutation Tester
- Test Quality Scorer
- Flaky Test Detector
- Documentation Tester
- Test Reporter
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.qa.test_executor import (
    TestExecutor, TestLevel, TestStatus, TestCase, TestRunResult
)
from app.qa.coverage_analyzer import CoverageAnalyzer, FileCoverage, CoverageReport
from app.qa.perf_regression_detector import PerformanceRegressionDetector, PerformanceMetrics
from app.qa.security_tester import SecurityTester, VulnerabilityType
from app.qa.mutation_tester import MutationTester, MutationType
from app.qa.test_quality_scorer import TestQualityScorer, TestQualityMetrics
from app.qa.flaky_test_detector import FlakyTestDetector
from app.qa.doc_tester import DocumentationTester, CodeSample
from app.qa.test_reporter import TestReporter


class TestTestExecutor:
    """Test the TestExecutor component"""
    
    @pytest.mark.asyncio
    async def test_register_test(self):
        """Test registering a test case"""
        executor = TestExecutor()
        
        test = await executor.register_test(
            "test_001",
            "test_example",
            TestLevel.UNIT,
            "tests/test_example.py"
        )
        
        assert test.test_id == "test_001"
        assert test.name == "test_example"
        assert test.level == TestLevel.UNIT
        assert test.status == TestStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_test_dependency_sorting(self):
        """Test topological sort of test dependencies"""
        executor = TestExecutor()
        
        await executor.register_test("t1", "test_1", TestLevel.UNIT, "test.py", dependencies=[])
        await executor.register_test("t2", "test_2", TestLevel.UNIT, "test.py", dependencies=["t1"])
        await executor.register_test("t3", "test_3", TestLevel.UNIT, "test.py", dependencies=["t2"])
        
        sorted_tests = executor._topological_sort(executor.tests)
        
        assert len(sorted_tests) == 3
        assert sorted_tests[0].test_id == "t1"
        assert sorted_tests[1].test_id == "t2"
        assert sorted_tests[2].test_id == "t3"
    
    @pytest.mark.asyncio
    async def test_execute_empty_suite(self):
        """Test executing empty test suite"""
        executor = TestExecutor()
        
        result = await executor.run_tests()
        
        assert result.total_tests == 0
        assert result.passed == 0
        assert result.failed == 0


class TestCoverageAnalyzer:
    """Test the CoverageAnalyzer component"""
    
    @pytest.mark.asyncio
    async def test_coverage_thresholds(self):
        """Test coverage threshold checking"""
        config = {
            "enforce": True,
            "threshold_overall": 80,
            "threshold_new_code": 90,
            "threshold_critical": 95,
        }
        
        analyzer = CoverageAnalyzer(config)
        
        report = CoverageReport(
            timestamp=datetime.now(),
            total_line_coverage=85,
            new_code_coverage=92,
            critical_path_coverage=96,
        )
        
        within_thresholds = report.is_within_thresholds(80, 90, 95)
        assert within_thresholds
    
    @pytest.mark.asyncio
    async def test_coverage_threshold_violation(self):
        """Test detection of coverage threshold violations"""
        report = CoverageReport(
            timestamp=datetime.now(),
            total_line_coverage=70,  # Below 80% threshold
            new_code_coverage=85,
            critical_path_coverage=95,
        )
        
        within_thresholds = report.is_within_thresholds(80, 90, 95)
        assert not within_thresholds
        assert len(report.threshold_violations) > 0


class TestPerformanceRegressionDetector:
    """Test the PerformanceRegressionDetector component"""
    
    @pytest.mark.asyncio
    async def test_benchmark_creation(self):
        """Test creating a performance baseline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"baseline_storage": f"{tmpdir}/baselines.json"}
            detector = PerformanceRegressionDetector(config)
            
            def dummy_test():
                return sum(range(100))
            
            baseline = await detector.benchmark("test_op", dummy_test, runs=1)
            
            assert baseline.name == "test_op"
            assert baseline.latency_ms > 0
            assert baseline.throughput_ops_sec > 0
    
    @pytest.mark.asyncio
    async def test_regression_detection(self):
        """Test regression detection"""
        detector = PerformanceRegressionDetector()
        
        # Mock baseline and current metrics
        from app.qa.perf_regression_detector import BenchmarkBaseline
        baseline = BenchmarkBaseline(
            name="test_op",
            latency_ms=100,
            memory_mb=10,
            throughput_ops_sec=100,
            timestamp=datetime.now(),
        )
        
        detector.baselines["test_op"] = baseline
        
        # Add current metrics with regression
        detector.current_metrics["test_op"] = PerformanceMetrics(
            name="test_op",
            latency_ms=115,  # 15% regression
            memory_mb=10,
            throughput_ops_sec=100,
        )
        
        report = await detector.detect_regressions()
        
        assert len(report.regressions) > 0
        assert "latency" in str(report.regressions[0]["type"])


class TestSecurityTester:
    """Test the SecurityTester component"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_detection(self):
        """Test SQL injection vulnerability detection"""
        tester = SecurityTester()
        
        # Create temp file with SQL injection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('query = f"SELECT * FROM users WHERE id={user_id}"')
            temp_file = f.name
        
        try:
            report = await tester.scan_codebase([Path(temp_file).parent.as_posix()])
            
            assert report is not None
            # SQL injection pattern should be detected
        finally:
            Path(temp_file).unlink()
    
    @pytest.mark.asyncio
    async def test_hardcoded_secret_detection(self):
        """Test hardcoded secret detection"""
        tester = SecurityTester()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('api_key = "sk_live_51234567890"')
            temp_file = f.name
        
        try:
            report = await tester.scan_codebase([Path(temp_file).parent.as_posix()])
            
            assert report is not None
        finally:
            Path(temp_file).unlink()


class TestMutationTester:
    """Test the MutationTester component"""
    
    @pytest.mark.asyncio
    async def test_mutant_generation(self):
        """Test mutant generation"""
        tester = MutationTester()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
""")
            temp_file = f.name
        
        try:
            mutants = await tester.generate_mutants(temp_file, max_mutants=5)
            
            assert len(mutants) > 0
            assert mutants[0].mutation_type in MutationType
        finally:
            Path(temp_file).unlink()


class TestTestQualityScorer:
    """Test the TestQualityScorer component"""
    
    @pytest.mark.asyncio
    async def test_quality_scoring(self):
        """Test test quality scoring"""
        scorer = TestQualityScorer({"min_test_quality_score": 70})
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def test_example():
    # Arrange
    value = 42
    
    # Act
    result = value
    
    # Assert
    assert result == 42
""")
            temp_file = f.name
        
        try:
            results = await scorer.score_test_file(temp_file)
            
            assert len(results) > 0
            for test_id, metrics in results.items():
                assert isinstance(metrics.overall_score, float)
                assert 0 <= metrics.overall_score <= 100
        finally:
            Path(temp_file).unlink()


class TestFlakyTestDetector:
    """Test the FlakyTestDetector component"""
    
    def test_flakiness_detection(self):
        """Test flaky test detection logic"""
        detector = FlakyTestDetector({"num_runs": 3, "flakiness_threshold": 50})
        
        # Test pattern: fails intermittently
        # With 4 runs [T,F,T,F]: pass=2, fail=2, inconsistency=50%
        # flakiness_threshold=50 means we flag if inconsistency >= 50%
        results = [True, False, True, False]  # pass=2, fail=2 -> 50%
        
        is_flaky = detector._is_flaky(results, 4)
        
        assert is_flaky
    
    def test_consistent_tests(self):
        """Test that consistent tests are not flagged as flaky"""
        detector = FlakyTestDetector()
        
        # All pass
        assert not detector._is_flaky([True, True, True], 3)
        
        # All fail
        assert not detector._is_flaky([False, False, False], 3)


class TestDocumentationTester:
    """Test the DocumentationTester component"""
    
    @pytest.mark.asyncio
    async def test_extract_code_samples(self):
        """Test code sample extraction from documentation"""
        tester = DocumentationTester()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""
# Example

Here's a code example:

```python
print("Hello, World!")
```

End example.
""")
            temp_file = f.name
        
        try:
            samples = await tester.scan_documentation([temp_file])
            
            assert len(samples) > 0
            assert samples[0].language in ["python", "py"]
            assert "print" in samples[0].code
        finally:
            Path(temp_file).unlink()


class TestTestReporter:
    """Test the TestReporter component"""
    
    @pytest.mark.asyncio
    async def test_report_generation(self):
        """Test report generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"report_storage": tmpdir}
            reporter = TestReporter(config)
            
            test_results = {
                "total_tests": 10,
                "passed": 9,
                "failed": 1,
                "skipped": 0,
                "success_rate": 90.0,
                "duration": 5.0,
            }
            
            report = await reporter.generate_report(test_results)
            
            assert report is not None
            assert report.test_results == test_results


class TestTestCaseDataClass:
    """Test TestCase data structure"""
    
    def test_test_case_creation(self):
        """Test creating a TestCase"""
        test = TestCase(
            test_id="test_001",
            name="example_test",
            level=TestLevel.UNIT,
            file_path="tests/test_example.py"
        )
        
        assert test.test_id == "test_001"
        assert test.status == TestStatus.PENDING
        assert test.duration == 0.0
    
    def test_test_case_to_dict(self):
        """Test TestCase serialization"""
        test = TestCase(
            test_id="test_001",
            name="example_test",
            level=TestLevel.UNIT,
            file_path="tests/test_example.py"
        )
        
        data = test.to_dict()
        
        assert data["test_id"] == "test_001"
        assert data["status"] == "pending"


class TestIntegration:
    """Integration tests for the testing pipeline"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """Test executing the full testing pipeline"""
        executor = TestExecutor()
        
        # Register tests
        for i in range(3):
            await executor.register_test(
                f"test_{i:03d}",
                f"test_example_{i}",
                TestLevel.UNIT,
                "tests/test_example.py"
            )
        
        # Verify tests registered
        assert len(executor.tests) == 3
        
        # Run tests
        result = await executor.run_tests()
        
        assert result.total_tests == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
