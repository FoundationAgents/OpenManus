"""
Startup Profiler
Measure and analyze component load times and startup performance.
"""

import json
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.component_registry import get_component_registry
from app.logger import logger


@dataclass
class ComponentProfile:
    """Performance profile for a component."""
    component_name: str
    load_time_ms: float
    resource_requirement_mb: int
    dependencies: List[str]
    status: str
    timestamp: str
    is_blocking: bool = True
    load_order: int = 0


@dataclass
class StartupProfile:
    """Complete startup performance profile."""
    total_duration_ms: float
    component_count: int
    successful_count: int
    failed_count: int
    parallel_efficiency: float
    bottleneck_components: List[str]
    optimization_suggestions: List[str]
    components: List[ComponentProfile]
    timestamp: str


class StartupProfiler:
    """
    Profile startup performance and provide optimization recommendations.
    """
    
    def __init__(self, profile_dir: Optional[Path] = None):
        self.registry = get_component_registry()
        self._lock = threading.RLock()
        self._profiles: List[StartupProfile] = []
        self._current_profile: Optional[StartupProfile] = None
        self.profile_dir = profile_dir or Path("./data/profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
    
    def start_profiling(self):
        """Start a new profiling session."""
        with self._lock:
            self._current_profile = None
    
    def create_profile(self, total_duration_ms: float) -> StartupProfile:
        """
        Create a startup profile from current component states.
        
        Args:
            total_duration_ms: Total startup duration in milliseconds
        
        Returns:
            StartupProfile with analysis
        """
        all_components = self.registry.get_all_components()
        
        component_profiles = []
        successful = 0
        failed = 0
        
        for i, comp in enumerate(all_components):
            if comp.load_time_ms > 0:
                component_profiles.append(ComponentProfile(
                    component_name=comp.name,
                    load_time_ms=comp.load_time_ms,
                    resource_requirement_mb=comp.resource_requirement_mb,
                    dependencies=comp.dependencies,
                    status=comp.status.value,
                    timestamp=datetime.now().isoformat(),
                    is_blocking=len(comp.dependencies) > 0,
                    load_order=i
                ))
                
                if comp.status.value == "loaded":
                    successful += 1
                elif comp.status.value == "failed":
                    failed += 1
        
        # Calculate parallel efficiency
        total_serial_time = sum(p.load_time_ms for p in component_profiles)
        parallel_efficiency = (total_serial_time / total_duration_ms) if total_duration_ms > 0 else 0
        
        # Find bottlenecks (components taking > 20% of total time)
        bottleneck_threshold = total_duration_ms * 0.2
        bottlenecks = [
            p.component_name for p in component_profiles
            if p.load_time_ms > bottleneck_threshold
        ]
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(component_profiles, total_duration_ms, bottlenecks)
        
        profile = StartupProfile(
            total_duration_ms=total_duration_ms,
            component_count=len(component_profiles),
            successful_count=successful,
            failed_count=failed,
            parallel_efficiency=parallel_efficiency,
            bottleneck_components=bottlenecks,
            optimization_suggestions=suggestions,
            components=component_profiles,
            timestamp=datetime.now().isoformat()
        )
        
        with self._lock:
            self._current_profile = profile
            self._profiles.append(profile)
        
        return profile
    
    def _generate_suggestions(
        self,
        components: List[ComponentProfile],
        total_duration_ms: float,
        bottlenecks: List[str]
    ) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        # Check for bottlenecks
        if bottlenecks:
            suggestions.append(
                f"Bottleneck components detected: {', '.join(bottlenecks)}. "
                f"Consider optimizing these components or deferring their loading."
            )
        
        # Check for unused dependencies
        heavy_components = [c for c in components if c.resource_requirement_mb > 100]
        if heavy_components:
            suggestions.append(
                f"Heavy components found: {', '.join(c.component_name for c in heavy_components)}. "
                f"Consider lazy loading these components."
            )
        
        # Check parallel efficiency
        total_serial_time = sum(c.load_time_ms for c in components)
        if total_serial_time > 0:
            efficiency = total_duration_ms / total_serial_time
            if efficiency < 0.3:
                suggestions.append(
                    f"Low parallelization efficiency ({efficiency * 100:.0f}%). "
                    f"Review dependency chains to enable more parallel loading."
                )
        
        # Check for long chains
        max_deps = max((len(c.dependencies) for c in components), default=0)
        if max_deps > 3:
            suggestions.append(
                f"Long dependency chains detected (up to {max_deps} levels). "
                f"Consider flattening dependencies where possible."
            )
        
        # Check startup time target
        target_ms = 3000  # 3 seconds target
        if total_duration_ms > target_ms:
            suggestions.append(
                f"Startup time ({total_duration_ms / 1000:.1f}s) exceeds target "
                f"({target_ms / 1000:.1f}s). "
                f"Focus on optimizing critical path components."
            )
        
        return suggestions
    
    def save_profile(self, profile: Optional[StartupProfile] = None) -> Path:
        """
        Save profile to disk.
        
        Args:
            profile: Profile to save (uses current if None)
        
        Returns:
            Path to saved profile file
        """
        if profile is None:
            profile = self._current_profile
        
        if not profile:
            raise ValueError("No profile to save")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"startup_profile_{timestamp}.json"
        filepath = self.profile_dir / filename
        
        # Convert to dict
        profile_dict = asdict(profile)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(profile_dict, f, indent=2)
        
        logger.info(f"Startup profile saved to {filepath}")
        
        return filepath
    
    def load_profile(self, filepath: Path) -> StartupProfile:
        """Load profile from disk."""
        with open(filepath, 'r') as f:
            profile_dict = json.load(f)
        
        # Convert component profiles
        components = [
            ComponentProfile(**comp)
            for comp in profile_dict['components']
        ]
        
        profile = StartupProfile(
            total_duration_ms=profile_dict['total_duration_ms'],
            component_count=profile_dict['component_count'],
            successful_count=profile_dict['successful_count'],
            failed_count=profile_dict['failed_count'],
            parallel_efficiency=profile_dict['parallel_efficiency'],
            bottleneck_components=profile_dict['bottleneck_components'],
            optimization_suggestions=profile_dict['optimization_suggestions'],
            components=components,
            timestamp=profile_dict['timestamp']
        )
        
        return profile
    
    def get_profiles(self) -> List[StartupProfile]:
        """Get all collected profiles."""
        with self._lock:
            return self._profiles.copy()
    
    def get_current_profile(self) -> Optional[StartupProfile]:
        """Get the current profile."""
        with self._lock:
            return self._current_profile
    
    def compare_profiles(self, profile1: StartupProfile, profile2: StartupProfile) -> Dict:
        """Compare two profiles and return differences."""
        duration_diff = profile2.total_duration_ms - profile1.total_duration_ms
        duration_diff_percent = (duration_diff / profile1.total_duration_ms * 100) if profile1.total_duration_ms > 0 else 0
        
        # Find component time differences
        comp_times1 = {c.component_name: c.load_time_ms for c in profile1.components}
        comp_times2 = {c.component_name: c.load_time_ms for c in profile2.components}
        
        component_diffs = []
        for name in set(comp_times1.keys()) | set(comp_times2.keys()):
            time1 = comp_times1.get(name, 0)
            time2 = comp_times2.get(name, 0)
            if time1 > 0:
                diff_percent = ((time2 - time1) / time1 * 100)
                component_diffs.append({
                    "component": name,
                    "time_diff_ms": time2 - time1,
                    "time_diff_percent": diff_percent
                })
        
        # Sort by absolute difference
        component_diffs.sort(key=lambda x: abs(x['time_diff_ms']), reverse=True)
        
        return {
            "duration_diff_ms": duration_diff,
            "duration_diff_percent": duration_diff_percent,
            "efficiency_diff": profile2.parallel_efficiency - profile1.parallel_efficiency,
            "component_diffs": component_diffs[:10],  # Top 10
            "improvement": duration_diff < 0
        }
    
    def format_profile(self, profile: Optional[StartupProfile] = None) -> str:
        """Format profile as human-readable string."""
        if profile is None:
            profile = self._current_profile
        
        if not profile:
            return "No profile available"
        
        lines = [
            "=" * 60,
            "Startup Performance Profile",
            "=" * 60,
            f"Timestamp: {profile.timestamp}",
            f"Total Duration: {profile.total_duration_ms:.1f}ms ({profile.total_duration_ms / 1000:.2f}s)",
            f"Components: {profile.component_count} ({profile.successful_count} successful, {profile.failed_count} failed)",
            f"Parallel Efficiency: {profile.parallel_efficiency:.2f}x",
            "",
            "Component Load Times:"
        ]
        
        # Sort by load time
        sorted_components = sorted(profile.components, key=lambda c: c.load_time_ms, reverse=True)
        
        for comp in sorted_components[:20]:  # Top 20
            deps_str = f", deps: {', '.join(comp.dependencies)}" if comp.dependencies else ""
            lines.append(
                f"  {comp.component_name}: {comp.load_time_ms:.1f}ms "
                f"({comp.resource_requirement_mb}MB{deps_str})"
            )
        
        if profile.bottleneck_components:
            lines.append("")
            lines.append("Bottlenecks:")
            for comp in profile.bottleneck_components:
                lines.append(f"  ⚠ {comp}")
        
        if profile.optimization_suggestions:
            lines.append("")
            lines.append("Optimization Suggestions:")
            for i, suggestion in enumerate(profile.optimization_suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Global singleton
_profiler = None
_profiler_lock = threading.Lock()


def get_startup_profiler() -> StartupProfiler:
    """Get the global startup profiler singleton."""
    global _profiler
    if _profiler is None:
        with _profiler_lock:
            if _profiler is None:
                _profiler = StartupProfiler()
    return _profiler
