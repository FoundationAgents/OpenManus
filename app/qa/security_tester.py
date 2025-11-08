"""
Security Testing

Comprehensive security scanning including:
- SAST (Static Application Security Testing)
- DAST (Dynamic Application Security Testing)
- Dependency vulnerability scanning
- Hardcoded secrets detection
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from app.logger import logger


class VulnerabilityType(str, Enum):
    """Types of vulnerabilities"""
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    XSS = "xss"
    XXE = "xxe"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    PATH_TRAVERSAL = "path_traversal"
    CSRF = "csrf"
    SSRF = "ssrf"
    DEPENDENCY_VULNERABILITY = "dependency_vulnerability"
    HARDCODED_CREDENTIAL = "hardcoded_credential"


class Severity(str, Enum):
    """Vulnerability severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Vulnerability:
    """Represents a security vulnerability"""
    id: str
    type: VulnerabilityType
    severity: Severity
    file_path: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    message: str = ""
    code_snippet: str = ""
    recommendation: str = ""
    cwe: Optional[str] = None  # Common Weakness Enumeration
    cvss_score: Optional[float] = None  # CVSS severity score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "cwe": self.cwe,
            "cvss_score": self.cvss_score,
        }


@dataclass
class SecurityScanReport:
    """Security scan report"""
    timestamp: datetime
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    scanned_files: int = 0
    dependencies_scanned: int = 0
    safe_to_deploy: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_vulnerabilities": len(self.vulnerabilities),
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "low": self.low_count,
            "scanned_files": self.scanned_files,
            "dependencies_scanned": self.dependencies_scanned,
            "safe_to_deploy": self.safe_to_deploy,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


