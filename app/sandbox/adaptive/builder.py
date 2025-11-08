"""Sandbox builder for constructing adaptive sandboxes with granted capabilities.

Assembles sandbox environments (volumes, environment, resources) based on:
1. Agent capabilities
2. Guardian grants
3. Requested isolation level
4. Runtime conditions
"""

import os
import platform
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from app.logger import logger
from app.sandbox.adaptive.capability_grant import CapabilityGrant, PathAccessMode
from app.sandbox.adaptive.isolation_levels import IsolationLevel, get_isolation_config


@dataclass
class SandboxEnvironment:
    """Built sandbox environment configuration."""
    
    environment_variables: Dict[str, str]
    """Environment variables for the sandbox."""
    
    volume_mounts: Dict[str, Tuple[str, str]]
    """Volume mounts: {host_path: (container_path, mode)}."""
    
    readonly_paths: list
    """Paths that should be read-only."""
    
    read_write_paths: list
    """Paths that should be read-write."""
    
    resource_limits: Dict
    """Resource limits: cpu_percent, memory_mb, timeout_seconds."""
    
    process_constraints: Dict
    """Process constraints: allow_subprocess, allow_network, etc."""
    
    isolation_level: IsolationLevel
    """Effective isolation level for this sandbox."""
    
    granted_capabilities: Dict
    """Summary of granted capabilities."""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "environment_variables": self.environment_variables,
            "volume_mounts": {k: (v[0], v[1]) for k, v in self.volume_mounts.items()},
            "readonly_paths": self.readonly_paths,
            "read_write_paths": self.read_write_paths,
            "resource_limits": self.resource_limits,
            "process_constraints": self.process_constraints,
            "isolation_level": self.isolation_level.name,
            "granted_capabilities": self.granted_capabilities,
        }


