"""
Smart Startup
Intelligent component loading orchestrator for fast startup.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from app.core.component_registry import ComponentStatus, get_component_registry
from app.core.error_isolation import get_error_isolation
from app.core.lazy_loader import get_lazy_loader
from app.core.parallel_loader import get_parallel_loader
from app.core.resource_monitor import get_resource_monitor
from app.core.startup_detection import get_startup_detection
from app.logger import logger


@dataclass
class StartupPhase:
    """Information about a startup phase."""
    name: str
    components: List[str]
    duration_ms: float = 0.0
    success: bool = True


@dataclass
class StartupReport:
    """Report of startup process."""
    total_duration_ms: float
    phases: List[StartupPhase]
    successful_components: List[str]
    failed_components: List[str]
    skipped_components: List[str]
    success: bool


class SmartStartup:
    """
    Intelligent component loading orchestrator.
    Loads components in optimal order with resource awareness.
    """
    
    def __init__(self):
        self.registry = get_component_registry()
        self.resource_monitor = get_resource_monitor()
        self.error_isolation = get_error_isolation()
        self.lazy_loader = get_lazy_loader()
        self.parallel_loader = get_parallel_loader()
        self.startup_detection = get_startup_detection()
        self._progress_callback: Optional[Callable[[str, float], None]] = None
    
    def startup(
        self,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> StartupReport:
        """
        Execute smart startup sequence.
        
        Args:
            on_progress: Progress callback (phase_name, progress_percent)
        
        Returns:
            StartupReport with startup results
        """
        logger.info("=" * 60)
        logger.info("Starting Smart Component Auto-Loading System")
        logger.info("=" * 60)
        
        self._progress_callback = on_progress
        start_time = time.time()
        
        phases: List[StartupPhase] = []
        successful = []
        failed = []
        skipped = []
        
        # Phase 1: Start resource monitoring
        phase = self._phase_start_monitoring()
        phases.append(phase)
        
        # Phase 2: Detect user intent
        phase = self._phase_detect_intent()
        phases.append(phase)
        
        # Phase 3: Load essential components
        phase = self._phase_load_essentials()
        phases.append(phase)
        successful.extend([c for c in phase.components if self.registry.is_loaded(c)])
        failed.extend([c for c in phase.components if not self.registry.is_loaded(c)])
        
        # Phase 4: Check resources and load recommended components
        recommended = self.startup_detection.get_recommended_components()
        
        # Remove already loaded components
        to_load = [c for c in recommended if not self.registry.is_loaded(c)]
        
        if to_load:
            phase = self._phase_load_recommended(to_load)
            phases.append(phase)
            successful.extend([c for c in phase.components if self.registry.is_loaded(c)])
            failed.extend([c for c in phase.components if not self.registry.is_loaded(c)])
        
        # Phase 5: Finalize startup
        phase = self._phase_finalize()
        phases.append(phase)
        
        total_duration = (time.time() - start_time) * 1000
        
        report = StartupReport(
            total_duration_ms=total_duration,
            phases=phases,
            successful_components=list(set(successful)),
            failed_components=list(set(failed)),
            skipped_components=skipped,
            success=len(failed) == 0
        )
        
        self._log_startup_report(report)
        
        return report
    
    async def startup_async(
        self,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> StartupReport:
        """
        Execute smart startup sequence asynchronously.
        
        Args:
            on_progress: Progress callback (phase_name, progress_percent)
        
        Returns:
            StartupReport with startup results
        """
        logger.info("=" * 60)
        logger.info("Starting Smart Component Auto-Loading System (Async)")
        logger.info("=" * 60)
        
        self._progress_callback = on_progress
        start_time = time.time()
        
        phases: List[StartupPhase] = []
        successful = []
        failed = []
        skipped = []
        
        # Phase 1: Start resource monitoring
        phase = self._phase_start_monitoring()
        phases.append(phase)
        
        # Phase 2: Detect user intent
        phase = self._phase_detect_intent()
        phases.append(phase)
        
        # Phase 3: Load essential components in parallel
        phase = await self._phase_load_essentials_async()
        phases.append(phase)
        successful.extend([c for c in phase.components if self.registry.is_loaded(c)])
        failed.extend([c for c in phase.components if not self.registry.is_loaded(c)])
        
        # Phase 4: Load recommended components in parallel
        recommended = self.startup_detection.get_recommended_components()
        to_load = [c for c in recommended if not self.registry.is_loaded(c)]
        
        if to_load:
            phase = await self._phase_load_recommended_async(to_load)
            phases.append(phase)
            successful.extend([c for c in phase.components if self.registry.is_loaded(c)])
            failed.extend([c for c in phase.components if not self.registry.is_loaded(c)])
        
        # Phase 5: Finalize startup
        phase = self._phase_finalize()
        phases.append(phase)
        
        total_duration = (time.time() - start_time) * 1000
        
        report = StartupReport(
            total_duration_ms=total_duration,
            phases=phases,
            successful_components=list(set(successful)),
            failed_components=list(set(failed)),
            skipped_components=skipped,
            success=len(failed) == 0
        )
        
        self._log_startup_report(report)
        
        return report
    
    def _phase_start_monitoring(self) -> StartupPhase:
        """Phase 1: Start resource monitoring."""
        phase_name = "Resource Monitoring"
        logger.info(f"Phase 1: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        self.resource_monitor.start_monitoring()
        duration = (time.time() - start) * 1000
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=[],
            duration_ms=duration,
            success=True
        )
    
    def _phase_detect_intent(self) -> StartupPhase:
        """Phase 2: Detect user intent."""
        phase_name = "Intent Detection"
        logger.info(f"Phase 2: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        intent = self.startup_detection.detect_intent()
        duration = (time.time() - start) * 1000
        
        logger.info(f"Detected intent: {intent.intent_type} (confidence: {intent.confidence * 100:.0f}%)")
        logger.info(f"Description: {intent.description}")
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=[],
            duration_ms=duration,
            success=True
        )
    
    def _phase_load_essentials(self) -> StartupPhase:
        """Phase 3: Load essential components."""
        phase_name = "Load Essentials"
        logger.info(f"Phase 3: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        essentials = self.startup_detection.get_essential_components()
        
        logger.info(f"Loading {len(essentials)} essential components in parallel")
        
        results = self.parallel_loader.load_components_parallel(
            essentials,
            on_progress=self._create_component_progress_callback(phase_name)
        )
        
        duration = (time.time() - start) * 1000
        success = all(s for s, _, _ in results.values())
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=essentials,
            duration_ms=duration,
            success=success
        )
    
    async def _phase_load_essentials_async(self) -> StartupPhase:
        """Phase 3: Load essential components asynchronously."""
        phase_name = "Load Essentials"
        logger.info(f"Phase 3: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        essentials = self.startup_detection.get_essential_components()
        
        logger.info(f"Loading {len(essentials)} essential components in parallel (async)")
        
        results = await self.parallel_loader.load_components_parallel_async(
            essentials,
            on_progress=self._create_component_progress_callback(phase_name)
        )
        
        duration = (time.time() - start) * 1000
        success = all(s for s, _, _ in results.values())
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=essentials,
            duration_ms=duration,
            success=success
        )
    
    def _phase_load_recommended(self, components: List[str]) -> StartupPhase:
        """Phase 4: Load recommended components with resource checks."""
        phase_name = "Load Recommended"
        logger.info(f"Phase 4: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        
        # Get resource requirements
        requirements = {
            c: self.registry.get_component(c).resource_requirement_mb
            for c in components
            if self.registry.get_component(c)
        }
        
        # Get recommendation
        recommendation = self.resource_monitor.get_recommendation(components, requirements)
        
        if recommendation.skip_components:
            logger.warning(
                f"Skipping {len(recommendation.skip_components)} components due to resource constraints"
            )
            for comp in recommendation.skip_components:
                logger.warning(f"  - {comp}")
        
        # Load recommended components
        to_load = recommendation.recommended_components
        logger.info(f"Loading {len(to_load)} recommended components in parallel")
        
        results = self.parallel_loader.load_components_parallel(
            to_load,
            on_progress=self._create_component_progress_callback(phase_name)
        )
        
        duration = (time.time() - start) * 1000
        success = all(s for s, _, _ in results.values())
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=to_load,
            duration_ms=duration,
            success=success
        )
    
    async def _phase_load_recommended_async(self, components: List[str]) -> StartupPhase:
        """Phase 4: Load recommended components asynchronously with resource checks."""
        phase_name = "Load Recommended"
        logger.info(f"Phase 4: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        
        # Get resource requirements
        requirements = {
            c: self.registry.get_component(c).resource_requirement_mb
            for c in components
            if self.registry.get_component(c)
        }
        
        # Get recommendation
        recommendation = self.resource_monitor.get_recommendation(components, requirements)
        
        if recommendation.skip_components:
            logger.warning(
                f"Skipping {len(recommendation.skip_components)} components due to resource constraints"
            )
            for comp in recommendation.skip_components:
                logger.warning(f"  - {comp}")
        
        # Load recommended components
        to_load = recommendation.recommended_components
        logger.info(f"Loading {len(to_load)} recommended components in parallel (async)")
        
        results = await self.parallel_loader.load_components_parallel_async(
            to_load,
            on_progress=self._create_component_progress_callback(phase_name)
        )
        
        duration = (time.time() - start) * 1000
        success = all(s for s, _, _ in results.values())
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=to_load,
            duration_ms=duration,
            success=success
        )
    
    def _phase_finalize(self) -> StartupPhase:
        """Phase 5: Finalize startup."""
        phase_name = "Finalize"
        logger.info(f"Phase 5: {phase_name}")
        self._notify_progress(phase_name, 0.0)
        
        start = time.time()
        
        # Log component status
        all_components = self.registry.get_all_components()
        loaded_count = sum(1 for c in all_components if c.status == ComponentStatus.LOADED)
        
        logger.info(f"Startup complete: {loaded_count}/{len(all_components)} components loaded")
        
        duration = (time.time() - start) * 1000
        
        self._notify_progress(phase_name, 100.0)
        
        return StartupPhase(
            name=phase_name,
            components=[],
            duration_ms=duration,
            success=True
        )
    
    def _create_component_progress_callback(self, phase_name: str) -> Callable:
        """Create a progress callback for component loading."""
        def callback(component_name: str, progress: float):
            if self._progress_callback:
                self._progress_callback(f"{phase_name}: {component_name}", progress)
        return callback
    
    def _notify_progress(self, phase_name: str, progress: float):
        """Notify progress callback."""
        if self._progress_callback:
            self._progress_callback(phase_name, progress)
    
    def _log_startup_report(self, report: StartupReport):
        """Log detailed startup report."""
        logger.info("=" * 60)
        logger.info("Startup Report")
        logger.info("=" * 60)
        logger.info(f"Total duration: {report.total_duration_ms:.1f}ms ({report.total_duration_ms / 1000:.2f}s)")
        logger.info(f"Status: {'SUCCESS' if report.success else 'PARTIAL SUCCESS'}")
        logger.info("")
        
        logger.info("Phases:")
        for i, phase in enumerate(report.phases, 1):
            status = "✓" if phase.success else "✗"
            logger.info(f"  {i}. {status} {phase.name}: {phase.duration_ms:.1f}ms")
            if phase.components:
                logger.info(f"     Components: {len(phase.components)}")
        
        logger.info("")
        logger.info(f"Successful components ({len(report.successful_components)}):")
        for comp in sorted(report.successful_components):
            logger.info(f"  ✓ {comp}")
        
        if report.failed_components:
            logger.info("")
            logger.info(f"Failed components ({len(report.failed_components)}):")
            for comp in sorted(report.failed_components):
                error = self.error_isolation.get_error(comp)
                error_msg = str(error.error) if error else "Unknown error"
                logger.error(f"  ✗ {comp}: {error_msg}")
        
        if report.skipped_components:
            logger.info("")
            logger.info(f"Skipped components ({len(report.skipped_components)}):")
            for comp in sorted(report.skipped_components):
                logger.info(f"  - {comp}")
        
        logger.info("=" * 60)


# Global singleton
_smart_startup = None


def get_smart_startup() -> SmartStartup:
    """Get the global smart startup singleton."""
    global _smart_startup
    if _smart_startup is None:
        _smart_startup = SmartStartup()
    return _smart_startup
