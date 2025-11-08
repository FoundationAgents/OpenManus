"""
Graceful Degradation System

Enables the system to continue operating with reduced functionality when
components fail or resources are constrained.
"""

import asyncio
import threading
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Callable, List

from pydantic import BaseModel

from app.logger import logger


class DegradationLevel(str, Enum):
    """Degradation level enumeration"""
    NORMAL = "normal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class ComponentFallback(BaseModel):
    """Component fallback configuration"""
    component_name: str
    fallback_type: str  # "knowledge_base", "template", "cache", "offline"
    enabled: bool = True
    description: str = ""


class GracefulDegradationManager:
    """Manages graceful degradation of components"""

    def __init__(self):
        self._lock = threading.RLock()
        self._degradation_level = DegradationLevel.NORMAL
        self._failed_components: Dict[str, datetime] = {}
        self._fallbacks: Dict[str, ComponentFallback] = {}
        self._recovery_tasks: Dict[str, asyncio.Task] = {}
        self._component_handlers: Dict[str, Callable] = {}

    def register_component_handler(self, component_name: str, handler: Callable):
        """Register a handler for component recovery"""
        with self._lock:
            self._component_handlers[component_name] = handler
            logger.debug(f"Registered component handler: {component_name}")

    def register_fallback(self, fallback: ComponentFallback):
        """Register a fallback strategy"""
        with self._lock:
            self._fallbacks[fallback.component_name] = fallback
            logger.info(f"Registered fallback for {fallback.component_name}: {fallback.fallback_type}")

    async def handle_component_failure(
        self, component_name: str, error: Exception, reason: str = ""
    ):
        """Handle a component failure with fallback"""
        try:
            with self._lock:
                self._failed_components[component_name] = datetime.now()

            logger.error(
                f"Component failure: {component_name} - {reason or str(error)}"
            )

            # Update degradation level
            self._update_degradation_level()

            # Trigger fallback if available
            fallback = self._fallbacks.get(component_name)
            if fallback and fallback.enabled:
                await self._activate_fallback(fallback)

            # Start recovery task
            if component_name not in self._recovery_tasks:
                self._recovery_tasks[component_name] = asyncio.create_task(
                    self._attempt_recovery(component_name)
                )

        except Exception as e:
            logger.error(f"Failed to handle component failure: {e}")

    async def _activate_fallback(self, fallback: ComponentFallback):
        """Activate a fallback strategy"""
        try:
            if fallback.fallback_type == "knowledge_base":
                logger.info(
                    f"Activated knowledge base fallback for {fallback.component_name}"
                )
                # Use knowledge base instead of LLM
            elif fallback.fallback_type == "template":
                logger.info(
                    f"Activated template fallback for {fallback.component_name}"
                )
                # Use pre-defined templates
            elif fallback.fallback_type == "cache":
                logger.info(
                    f"Activated cache fallback for {fallback.component_name}"
                )
                # Use cached responses
            elif fallback.fallback_type == "offline":
                logger.info(
                    f"Activated offline mode for {fallback.component_name}"
                )
                # Go into offline mode
        except Exception as e:
            logger.error(f"Failed to activate fallback: {e}")

    async def _attempt_recovery(self, component_name: str):
        """Attempt to recover a failed component"""
        try:
            max_attempts = 5
            backoff_seconds = 10

            for attempt in range(max_attempts):
                try:
                    await asyncio.sleep(backoff_seconds * (attempt + 1))

                    # Call component-specific recovery handler
                    if component_name in self._component_handlers:
                        handler = self._component_handlers[component_name]
                        success = await handler()

                        if success:
                            with self._lock:
                                del self._failed_components[component_name]
                            self._update_degradation_level()
                            logger.info(
                                f"Component recovered: {component_name}"
                            )
                            return

                except Exception as e:
                    logger.debug(
                        f"Recovery attempt {attempt + 1} failed for {component_name}: {e}"
                    )

            logger.error(
                f"Failed to recover {component_name} after {max_attempts} attempts"
            )

        except Exception as e:
            logger.error(f"Error in recovery loop: {e}")
        finally:
            with self._lock:
                self._recovery_tasks.pop(component_name, None)

    def _update_degradation_level(self):
        """Update the overall degradation level based on failed components"""
        with self._lock:
            failed_count = len(self._failed_components)
            critical_components = {"llm", "database"}
            failed_critical = any(
                c in critical_components for c in self._failed_components
            )

            if failed_count == 0:
                self._degradation_level = DegradationLevel.NORMAL
            elif failed_critical:
                self._degradation_level = DegradationLevel.CRITICAL
            elif failed_count >= 3:
                self._degradation_level = DegradationLevel.CRITICAL
            else:
                self._degradation_level = DegradationLevel.DEGRADED

    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status"""
        with self._lock:
            return {
                "level": self._degradation_level.value,
                "failed_components": list(self._failed_components.keys()),
                "failed_count": len(self._failed_components),
                "recovery_in_progress": list(self._recovery_tasks.keys()),
                "timestamp": datetime.now().isoformat(),
            }

    def is_degraded(self) -> bool:
        """Check if system is in degraded mode"""
        return self._degradation_level != DegradationLevel.NORMAL

    def is_critical(self) -> bool:
        """Check if system is in critical state"""
        return self._degradation_level == DegradationLevel.CRITICAL

    def is_component_failed(self, component_name: str) -> bool:
        """Check if a component has failed"""
        with self._lock:
            return component_name in self._failed_components

    async def wait_for_recovery(self, component_name: str, timeout: int = 300):
        """Wait for a component to recover"""
        try:
            start_time = datetime.now()

            while True:
                with self._lock:
                    if component_name not in self._failed_components:
                        return True

                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    return False

                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error waiting for recovery: {e}")
            return False

    def get_degraded_capabilities(self) -> Dict[str, bool]:
        """Get available capabilities in current degradation state"""
        with self._lock:
            return {
                "llm_available": "llm" not in self._failed_components,
                "database_available": "database" not in self._failed_components,
                "web_search_available": "web_search" not in self._failed_components,
                "sandbox_available": "sandbox" not in self._failed_components,
                "cache_available": True,  # Cache is always available
                "offline_mode": self._degradation_level == DegradationLevel.OFFLINE,
            }

    async def shutdown_degraded_components(self):
        """Gracefully shutdown non-essential components in critical state"""
        if self.is_critical():
            try:
                logger.warning("Shutting down non-essential components")
                # This would be called to reduce resource usage
                # Implementation depends on specific components
            except Exception as e:
                logger.error(f"Error shutting down components: {e}")
