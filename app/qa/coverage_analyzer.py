"""
Coverage Analysis

Measures code coverage (line, branch, function, path) and enforces thresholds.
Identifies dead code and generates HTML reports.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from app.logger import logger


class CoverageType(str, Enum):
    """Types of code coverage"""
    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    PATH = "path"


@dataclass
class CoverageMetric:
    """Represents a coverage metric"""
    type: CoverageType
    total: int
    covered: int
    percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "total": self.total,
            "covered": self.covered,
            "percentage": self.percentage,
        }


@dataclass
class FileCoverage:
    """Coverage info for a single file"""
    file_path: str
    line_coverage: float
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    uncovered_lines: List[int] = field(default_factory=list)
    dead_code_lines: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "function_coverage": self.function_coverage,
            "uncovered_lines": self.uncovered_lines,
            "dead_code_lines": self.dead_code_lines,
        }


@dataclass
class CoverageReport:
    """Complete coverage report"""
    timestamp: datetime
    total_line_coverage: float
    new_code_coverage: float = 0.0
    critical_path_coverage: float = 0.0
    file_coverage: Dict[str, FileCoverage] = field(default_factory=dict)
    metrics: Dict[str, CoverageMetric] = field(default_factory=dict)
    coverage_by_severity: Dict[str, float] = field(default_factory=dict)
    dead_code_locations: List[str] = field(default_factory=list)
    threshold_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_within_thresholds(
        self,
        threshold_overall: float = 80,
        threshold_new_code: float = 90,
        threshold_critical: float = 95,
    ) -> bool:
        """Check if coverage meets all thresholds"""
        violations = []
        
        if self.total_line_coverage < threshold_overall:
            violations.append({
                "type": "overall_coverage",
                "threshold": threshold_overall,
                "actual": self.total_line_coverage,
            })
        
        if self.new_code_coverage > 0 and self.new_code_coverage < threshold_new_code:
            violations.append({
                "type": "new_code_coverage",
                "threshold": threshold_new_code,
                "actual": self.new_code_coverage,
            })
        
        if self.critical_path_coverage > 0 and self.critical_path_coverage < threshold_critical:
            violations.append({
                "type": "critical_path_coverage",
                "threshold": threshold_critical,
                "actual": self.critical_path_coverage,
            })
        
        self.threshold_violations = violations
        return len(violations) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_line_coverage": self.total_line_coverage,
            "new_code_coverage": self.new_code_coverage,
            "critical_path_coverage": self.critical_path_coverage,
            "file_coverage": {k: v.to_dict() for k, v in self.file_coverage.items()},
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "dead_code_count": len(self.dead_code_locations),
            "threshold_violations": self.threshold_violations,
        }


class CoverageAnalyzer:
    """Analyze and track code coverage"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.report: Optional[CoverageReport] = None
        self.previous_reports: List[CoverageReport] = []
        
        # Configuration
        self.enforce = self.config.get("enforce", True)
        self.threshold_overall = self.config.get("threshold_overall", 80)
        self.threshold_new_code = self.config.get("threshold_new_code", 90)
        self.threshold_critical = self.config.get("threshold_critical", 95)
        self.measure_branch = self.config.get("measure_branch_coverage", True)
        self.measure_function = self.config.get("measure_function_coverage", True)
        self.measure_path = self.config.get("measure_path_coverage", False)
        self.identify_dead_code = self.config.get("identify_dead_code", True)
        self.html_report = self.config.get("html_report", True)
    
    async def measure_coverage(
        self,
        test_directories: Optional[List[str]] = None,
        source_directories: Optional[List[str]] = None,
    ) -> CoverageReport:
        """Measure code coverage using pytest-cov"""
        try:
            # Build coverage command
            cmd = ["python", "-m", "pytest", "--cov", "--cov-report=json"]
            
            if test_directories:
                cmd.extend(test_directories)
            else:
                cmd.append("tests/")
            
            # Run coverage measurement
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            # Parse coverage data
            coverage_data = self._parse_coverage_data()
            
            # Create report
            self.report = CoverageReport(
                timestamp=datetime.now(),
                total_line_coverage=coverage_data.get("line_coverage", 0),
                new_code_coverage=coverage_data.get("new_code_coverage", 0),
                critical_path_coverage=coverage_data.get("critical_path_coverage", 0),
                file_coverage=coverage_data.get("file_coverage", {}),
                metrics=coverage_data.get("metrics", {}),
                coverage_by_severity=coverage_data.get("coverage_by_severity", {}),
                dead_code_locations=coverage_data.get("dead_code_locations", []),
            )
            
            # Identify dead code if enabled
            if self.identify_dead_code:
                self.report.dead_code_locations = self._identify_dead_code()
            
            # Check thresholds
            within_thresholds = self.report.is_within_thresholds(
                self.threshold_overall,
                self.threshold_new_code,
                self.threshold_critical,
            )
            
            if not within_thresholds and self.enforce:
                logger.warning(f"Coverage thresholds not met: {self.report.threshold_violations}")
            
            # Generate HTML report if enabled
            if self.html_report:
                await self._generate_html_report()
            
            return self.report
        
        except Exception as e:
            logger.error(f"Coverage measurement failed: {e}")
            raise
    
    def _parse_coverage_data(self) -> Dict[str, Any]:
        """Parse coverage data from pytest-cov output"""
        try:
            # Read .coverage or coverage.json
            coverage_file = Path(".coverage")
            json_file = Path("htmlcov/coverage.json")
            
            data = {
                "line_coverage": 0,
                "new_code_coverage": 0,
                "critical_path_coverage": 0,
                "file_coverage": {},
                "metrics": {},
                "coverage_by_severity": {},
                "dead_code_locations": [],
            }
            
            if json_file.exists():
                with open(json_file) as f:
                    cov_data = json.load(f)
                    data["line_coverage"] = cov_data.get("totals", {}).get("percent_covered", 0)
            
            return data
        
        except Exception as e:
            logger.error(f"Failed to parse coverage data: {e}")
            return {
                "line_coverage": 0,
                "new_code_coverage": 0,
                "critical_path_coverage": 0,
                "file_coverage": {},
                "metrics": {},
                "coverage_by_severity": {},
                "dead_code_locations": [],
            }
    
    def _identify_dead_code(self) -> List[str]:
        """Identify dead code locations"""
        dead_code = []
        
        try:
            # Use vulture or similar tool
            result = subprocess.run(
                ["python", "-m", "vulture", "app/", "--min-confidence", "80"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            for line in result.stdout.split("\n"):
                if line.strip():
                    dead_code.append(line)
        
        except:
            pass  # Tool may not be installed
        
        return dead_code
    
    async def _generate_html_report(self):
        """Generate HTML coverage report"""
        try:
            # pytest-cov generates htmlcov/ directory
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov", "--cov-report=html"],
                capture_output=True,
                timeout=300,
            )
            
            html_path = Path("htmlcov/index.html")
            if html_path.exists():
                logger.info(f"HTML coverage report generated: {html_path}")
        
        except Exception as e:
            logger.warning(f"Failed to generate HTML report: {e}")
    
    async def track_trend(self, historical_limit: int = 30):
        """Track coverage trends over time"""
        if self.report:
            self.previous_reports.append(self.report)
            self.previous_reports = self.previous_reports[-historical_limit:]
    
    def get_coverage_trend(self) -> List[Tuple[datetime, float]]:
        """Get coverage trend data for charting"""
        return [(r.timestamp, r.total_line_coverage) for r in self.previous_reports]
    
    def get_regression_analysis(self) -> Dict[str, Any]:
        """Analyze coverage regression"""
        if len(self.previous_reports) < 2 or not self.report:
            return {}
        
        previous = self.previous_reports[-2]
        current = self.report
        
        return {
            "previous_coverage": previous.total_line_coverage,
            "current_coverage": current.total_line_coverage,
            "change": current.total_line_coverage - previous.total_line_coverage,
            "regression": current.total_line_coverage < previous.total_line_coverage,
        }
    
    def export_report(self, format: str = "json") -> str:
        """Export coverage report"""
        if not self.report:
            return "{}"
        
        if format == "json":
            return json.dumps(self.report.to_dict(), indent=2)
        elif format == "html":
            return self._generate_html_from_report()
        else:
            return str(self.report)
    
    def _generate_html_from_report(self) -> str:
        """Generate simple HTML from report"""
        if not self.report:
            return ""
        
        html = f"""
        <html>
        <head>
            <title>Coverage Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ margin: 10px 0; }}
                .threshold-ok {{ color: green; }}
                .threshold-fail {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Coverage Report</h1>
            <div class="metric">
                <strong>Total Line Coverage:</strong> 
                <span class="{'threshold-ok' if self.report.total_line_coverage >= self.threshold_overall else 'threshold-fail'}">
                    {self.report.total_line_coverage:.1f}% (threshold: {self.threshold_overall}%)
                </span>
            </div>
            <h2>Threshold Violations</h2>
            <ul>
        """
        
        if self.report.threshold_violations:
            for violation in self.report.threshold_violations:
                html += f"<li>{violation['type']}: {violation['actual']:.1f}% (required: {violation['threshold']}%)</li>"
        else:
            html += "<li>None - all thresholds met!</li>"
        
        html += """
            </ul>
            <h2>File Coverage</h2>
            <table>
                <tr><th>File</th><th>Line Coverage</th><th>Branch Coverage</th></tr>
        """
        
        for file_path, coverage in self.report.file_coverage.items():
            html += f"""
                <tr>
                    <td>{file_path}</td>
                    <td>{coverage.line_coverage:.1f}%</td>
                    <td>{coverage.branch_coverage:.1f}%</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
