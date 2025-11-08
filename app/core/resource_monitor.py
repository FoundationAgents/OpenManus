"""
Resource Monitor
Monitor system resources (CPU, memory) to prevent overloading.
"""

import psutil
import threading
import time
from dataclasses import dataclass
from typing import List, Optional

from app.logger import logger


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_available_mb: int
    memory_used_mb: int
    memory_percent: float
    memory_total_mb: int


@dataclass
class ResourceRecommendation:
    """Recommendation for component loading based on available resources."""
    can_load: bool
    reason: str
    available_memory_mb: int
    required_memory_mb: int
    recommended_components: List[str]
    skip_components: List[str]


class ResourceMonitor:
    """
    Monitor system resources and provide recommendations for component loading.
    """
    
    def __init__(self, min_available_memory_mb: int = 512, max_cpu_percent: float = 80.0):
        self.min_available_memory_mb = min_available_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self._lock = threading.RLock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._snapshots: List[ResourceSnapshot] = []
        self._max_snapshots = 100
    
    def get_current_snapshot(self) -> ResourceSnapshot:
        """Get current system resource snapshot."""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_available_mb=memory.available // (1024 * 1024),
            memory_used_mb=memory.used // (1024 * 1024),
            memory_percent=memory.percent,
            memory_total_mb=memory.total // (1024 * 1024)
        )
    
    def get_available_memory_mb(self) -> int:
        """Get available memory in MB."""
        return psutil.virtual_memory().available // (1024 * 1024)
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    def is_resource_available(self, required_memory_mb: int) -> bool:
        """Check if required resources are available."""
        available_memory = self.get_available_memory_mb()
        cpu_usage = self.get_cpu_usage()
        
        # Check memory
        if available_memory < required_memory_mb + self.min_available_memory_mb:
            return False
        
        # Check CPU
        if cpu_usage > self.max_cpu_percent:
            return False
        
        return True
    
    def get_recommendation(
        self,
        components: List[str],
        resource_requirements: dict
    ) -> ResourceRecommendation:
        """
        Get recommendation for loading components based on available resources.
        
        Args:
            components: List of component names to load
            resource_requirements: Dict mapping component name to required memory in MB
        
        Returns:
            ResourceRecommendation with loading recommendations
        """
        snapshot = self.get_current_snapshot()
        available_memory = snapshot.memory_available_mb - self.min_available_memory_mb
        
        total_required = sum(resource_requirements.get(c, 0) for c in components)
        
        # Check if all components can be loaded
        if available_memory >= total_required:
            return ResourceRecommendation(
                can_load=True,
                reason="Sufficient resources available",
                available_memory_mb=available_memory,
                required_memory_mb=total_required,
                recommended_components=components,
                skip_components=[]
            )
        
        # Need to prioritize components
        # Sort by requirement (load smaller first)
        sorted_components = sorted(
            components,
            key=lambda c: resource_requirements.get(c, 0)
        )
        
        recommended = []
        skip = []
        used = 0
        
        for component in sorted_components:
            requirement = resource_requirements.get(component, 0)
            if used + requirement <= available_memory:
                recommended.append(component)
                used += requirement
            else:
                skip.append(component)
        
        reason = f"Limited resources: {available_memory}MB available, {total_required}MB required"
        
        return ResourceRecommendation(
            can_load=len(recommended) > 0,
            reason=reason,
            available_memory_mb=available_memory,
            required_memory_mb=total_required,
            recommended_components=recommended,
            skip_components=skip
        )
    
    def start_monitoring(self, interval: float = 5.0):
        """Start background resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop background resource monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                snapshot = self.get_current_snapshot()
                with self._lock:
                    self._snapshots.append(snapshot)
                    if len(self._snapshots) > self._max_snapshots:
                        self._snapshots.pop(0)
                
                # Log warnings if resources are low
                if snapshot.memory_available_mb < self.min_available_memory_mb * 2:
                    logger.warning(
                        f"Low memory: {snapshot.memory_available_mb}MB available "
                        f"({snapshot.memory_percent:.1f}% used)"
                    )
                
                if snapshot.cpu_percent > self.max_cpu_percent:
                    logger.warning(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
            
            time.sleep(interval)
    
    def get_snapshots(self, last_n: Optional[int] = None) -> List[ResourceSnapshot]:
        """Get resource snapshots."""
        with self._lock:
            if last_n:
                return self._snapshots[-last_n:]
            return self._snapshots.copy()
    
    def get_average_usage(self, last_n: int = 10) -> tuple:
        """Get average CPU and memory usage over last N snapshots."""
        snapshots = self.get_snapshots(last_n)
        if not snapshots:
            return 0.0, 0.0
        
        avg_cpu = sum(s.cpu_percent for s in snapshots) / len(snapshots)
        avg_memory = sum(s.memory_percent for s in snapshots) / len(snapshots)
        
        return avg_cpu, avg_memory
    
    def format_recommendation(self, recommendation: ResourceRecommendation) -> str:
        """Format recommendation as human-readable string."""
        lines = [
            f"Available RAM: {recommendation.available_memory_mb}MB",
            f"Required RAM: {recommendation.required_memory_mb}MB",
            "",
            "Recommended components:"
        ]
        
        for comp in recommendation.recommended_components:
            lines.append(f"  ✓ {comp}")
        
        if recommendation.skip_components:
            lines.append("")
            lines.append("Skip components (insufficient resources):")
            for comp in recommendation.skip_components:
                lines.append(f"  ✗ {comp}")
        
        return "\n".join(lines)


# Global singleton
_monitor = None
_monitor_lock = threading.Lock()


def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor singleton."""
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = ResourceMonitor()
    return _monitor
