"""
Documentation Testing

Extracts code samples from documentation and verifies they work correctly.
Detects mismatches between documentation and actual API.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from app.logger import logger


@dataclass
class CodeSample:
    """A code sample from documentation"""
    doc_file: str
    line_number: int
    language: str
    code: str
    expected_output: Optional[str] = None


@dataclass
class DocTestResult:
    """Result of testing a code sample"""
    sample: CodeSample
    passed: bool
    error: Optional[str] = None
    actual_output: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_file": self.sample.doc_file,
            "line": self.sample.line_number,
            "language": self.sample.language,
            "passed": self.passed,
            "error": self.error,
            "execution_time": self.execution_time,
        }


@dataclass
class DocTestReport:
    """Report of documentation tests"""
    timestamp: datetime
    total_samples: int
    passed_samples: int
    failed_samples: int
    results: List[DocTestResult] = field(default_factory=list)
    api_mismatches: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total": self.total_samples,
            "passed": self.passed_samples,
            "failed": self.failed_samples,
            "success_rate": (self.passed_samples / self.total_samples * 100) if self.total_samples > 0 else 0,
            "mismatches": self.api_mismatches,
            "results": [r.to_dict() for r in self.results],
        }


class DocumentationTester:
    """Test code samples in documentation"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.test_code_samples = self.config.get("test_code_samples", True)
        self.verify_api_docs = self.config.get("verify_api_docs", True)
        self.report_mismatches = self.config.get("report_mismatches", True)
    
    async def scan_documentation(self, doc_dirs: Optional[List[str]] = None) -> List[CodeSample]:
        """Extract code samples from documentation"""
        if doc_dirs is None:
            doc_dirs = ["docs/", "README.md"]
        
        samples = []
        
        for doc_path in doc_dirs:
            doc_path_obj = Path(doc_path)
            
            if doc_path_obj.is_file():
                extracted = self._extract_samples_from_file(doc_path)
                samples.extend(extracted)
            elif doc_path_obj.is_dir():
                for md_file in doc_path_obj.rglob("*.md"):
                    extracted = self._extract_samples_from_file(str(md_file))
                    samples.extend(extracted)
        
        return samples
    
    def _extract_samples_from_file(self, file_path: str) -> List[CodeSample]:
        """Extract code samples from a single file"""
        samples = []
        
        try:
            with open(file_path) as f:
                lines = f.readlines()
            
            current_block = None
            language = None
            code_lines = []
            start_line = 0
            
            for i, line in enumerate(lines, 1):
                # Detect code block start
                if line.strip().startswith("```"):
                    if current_block is None:
                        # Start of code block
                        match = re.search(r"```(\w+)?", line)
                        language = match.group(1) if match else "python"
                        current_block = i
                        start_line = i
                        code_lines = []
                    else:
                        # End of code block
                        code = "\n".join(code_lines).strip()
                        if code and language in ["python", "py"]:
                            sample = CodeSample(
                                doc_file=file_path,
                                line_number=start_line,
                                language=language,
                                code=code,
                            )
                            samples.append(sample)
                        current_block = None
                
                elif current_block is not None:
                    code_lines.append(line.rstrip())
        
        except Exception as e:
            logger.warning(f"Failed to extract samples from {file_path}: {e}")
        
        return samples
    
    async def test_samples(self, samples: List[CodeSample]) -> DocTestReport:
        """Test all code samples"""
        results = []
        passed = 0
        failed = 0
        
        for sample in samples:
            try:
                result = await self._test_sample(sample)
                results.append(result)
                
                if result.passed:
                    passed += 1
                else:
                    failed += 1
            
            except Exception as e:
                result = DocTestResult(
                    sample=sample,
                    passed=False,
                    error=str(e),
                )
                results.append(result)
                failed += 1
        
        # Detect API mismatches
        mismatches = await self._detect_api_mismatches(results)
        
        report = DocTestReport(
            timestamp=datetime.now(),
            total_samples=len(samples),
            passed_samples=passed,
            failed_samples=failed,
            results=results,
            api_mismatches=mismatches,
        )
        
        return report
    
    async def _test_sample(self, sample: CodeSample) -> DocTestResult:
        """Test a single code sample"""
        import time
        
        try:
            start_time = time.time()
            
            # Create temp file for sample
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(sample.code)
                temp_file = f.name
            
            try:
                # Execute sample
                result = subprocess.run(
                    ["python", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                execution_time = time.time() - start_time
                
                if result.returncode == 0:
                    return DocTestResult(
                        sample=sample,
                        passed=True,
                        actual_output=result.stdout,
                        execution_time=execution_time,
                    )
                else:
                    return DocTestResult(
                        sample=sample,
                        passed=False,
                        error=result.stderr,
                        execution_time=execution_time,
                    )
            
            finally:
                Path(temp_file).unlink()
        
        except subprocess.TimeoutExpired:
            return DocTestResult(
                sample=sample,
                passed=False,
                error="Execution timeout",
            )
        
        except Exception as e:
            return DocTestResult(
                sample=sample,
                passed=False,
                error=str(e),
            )
    
    async def _detect_api_mismatches(self, results: List[DocTestResult]) -> List[str]:
        """Detect mismatches between documentation and actual API"""
        mismatches = []
        
        if not self.verify_api_docs:
            return mismatches
        
        for result in results:
            if not result.passed and result.error:
                # Common API mismatch patterns
                if "AttributeError" in result.error or "ImportError" in result.error:
                    # Extract function/class name from error
                    match = re.search(r"'(\w+)'", result.error)
                    if match:
                        mismatches.append(f"Missing API: {match.group(1)}")
                
                if "TypeError" in result.error:
                    match = re.search(r"TypeError: (.+)", result.error)
                    if match:
                        mismatches.append(f"API signature mismatch: {match.group(1)}")
        
        return list(set(mismatches))  # Remove duplicates
    
    async def generate_docs_update_suggestions(self, report: DocTestReport) -> Dict[str, Any]:
        """Generate suggestions for documentation updates"""
        suggestions = {
            "files_to_update": [],
            "common_issues": [],
            "recommendations": [],
        }
        
        # Group failures by file
        failures_by_file = {}
        for result in report.results:
            if not result.passed:
                file_path = result.sample.doc_file
                if file_path not in failures_by_file:
                    failures_by_file[file_path] = []
                failures_by_file[file_path].append(result)
        
        suggestions["files_to_update"] = list(failures_by_file.keys())
        
        # Identify common issues
        error_counts = {}
        for result in report.results:
            if result.error:
                error_type = result.error.split(":")[0]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        suggestions["common_issues"] = [
            f"{error_type}: {count} occurrences"
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Generate recommendations
        if report.failed_samples > 0:
            failure_rate = (report.failed_samples / report.total_samples) * 100
            if failure_rate > 50:
                suggestions["recommendations"].append(
                    f"High failure rate ({failure_rate:.1f}%) - comprehensive documentation review recommended"
                )
            elif failure_rate > 20:
                suggestions["recommendations"].append(
                    f"Moderate failure rate ({failure_rate:.1f}%) - update outdated code samples"
                )
        
        if report.api_mismatches:
            suggestions["recommendations"].append(
                f"API mismatches detected: {', '.join(report.api_mismatches[:3])}"
            )
        
        return suggestions
    
    def export_report(self, report: DocTestReport, format: str = "json") -> str:
        """Export documentation test report"""
        if format == "json":
            return json.dumps(report.to_dict(), indent=2)
        else:
            return self._generate_text_report(report)
    
    def _generate_text_report(self, report: DocTestReport) -> str:
        """Generate text format report"""
        text = ["=" * 80]
        text.append("DOCUMENTATION TEST REPORT")
        text.append("=" * 80)
        text.append("")
        
        text.append("SUMMARY:")
        text.append(f"  Total Code Samples: {report.total_samples}")
        text.append(f"  Passed: {report.passed_samples}")
        text.append(f"  Failed: {report.failed_samples}")
        if report.total_samples > 0:
            success_rate = (report.passed_samples / report.total_samples) * 100
            text.append(f"  Success Rate: {success_rate:.1f}%")
        text.append("")
        
        if report.failed_samples > 0:
            text.append("FAILED SAMPLES:")
            for result in report.results:
                if not result.passed:
                    text.append(f"  {result.sample.doc_file}:{result.sample.line_number}")
                    if result.error:
                        text.append(f"    Error: {result.error.split(chr(10))[0]}")
            text.append("")
        
        if report.api_mismatches:
            text.append("API MISMATCHES:")
            for mismatch in report.api_mismatches:
                text.append(f"  - {mismatch}")
            text.append("")
        
        text.append("=" * 80)
        return "\n".join(text)
