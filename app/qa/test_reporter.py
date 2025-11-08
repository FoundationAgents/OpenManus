"""
Test Reporter

Generates comprehensive test reports in multiple formats (HTML, JSON, JUnit).
Tracks trends and integrates with CI/CD.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from jinja2 import Template
from app.logger import logger


@dataclass
class TestReport:
    """Comprehensive test report"""
    timestamp: datetime
    test_results: Dict[str, Any]
    coverage_report: Optional[Dict[str, Any]] = None
    performance_report: Optional[Dict[str, Any]] = None
    security_report: Optional[Dict[str, Any]] = None
    mutation_report: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    flaky_report: Optional[Dict[str, Any]] = None
    git_commit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "test_results": self.test_results,
            "coverage": self.coverage_report,
            "performance": self.performance_report,
            "security": self.security_report,
            "mutation": self.mutation_report,
            "quality": self.quality_report,
            "flaky": self.flaky_report,
            "git_commit": self.git_commit,
        }


class TestReporter:
    """Generate test reports in various formats"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.report_storage = self.config.get("report_storage", "reports/test_reports")
        self.reports: List[TestReport] = []
        
        Path(self.report_storage).mkdir(parents=True, exist_ok=True)
    
    async def generate_report(
        self,
        test_results: Dict[str, Any],
        coverage_report: Optional[Dict[str, Any]] = None,
        performance_report: Optional[Dict[str, Any]] = None,
        security_report: Optional[Dict[str, Any]] = None,
        mutation_report: Optional[Dict[str, Any]] = None,
        quality_report: Optional[Dict[str, Any]] = None,
        flaky_report: Optional[Dict[str, Any]] = None,
    ) -> TestReport:
        """Generate comprehensive test report"""
        report = TestReport(
            timestamp=datetime.now(),
            test_results=test_results,
            coverage_report=coverage_report,
            performance_report=performance_report,
            security_report=security_report,
            mutation_report=mutation_report,
            quality_report=quality_report,
            flaky_report=flaky_report,
            git_commit=self._get_git_commit(),
        )
        
        self.reports.append(report)
        
        # Generate outputs
        await self._generate_html(report)
        await self._generate_json(report)
        await self._generate_junit(report)
        
        return report
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except:
            return None
    
    async def _generate_html(self, report: TestReport):
        """Generate HTML report"""
        try:
            html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #333; color: white; padding: 20px; border-radius: 5px; }
        .section { background: white; padding: 15px; margin: 15px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; width: 22%; margin: 1%; padding: 10px; background: #f9f9f9; border-left: 4px solid #007bff; }
        .passed { border-left-color: #28a745; }
        .failed { border-left-color: #dc3545; }
        .skipped { border-left-color: #6c757d; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f9f9f9; font-weight: bold; }
        .timestamp { color: #666; font-size: 0.9em; }
        .status-ok { color: #28a745; }
        .status-fail { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Test Report</h1>
        <p class="timestamp">Generated: {{ timestamp }}</p>
        {% if git_commit %}<p>Commit: {{ git_commit }}</p>{% endif %}
    </div>
    
    <div class="section">
        <h2>Test Results</h2>
        <div class="metric passed">
            <div><strong>{{ test_results.passed }}</strong></div>
            <div>Passed</div>
        </div>
        <div class="metric failed">
            <div><strong>{{ test_results.failed }}</strong></div>
            <div>Failed</div>
        </div>
        <div class="metric skipped">
            <div><strong>{{ test_results.skipped }}</strong></div>
            <div>Skipped</div>
        </div>
        <div class="metric">
            <div><strong>{{ test_results.success_rate }}%</strong></div>
            <div>Success Rate</div>
        </div>
    </div>
    
    {% if coverage_report %}
    <div class="section">
        <h2>Code Coverage</h2>
        <p>Overall Coverage: <strong>{{ coverage_report.total_line_coverage }}%</strong></p>
        {% if coverage_report.threshold_violations %}
        <p class="status-fail">⚠️ Threshold Violations:</p>
        <ul>
        {% for violation in coverage_report.threshold_violations %}
            <li>{{ violation.type }}: {{ violation.actual }}% (required: {{ violation.threshold }}%)</li>
        {% endfor %}
        </ul>
        {% else %}
        <p class="status-ok">✓ All coverage thresholds met</p>
        {% endif %}
    </div>
    {% endif %}
    
    {% if security_report %}
    <div class="section">
        <h2>Security Scan</h2>
        <p>Vulnerabilities: {{ security_report.total_vulnerabilities }}</p>
        <ul>
            <li>Critical: {{ security_report.critical }}</li>
            <li>High: {{ security_report.high }}</li>
            <li>Medium: {{ security_report.medium }}</li>
            <li>Low: {{ security_report.low }}</li>
        </ul>
        <p class="status-{% if security_report.safe_to_deploy %}ok{% else %}fail{% endif %}">
            Safe to Deploy: {% if security_report.safe_to_deploy %}✓ Yes{% else %}✗ No{% endif %}
        </p>
    </div>
    {% endif %}
    
    {% if performance_report %}
    <div class="section">
        <h2>Performance</h2>
        <p>Regressions Detected: {{ performance_report.regression_count }}</p>
        <p>Improvements: {{ performance_report.improvement_count }}</p>
    </div>
    {% endif %}
    
    {% if mutation_report %}
    <div class="section">
        <h2>Mutation Testing</h2>
        <p>Mutation Score: <strong>{{ mutation_report.mutation_score }}%</strong></p>
        <p>Killed Mutants: {{ mutation_report.killed_mutants }} / {{ mutation_report.total_mutants }}</p>
    </div>
    {% endif %}
    
    {% if quality_report %}
    <div class="section">
        <h2>Test Quality</h2>
        <p>Average Quality Score: {{ quality_report.average_score }}</p>
        <p>Tests Below Threshold: {{ quality_report.below_threshold }}</p>
    </div>
    {% endif %}
    
</body>
</html>
            """
            
            template = Template(html_template)
            html_content = template.render(
                timestamp=report.timestamp.isoformat(),
                test_results=report.test_results,
                coverage_report=report.coverage_report,
                security_report=report.security_report,
                performance_report=report.performance_report,
                mutation_report=report.mutation_report,
                quality_report=report.quality_report,
                git_commit=report.git_commit,
            )
            
            report_path = Path(self.report_storage) / f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.html"
            with open(report_path, "w") as f:
                f.write(html_content)
            
            logger.info(f"HTML report saved: {report_path}")
        
        except Exception as e:
            logger.warning(f"Failed to generate HTML report: {e}")
    
    async def _generate_json(self, report: TestReport):
        """Generate JSON report"""
        try:
            report_path = Path(self.report_storage) / f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
            
            logger.info(f"JSON report saved: {report_path}")
        
        except Exception as e:
            logger.warning(f"Failed to generate JSON report: {e}")
    
    async def _generate_junit(self, report: TestReport):
        """Generate JUnit format report"""
        try:
            junit_template = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="Test Suite" tests="{{ test_results.total_tests }}" failures="{{ test_results.failed }}" skipped="{{ test_results.skipped }}" time="{{ test_results.duration }}">
        <properties>
            <property name="timestamp" value="{{ timestamp }}"/>
            {% if git_commit %}<property name="git_commit" value="{{ git_commit }}"/>{% endif %}
        </properties>
        <!-- Test cases would go here -->
    </testsuite>
</testsuites>
            """
            
            template = Template(junit_template)
            junit_content = template.render(
                test_results=report.test_results,
                timestamp=report.timestamp.isoformat(),
                git_commit=report.git_commit,
            )
            
            report_path = Path(self.report_storage) / f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.xml"
            with open(report_path, "w") as f:
                f.write(junit_content)
            
            logger.info(f"JUnit report saved: {report_path}")
        
        except Exception as e:
            logger.warning(f"Failed to generate JUnit report: {e}")
    
    async def track_trend(self, metric_name: str, value: float):
        """Track metric trend over time"""
        trend_file = Path(self.report_storage) / "trends.json"
        
        try:
            if trend_file.exists():
                with open(trend_file) as f:
                    trends = json.load(f)
            else:
                trends = {}
            
            if metric_name not in trends:
                trends[metric_name] = []
            
            trends[metric_name].append({
                "timestamp": datetime.now().isoformat(),
                "value": value,
            })
            
            # Keep last 100 entries
            for key in trends:
                trends[key] = trends[key][-100:]
            
            with open(trend_file, "w") as f:
                json.dump(trends, f, indent=2)
        
        except Exception as e:
            logger.warning(f"Failed to track trend: {e}")
    
    def export_summary(self) -> Dict[str, Any]:
        """Export summary of all reports"""
        if not self.reports:
            return {}
        
        latest = self.reports[-1]
        
        return {
            "latest_report": latest.timestamp.isoformat(),
            "total_reports": len(self.reports),
            "git_commit": latest.git_commit,
            "test_stats": latest.test_results,
            "coverage": latest.coverage_report,
            "security": latest.security_report,
            "quality": latest.quality_report,
        }
