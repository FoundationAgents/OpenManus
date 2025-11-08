import asyncio
import io
import os
import tarfile
import tempfile
import uuid
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass

import docker
from docker.errors import NotFound
from docker.models.containers import Container

from app.config import SandboxSettings
from app.sandbox.core.exceptions import SandboxTimeoutError, SandboxResourceError
from app.sandbox.core.terminal import AsyncDockerizedTerminal
from app.sandbox.core.guardian import Guardian, OperationRequest, GuardianDecision
from app.sandbox.core.monitor import ResourceMonitor, ResourceLimits, ResourceUsage
from app.sandbox.core.audit import AuditLogger, OperationType, OperationStatus, AuditLog
from app.logger import logger


@dataclass
class SandboxMetadata:
    """Metadata for a sandbox instance."""
    sandbox_id: str
    agent_id: str
    agent_version: Optional[str] = None
    created_at: Optional[float] = None
    last_activity: Optional[float] = None
    tags: Optional[Dict[str, str]] = None


class DockerSandbox:
    """Docker sandbox environment.

    Provides a containerized execution environment with resource limits,
    file operations, command execution capabilities, Guardian validation,
    resource monitoring, and audit logging.

    Attributes:
        config: Sandbox configuration.
        volume_bindings: Volume mapping configuration.
        client: Docker client.
        container: Docker container instance.
        terminal: Container terminal interface.
        metadata: Sandbox metadata.
        guardian: Guardian validation instance.
        monitor: Resource monitor instance.
        audit_logger: Audit logger instance.
        resource_limits: Resource limits for this sandbox.
    """

    def __init__(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        guardian: Optional[Guardian] = None,
        monitor: Optional[ResourceMonitor] = None,
        audit_logger: Optional[AuditLogger] = None,
        resource_limits: Optional[ResourceLimits] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Initializes a sandbox instance.

        Args:
            config: Sandbox configuration. Default configuration used if None.
            volume_bindings: Volume mappings in {host_path: container_path} format.
            agent_id: Agent ID owning this sandbox.
            agent_version: Agent version.
            guardian: Guardian validation instance.
            monitor: Resource monitor instance.
            audit_logger: Audit logger instance.
            resource_limits: Resource limits for this sandbox.
            tags: Additional metadata tags.
        """
        self.config = config or SandboxSettings()
        self.volume_bindings = volume_bindings or {}
        self.client = docker.from_env()
        self.container: Optional[Container] = None
        self.terminal: Optional[AsyncDockerizedTerminal] = None
        
        # Enhanced features
        self.sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"
        self.metadata = SandboxMetadata(
            sandbox_id=self.sandbox_id,
            agent_id=agent_id or "unknown",
            agent_version=agent_version,
            created_at=time.time(),
            last_activity=time.time(),
            tags=tags or {}
        )
        self.guardian = guardian
        self.monitor = monitor
        self.audit_logger = audit_logger
        self.resource_limits = resource_limits or ResourceLimits(
            cpu_percent=80.0,
            memory_mb=int(self.config.memory_limit.rstrip('m')) if self.config.memory_limit.endswith('m') else 512,
            timeout_seconds=self.config.timeout
        )

    async def create(self) -> "DockerSandbox":
        """Creates and starts the sandbox container.

        Returns:
            Current sandbox instance.

        Raises:
            docker.errors.APIError: If Docker API call fails.
            RuntimeError: If container creation or startup fails.
            SandboxResourceError: If Guardian validation fails.
        """
        start_time = time.time()
        
        try:
            # Guardian validation for sandbox creation
            if self.guardian:
                operation_request = OperationRequest(
                    agent_id=self.metadata.agent_id,
                    operation="sandbox_create",
                    volume_bindings=self.volume_bindings,
                    resource_limits={
                        "cpu_limit": self.config.cpu_limit,
                        "memory_limit": self.config.memory_limit,
                        "timeout": self.config.timeout
                    },
                    metadata={
                        "sandbox_id": self.sandbox_id,
                        "image": self.config.image,
                        "work_dir": self.config.work_dir,
                        "network_enabled": self.config.network_enabled
                    }
                )
                
                decision = await self.guardian.validate_operation(operation_request)
                
                if not decision.approved:
                    if self.audit_logger:
                        audit_log = AuditLog(
                            timestamp=time.time(),
                            agent_id=self.metadata.agent_id,
                            sandbox_id=self.sandbox_id,
                            operation_type=OperationType.GUARDIAN_DENIAL,
                            status=OperationStatus.DENIED,
                            details={
                                "operation": "sandbox_create",
                                "reason": decision.reason,
                                "risk_level": decision.risk_level.value
                            }
                        )
                        await self.audit_logger.log_operation(audit_log)
                    
                    raise SandboxResourceError(f"Guardian denied sandbox creation: {decision.reason}")
                
                logger.info(f"Guardian approved sandbox creation: {decision.reason}")

            # Prepare container config with enhanced resource limits
            host_config = self.client.api.create_host_config(
                mem_limit=self.config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(100000 * self.config.cpu_limit),
                network_mode="none" if not self.config.network_enabled else "bridge",
                binds=self._prepare_volume_bindings(),
                # Additional security constraints
                read_only=False,  # Allow write operations in working directory
                tmpfs={
                    "/tmp": "rw,noexec,nosuid,size=100m",
                    "/var/tmp": "rw,noexec,nosuid,size=100m"
                }
            )

            # Generate container name with agent prefix
            container_name = f"sandbox_{self.metadata.agent_id}_{self.sandbox_id}"

            # Create container
            container = await asyncio.to_thread(
                self.client.api.create_container,
                image=self.config.image,
                command="tail -f /dev/null",
                hostname="sandbox",
                working_dir=self.config.work_dir,
                host_config=host_config,
                name=container_name,
                tty=True,
                detach=True,
                labels={
                    "agent_id": self.metadata.agent_id,
                    "sandbox_id": self.sandbox_id,
                    "created_at": str(self.metadata.created_at)
                }
            )

            self.container = self.client.containers.get(container["Id"])

            # Start container
            await asyncio.to_thread(self.container.start)

            # Initialize terminal
            self.terminal = AsyncDockerizedTerminal(
                container["Id"],
                self.config.work_dir,
                env_vars={
                    "PYTHONUNBUFFERED": "1",
                    "SANDBOX_ID": self.sandbox_id,
                    "AGENT_ID": self.metadata.agent_id
                }
            )
            await self.terminal.init()

            # Add to resource monitor
            if self.monitor:
                self.monitor.add_sandbox(
                    self.sandbox_id,
                    self.container,
                    self.metadata.agent_id,
                    self.resource_limits
                )

            # Log successful creation
            duration_ms = int((time.time() - start_time) * 1000)
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=time.time(),
                    agent_id=self.metadata.agent_id,
                    sandbox_id=self.sandbox_id,
                    operation_type=OperationType.SANDBOX_CREATE,
                    status=OperationStatus.SUCCESS,
                    details={
                        "container_name": container_name,
                        "container_id": container["Id"],
                        "image": self.config.image,
                        "work_dir": self.config.work_dir,
                        "volume_bindings": self.volume_bindings,
                        "resource_limits": {
                            "cpu_limit": self.config.cpu_limit,
                            "memory_limit": self.config.memory_limit,
                            "timeout": self.config.timeout
                        }
                    },
                    duration_ms=duration_ms
                )
                await self.audit_logger.log_operation(audit_log)

            logger.info(f"Created sandbox {self.sandbox_id} for agent {self.metadata.agent_id}")
            return self

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failure
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=time.time(),
                    agent_id=self.metadata.agent_id,
                    sandbox_id=self.sandbox_id,
                    operation_type=OperationType.SANDBOX_CREATE,
                    status=OperationStatus.FAILURE,
                    details={"error": str(e)},
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                await self.audit_logger.log_operation(audit_log)
            
            await self.cleanup()  # Ensure resources are cleaned up
            raise RuntimeError(f"Failed to create sandbox: {e}") from e

    def _prepare_volume_bindings(self) -> Dict[str, Dict[str, str]]:
        """Prepares volume binding configuration.

        Returns:
            Volume binding configuration dictionary.
        """
        bindings = {}

        # Create and add working directory mapping
        work_dir = self._ensure_host_dir(self.config.work_dir)
        bindings[work_dir] = {"bind": self.config.work_dir, "mode": "rw"}

        # Add custom volume bindings
        for host_path, container_path in self.volume_bindings.items():
            bindings[host_path] = {"bind": container_path, "mode": "rw"}

        return bindings

    @staticmethod
    def _ensure_host_dir(path: str) -> str:
        """Ensures directory exists on the host.

        Args:
            path: Directory path.

        Returns:
            Actual path on the host.
        """
        host_path = os.path.join(
            tempfile.gettempdir(),
            f"sandbox_{os.path.basename(path)}_{os.urandom(4).hex()}",
        )
        os.makedirs(host_path, exist_ok=True)
        return host_path

    async def run_command(self, cmd: str, timeout: Optional[int] = None) -> str:
        """Runs a command in the sandbox.

        Args:
            cmd: Command to execute.
            timeout: Timeout in seconds.

        Returns:
            Command output as string.

        Raises:
            RuntimeError: If sandbox not initialized or command execution fails.
            TimeoutError: If command execution times out.
            SandboxResourceError: If Guardian validation fails.
        """
        if not self.terminal:
            raise RuntimeError("Sandbox not initialized")

        start_time = time.time()
        self.metadata.last_activity = start_time
        
        # Guardian validation for command execution
        if self.guardian:
            operation_request = OperationRequest(
                agent_id=self.metadata.agent_id,
                operation="command_execute",
                command=cmd,
                metadata={
                    "sandbox_id": self.sandbox_id,
                    "timeout": timeout or self.config.timeout
                }
            )
            
            decision = await self.guardian.validate_operation(operation_request)
            
            if not decision.approved:
                if self.audit_logger:
                    audit_log = AuditLog(
                        timestamp=time.time(),
                        agent_id=self.metadata.agent_id,
                        sandbox_id=self.sandbox_id,
                        operation_type=OperationType.GUARDIAN_DENIAL,
                        status=OperationStatus.DENIED,
                        details={
                            "operation": "command_execute",
                            "command": cmd,
                            "reason": decision.reason,
                            "risk_level": decision.risk_level.value
                        }
                    )
                    await self.audit_logger.log_operation(audit_log)
                
                raise SandboxResourceError(f"Guardian denied command execution: {decision.reason}")
            
            # Apply Guardian conditions (e.g., timeout override)
            effective_timeout = decision.timeout_override or timeout or self.config.timeout

        try:
            # Get current resource usage before execution
            current_usage = None
            if self.monitor:
                metrics = await self.monitor.get_sandbox_metrics(self.sandbox_id)
                if metrics and metrics.get("current_usage"):
                    current_usage = ResourceUsage(**metrics["current_usage"])

            # Execute command
            result = await self.terminal.run_command(
                cmd, timeout=effective_timeout
            )

            # Log successful execution
            duration_ms = int((time.time() - start_time) * 1000)
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=time.time(),
                    agent_id=self.metadata.agent_id,
                    sandbox_id=self.sandbox_id,
                    operation_type=OperationType.COMMAND_EXECUTE,
                    status=OperationStatus.SUCCESS,
                    details={
                        "command": cmd,
                        "timeout": effective_timeout,
                        "output_length": len(result),
                        "guardian_conditions": decision.conditions if self.guardian else []
                    },
                    resource_usage=current_usage,
                    duration_ms=duration_ms
                )
                await self.audit_logger.log_operation(audit_log)

            return result

        except TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log timeout
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=time.time(),
                    agent_id=self.metadata.agent_id,
                    sandbox_id=self.sandbox_id,
                    operation_type=OperationType.COMMAND_EXECUTE,
                    status=OperationStatus.TIMEOUT,
                    details={
                        "command": cmd,
                        "timeout": effective_timeout,
                        "reason": f"Command execution timed out after {effective_timeout} seconds"
                    },
                    resource_usage=current_usage,
                    duration_ms=duration_ms,
                    error_message=f"Command timed out after {effective_timeout} seconds"
                )
                await self.audit_logger.log_operation(audit_log)

            raise SandboxTimeoutError(
                f"Command execution timed out after {effective_timeout} seconds"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failure
            if self.audit_logger:
                audit_log = AuditLog(
                    timestamp=time.time(),
                    agent_id=self.metadata.agent_id,
                    sandbox_id=self.sandbox_id,
                    operation_type=OperationType.COMMAND_EXECUTE,
                    status=OperationStatus.FAILURE,
                    details={
                        "command": cmd,
                        "timeout": effective_timeout,
                        "error": str(e)
                    },
                    resource_usage=current_usage,
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                await self.audit_logger.log_operation(audit_log)

            raise

    async def read_file(self, path: str) -> str:
        """Reads a file from the container.

        Args:
            path: File path.

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file does not exist.
            RuntimeError: If read operation fails.
        """
        if not self.container:
            raise RuntimeError("Sandbox not initialized")

        try:
            # Get file archive
            resolved_path = self._safe_resolve_path(path)
            tar_stream, _ = await asyncio.to_thread(
                self.container.get_archive, resolved_path
            )

            # Read file content from tar stream
            content = await self._read_from_tar(tar_stream)
            return content.decode("utf-8")

        except NotFound:
            raise FileNotFoundError(f"File not found: {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {e}")

    async def write_file(self, path: str, content: str) -> None:
        """Writes content to a file in the container.

        Args:
            path: Target path.
            content: File content.

        Raises:
            RuntimeError: If write operation fails.
        """
        if not self.container:
            raise RuntimeError("Sandbox not initialized")

        try:
            resolved_path = self._safe_resolve_path(path)
            parent_dir = os.path.dirname(resolved_path)

            # Create parent directory
            if parent_dir:
                await self.run_command(f"mkdir -p {parent_dir}")

            # Prepare file data
            tar_stream = await self._create_tar_stream(
                os.path.basename(path), content.encode("utf-8")
            )

            # Write file
            await asyncio.to_thread(
                self.container.put_archive, parent_dir or "/", tar_stream
            )

        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")

    def _safe_resolve_path(self, path: str) -> str:
        """Safely resolves container path, preventing path traversal.

        Args:
            path: Original path.

        Returns:
            Resolved absolute path.

        Raises:
            ValueError: If path contains potentially unsafe patterns.
        """
        # Check for path traversal attempts
        if ".." in path.split("/"):
            raise ValueError("Path contains potentially unsafe patterns")

        resolved = (
            os.path.join(self.config.work_dir, path)
            if not os.path.isabs(path)
            else path
        )
        return resolved

    async def copy_from(self, src_path: str, dst_path: str) -> None:
        """Copies a file from the container.

        Args:
            src_path: Source file path (container).
            dst_path: Destination path (host).

        Raises:
            FileNotFoundError: If source file does not exist.
            RuntimeError: If copy operation fails.
        """
        try:
            # Ensure destination file's parent directory exists
            parent_dir = os.path.dirname(dst_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Get file stream
            resolved_src = self._safe_resolve_path(src_path)
            stream, stat = await asyncio.to_thread(
                self.container.get_archive, resolved_src
            )

            # Create temporary directory to extract file
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Write stream to temporary file
                tar_path = os.path.join(tmp_dir, "temp.tar")
                with open(tar_path, "wb") as f:
                    for chunk in stream:
                        f.write(chunk)

                # Extract file
                with tarfile.open(tar_path) as tar:
                    members = tar.getmembers()
                    if not members:
                        raise FileNotFoundError(f"Source file is empty: {src_path}")

                    # If destination is a directory, we should preserve relative path structure
                    if os.path.isdir(dst_path):
                        tar.extractall(dst_path)
                    else:
                        # If destination is a file, we only extract the source file's content
                        if len(members) > 1:
                            raise RuntimeError(
                                f"Source path is a directory but destination is a file: {src_path}"
                            )

                        with open(dst_path, "wb") as dst:
                            src_file = tar.extractfile(members[0])
                            if src_file is None:
                                raise RuntimeError(
                                    f"Failed to extract file: {src_path}"
                                )
                            dst.write(src_file.read())

        except docker.errors.NotFound:
            raise FileNotFoundError(f"Source file not found: {src_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to copy file: {e}")

    async def copy_to(self, src_path: str, dst_path: str) -> None:
        """Copies a file to the container.

        Args:
            src_path: Source file path (host).
            dst_path: Destination path (container).

        Raises:
            FileNotFoundError: If source file does not exist.
            RuntimeError: If copy operation fails.
        """
        try:
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"Source file not found: {src_path}")

            # Create destination directory in container
            resolved_dst = self._safe_resolve_path(dst_path)
            container_dir = os.path.dirname(resolved_dst)
            if container_dir:
                await self.run_command(f"mkdir -p {container_dir}")

            # Create tar file to upload
            with tempfile.TemporaryDirectory() as tmp_dir:
                tar_path = os.path.join(tmp_dir, "temp.tar")
                with tarfile.open(tar_path, "w") as tar:
                    # Handle directory source path
                    if os.path.isdir(src_path):
                        os.path.basename(src_path.rstrip("/"))
                        for root, _, files in os.walk(src_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.join(
                                    os.path.basename(dst_path),
                                    os.path.relpath(file_path, src_path),
                                )
                                tar.add(file_path, arcname=arcname)
                    else:
                        # Add single file to tar
                        tar.add(src_path, arcname=os.path.basename(dst_path))

                # Read tar file content
                with open(tar_path, "rb") as f:
                    data = f.read()

                # Upload to container
                await asyncio.to_thread(
                    self.container.put_archive,
                    os.path.dirname(resolved_dst) or "/",
                    data,
                )

                # Verify file was created successfully
                try:
                    await self.run_command(f"test -e {resolved_dst}")
                except Exception:
                    raise RuntimeError(f"Failed to verify file creation: {dst_path}")

        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to copy file: {e}")

    @staticmethod
    async def _create_tar_stream(name: str, content: bytes) -> io.BytesIO:
        """Creates a tar file stream.

        Args:
            name: Filename.
            content: File content.

        Returns:
            Tar file stream.
        """
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(name=name)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))
        tar_stream.seek(0)
        return tar_stream

    @staticmethod
    async def _read_from_tar(tar_stream) -> bytes:
        """Reads file content from a tar stream.

        Args:
            tar_stream: Tar file stream.

        Returns:
            File content.

        Raises:
            RuntimeError: If read operation fails.
        """
        with tempfile.NamedTemporaryFile() as tmp:
            for chunk in tar_stream:
                tmp.write(chunk)
            tmp.seek(0)

            with tarfile.open(fileobj=tmp) as tar:
                member = tar.next()
                if not member:
                    raise RuntimeError("Empty tar archive")

                file_content = tar.extractfile(member)
                if not file_content:
                    raise RuntimeError("Failed to extract file content")

                return file_content.read()

    async def cleanup(self) -> None:
        """Cleans up sandbox resources."""
        start_time = time.time()
        errors = []
        
        try:
            # Remove from resource monitor
            if self.monitor:
                self.monitor.remove_sandbox(self.sandbox_id)

            if self.terminal:
                try:
                    await self.terminal.close()
                except Exception as e:
                    errors.append(f"Terminal cleanup error: {e}")
                finally:
                    self.terminal = None

            if self.container:
                try:
                    await asyncio.to_thread(self.container.stop, timeout=5)
                except Exception as e:
                    errors.append(f"Container stop error: {e}")

                try:
                    await asyncio.to_thread(self.container.remove, force=True)
                except Exception as e:
                    errors.append(f"Container remove error: {e}")
                finally:
                    self.container = None

        except Exception as e:
            errors.append(f"General cleanup error: {e}")

        # Log cleanup operation
        duration_ms = int((time.time() - start_time) * 1000)
        if self.audit_logger:
            audit_log = AuditLog(
                timestamp=time.time(),
                agent_id=self.metadata.agent_id,
                sandbox_id=self.sandbox_id,
                operation_type=OperationType.SANDBOX_DELETE,
                status=OperationStatus.SUCCESS if not errors else OperationStatus.FAILURE,
                details={
                    "uptime_seconds": time.time() - self.metadata.created_at if self.metadata.created_at else 0,
                    "cleanup_errors": errors,
                    "last_activity": self.metadata.last_activity
                },
                duration_ms=duration_ms,
                error_message="; ".join(errors) if errors else None
            )
            await self.audit_logger.log_operation(audit_log)

        if errors:
            logger.warning(f"Errors during sandbox cleanup: {', '.join(errors)}")
        else:
            logger.info(f"Successfully cleaned up sandbox {self.sandbox_id}")

    def get_status(self) -> Dict[str, Any]:
        """Get current sandbox status.

        Returns:
            Dictionary with sandbox status information.
        """
        status = {
            "sandbox_id": self.sandbox_id,
            "agent_id": self.metadata.agent_id,
            "agent_version": self.metadata.agent_version,
            "created_at": self.metadata.created_at,
            "last_activity": self.metadata.last_activity,
            "is_initialized": self.container is not None and self.terminal is not None,
            "container_id": self.container.id if self.container else None,
            "config": {
                "image": self.config.image,
                "work_dir": self.config.work_dir,
                "memory_limit": self.config.memory_limit,
                "cpu_limit": self.config.cpu_limit,
                "timeout": self.config.timeout,
                "network_enabled": self.config.network_enabled
            },
            "resource_limits": {
                "cpu_percent": self.resource_limits.cpu_percent,
                "memory_mb": self.resource_limits.memory_mb,
                "disk_mb": self.resource_limits.disk_mb,
                "timeout_seconds": self.resource_limits.timeout_seconds
            },
            "volume_bindings": self.volume_bindings,
            "tags": self.metadata.tags
        }

        # Add container status if available
        if self.container:
            try:
                container_info = self.container.attrs
                status["container_status"] = {
                    "state": container_info["State"]["Status"],
                    "started_at": container_info["State"]["StartedAt"],
                    "finished_at": container_info["State"]["FinishedAt"],
                    "exit_code": container_info["State"]["ExitCode"],
                    "error": container_info["State"].get("Error")
                }
            except Exception as e:
                status["container_status"] = {"error": str(e)}

        return status

    async def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current resource metrics.

        Returns:
            Resource metrics or None if unavailable.
        """
        if self.monitor:
            return await self.monitor.get_sandbox_metrics(self.sandbox_id)
        return None

    async def __aenter__(self) -> "DockerSandbox":
        """Async context manager entry."""
        return await self.create()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()
