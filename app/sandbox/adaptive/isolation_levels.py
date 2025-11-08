"""Isolation level definitions and configurations for adaptive sandboxes.

Defines 5 levels of isolation from fully trusted to complete VM isolation,
with automatic escalation based on Guardian risk assessment and runtime anomalies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class IsolationLevel(Enum):
    """Isolation level for sandbox execution."""
    
    TRUSTED = 0
    """Full trust: inherit environment, no filesystem restrictions, direct execution."""
    
    MONITORED = 1
    """Monitored: filtered environment, all operations logged, no restrictions."""
    
    RESTRICTED = 2
    """Restricted: granted capabilities only, file ACL enforced, network policies applied."""
    
    SANDBOXED = 3
    """Sandboxed: minimal environment, Docker or strict process isolation, kill on risky syscalls."""
    
    ISOLATED = 4
    """Isolated: full VM isolation if Guardian detects attack/anomaly during execution."""
    
    @property
    def description(self) -> str:
        """Get human-readable description."""
        descriptions = {
            IsolationLevel.TRUSTED: "Full trust - inherit environment as-is (for dev)",
            IsolationLevel.MONITORED: "Monitored - filtered environment, all ops logged",
            IsolationLevel.RESTRICTED: "Restricted - granted capabilities only",
            IsolationLevel.SANDBOXED: "Sandboxed - minimal environment, Docker/strict process",
            IsolationLevel.ISOLATED: "Isolated - full VM isolation if anomaly detected",
        }
        return descriptions.get(self, "Unknown")


@dataclass
class IsolationConfig:
    """Configuration for a specific isolation level."""
    
    level: IsolationLevel
    
    # Environment filtering
    inherit_environment: bool
    """Whether to inherit host process environment."""
    
    env_whitelist: List[str]
    """List of environment variables to allow (if not inheriting all)."""
    
    # File system access
    enforce_acl: bool
    """Whether to enforce file ACLs."""
    
    readonly_filesystem: bool
    """Whether filesystem should be read-only (except granted paths)."""
    
    # Process constraints
    allow_subprocess_creation: bool
    """Whether to allow subprocess spawning."""
    
    allow_network_access: bool
    """Whether to allow network access."""
    
    allow_device_access: bool
    """Whether to allow direct device access."""
    
    # System call filtering
    enable_seccomp: bool
    """Whether to enable seccomp syscall filtering (Linux)."""
    
    blocked_syscalls: List[str]
    """List of syscalls to block."""
    
    # Resource limits
    enforce_cpu_limit: bool
    cpu_percent: float
    
    enforce_memory_limit: bool
    memory_mb: int
    
    timeout_seconds: int
    
    # Execution mode
    use_docker: bool
    """Whether to use Docker containerization."""
    
    use_job_object: bool
    """Whether to use Windows job objects."""
    
    # Logging and monitoring
    enable_audit_logging: bool
    enable_syscall_tracing: bool
    enable_network_monitoring: bool
    
    # Escalation
    auto_escalate_on_anomaly: bool
    escalate_to_level: Optional['IsolationLevel'] = None
    
    # Description
    description: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "level_name": self.level.name,
            "inherit_environment": self.inherit_environment,
            "env_whitelist": self.env_whitelist,
            "enforce_acl": self.enforce_acl,
            "readonly_filesystem": self.readonly_filesystem,
            "allow_subprocess_creation": self.allow_subprocess_creation,
            "allow_network_access": self.allow_network_access,
            "allow_device_access": self.allow_device_access,
            "enable_seccomp": self.enable_seccomp,
            "blocked_syscalls": self.blocked_syscalls,
            "enforce_cpu_limit": self.enforce_cpu_limit,
            "cpu_percent": self.cpu_percent,
            "enforce_memory_limit": self.enforce_memory_limit,
            "memory_mb": self.memory_mb,
            "timeout_seconds": self.timeout_seconds,
            "use_docker": self.use_docker,
            "use_job_object": self.use_job_object,
            "enable_audit_logging": self.enable_audit_logging,
            "enable_syscall_tracing": self.enable_syscall_tracing,
            "enable_network_monitoring": self.enable_network_monitoring,
            "auto_escalate_on_anomaly": self.auto_escalate_on_anomaly,
            "escalate_to_level": self.escalate_to_level.value if self.escalate_to_level else None,
            "description": self.description,
        }


def get_isolation_config(level: IsolationLevel) -> IsolationConfig:
    """Get the configuration for an isolation level."""
    
    if level == IsolationLevel.TRUSTED:
        return IsolationConfig(
            level=IsolationLevel.TRUSTED,
            inherit_environment=True,
            env_whitelist=[],  # Not used when inheriting all
            enforce_acl=False,
            readonly_filesystem=False,
            allow_subprocess_creation=True,
            allow_network_access=True,
            allow_device_access=True,
            enable_seccomp=False,
            blocked_syscalls=[],
            enforce_cpu_limit=False,
            cpu_percent=100.0,
            enforce_memory_limit=False,
            memory_mb=0,  # Unlimited
            timeout_seconds=3600,
            use_docker=False,
            use_job_object=False,
            enable_audit_logging=True,
            enable_syscall_tracing=False,
            enable_network_monitoring=False,
            auto_escalate_on_anomaly=False,
            escalate_to_level=IsolationLevel.MONITORED,
            description=IsolationLevel.TRUSTED.description,
        )
    
    elif level == IsolationLevel.MONITORED:
        return IsolationConfig(
            level=IsolationLevel.MONITORED,
            inherit_environment=True,
            env_whitelist=[],
            enforce_acl=False,
            readonly_filesystem=False,
            allow_subprocess_creation=True,
            allow_network_access=True,
            allow_device_access=False,
            enable_seccomp=False,
            blocked_syscalls=[],
            enforce_cpu_limit=False,
            cpu_percent=100.0,
            enforce_memory_limit=False,
            memory_mb=0,
            timeout_seconds=3600,
            use_docker=False,
            use_job_object=False,
            enable_audit_logging=True,
            enable_syscall_tracing=True,
            enable_network_monitoring=True,
            auto_escalate_on_anomaly=True,
            escalate_to_level=IsolationLevel.RESTRICTED,
            description=IsolationLevel.MONITORED.description,
        )
    
    elif level == IsolationLevel.RESTRICTED:
        return IsolationConfig(
            level=IsolationLevel.RESTRICTED,
            inherit_environment=False,
            env_whitelist=["PATH", "HOME", "USER", "SHELL", "TERM"],
            enforce_acl=True,
            readonly_filesystem=True,
            allow_subprocess_creation=True,
            allow_network_access=False,
            allow_device_access=False,
            enable_seccomp=True,
            blocked_syscalls=[
                "ptrace", "kexec_load", "sysrq", "setns", "unshare",
                "clone", "mount", "umount", "reboot"
            ],
            enforce_cpu_limit=True,
            cpu_percent=80.0,
            enforce_memory_limit=True,
            memory_mb=512,
            timeout_seconds=600,
            use_docker=False,
            use_job_object=False,
            enable_audit_logging=True,
            enable_syscall_tracing=True,
            enable_network_monitoring=True,
            auto_escalate_on_anomaly=True,
            escalate_to_level=IsolationLevel.SANDBOXED,
            description=IsolationLevel.RESTRICTED.description,
        )
    
    elif level == IsolationLevel.SANDBOXED:
        return IsolationConfig(
            level=IsolationLevel.SANDBOXED,
            inherit_environment=False,
            env_whitelist=["PATH"],
            enforce_acl=True,
            readonly_filesystem=True,
            allow_subprocess_creation=False,
            allow_network_access=False,
            allow_device_access=False,
            enable_seccomp=True,
            blocked_syscalls=[
                "ptrace", "kexec_load", "sysrq", "setns", "unshare",
                "clone", "mount", "umount", "reboot", "socket",
                "connect", "bind", "accept", "listen", "execve"
            ],
            enforce_cpu_limit=True,
            cpu_percent=50.0,
            enforce_memory_limit=True,
            memory_mb=256,
            timeout_seconds=300,
            use_docker=True,
            use_job_object=True,
            enable_audit_logging=True,
            enable_syscall_tracing=True,
            enable_network_monitoring=True,
            auto_escalate_on_anomaly=True,
            escalate_to_level=IsolationLevel.ISOLATED,
            description=IsolationLevel.SANDBOXED.description,
        )
    
    elif level == IsolationLevel.ISOLATED:
        return IsolationConfig(
            level=IsolationLevel.ISOLATED,
            inherit_environment=False,
            env_whitelist=[],
            enforce_acl=True,
            readonly_filesystem=True,
            allow_subprocess_creation=False,
            allow_network_access=False,
            allow_device_access=False,
            enable_seccomp=True,
            blocked_syscalls=[
                "ptrace", "kexec_load", "sysrq", "setns", "unshare",
                "clone", "mount", "umount", "reboot", "socket",
                "connect", "bind", "accept", "listen", "execve",
                "fork", "vfork", "exec"
            ],
            enforce_cpu_limit=True,
            cpu_percent=25.0,
            enforce_memory_limit=True,
            memory_mb=128,
            timeout_seconds=120,
            use_docker=True,
            use_job_object=True,
            enable_audit_logging=True,
            enable_syscall_tracing=True,
            enable_network_monitoring=True,
            auto_escalate_on_anomaly=False,
            escalate_to_level=None,
            description=IsolationLevel.ISOLATED.description,
        )
    
    else:
        raise ValueError(f"Unknown isolation level: {level}")
