"""
FreEco.ai Platform - Anti-Hacking System
Enhanced OpenManus with comprehensive anti-hacking measures

This module provides protection against:
- SQL injection attacks
- XSS (Cross-Site Scripting) attacks
- CSRF (Cross-Site Request Forgery) attacks
- Command injection attacks
- Intrusion detection
- Secure file upload handling

Part of Security Framework
"""

import logging
import mimetypes
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Set


logger = logging.getLogger(__name__)


class AttackType(Enum):
    """Types of attacks"""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    FILE_UPLOAD = "file_upload"
    BRUTE_FORCE = "brute_force"


@dataclass
class IntrusionAttempt:
    """Intrusion attempt record"""

    timestamp: datetime
    attack_type: AttackType
    source_ip: Optional[str]
    user_id: Optional[str]
    payload: str
    blocked: bool
    severity: str  # low, medium, high, critical

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "attack_type": self.attack_type.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "payload_preview": self.payload[:100],
            "blocked": self.blocked,
            "severity": self.severity,
        }


@dataclass
class CSRFToken:
    """CSRF token"""

    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    used: bool = False

    def is_valid(self) -> bool:
        """Check if token is valid"""
        return not self.used and datetime.now() < self.expires_at


@dataclass
class FileUploadResult:
    """File upload validation result"""

    safe: bool
    file_type: str
    file_size: int
    issues: List[str]
    sanitized_filename: str