class SandboxBuilder:
    """Builds sandbox environments from grants and policies.
    
    Responsible for:
    1. Validating grants and capabilities
    2. Constructing environment variables from whitelists
    3. Building volume mounts from allowed paths
    4. Setting resource limits
    5. Determining effective isolation level
    """
    
    def __init__(
        self,
        agent_id: str,
        grant: CapabilityGrant,
        isolation_level: Optional[IsolationLevel] = None,
        host_environment: Optional[Dict[str, str]] = None,
    ):
        """Initialize sandbox builder.
        
        Args:
            agent_id: Agent ID
            grant: Capability grant defining allowed capabilities
            isolation_level: Requested isolation level (or auto-determined from grant)
            host_environment: Host environment variables to filter
        """
        self.agent_id = agent_id
        self.grant = grant
        self.host_environment = host_environment or dict(os.environ)
        self.isolation_level = isolation_level or self._determine_isolation_level()
    
    def _determine_isolation_level(self) -> IsolationLevel:
        """Determine effective isolation level from grant constraints."""
        # Grant specifies a range, we'll use the minimum as default
        level_value = self.grant.min_isolation_level
        return IsolationLevel(level_value)
    
    def build(self) -> SandboxEnvironment:
        """Build the complete sandbox environment.
        
        Returns:
            SandboxEnvironment with all configurations.
        """
        logger.info(
            f"Building sandbox for agent {self.agent_id} "
            f"with isolation level {self.isolation_level.name}"
        )
        
        # Get isolation configuration
        iso_config = get_isolation_config(self.isolation_level)
        
        # Build environment variables
        env_vars = self._build_environment(iso_config)
        
        # Build volume mounts
        volumes, ro_paths, rw_paths = self._build_volumes(iso_config)
        
        # Build resource limits
        resource_limits = self._build_resource_limits(iso_config)
        
        # Build process constraints
        process_constraints = self._build_process_constraints(iso_config)
        
        # Summary of capabilities
        capabilities = {
            "allowed_tools": list(self.grant.allowed_tools),
            "allowed_paths": {k: v.value for k, v in self.grant.allowed_paths.items()},
            "network_enabled": self.grant.network_enabled and iso_config.allow_network_access,
            "env_variables": len(env_vars),
        }
        
        sandbox_env = SandboxEnvironment(
            environment_variables=env_vars,
            volume_mounts=volumes,
            readonly_paths=ro_paths,
            read_write_paths=rw_paths,
            resource_limits=resource_limits,
            process_constraints=process_constraints,
            isolation_level=self.isolation_level,
            granted_capabilities=capabilities,
        )
        
        logger.debug(f"Built sandbox environment: {sandbox_env.to_dict()}")
        return sandbox_env
    
    def _build_environment(self, iso_config) -> Dict[str, str]:
        """Build environment variables for the sandbox."""
        env = {}
        
        if iso_config.inherit_environment:
            # Inherit all host environment
            env.update(self.host_environment)
        else:
            # Only include whitelisted variables
            for var_name in iso_config.env_whitelist:
                if var_name in self.host_environment:
                    env[var_name] = self.host_environment[var_name]
        
        # Apply grant-specific environment filtering
        if not iso_config.inherit_environment:
            # Get filtered environment from grant
            grant_env = self.grant.get_filtered_environment(self.host_environment)
            env.update(grant_env)
        else:
            # Merge grant's explicit variables
            env.update(self.grant.env_vars)
        
        # Add sandbox identifiers
        env.update({
            "SANDBOX_MODE": "adaptive",
            "SANDBOX_AGENT_ID": self.agent_id,
            "SANDBOX_GRANT_ID": self.grant.grant_id,
            "SANDBOX_ISOLATION_LEVEL": self.isolation_level.name,
        })
        
        # Handle platform-specific variables
        platform_type = platform.system()
        if platform_type == "Windows":
            env["SANDBOX_PLATFORM"] = "windows"
            # Windows-specific paths
            if "MSVC_PATH" in self.host_environment:
                env["MSVC_PATH"] = self.host_environment["MSVC_PATH"]
            if "VS_INSTALLATION" in self.host_environment:
                env["VS_INSTALLATION"] = self.host_environment["VS_INSTALLATION"]
        else:
            env["SANDBOX_PLATFORM"] = "linux"
            # Linux-specific paths
            if "CUDA_HOME" in self.host_environment:
                env["CUDA_HOME"] = self.host_environment["CUDA_HOME"]
        
        return env
    
    def _build_volumes(self, iso_config) -> Tuple[Dict, list, list]:
        """Build volume mount configuration.
        
        Returns:
            Tuple of (volumes_dict, readonly_paths, read_write_paths)
        """
        volumes = {}
        readonly_paths = []
        read_write_paths = []
        
        # Add granted paths
        for host_path, access_mode in self.grant.allowed_paths.items():
            container_path = f"/mount{host_path}" if not host_path.startswith("/mount") else host_path
            mode = "ro" if access_mode == PathAccessMode.READ_ONLY else "rw"
            
            volumes[host_path] = (container_path, mode)
            
            if access_mode == PathAccessMode.READ_ONLY:
                readonly_paths.append(container_path)
            else:
                read_write_paths.append(container_path)
        
        # For sandbox and isolated levels, enforce read-only root
        if iso_config.readonly_filesystem:
            readonly_paths.append("/")
            # But allow certain standard writable paths
            standard_writable = ["/tmp", "/var/tmp", "/home"]
            for path in standard_writable:
                if path not in read_write_paths:
                    read_write_paths.append(path)
        
        return volumes, readonly_paths, read_write_paths
    
    def _build_resource_limits(self, iso_config) -> Dict:
        """Build resource limit configuration."""
        limits = {}
        
        if iso_config.enforce_cpu_limit:
            limits["cpu_percent"] = min(
                iso_config.cpu_percent,
                self.grant.cpu_percent
            )
        else:
            limits["cpu_percent"] = self.grant.cpu_percent
        
        if iso_config.enforce_memory_limit:
            limits["memory_mb"] = min(
                iso_config.memory_mb if iso_config.memory_mb > 0 else float('inf'),
                self.grant.memory_mb
            )
        else:
            limits["memory_mb"] = self.grant.memory_mb
        
        limits["timeout_seconds"] = min(
            iso_config.timeout_seconds,
            self.grant.timeout_seconds
        )
        
        return limits
    
    def _build_process_constraints(self, iso_config) -> Dict:
        """Build process constraint configuration."""
        return {
            "allow_subprocess_creation": iso_config.allow_subprocess_creation,
            "allow_network_access": iso_config.allow_network_access and self.grant.network_enabled,
            "allow_device_access": iso_config.allow_device_access,
            "enable_seccomp": iso_config.enable_seccomp,
            "blocked_syscalls": iso_config.blocked_syscalls,
            "use_docker": iso_config.use_docker,
            "use_job_object": iso_config.use_job_object,
            "enable_audit_logging": iso_config.enable_audit_logging,
            "enable_syscall_tracing": iso_config.enable_syscall_tracing,
            "enable_network_monitoring": iso_config.enable_network_monitoring,
        }
    
    def suggest_required_capabilities(self, error_message: str) -> list:
        """Suggest missing capabilities based on error message.
        
        Args:
            error_message: Error message from failed command
        
        Returns:
            List of suggested capability grants
        """
        suggestions = []
        
        # Check for common missing tool patterns
        missing_tools = {
            "command not found": "Missing tool - check allowed_tools",
            "No such file or directory": "Missing path - check allowed_paths",
            "Permission denied": "Insufficient permissions - check path access mode",
            "Network is unreachable": "Network access needed - set network_enabled=true",
        }
        
        for pattern, suggestion in missing_tools.items():
            if pattern.lower() in error_message.lower():
                suggestions.append(suggestion)
        
        # Check for specific tools
        tool_patterns = {
            "python": "python",
            "git": "git",
            "npm": "npm",
            "node": "node",
            "docker": "docker",
            "curl": "curl",
            "wget": "wget",
        }
        
        for tool_name, tool_key in tool_patterns.items():
            if f"{tool_name}:" in error_message.lower():
                if tool_key not in self.grant.allowed_tools:
                    suggestions.append(f"Add tool to allowed_tools: {tool_key}")
        
        return suggestions
