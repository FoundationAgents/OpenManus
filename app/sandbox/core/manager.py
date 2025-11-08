import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Set, Any, List

import docker
from docker.errors import APIError, ImageNotFound

from app.config import SandboxSettings
from app.logger import logger
from app.sandbox.core.sandbox import DockerSandbox, ResourceLimits
from app.sandbox.core.guardian import Guardian, get_guardian
from app.sandbox.core.monitor import ResourceMonitor
from app.sandbox.core.audit import AuditLogger, get_audit_logger


class SandboxManager:
    """Enhanced Docker sandbox manager.

    Manages multiple DockerSandbox instances lifecycle including creation,
    monitoring, and cleanup. Provides concurrent access control, automatic
    cleanup mechanisms, Guardian validation, resource monitoring, and
    audit logging for sandbox resources.

    Attributes:
        max_sandboxes: Maximum allowed number of sandboxes.
        idle_timeout: Sandbox idle timeout in seconds.
        cleanup_interval: Cleanup check interval in seconds.
        _sandboxes: Active sandbox instance mapping.
        _last_used: Last used time record for sandboxes.
        guardian: Guardian validation instance.
        monitor: Resource monitor instance.
        audit_logger: Audit logger instance.
    """

    def __init__(
        self,
        max_sandboxes: int = 100,
        idle_timeout: int = 3600,
        cleanup_interval: int = 300,
        guardian: Optional[Guardian] = None,
        monitor: Optional[ResourceMonitor] = None,
        audit_logger: Optional[AuditLogger] = None,
        auto_start_monitoring: bool = True,
    ):
        """Initializes sandbox manager.

        Args:
            max_sandboxes: Maximum sandbox count limit.
            idle_timeout: Idle timeout in seconds.
            cleanup_interval: Cleanup check interval in seconds.
            guardian: Guardian validation instance.
            monitor: Resource monitor instance.
            audit_logger: Audit logger instance.
            auto_start_monitoring: Whether to auto-start resource monitoring.
        """
        self.max_sandboxes = max_sandboxes
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval

        # Docker client
        self._client = docker.from_env()

        # Resource mappings
        self._sandboxes: Dict[str, DockerSandbox] = {}
        self._last_used: Dict[str, float] = {}
        self._agent_sandboxes: Dict[str, Set[str]] = {}  # agent_id -> set of sandbox_ids

        # Concurrency control
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._active_operations: Set[str] = set()

        # Enhanced features
        self.guardian = guardian or get_guardian()
        self.monitor = monitor or ResourceMonitor(audit_logger=audit_logger or get_audit_logger())
        self.audit_logger = audit_logger or get_audit_logger()

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_shutting_down = False

        # Start monitoring and cleanup
        if auto_start_monitoring:
            self.monitor.start_monitoring()
        self.start_cleanup_task()

    async def ensure_image(self, image: str) -> bool:
        """Ensures Docker image is available.

        Args:
            image: Image name.

        Returns:
            bool: Whether image is available.
        """
        try:
            self._client.images.get(image)
            return True
        except ImageNotFound:
            try:
                logger.info(f"Pulling image {image}...")
                await asyncio.get_event_loop().run_in_executor(
                    None, self._client.images.pull, image
                )
                return True
            except (APIError, Exception) as e:
                logger.error(f"Failed to pull image {image}: {e}")
                return False

    @asynccontextmanager
    async def sandbox_operation(self, sandbox_id: str):
        """Context manager for sandbox operations.

        Provides concurrency control and usage time updates.

        Args:
            sandbox_id: Sandbox ID.

        Raises:
            KeyError: If sandbox not found.
        """
        if sandbox_id not in self._locks:
            self._locks[sandbox_id] = asyncio.Lock()

        async with self._locks[sandbox_id]:
            if sandbox_id not in self._sandboxes:
                raise KeyError(f"Sandbox {sandbox_id} not found")

            self._active_operations.add(sandbox_id)
            try:
                self._last_used[sandbox_id] = asyncio.get_event_loop().time()
                yield self._sandboxes[sandbox_id]
            finally:
                self._active_operations.remove(sandbox_id)

    async def create_sandbox(
        self,
        config: Optional[SandboxSettings] = None,
        volume_bindings: Optional[Dict[str, str]] = None,
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Creates a new sandbox instance with enhanced features.

        Args:
            config: Sandbox configuration.
            volume_bindings: Volume mapping configuration.
            agent_id: Agent ID that will own this sandbox.
            agent_version: Agent version.
            resource_limits: Resource limits for this sandbox.
            tags: Additional metadata tags.

        Returns:
            str: Sandbox ID.

        Raises:
            RuntimeError: If max sandbox count reached or creation fails.
        """
        async with self._global_lock:
            if len(self._sandboxes) >= self.max_sandboxes:
                raise RuntimeError(
                    f"Maximum number of sandboxes ({self.max_sandboxes}) reached"
                )

            config = config or SandboxSettings()
            if not await self.ensure_image(config.image):
                raise RuntimeError(f"Failed to ensure Docker image: {config.image}")

            # Auto-approve agent if not already approved
            if agent_id and self.guardian and agent_id not in self.guardian.approved_agents:
                self.guardian.approve_agent(agent_id)

            try:
                sandbox = DockerSandbox(
                    config=config,
                    volume_bindings=volume_bindings,
                    agent_id=agent_id,
                    agent_version=agent_version,
                    guardian=self.guardian,
                    monitor=self.monitor,
                    audit_logger=self.audit_logger,
                    resource_limits=resource_limits,
                    tags=tags
                )
                await sandbox.create()

                sandbox_id = sandbox.sandbox_id
                self._sandboxes[sandbox_id] = sandbox
                self._last_used[sandbox_id] = asyncio.get_event_loop().time()
                self._locks[sandbox_id] = asyncio.Lock()

                # Track agent-sandbox relationship
                if agent_id:
                    if agent_id not in self._agent_sandboxes:
                        self._agent_sandboxes[agent_id] = set()
                    self._agent_sandboxes[agent_id].add(sandbox_id)

                logger.info(f"Created sandbox {sandbox_id} for agent {agent_id or 'unknown'}")
                return sandbox_id

            except Exception as e:
                logger.error(f"Failed to create sandbox: {e}")
                raise RuntimeError(f"Failed to create sandbox: {e}")

    async def get_agent_sandboxes(self, agent_id: str) -> List[str]:
        """Get all sandbox IDs for a specific agent.

        Args:
            agent_id: Agent ID.

        Returns:
            List of sandbox IDs belonging to the agent.
        """
        return list(self._agent_sandboxes.get(agent_id, set()))

    async def kill_agent_sandboxes(self, agent_id: str) -> int:
        """Kill all sandboxes belonging to an agent.

        Args:
            agent_id: Agent ID.

        Returns:
            Number of sandboxes killed.
        """
        sandbox_ids = self._agent_sandboxes.get(agent_id, set()).copy()
        killed_count = 0

        for sandbox_id in sandbox_ids:
            try:
                await self.delete_sandbox(sandbox_id)
                killed_count += 1
            except Exception as e:
                logger.error(f"Failed to kill sandbox {sandbox_id} for agent {agent_id}: {e}")

        return killed_count

    async def get_sandbox_metrics(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific sandbox.

        Args:
            sandbox_id: Sandbox ID.

        Returns:
            Sandbox metrics or None if not found.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox:
            return await sandbox.get_metrics()
        return None

    async def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for all agent sandboxes.

        Args:
            agent_id: Agent ID.

        Returns:
            Aggregated metrics for the agent.
        """
        sandbox_ids = self._agent_sandboxes.get(agent_id, set())
        metrics = {
            "agent_id": agent_id,
            "total_sandboxes": len(sandbox_ids),
            "sandbox_metrics": []
        }

        total_cpu = 0
        total_memory = 0
        active_sandboxes = 0

        for sandbox_id in sandbox_ids:
            sandbox_metrics = await self.get_sandbox_metrics(sandbox_id)
            if sandbox_metrics:
                metrics["sandbox_metrics"].append(sandbox_metrics)
                
                if sandbox_metrics.get("current_usage"):
                    usage = sandbox_metrics["current_usage"]
                    total_cpu += usage.get("cpu_percent", 0)
                    total_memory += usage.get("memory_mb", 0)
                    active_sandboxes += 1

        # Calculate averages
        if active_sandboxes > 0:
            metrics["aggregated_metrics"] = {
                "avg_cpu_percent": total_cpu / active_sandboxes,
                "avg_memory_mb": total_memory / active_sandboxes,
                "total_memory_mb": total_memory,
                "active_sandboxes": active_sandboxes
            }

        return metrics

    async def get_sandbox(self, sandbox_id: str) -> DockerSandbox:
        """Gets a sandbox instance.

        Args:
            sandbox_id: Sandbox ID.

        Returns:
            DockerSandbox: Sandbox instance.

        Raises:
            KeyError: If sandbox does not exist.
        """
        async with self.sandbox_operation(sandbox_id) as sandbox:
            return sandbox

    def start_cleanup_task(self) -> None:
        """Starts automatic cleanup task."""

        async def cleanup_loop():
            while not self._is_shutting_down:
                try:
                    await self._cleanup_idle_sandboxes()
                except Exception as e:
                    logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def _cleanup_idle_sandboxes(self) -> None:
        """Cleans up idle sandboxes."""
        current_time = asyncio.get_event_loop().time()
        to_cleanup = []

        async with self._global_lock:
            for sandbox_id, last_used in self._last_used.items():
                if (
                    sandbox_id not in self._active_operations
                    and current_time - last_used > self.idle_timeout
                ):
                    to_cleanup.append(sandbox_id)

        for sandbox_id in to_cleanup:
            try:
                await self.delete_sandbox(sandbox_id)
            except Exception as e:
                logger.error(f"Error cleaning up sandbox {sandbox_id}: {e}")

    async def cleanup(self) -> None:
        """Cleans up all resources."""
        logger.info("Starting manager cleanup...")
        self._is_shutting_down = True

        # Stop resource monitoring
        if self.monitor:
            self.monitor.stop_monitoring()

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Get all sandbox IDs to clean up
        async with self._global_lock:
            sandbox_ids = list(self._sandboxes.keys())

        # Concurrently clean up all sandboxes
        cleanup_tasks = []
        for sandbox_id in sandbox_ids:
            task = asyncio.create_task(self._safe_delete_sandbox(sandbox_id))
            cleanup_tasks.append(task)

        if cleanup_tasks:
            # Wait for all cleanup tasks to complete, with timeout to avoid infinite waiting
            try:
                await asyncio.wait(cleanup_tasks, timeout=30.0)
            except asyncio.TimeoutError:
                logger.error("Sandbox cleanup timed out")

        # Clean up remaining references
        self._sandboxes.clear()
        self._last_used.clear()
        self._locks.clear()
        self._active_operations.clear()
        self._agent_sandboxes.clear()

        logger.info("Manager cleanup completed")

    async def _safe_delete_sandbox(self, sandbox_id: str) -> None:
        """Safely deletes a single sandbox.

        Args:
            sandbox_id: Sandbox ID to delete.
        """
        try:
            if sandbox_id in self._active_operations:
                logger.warning(
                    f"Sandbox {sandbox_id} has active operations, waiting for completion"
                )
                for _ in range(10):  # Wait at most 10 times
                    await asyncio.sleep(0.5)
                    if sandbox_id not in self._active_operations:
                        break
                else:
                    logger.warning(
                        f"Timeout waiting for sandbox {sandbox_id} operations to complete"
                    )

            # Get reference to sandbox object
            sandbox = self._sandboxes.get(sandbox_id)
            if sandbox:
                await sandbox.cleanup()

                # Remove sandbox record from manager
                async with self._global_lock:
                    self._sandboxes.pop(sandbox_id, None)
                    self._last_used.pop(sandbox_id, None)
                    self._locks.pop(sandbox_id, None)

                    # Remove from agent tracking
                    agent_id = sandbox.metadata.agent_id
                    if agent_id and agent_id in self._agent_sandboxes:
                        self._agent_sandboxes[agent_id].discard(sandbox_id)
                        if not self._agent_sandboxes[agent_id]:
                            self._agent_sandboxes.pop(agent_id, None)

                    logger.info(f"Deleted sandbox {sandbox_id} (agent: {agent_id})")
        except Exception as e:
            logger.error(f"Error during cleanup of sandbox {sandbox_id}: {e}")

    async def delete_sandbox(self, sandbox_id: str) -> None:
        """Deletes specified sandbox.

        Args:
            sandbox_id: Sandbox ID.
        """
        if sandbox_id not in self._sandboxes:
            return

        try:
            await self._safe_delete_sandbox(sandbox_id)
        except Exception as e:
            logger.error(f"Failed to delete sandbox {sandbox_id}: {e}")

    async def __aenter__(self) -> "SandboxManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()

    def get_stats(self) -> Dict:
        """Gets enhanced manager statistics.

        Returns:
            Dict: Statistics information.
        """
        stats = {
            "total_sandboxes": len(self._sandboxes),
            "active_operations": len(self._active_operations),
            "max_sandboxes": self.max_sandboxes,
            "idle_timeout": self.idle_timeout,
            "cleanup_interval": self.cleanup_interval,
            "is_shutting_down": self._is_shutting_down,
            "total_agents": len(self._agent_sandboxes),
            "agent_sandbox_counts": {
                agent_id: len(sandbox_ids)
                for agent_id, sandbox_ids in self._agent_sandboxes.items()
            }
        }

        # Add Guardian statistics
        if self.guardian:
            stats["guardian"] = self.guardian.get_security_summary()

        # Add monitoring statistics
        if self.monitor:
            stats["monitoring"] = self.monitor.get_monitoring_stats()

        return stats

    async def get_comprehensive_stats(self) -> Dict:
        """Get comprehensive statistics including metrics.

        Returns:
            Dict: Comprehensive statistics with metrics.
        """
        stats = self.get_stats()

        # Add detailed metrics for all sandboxes
        sandbox_metrics = []
        for sandbox_id in self._sandboxes.keys():
            metrics = await self.get_sandbox_metrics(sandbox_id)
            if metrics:
                sandbox_metrics.append(metrics)

        stats["sandbox_metrics"] = sandbox_metrics

        # Add agent summaries
        agent_summaries = {}
        for agent_id in self._agent_sandboxes.keys():
            if self.audit_logger:
                summary = await self.audit_logger.get_agent_summary(agent_id, days=1)
                agent_summaries[agent_id] = summary

        stats["agent_summaries"] = agent_summaries

        # Add audit database statistics
        if self.audit_logger:
            stats["audit_database"] = await self.audit_logger.get_database_stats()

        return stats
