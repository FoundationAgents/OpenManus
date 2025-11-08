"""
Test Execution Pipeline

Orchestrates test runs with dependency ordering, parallel execution,
timeout management, and comprehensive failure capture.
"""

import asyncio
import subprocess
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from app.logger import logger


class TestLevel(str, Enum):
    """Test execution levels"""
    SMOKE = "smoke"           # 5 min: Basic functionality
    UNIT = "unit"             # 15 min: Component-level
    INTEGRATION = "integration"  # 30 min: Cross-component
    E2E = "e2e"                # 45 min: Full workflow
    PERFORMANCE = "performance"  # 60 min: Benchmarks
    SECURITY = "security"      # 20 min: Vulnerability scan


class TestStatus(str, Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestCase:
    """Represents a single test case"""
    test_id: str
    name: str
    level: TestLevel
    file_path: str
    timeout: int = 30
    dependencies: List[str] = field(default_factory=list)
    status: TestStatus = TestStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "level": self.level.value,
            "file_path": self.file_path,
            "timeout": self.timeout,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "error_message": self.error_message,
            "duration": self.duration,
            "retries": self.retries,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class TestRunResult:
    """Results from a test run"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    timeout: int
    start_time: datetime
    end_time: datetime
    duration: float
    coverage_percentage: float = 0.0
    coverage_details: Dict[str, Any] = field(default_factory=dict)
    test_results: List[TestCase] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    security_findings: List[Dict[str, Any]] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "timeout": self.timeout,
            "duration": self.duration,
            "success_rate": self.success_rate(),
            "coverage_percentage": self.coverage_percentage,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "test_results": [t.to_dict() for t in self.test_results],
            "performance_metrics": self.performance_metrics,
            "security_findings": self.security_findings,
            "coverage_details": self.coverage_details,
        }


class TestExecutor:
    """Orchestrates test execution with dependency management and parallelization"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tests: Dict[str, TestCase] = {}
        self.results: Optional[TestRunResult] = None
        self.lock = threading.RLock()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.parallel_workers = self.config.get("parallel_workers", 4)
        self.base_timeout = self.config.get("timeout_per_test", 30)
        self.retry_enabled = self.config.get("retry_flaky", True)
        self.max_retries = self.config.get("retry_count", 2)
        
        # Test timeouts by level
        self.level_timeouts = self.config.get("timeout_per_level", {
            "smoke": 300,
            "unit": 900,
            "integration": 1800,
            "e2e": 2700,
            "performance": 3600,
            "security": 1200,
        })
    
    async def register_test(
        self,
        test_id: str,
        name: str,
        level: TestLevel,
        file_path: str,
        dependencies: Optional[List[str]] = None,
    ) -> TestCase:
        """Register a test case"""
        timeout = self.level_timeouts.get(level.value, self.base_timeout)
        
        test = TestCase(
            test_id=test_id,
            name=name,
            level=level,
            file_path=file_path,
            timeout=timeout,
            dependencies=dependencies or [],
            max_retries=self.max_retries if self.retry_enabled else 0,
        )
        
        with self.lock:
            self.tests[test_id] = test
        
        return test
    
    async def execute_test(self, test: TestCase) -> TestCase:
        """Execute a single test with timeout and output capture"""
        test.started_at = datetime.now()
        test.status = TestStatus.RUNNING
        
        try:
            # Build pytest command
            cmd = [
                "python", "-m", "pytest",
                test.file_path,
                "-v",
                "--tb=short",
                f"--timeout={test.timeout}",
            ]
            
            # Run test
            start_time = time.time()
            result = await self._run_subprocess(cmd, timeout=test.timeout + 5)
            test.duration = time.time() - start_time
            
            # Parse result
            if result["returncode"] == 0:
                test.status = TestStatus.PASSED
            else:
                test.status = TestStatus.FAILED
                test.error_message = result.get("stderr", "")
            
            test.stdout = result.get("stdout", "")
            test.stderr = result.get("stderr", "")
            
        except asyncio.TimeoutError:
            test.status = TestStatus.TIMEOUT
            test.error_message = f"Test timeout after {test.timeout} seconds"
            test.duration = test.timeout
            
            # Retry on timeout if enabled
            if test.retries < test.max_retries and self.retry_enabled:
                test.retries += 1
                logger.warning(f"Test {test.test_id} timed out, retrying ({test.retries}/{test.max_retries})")
                return await self.execute_test(test)
        
        except Exception as e:
            test.status = TestStatus.FAILED
            test.error_message = f"Execution error: {str(e)}"
            test.duration = time.time() - start_time if 'start_time' in locals() else 0
        
        finally:
            test.completed_at = datetime.now()
        
        return test
    
    async def _run_subprocess(
        self,
        cmd: List[str],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Run subprocess with timeout and output capture"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        
        except asyncio.TimeoutError:
            if process:
                process.kill()
                try:
                    await process.wait()
                except:
                    pass
            raise
    
    def _topological_sort(self, tests: Dict[str, TestCase]) -> List[TestCase]:
        """Sort tests by dependencies using topological sort"""
        sorted_tests = []
        visited = set()
        visiting = set()
        
        def visit(test_id: str):
            if test_id in visited:
                return
            if test_id in visiting:
                logger.warning(f"Circular dependency detected involving {test_id}")
                return
            
            visiting.add(test_id)
            test = tests.get(test_id)
            if test:
                for dep_id in test.dependencies:
                    if dep_id in tests:
                        visit(dep_id)
            visiting.remove(test_id)
            visited.add(test_id)
            if test:
                sorted_tests.append(test)
        
        for test_id in tests:
            visit(test_id)
        
        return sorted_tests
    
    async def run_tests(
        self,
        levels: Optional[List[TestLevel]] = None,
        parallel: bool = True,
    ) -> TestRunResult:
        """Execute all registered tests"""
        start_time = datetime.now()
        
        # Filter tests by level
        if levels:
            tests_to_run = {
                tid: t for tid, t in self.tests.items()
                if t.level in levels
            }
        else:
            tests_to_run = self.tests
        
        if not tests_to_run:
            logger.warning("No tests to run")
            return TestRunResult(
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                timeout=0,
                start_time=start_time,
                end_time=datetime.now(),
                duration=0,
            )
        
        # Sort by dependencies
        sorted_tests = self._topological_sort(tests_to_run)
        
        # Execute tests
        if parallel:
            await self._execute_parallel(sorted_tests)
        else:
            await self._execute_sequential(sorted_tests)
        
        # Compile results
        end_time = datetime.now()
        passed = sum(1 for t in self.tests.values() if t.status == TestStatus.PASSED)
        failed = sum(1 for t in self.tests.values() if t.status == TestStatus.FAILED)
        skipped = sum(1 for t in self.tests.values() if t.status == TestStatus.SKIPPED)
        timeout = sum(1 for t in self.tests.values() if t.status == TestStatus.TIMEOUT)
        
        self.results = TestRunResult(
            total_tests=len(self.tests),
            passed=passed,
            failed=failed,
            skipped=skipped,
            timeout=timeout,
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time).total_seconds(),
            test_results=list(self.tests.values()),
        )
        
        return self.results
    
    async def _execute_sequential(self, tests: List[TestCase]):
        """Execute tests sequentially"""
        for test in tests:
            await self.execute_test(test)
    
    async def _execute_parallel(self, tests: List[TestCase]):
        """Execute tests in parallel with worker limit"""
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def run_with_semaphore(test: TestCase):
            async with semaphore:
                await self.execute_test(test)
        
        tasks = [run_with_semaphore(t) for t in tests]
        await asyncio.gather(*tasks)
    
    def get_test_results(self, test_id: str) -> Optional[TestCase]:
        """Get results for a specific test"""
        with self.lock:
            return self.tests.get(test_id)
    
    def get_failed_tests(self) -> List[TestCase]:
        """Get all failed tests"""
        with self.lock:
            return [t for t in self.tests.values() if t.status == TestStatus.FAILED]
    
    def get_flaky_tests(self) -> List[TestCase]:
        """Get tests that have been retried"""
        with self.lock:
            return [t for t in self.tests.values() if t.retries > 0]
    
    def export_results(self, format: str = "json") -> str:
        """Export test results in various formats"""
        if not self.results:
            return "{}"
        
        if format == "json":
            return json.dumps(self.results.to_dict(), indent=2)
        else:
            return str(self.results)
