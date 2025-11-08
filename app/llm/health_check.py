"""
Connection health check for LLM API endpoints.

Performs:
- On startup: quick test call
- Periodic: every 5 minutes
- Status tracking: Connected, Slow, Disconnected
- Auto-recovery when back online
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional, List

from app.logger import logger
from app.llm.api_client import OpenAICompatibleClient, APIClientError


class HealthStatus(Enum):
    """Health check status."""
    CONNECTED = "connected"
    SLOW = "slow"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


class EndpointHealth:
    """Health status for a single endpoint."""

    def __init__(self, endpoint_url: str, model: str):
        self.endpoint_url = endpoint_url
        self.model = model
        self.status = HealthStatus.UNKNOWN
        self.last_check_time = 0
        self.response_time_ms = 0
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "endpoint": self.endpoint_url,
            "model": self.model,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "last_check": self.last_check_time,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
        }


class HealthChecker:
    """
    Performs health checks on API endpoints.
    """

    def __init__(
        self,
        check_interval: int = 300,  # 5 minutes
        timeout: int = 10,
        slow_threshold_ms: int = 500,
        fast_threshold_ms: int = 2000,
    ):
        """
        Initialize health checker.

        Args:
            check_interval: Seconds between health checks
            timeout: Request timeout for health check
            slow_threshold_ms: Response time threshold for "slow" status
            fast_threshold_ms: Response time threshold for "disconnected" status
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.slow_threshold_ms = slow_threshold_ms
        self.fast_threshold_ms = fast_threshold_ms

        self.endpoints: Dict[str, EndpointHealth] = {}
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

    def register_endpoint(self, endpoint_url: str, model: str):
        """
        Register an endpoint for health monitoring.

        Args:
            endpoint_url: API endpoint URL
            model: Model name
        """
        if endpoint_url not in self.endpoints:
            self.endpoints[endpoint_url] = EndpointHealth(endpoint_url, model)
            logger.info(f"Registered endpoint for health monitoring: {endpoint_url}")

    async def check_endpoint(self, endpoint_url: str) -> HealthStatus:
        """
        Perform a health check on an endpoint.

        Args:
            endpoint_url: API endpoint URL

        Returns:
            HealthStatus value
        """
        if endpoint_url not in self.endpoints:
            self.register_endpoint(endpoint_url, "unknown")

        health = self.endpoints[endpoint_url]

        try:
            client = OpenAICompatibleClient(
                endpoint=endpoint_url,
                model=health.model,
                timeout=self.timeout,
            )

            start_time = time.time()
            is_healthy = await client.health_check()
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            await client.close()

            health.response_time_ms = response_time
            health.last_check_time = time.time()
            health.consecutive_failures = 0
            health.last_error = None

            # Determine status based on response time
            if response_time < self.slow_threshold_ms:
                health.status = HealthStatus.CONNECTED
            elif response_time < self.fast_threshold_ms:
                health.status = HealthStatus.SLOW
            else:
                health.status = HealthStatus.DISCONNECTED

            logger.debug(
                f"Health check: {endpoint_url} - {health.status.value} ({response_time:.0f}ms)"
            )

        except asyncio.TimeoutError:
            health.consecutive_failures += 1
            health.status = HealthStatus.DISCONNECTED
            health.last_error = "Timeout"
            logger.warning(f"Health check timeout: {endpoint_url}")

        except APIClientError as e:
            health.consecutive_failures += 1
            health.status = HealthStatus.DISCONNECTED
            health.last_error = str(e)
            logger.warning(f"Health check failed: {endpoint_url} - {e}")

        except Exception as e:
            health.consecutive_failures += 1
            health.status = HealthStatus.UNKNOWN
            health.last_error = str(e)
            logger.error(f"Health check error: {endpoint_url} - {e}")

        return health.status

    async def start_monitoring(self):
        """Start periodic health monitoring."""
        if self.is_monitoring:
            logger.warning("Health monitoring already running")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Started health monitoring (interval: {self.check_interval}s)")

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped health monitoring")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check all registered endpoints
                for endpoint_url in list(self.endpoints.keys()):
                    await self.check_endpoint(endpoint_url)

                # Sleep before next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    def get_status(self, endpoint_url: Optional[str] = None) -> Dict:
        """
        Get health status.

        Args:
            endpoint_url: Specific endpoint to check, or None for all

        Returns:
            Health status dictionary
        """
        if endpoint_url:
            if endpoint_url in self.endpoints:
                return self.endpoints[endpoint_url].to_dict()
            return {"error": "Endpoint not found"}

        # Return all endpoints
        return {
            "monitoring": self.is_monitoring,
            "endpoints": [h.to_dict() for h in self.endpoints.values()],
        }

    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.

        Returns:
            HealthStatus value (best of all endpoints)
        """
        if not self.endpoints:
            return HealthStatus.UNKNOWN

        statuses = [h.status for h in self.endpoints.values()]

        # Return best status
        if HealthStatus.CONNECTED in statuses:
            return HealthStatus.CONNECTED
        elif HealthStatus.SLOW in statuses:
            return HealthStatus.SLOW
        elif HealthStatus.DISCONNECTED in statuses:
            return HealthStatus.DISCONNECTED
        else:
            return HealthStatus.UNKNOWN

    def get_status_emoji(self, status: Optional[HealthStatus] = None) -> str:
        """Get emoji representation of health status."""
        if status is None:
            status = self.get_overall_status()

        emojis = {
            HealthStatus.CONNECTED: "🟢",
            HealthStatus.SLOW: "🟡",
            HealthStatus.DISCONNECTED: "🔴",
            HealthStatus.UNKNOWN: "⚪",
        }
        return emojis.get(status, "⚪")

    def get_available_endpoints(self) -> List[str]:
        """Get list of available (connected) endpoints."""
        available = []
        for endpoint_url, health in self.endpoints.items():
            if health.status in (HealthStatus.CONNECTED, HealthStatus.SLOW):
                available.append(endpoint_url)
        return available

    def reset_failures(self, endpoint_url: str):
        """Reset failure counter for an endpoint."""
        if endpoint_url in self.endpoints:
            self.endpoints[endpoint_url].consecutive_failures = 0
            logger.info(f"Reset failures for endpoint: {endpoint_url}")