class AntiHackingSystem:
    """
    Comprehensive anti-hacking protection system

    Features:
    - SQL injection prevention
    - XSS protection
    - CSRF token management
    - Command injection prevention
    - Intrusion detection
    - Secure file upload validation

    Example:
        anti_hack = AntiHackingSystem()

        # Prevent SQL injection
        safe_query = anti_hack.prevent_sql_injection(user_query)

        # Sanitize HTML
        safe_html = anti_hack.sanitize_html(user_content)

        # Generate CSRF token
        token = anti_hack.generate_csrf_token(user_id)

        # Validate CSRF token
        if anti_hack.validate_csrf_token(token, user_id):
            # Process request
            pass
    """

    def __init__(self):
        """Initialize anti-hacking system"""
        # SQL injection patterns
        self.sql_patterns = self._load_sql_patterns()

        # XSS patterns
        self.xss_patterns = self._load_xss_patterns()

        # Command injection patterns
        self.command_patterns = self._load_command_patterns()

        # CSRF tokens
        self.csrf_tokens: Dict[str, CSRFToken] = {}

        # Intrusion attempts log
        self.intrusion_log: List[IntrusionAttempt] = []

        # Blocked IPs
        self.blocked_ips: Set[str] = set()

        # Failed login attempts
        self.failed_logins: Dict[str, List[datetime]] = {}

        # Allowed file extensions
        self.allowed_extensions = {
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".mp3",
            ".mp4",
            ".wav",
            ".avi",
            ".zip",
            ".tar",
            ".gz",
        }

    def prevent_sql_injection(self, query: str) -> str:
        """
        Prevent SQL injection by sanitizing query

        Args:
            query: SQL query or user input

        Returns:
            Sanitized query
        """
        # Check for SQL injection patterns
        for pattern_name, pattern in self.sql_patterns.items():
            if pattern.search(query):
                self._log_intrusion(
                    attack_type=AttackType.SQL_INJECTION,
                    payload=query,
                    severity="high",
                )

                # Remove dangerous SQL keywords
                query = pattern.sub("", query)

        # Escape single quotes
        query = query.replace("'", "''")

        # Remove comments
        query = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
        query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)

        return query

    def sanitize_html(
        self, content: str, allowed_tags: Optional[Set[str]] = None
    ) -> str:
        """
        Sanitize HTML content to prevent XSS

        Args:
            content: HTML content to sanitize
            allowed_tags: Set of allowed HTML tags

        Returns:
            Sanitized HTML
        """
        if allowed_tags is None:
            allowed_tags = {"p", "br", "strong", "em", "u", "a", "ul", "ol", "li"}

        # Check for XSS patterns
        for pattern_name, pattern in self.xss_patterns.items():
            if pattern.search(content):
                self._log_intrusion(
                    attack_type=AttackType.XSS,
                    payload=content,
                    severity="high",
                )

                # Remove dangerous patterns
                content = pattern.sub("", content)

        # Remove script tags
        content = re.sub(
            r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove event handlers
        content = re.sub(
            r'\s*on\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE
        )

        # Remove javascript: protocol
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

        # Remove data: protocol
        content = re.sub(r"data:", "", content, flags=re.IGNORECASE)

        # Remove disallowed tags
        def replace_tag(match):
            tag = match.group(1).lower()
            if tag in allowed_tags:
                return match.group(0)
            return ""

        content = re.sub(r"<(/?)(\w+)[^>]*>", replace_tag, content)

        return content

    def generate_csrf_token(self, user_id: str, ttl_minutes: int = 30) -> str:
        """
        Generate CSRF token

        Args:
            user_id: User identifier
            ttl_minutes: Token time-to-live in minutes

        Returns:
            CSRF token string
        """
        token = secrets.token_urlsafe(32)

        csrf_token = CSRFToken(
            token=token,
            user_id=user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=ttl_minutes),
        )

        self.csrf_tokens[token] = csrf_token

        logger.info(f"Generated CSRF token for user: {user_id}")
        return token

    def validate_csrf_token(self, token: str, user_id: str) -> bool:
        """
        Validate CSRF token

        Args:
            token: CSRF token to validate
            user_id: User identifier

        Returns:
            True if token is valid
        """
        if token not in self.csrf_tokens:
            self._log_intrusion(
                attack_type=AttackType.CSRF,
                payload=f"Invalid token: {token[:10]}...",
                user_id=user_id,
                severity="medium",
            )
            return False

        csrf_token = self.csrf_tokens[token]

        # Check user ID
        if csrf_token.user_id != user_id:
            self._log_intrusion(
                attack_type=AttackType.CSRF,
                payload=f"User mismatch: {user_id}",
                user_id=user_id,
                severity="high",
            )
            return False

        # Check validity
        if not csrf_token.is_valid():
            self._log_intrusion(
                attack_type=AttackType.CSRF,
                payload=f"Expired/used token",
                user_id=user_id,
                severity="medium",
            )
            return False

        # Mark as used
        csrf_token.used = True

        return True

    def safe_shell_exec(
        self, command: str, allowed_commands: Optional[Set[str]] = None
    ) -> Optional[str]:
        """
        Safely execute shell command

        Args:
            command: Command to execute
            allowed_commands: Set of allowed command names

        Returns:
            Sanitized command or None if dangerous
        """
        if allowed_commands is None:
            allowed_commands = {"ls", "cat", "grep", "find", "echo"}

        # Check for command injection patterns
        for pattern_name, pattern in self.command_patterns.items():
            if pattern.search(command):
                self._log_intrusion(
                    attack_type=AttackType.COMMAND_INJECTION,
                    payload=command,
                    severity="critical",
                )
                return None

        # Extract command name
        command_name = command.split()[0] if command else ""

        # Check if command is allowed
        if command_name not in allowed_commands:
            self._log_intrusion(
                attack_type=AttackType.COMMAND_INJECTION,
                payload=f"Disallowed command: {command_name}",
                severity="high",
            )
            return None

        # Remove dangerous characters
        safe_command = re.sub(r"[;&|`$()]", "", command)

        return safe_command

    def detect_intrusion(self, activity: Dict[str, any]) -> bool:
        """
        Detect intrusion based on activity patterns

        Args:
            activity: Activity data to analyze

        Returns:
            True if intrusion detected
        """
        user_id = activity.get("user_id")
        ip_address = activity.get("ip_address")

        # Check if IP is blocked
        if ip_address and ip_address in self.blocked_ips:
            return True

        # Check for brute force attacks
        if user_id and "login_failed" in activity:
            if user_id not in self.failed_logins:
                self.failed_logins[user_id] = []

            self.failed_logins[user_id].append(datetime.now())

            # Check recent failures
            recent_failures = [
                t
                for t in self.failed_logins[user_id]
                if datetime.now() - t < timedelta(minutes=5)
            ]

            if len(recent_failures) >= 5:
                self._log_intrusion(
                    attack_type=AttackType.BRUTE_FORCE,
                    payload=f"Multiple failed logins: {len(recent_failures)}",
                    user_id=user_id,
                    source_ip=ip_address,
                    severity="high",
                )

                # Block IP if available
                if ip_address:
                    self.blocked_ips.add(ip_address)
                    logger.warning(f"Blocked IP due to brute force: {ip_address}")

                return True

        return False

    def scan_file_upload(
        self, file_path: Path, original_filename: str
    ) -> FileUploadResult:
        """
        Scan uploaded file for security issues

        Args:
            file_path: Path to uploaded file
            original_filename: Original filename

        Returns:
            FileUploadResult with validation results
        """
        issues = []

        # Check file extension
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            issues.append(f"Disallowed file extension: {file_ext}")

        # Check file size (max 10MB)
        file_size = file_path.stat().st_size
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            issues.append(f"File too large: {file_size} bytes")

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        if mime_type and mime_type.startswith("application/x-"):
            issues.append(f"Suspicious MIME type: {mime_type}")

        # Sanitize filename
        sanitized_filename = self._sanitize_filename(original_filename)

        # Check for path traversal
        if (
            ".." in original_filename
            or "/" in original_filename
            or "\\" in original_filename
        ):
            issues.append("Path traversal attempt detected")
            self._log_intrusion(
                attack_type=AttackType.PATH_TRAVERSAL,
                payload=original_filename,
                severity="high",
            )

        # Determine if safe
        safe = len(issues) == 0

        if not safe:
            self._log_intrusion(
                attack_type=AttackType.FILE_UPLOAD,
                payload=f"Unsafe file upload: {original_filename}",
                severity="medium",
            )

        return FileUploadResult(
            safe=safe,
            file_type=mime_type or "unknown",
            file_size=file_size,
            issues=issues,
            sanitized_filename=sanitized_filename,
        )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent attacks"""
        # Remove path components
        filename = Path(filename).name

        # Remove dangerous characters
        filename = re.sub(r"[^\w\s.-]", "", filename)

        # Limit length
        if len(filename) > 255:
            name, ext = Path(filename).stem, Path(filename).suffix
            filename = name[: 255 - len(ext)] + ext

        return filename

    def _log_intrusion(
        self,
        attack_type: AttackType,
        payload: str,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        severity: str = "medium",
    ):
        """Log an intrusion attempt"""
        attempt = IntrusionAttempt(
            timestamp=datetime.now(),
            attack_type=attack_type,
            source_ip=source_ip,
            user_id=user_id,
            payload=payload,
            blocked=True,
            severity=severity,
        )

        self.intrusion_log.append(attempt)

        logger.warning(
            f"Intrusion attempt: {attack_type.value} "
            f"(severity: {severity}, user: {user_id}, ip: {source_ip})"
        )

    def _load_sql_patterns(self) -> Dict[str, Pattern]:
        """Load SQL injection patterns"""
        return {
            "union": re.compile(r"\bUNION\b.*\bSELECT\b", re.IGNORECASE),
            "select": re.compile(r"\bSELECT\b.*\bFROM\b", re.IGNORECASE),
            "insert": re.compile(r"\bINSERT\b.*\bINTO\b", re.IGNORECASE),
            "update": re.compile(r"\bUPDATE\b.*\bSET\b", re.IGNORECASE),
            "delete": re.compile(r"\bDELETE\b.*\bFROM\b", re.IGNORECASE),
            "drop": re.compile(r"\bDROP\b.*\b(TABLE|DATABASE)\b", re.IGNORECASE),
            "exec": re.compile(r"\b(EXEC|EXECUTE)\b", re.IGNORECASE),
        }

    def _load_xss_patterns(self) -> Dict[str, Pattern]:
        """Load XSS attack patterns"""
        return {
            "script_tag": re.compile(
                r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL
            ),
            "javascript": re.compile(r"javascript:", re.IGNORECASE),
            "onerror": re.compile(r"\bonerror\s*=", re.IGNORECASE),
            "onload": re.compile(r"\bonload\s*=", re.IGNORECASE),
            "onclick": re.compile(r"\bonclick\s*=", re.IGNORECASE),
            "iframe": re.compile(r"<iframe[^>]*>", re.IGNORECASE),
            "object": re.compile(r"<object[^>]*>", re.IGNORECASE),
            "embed": re.compile(r"<embed[^>]*>", re.IGNORECASE),
        }

    def _load_command_patterns(self) -> Dict[str, Pattern]:
        """Load command injection patterns"""
        return {
            "semicolon": re.compile(r";"),
            "pipe": re.compile(r"\|"),
            "ampersand": re.compile(r"&&"),
            "backtick": re.compile(r"`"),
            "dollar": re.compile(r"\$\("),
            "redirect": re.compile(r"[<>]"),
        }

    def get_intrusion_log(self, hours: int = 24) -> List[IntrusionAttempt]:
        """Get intrusion attempts from last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.intrusion_log if a.timestamp >= cutoff_time]

    def get_blocked_ips(self) -> Set[str]:
        """Get set of blocked IP addresses"""
        return self.blocked_ips.copy()

    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            logger.info(f"Unblocked IP: {ip_address}")


# Global anti-hacking instance
default_anti_hacking = AntiHackingSystem()
