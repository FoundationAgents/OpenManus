"""
Flaky Test Detection

Detects and reports intermittent test failures.
Runs tests multiple times to identify flakiness causes.
"""

import json
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from app.logger import logger


class FlakinessCause(str, Enum):
    """Causes of test flakiness"""
    TIMING = "timing"              # Sleep/timeout not enough
    RANDOM_SEED = "random_seed"    # Non-deterministic random values
    EXTERNAL_SERVICE = "external_service"  # Dependency on external service
    CONCURRENCY = "concurrency"    # Race condition or threading issue
    ORDER_DEPENDENCY = "order_dependency"  # Depends on test execution order
    ENVIRONMENT = "environment"    # Environment-dependent
    RESOURCE = "resource"          # Resource exhaustion


@dataclass
class FlakyTestInfo:
    """Information about a flaky test"""
    test_name: str
    file_path: str
    num_runs: int
    pass_count: int
    fail_count: int
    pass_rate: float
    failure_pattern: str
    estimated_cause: Optional[FlakinessCause] = None
    recommendation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "file_path": self.file_path,
            "num_runs": self.num_runs,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "pass_rate": self.pass_rate,
            "failure_pattern": self.failure_pattern,
            "estimated_cause": self.estimated_cause.value if self.estimated_cause else None,
            "recommendation": self.recommendation,
        }


@dataclass
class FlakyTestReport:
    """Report of flaky tests"""
    timestamp: datetime
    total_tests_analyzed: int
    flaky_tests: List[FlakyTestInfo] = field(default_factory=list)
    non_flaky_tests: int = 0
    flakiness_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_tests": self.total_tests_analyzed,
            "flaky_count": len(self.flaky_tests),
            "non_flaky_count": self.non_flaky_tests,
            "flakiness_rate": self.flakiness_rate,
            "flaky_details": [t.to_dict() for t in self.flaky_tests],
        }