class SecurityTester:
    """Perform comprehensive security testing"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.report: Optional[SecurityScanReport] = None
        
        # Configuration
        self.sast_enabled = self.config.get("sast_enabled", True)
        self.dast_enabled = self.config.get("dast_enabled", False)
        self.dependency_scan = self.config.get("dependency_scan", True)
        self.block_on_critical = self.config.get("block_on_critical", True)
        self.block_on_high = self.config.get("block_on_high", False)
        
        # Patterns for vulnerability detection
        self.vulnerability_patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize regex patterns for vulnerability detection"""
        return {
            VulnerabilityType.SQL_INJECTION: {
                "patterns": [
                    r"f['\"]SELECT.*{",  # f-string SQL
                    r"f['\"]INSERT.*{",
                    r"f['\"]UPDATE.*{",
                    r"f['\"]DELETE.*{",
                    r"\.format\(['\"].*SQL",
                    r"\%.*(SELECT|INSERT|UPDATE|DELETE)",
                    r"execute\(.*\+.*\)",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-89",
            },
            VulnerabilityType.COMMAND_INJECTION: {
                "patterns": [
                    r"subprocess\.(call|run|Popen)\(.*shell=True",
                    r"os\.system\(.*{",
                    r"os\.popen\(.*{",
                    r"eval\(",
                    r"exec\(",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-78",
            },
            VulnerabilityType.HARDCODED_SECRET: {
                "patterns": [
                    r"password\s*=\s*['\"].*['\"]",
                    r"api_key\s*=\s*['\"].*['\"]",
                    r"secret_key\s*=\s*['\"].*['\"]",
                    r"token\s*=\s*['\"].*['\"]",
                    r"credentials\s*=\s*['\"].*['\"]",
                    r"PRIVATE_KEY\s*=\s*['\"].*['\"]",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-798",
            },
            VulnerabilityType.WEAK_CRYPTO: {
                "patterns": [
                    r"md5\(",
                    r"sha1\(",
                    r"DES\(",
                    r"RC4\(",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-327",
            },
            VulnerabilityType.UNSAFE_DESERIALIZATION: {
                "patterns": [
                    r"pickle\.loads\(",
                    r"pickle\.load\(",
                    r"yaml\.load\(",
                    r"json\.loads\(.*\.decode",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-502",
            },
            VulnerabilityType.PATH_TRAVERSAL: {
                "patterns": [
                    r"open\(.*\.\.\s*\/",
                    r"join\(.*\.\.\s*\/",
                    r"file\(.*\.\.\s*\/",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-22",
            },
            VulnerabilityType.XXE: {
                "patterns": [
                    r"xml\.etree\.ElementTree\.parse\(.*defusedxml",
                    r"xml\.dom\.minidom\.parse\(",
                    r"lxml\.etree\.parse\(",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-611",
            },
        }
    
    async def scan_codebase(self, source_dirs: Optional[List[str]] = None) -> SecurityScanReport:
        """Perform SAST on codebase"""
        if source_dirs is None:
            source_dirs = ["app/"]
        
        vulnerabilities = []
        scanned_files = 0
        
        # Scan Python files
        for source_dir in source_dirs:
            path = Path(source_dir)
            if not path.exists():
                continue
            
            for py_file in path.rglob("*.py"):
                scanned_files += 1
                file_vulns = self._scan_file(py_file)
                vulnerabilities.extend(file_vulns)
        
        # Run bandit if available
        if self.sast_enabled:
            bandit_vulns = await self._run_bandit(source_dirs)
            vulnerabilities.extend(bandit_vulns)
        
        # Count by severity
        critical = sum(1 for v in vulnerabilities if v.severity == Severity.CRITICAL)
        high = sum(1 for v in vulnerabilities if v.severity == Severity.HIGH)
        medium = sum(1 for v in vulnerabilities if v.severity == Severity.MEDIUM)
        low = sum(1 for v in vulnerabilities if v.severity == Severity.LOW)
        
        # Create report
        safe_to_deploy = True
        if self.block_on_critical and critical > 0:
            safe_to_deploy = False
        if self.block_on_high and high > 0:
            safe_to_deploy = False
        
        self.report = SecurityScanReport(
            timestamp=datetime.now(),
            vulnerabilities=vulnerabilities,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            scanned_files=scanned_files,
            safe_to_deploy=safe_to_deploy,
        )
        
        return self.report
    
    def _scan_file(self, file_path: Path) -> List[Vulnerability]:
        """Scan a single Python file for vulnerabilities"""
        vulnerabilities = []
        
        try:
            with open(file_path) as f:
                lines = f.readlines()
            
            for line_no, line in enumerate(lines, 1):
                # Check each vulnerability type
                for vuln_type, pattern_info in self.vulnerability_patterns.items():
                    for pattern in pattern_info["patterns"]:
                        if re.search(pattern, line, re.IGNORECASE):
                            vulnerability = Vulnerability(
                                id=f"{file_path.name}_{line_no}_{vuln_type.value}",
                                type=vuln_type,
                                severity=pattern_info["severity"],
                                file_path=str(file_path),
                                line_number=line_no,
                                code_snippet=line.strip(),
                                message=f"Potential {vuln_type.value} detected",
                                cwe=pattern_info.get("cwe"),
                            )
                            vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
        
        return vulnerabilities
    
    async def _run_bandit(self, source_dirs: List[str]) -> List[Vulnerability]:
        """Run bandit security scanner if available"""
        vulnerabilities = []
        
        try:
            cmd = ["python", "-m", "bandit", "-r", "-f", "json"] + source_dirs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0 and result.stdout:
                data = json.loads(result.stdout)
                for result_item in data.get("results", []):
                    severity_map = {
                        "HIGH": Severity.HIGH,
                        "MEDIUM": Severity.MEDIUM,
                        "LOW": Severity.LOW,
                    }
                    
                    vulnerability = Vulnerability(
                        id=f"bandit_{result_item.get('test_id')}_{result_item.get('line_number')}",
                        type=VulnerabilityType.COMMAND_INJECTION,  # Default
                        severity=severity_map.get(result_item.get("severity"), Severity.MEDIUM),
                        file_path=result_item.get("filename", ""),
                        line_number=result_item.get("line_number"),
                        message=result_item.get("issue_text", ""),
                        code_snippet=result_item.get("test_code", ""),
                        cwe=result_item.get("cwe", {}).get("id"),
                    )
                    vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.debug(f"Bandit not available or failed: {e}")
        
        return vulnerabilities
    
    async def scan_dependencies(self) -> List[Vulnerability]:
        """Scan dependencies for known vulnerabilities"""
        vulnerabilities = []
        
        if not self.dependency_scan:
            return vulnerabilities
        
        try:
            # Try safety package
            cmd = ["python", "-m", "safety", "check", "--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.stdout:
                vulnerabilities_data = json.loads(result.stdout)
                for vuln in vulnerabilities_data:
                    vulnerability = Vulnerability(
                        id=f"dep_{vuln.get('id')}",
                        type=VulnerabilityType.DEPENDENCY_VULNERABILITY,
                        severity=Severity.HIGH,
                        file_path="requirements.txt",
                        message=vuln.get("advisory", ""),
                        code_snippet=vuln.get("package", ""),
                        recommendation=f"Update {vuln.get('package')} to {vuln.get('safe_version')}",
                    )
                    vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.debug(f"Dependency scan failed: {e}")
        
        return vulnerabilities
    
    async def fuzz_api_endpoints(self, base_url: str, endpoints: List[str]) -> List[Vulnerability]:
        """DAST: Fuzz API endpoints with common payloads"""
        if not self.dast_enabled:
            return []
        
        vulnerabilities = []
        
        # Common injection payloads
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "'; DELETE FROM users; --",
        ]
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints:
                    for payload in payloads:
                        try:
                            url = f"{base_url}{endpoint}"
                            async with session.get(url, params={"q": payload}, timeout=5) as response:
                                if response.status >= 400:
                                    # May indicate vulnerability
                                    vulnerability = Vulnerability(
                                        id=f"dast_{endpoint}_{hash(payload)}",
                                        type=VulnerabilityType.SQL_INJECTION,
                                        severity=Severity.MEDIUM,
                                        file_path=endpoint,
                                        message=f"Potential vulnerability with payload: {payload[:50]}",
                                    )
                                    vulnerabilities.append(vulnerability)
                        except:
                            pass
        
        except Exception as e:
            logger.warning(f"DAST fuzzing failed: {e}")
        
        return vulnerabilities
    
    def export_report(self, format: str = "json") -> str:
        """Export security report"""
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
        report.append("SECURITY SCAN REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Timestamp: {self.report.timestamp}")
        report.append(f"Files Scanned: {self.report.scanned_files}")
        report.append("")
        
        report.append("VULNERABILITY SUMMARY:")
        report.append(f"  Critical: {self.report.critical_count}")
        report.append(f"  High:     {self.report.high_count}")
        report.append(f"  Medium:   {self.report.medium_count}")
        report.append(f"  Low:      {self.report.low_count}")
        report.append("")
        
        if self.report.vulnerabilities:
            report.append("VULNERABILITIES:")
            for vuln in self.report.vulnerabilities:
                report.append(f"  [{vuln.severity.value.upper()}] {vuln.type.value}")
                report.append(f"    File: {vuln.file_path}:{vuln.line_number}")
                report.append(f"    Message: {vuln.message}")
                if vuln.recommendation:
                    report.append(f"    Fix: {vuln.recommendation}")
                report.append("")
        
        report.append(f"Safe to Deploy: {'YES' if self.report.safe_to_deploy else 'NO'}")
        report.append("=" * 80)
        
        return "\n".join(report)
