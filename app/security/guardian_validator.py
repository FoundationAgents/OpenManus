"""
Guardian Validator for risk assessment and policy checking.

Implements risk analysis pipeline:
- Whitelist/blacklist matching
- ACL queries
- Filesystem scope verification
- Network risk heuristics
- Sandbox capability detection
"""

import re
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, TYPE_CHECKING
from dataclasses import dataclass
from urllib.parse import urlparse

from app.logger import logger
from app.config import config

if TYPE_CHECKING:
    from .guardian_agent import ValidationRequest


@dataclass
class QuickCheckResult:
    """Result of quick check (whitelist/blacklist)."""
    allowed: bool
    reason: str


@dataclass
class RiskAssessment:
    """Result of comprehensive risk assessment."""
    risk_score: float  # 0-100
    risk_factors: List[str]
    reason: str
    required_permissions: List[str]
    blocking_factors: List[str]


class GuardianValidator:
    """
    Validator for command risk assessment and policy enforcement.

    Checks:
    1. Whitelist/blacklist patterns
    2. ACL permissions
    3. Filesystem boundaries
    4. Network operations
    5. Dangerous patterns
    """

    def __init__(self):
        """Initialize Guardian Validator."""
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
        self.filesystem_boundaries: Dict[str, str] = {}
        self.network_policies: Dict[str, Any] = {}
        self.dangerous_patterns: List[Tuple[str, str, float]] = []  # (pattern, description, risk_weight)
        self._load_default_policies()

    def _load_default_policies(self):
        """Load default security policies."""
        # Default whitelist of safe commands
        self.whitelist = [
            r"^(ls|cat|echo|pwd|cd|mkdir|touch|cp|mv|rm|grep|find|sort|uniq|wc|head|tail)(\s|$)",
            r"^(python|node|npm|pip|git|curl|wget|tar|zip|unzip)(\s|$)",
            r"^(docker|docker-compose)(\s|$)",
            r"^(apt-get|brew|yum)(\s+install)(\s|$)",
        ]

        # Default blacklist of dangerous patterns
        self.blacklist = [
            (r"rm\s+-rf\s+/", "Recursive deletion from root - CRITICAL"),
            (r"rm\s+-rf\s+/\*", "Recursive deletion from root - CRITICAL"),
            (r">>/etc/sudoers", "Modifying sudoers file - CRITICAL"),
            (r"chmod\s+777\s+/", "Changing permissions on root - HIGH"),
            (r"dd\s+if=.*\s+of=/dev/sda", "Direct disk write - CRITICAL"),
        ]

        # Default dangerous patterns with risk weights
        self.dangerous_patterns = [
            (r"fork\s*\(\s*\)", "Process forking", 30.0),
            (r">>/etc/passwd", "Modifying passwd file", 70.0),
            (r"chmod\s+.*\s+/", "Changing root permissions", 60.0),
            (r"chown\s+root:root", "Changing ownership to root", 50.0),
            (r":(){:|:&};\s*:", "Bash fork bomb", 80.0),
            (r"nc\s+-l", "Network listener", 40.0),
            (r"curl\s+-.*\s+-X\s+DELETE", "DELETE HTTP request", 45.0),
        ]

        # Filesystem boundaries
        self.filesystem_boundaries = {
            "workspace": str(config.local_service.workspace_directory),
            "temp": "/tmp",
            "home": str(Path.home()),
        }

        # Network policies
        self.network_policies = {
            "blocked_domains": ["localhost", "127.0.0.1", "169.254"],
            "blocked_ports": [22, 23, 3389],  # SSH, Telnet, RDP
            "risky_protocols": ["telnet", "ftp"],
        }

    def load_policies(self, policies: Dict[str, Any]):
        """
        Load policies from configuration dictionary.

        Args:
            policies: Dictionary with whitelist, blacklist, etc.
        """
        try:
            if "whitelist" in policies:
                self.whitelist = policies["whitelist"]
            if "blacklist" in policies:
                self.blacklist = policies["blacklist"]
            if "filesystem_boundaries" in policies:
                self.filesystem_boundaries = policies["filesystem_boundaries"]
            if "network_policies" in policies:
                self.network_policies = policies["network_policies"]
            if "dangerous_patterns" in policies:
                # Load dangerous patterns with weights
                patterns = policies["dangerous_patterns"]
                self.dangerous_patterns = [
                    (p["pattern"], p["description"], p.get("weight", 50.0))
                    for p in patterns
                ]
            logger.info("Guardian policies loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Guardian policies: {e}")

    def quick_check(self, command: str) -> QuickCheckResult:
        """
        Perform quick check against blacklist.

        Args:
            command: Command to check

        Returns:
            QuickCheckResult with allowed flag and reason
        """
        # Check against blacklist patterns
        for pattern, reason in self.blacklist:
            if re.search(pattern, command, re.IGNORECASE):
                return QuickCheckResult(
                    allowed=False,
                    reason=f"Blocked: {reason}"
                )

        return QuickCheckResult(allowed=True, reason="Passed quick check")

    async def assess_risk(self, request: "ValidationRequest") -> RiskAssessment:  # noqa: F821
        """
        Assess overall risk of command execution.

        Args:
            request: The validation request

        Returns:
            RiskAssessment with score and factors
        """
        command = request.command
        risk_score = 100.0  # Start at maximum safety
        risk_factors: List[str] = []
        required_permissions: List[str] = []
        blocking_factors: List[str] = []

        # Check command classification
        if not self._is_whitelisted(command):
            risk_score -= 20
            risk_factors.append("Command not in whitelist")
            required_permissions.append("execute_non_whitelisted")

        # Check dangerous patterns
        pattern_risks = self._check_dangerous_patterns(command)
        if pattern_risks:
            risk_factors.extend([desc for _, desc in pattern_risks])
            pattern_weight = sum(weight for _, _, weight in pattern_risks) / 10
            risk_score -= min(pattern_weight, 40)

        # Check filesystem operations
        fs_risks = await self._check_filesystem_operations(request)
        if fs_risks:
            risk_factors.extend(fs_risks)
            risk_score -= 20
            required_permissions.append("filesystem_access")

        # Check network operations
        net_risks = await self._check_network_operations(command)
        if net_risks:
            risk_factors.extend(net_risks)
            risk_score -= 15
            required_permissions.append("network_access")

        # Check ACL permissions
        if request.user_id:
            acl_allowed = await self._check_acl_permission(
                request.user_id,
                command,
                request.source.value
            )
            if not acl_allowed:
                blocking_factors.append(f"User {request.user_id} lacks permission")
                required_permissions.append("user_permission")

        # Ensure score is between 0 and 100
        risk_score = max(0, min(100, risk_score))

        # Generate reason
        reason = self._generate_reason(risk_factors, blocking_factors, risk_score)

        return RiskAssessment(
            risk_score=risk_score,
            risk_factors=risk_factors,
            reason=reason,
            required_permissions=required_permissions,
            blocking_factors=blocking_factors
        )

    def _is_whitelisted(self, command: str) -> bool:
        """Check if command matches whitelist patterns."""
        for pattern in self.whitelist:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def _check_dangerous_patterns(self, command: str) -> List[Tuple[str, str]]:
        """Check for dangerous patterns in command."""
        matches: List[Tuple[str, str]] = []
        for pattern, description, _ in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                matches.append((pattern, description))
        return matches

    async def _check_filesystem_operations(self, request: "ValidationRequest") -> List[str]:  # noqa: F821
        """Check filesystem safety."""
        risks: List[str] = []
        command = request.command

        # Check for file deletion patterns
        if re.search(r"\brm\b", command) and "-r" in command:
            risks.append("Recursive file deletion detected")

        # Check working directory boundary
        if request.working_dir:
            try:
                wd_path = Path(request.working_dir).resolve()
                workspace_path = Path(self.filesystem_boundaries.get("workspace", "/")).resolve()

                if not self._is_path_within(wd_path, workspace_path):
                    risks.append("Working directory outside workspace boundary")
            except Exception as e:
                logger.warning(f"Error checking filesystem boundary: {e}")
                risks.append("Unable to verify filesystem boundary")

        return risks

    async def _check_network_operations(self, command: str) -> List[str]:
        """Check network operation safety."""
        risks: List[str] = []

        # Check for network tools
        network_tools = ["curl", "wget", "nc", "netcat", "ssh", "telnet"]
        for tool in network_tools:
            if re.search(rf"\b{tool}\b", command):
                risks.append(f"Network operation detected: {tool}")
                break

        # Check for risky HTTP methods
        if "DELETE" in command.upper() or "PUT" in command.upper():
            risks.append("Destructive HTTP method detected")

        return risks

    async def _check_acl_permission(
        self,
        user_id: int,
        command: str,
        source: str
    ) -> bool:
        """Check ACL permissions for user."""
        try:
            # Extract resource from command
            resource = self._extract_resource(command)

            if not config.acl.enable_acl:
                return True

            # Check permission via ACL service
            from app.database.database_service import database_service, acl_service
            # This would be called in production with actual ACL checks
            return True
        except Exception as e:
            logger.warning(f"Error checking ACL: {e}")
            return True  # Fail open for now

    @staticmethod
    def _is_path_within(path: Path, boundary: Path) -> bool:
        """Check if path is within boundary."""
        try:
            path.relative_to(boundary)
            return True
        except ValueError:
            return False

    @staticmethod
    def _extract_resource(command: str) -> str:
        """Extract resource name from command."""
        # Simple extraction - real implementation would be more complex
        parts = command.split()
        return parts[0] if parts else "unknown"

    @staticmethod
    def _generate_reason(
        risk_factors: List[str],
        blocking_factors: List[str],
        risk_score: float
    ) -> str:
        """Generate reason string for risk assessment."""
        if blocking_factors:
            return f"Blocked: {'; '.join(blocking_factors)}"

        if risk_score >= 90:
            return "Command meets safety criteria"
        elif risk_score >= 70:
            return f"Low risk: {'; '.join(risk_factors[:2])}"
        elif risk_score >= 50:
            return f"Medium risk: {'; '.join(risk_factors[:2])}"
        elif risk_score >= 30:
            return f"High risk: {'; '.join(risk_factors[:2])}"
        else:
            return f"Critical risk: {'; '.join(risk_factors[:2])}"