class FlakyTestDetector:
    """Detect flaky tests by running them multiple times"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.num_runs = self.config.get("num_runs", 3)
        self.flakiness_threshold = self.config.get("flakiness_threshold", 50)  # % inconsistency
        self.cache_location = self.config.get("cache_location", "cache/flaky_tests.json")
        self.report: Optional[FlakyTestReport] = None
        self.lock = threading.RLock()
        self._load_cache()
    
    def _load_cache(self):
        """Load cached flaky test results"""
        try:
            cache_path = Path(self.cache_location)
            if cache_path.exists():
                with open(cache_path) as f:
                    self._cached_flaky = json.load(f)
            else:
                self._cached_flaky = {}
        except Exception as e:
            logger.warning(f"Failed to load flaky test cache: {e}")
            self._cached_flaky = {}
    
    def _save_cache(self):
        """Save flaky test results to cache"""
        try:
            cache_path = Path(self.cache_location)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            cache_data = {
                test.test_name: test.to_dict()
                for test in (self.report.flaky_tests if self.report else [])
            }
            
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save flaky test cache: {e}")
    
    async def detect_flaky_tests(
        self,
        test_files: Optional[List[str]] = None,
        num_runs: Optional[int] = None,
    ) -> FlakyTestReport:
        """Detect flaky tests by running them multiple times"""
        num_runs = num_runs or self.num_runs
        flaky_tests = []
        non_flaky_count = 0
        
        if test_files is None:
            test_files = self._find_test_files()
        
        total_tests = 0
        
        for test_file in test_files:
            tests_in_file = self._extract_test_names(test_file)
            total_tests += len(tests_in_file)
            
            for test_name in tests_in_file:
                # Run test multiple times
                results = await self._run_test_multiple_times(
                    test_file,
                    test_name,
                    num_runs
                )
                
                # Analyze results
                if self._is_flaky(results, num_runs):
                    flaky_info = self._analyze_flakiness(test_file, test_name, results, num_runs)
                    flaky_tests.append(flaky_info)
                else:
                    non_flaky_count += 1
        
        # Create report
        flakiness_rate = (len(flaky_tests) / total_tests * 100) if total_tests > 0 else 0
        
        self.report = FlakyTestReport(
            timestamp=datetime.now(),
            total_tests_analyzed=total_tests,
            flaky_tests=flaky_tests,
            non_flaky_tests=non_flaky_count,
            flakiness_rate=flakiness_rate,
        )
        
        # Save results
        self._save_cache()
        
        return self.report
    
    def _find_test_files(self) -> List[str]:
        """Find all test files"""
        test_files = []
        test_dir = Path("tests")
        
        if test_dir.exists():
            test_files.extend(str(f) for f in test_dir.rglob("test_*.py"))
            test_files.extend(str(f) for f in test_dir.rglob("*_test.py"))
        
        return test_files
    
    def _extract_test_names(self, test_file: str) -> List[str]:
        """Extract test function names from file"""
        test_names = []
        
        try:
            with open(test_file) as f:
                for line in f:
                    if line.strip().startswith("def test_"):
                        test_name = line.split("def ")[1].split("(")[0]
                        test_names.append(test_name)
        except Exception as e:
            logger.warning(f"Failed to extract tests from {test_file}: {e}")
        
        return test_names
    
    async def _run_test_multiple_times(
        self,
        test_file: str,
        test_name: str,
        num_runs: int,
    ) -> List[bool]:
        """Run a test multiple times and collect results"""
        results = []
        
        for i in range(num_runs):
            try:
                # Run pytest for single test
                cmd = [
                    "python", "-m", "pytest",
                    f"{test_file}::{test_name}",
                    "-q", "--tb=no"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                # Test passed if return code is 0
                results.append(result.returncode == 0)
            
            except subprocess.TimeoutExpired:
                results.append(False)
            except Exception as e:
                logger.warning(f"Error running test {test_file}::{test_name}: {e}")
                results.append(False)
        
        return results
    
    def _is_flaky(self, results: List[bool], num_runs: int) -> bool:
        """Determine if test is flaky based on results"""
        pass_count = sum(results)
        fail_count = len(results) - pass_count
        
        # Test is flaky if it doesn't consistently pass or fail
        if pass_count > 0 and fail_count > 0:
            # Calculate inconsistency percentage
            inconsistency_rate = (min(pass_count, fail_count) / num_runs) * 100
            # Flaky if inconsistency rate is above threshold (e.g., 33% for 3 runs)
            return inconsistency_rate >= (100.0 - self.flakiness_threshold)
        
        return False
    
    def _analyze_flakiness(
        self,
        test_file: str,
        test_name: str,
        results: List[bool],
        num_runs: int,
    ) -> FlakyTestInfo:
        """Analyze flakiness pattern and estimate cause"""
        pass_count = sum(results)
        fail_count = num_runs - pass_count
        pass_rate = (pass_count / num_runs) * 100
        
        # Determine pattern
        if pass_count == num_runs:
            failure_pattern = "always_passes"
        elif fail_count == num_runs:
            failure_pattern = "always_fails"
        else:
            # Check for patterns
            if results == [True, False, True] or results == [False, True, False]:
                failure_pattern = "alternating"
            elif results.count(True) > results.count(False):
                failure_pattern = "mostly_passes"
            else:
                failure_pattern = "mostly_fails"
        
        # Estimate cause
        estimated_cause = self._estimate_cause(test_file, test_name)
        recommendation = self._get_recommendation(estimated_cause)
        
        flaky_info = FlakyTestInfo(
            test_name=test_name,
            file_path=test_file,
            num_runs=num_runs,
            pass_count=pass_count,
            fail_count=fail_count,
            pass_rate=pass_rate,
            failure_pattern=failure_pattern,
            estimated_cause=estimated_cause,
            recommendation=recommendation,
        )
        
        return flaky_info
    
    def _estimate_cause(self, test_file: str, test_name: str) -> Optional[FlakinessCause]:
        """Estimate the cause of flakiness"""
        try:
            with open(test_file) as f:
                source = f.read()
            
            # Look for indicators
            if "sleep(" in source or "time.sleep" in source:
                if test_name in source[source.find("def " + test_name):]:
                    return FlakinessCause.TIMING
            
            if "random" in source.lower():
                return FlakinessCause.RANDOM_SEED
            
            if "request" in source.lower() or "http" in source.lower():
                return FlakinessCause.EXTERNAL_SERVICE
            
            if "thread" in source.lower() or "lock" in source.lower():
                return FlakinessCause.CONCURRENCY
            
            if "global" in source or "static" in source:
                return FlakinessCause.ORDER_DEPENDENCY
        
        except Exception as e:
            logger.warning(f"Failed to estimate cause: {e}")
        
        return None
    
    def _get_recommendation(self, cause: Optional[FlakinessCause]) -> str:
        """Get recommendation based on estimated cause"""
        recommendations = {
            FlakinessCause.TIMING: "Increase sleep duration or use explicit wait conditions",
            FlakinessCause.RANDOM_SEED: "Set random seed in setUp or use fixed test data",
            FlakinessCause.EXTERNAL_SERVICE: "Mock/patch external service calls using unittest.mock",
            FlakinessCause.CONCURRENCY: "Use locks, queues, or explicit synchronization; avoid race conditions",
            FlakinessCause.ORDER_DEPENDENCY: "Ensure test is independent; use setUp/tearDown for state management",
            FlakinessCause.ENVIRONMENT: "Verify environment configuration; use isolation/containers",
            FlakinessCause.RESOURCE: "Check resource limits; reduce test scope or optimize",
        }
        
        return recommendations.get(cause, "Investigate test implementation for non-deterministic behavior")
    
    def get_flakiest_tests(self, limit: int = 10) -> List[FlakyTestInfo]:
        """Get most flaky tests (lowest pass rate)"""
        if not self.report:
            return []
        
        return sorted(
            self.report.flaky_tests,
            key=lambda t: t.pass_rate
        )[:limit]
    
    def export_report(self, format: str = "json") -> str:
        """Export flaky test report"""
        if not self.report:
            return "{}"
        
        if format == "json":
            return json.dumps(self.report.to_dict(), indent=2)
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        if not self.report:
            return ""
        
        report = ["=" * 80]
        report.append("FLAKY TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Tests Analyzed: {self.report.total_tests_analyzed}")
        report.append(f"Flaky Tests: {len(self.report.flaky_tests)}")
        report.append(f"Overall Flakiness Rate: {self.report.flakiness_rate:.1f}%")
        report.append("")
        
        if self.report.flaky_tests:
            report.append("FLAKY TESTS DETECTED:")
            for flaky in sorted(self.report.flaky_tests, key=lambda t: t.pass_rate):
                report.append(f"  {flaky.test_name}")
                report.append(f"    Pass Rate: {flaky.pass_rate:.1f}% ({flaky.pass_count}/{flaky.num_runs})")
                report.append(f"    Pattern: {flaky.failure_pattern}")
                if flaky.estimated_cause:
                    report.append(f"    Estimated Cause: {flaky.estimated_cause.value}")
                report.append(f"    Recommendation: {flaky.recommendation}")
                report.append("")
        else:
            report.append("No flaky tests detected!")
        
        report.append("=" * 80)
        
        return "\n".join(report)
