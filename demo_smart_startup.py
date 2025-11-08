#!/usr/bin/env python3
"""
Demo script for Smart Component Auto-Loading System.

This script demonstrates the various features of the smart startup system:
1. Component registry
2. Resource monitoring
3. Startup detection
4. Lazy loading
5. Parallel loading
6. Smart startup orchestration
7. Performance profiling
"""

import asyncio
import time
from pathlib import Path

# Ensure directories exist
Path("./data").mkdir(exist_ok=True)
Path("./data/profiles").mkdir(exist_ok=True)

from app.core.component_registry import get_component_registry, ComponentType, ComponentStatus
from app.core.resource_monitor import get_resource_monitor
from app.core.error_isolation import get_error_isolation
from app.core.lazy_loader import get_lazy_loader
from app.core.parallel_loader import get_parallel_loader
from app.core.startup_detection import get_startup_detection
from app.core.smart_startup import get_smart_startup
from app.profiling.startup_profiler import get_startup_profiler


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def demo_component_registry():
    """Demo 1: Component Registry."""
    print_section("Demo 1: Component Registry")
    
    registry = get_component_registry()
    
    # Show all components
    print("All registered components:")
    for comp in registry.get_components_by_priority():
        status_icon = "✓" if comp.status == ComponentStatus.LOADED else "○"
        required = "required" if not comp.optional else "optional"
        print(f"  {status_icon} {comp.name:20s} [{comp.component_type.value:12s}] "
              f"({comp.resource_requirement_mb:3d}MB, priority:{comp.load_priority}, {required})")
    
    # Show component types
    print("\nComponents by type:")
    for comp_type in ComponentType:
        components = registry.get_components_by_type(comp_type)
        if components:
            print(f"  {comp_type.value}: {len(components)} components")
    
    # Show dependencies
    print("\nDependency chains:")
    for comp_name in ["database", "agent_control", "knowledge_graph"]:
        chain = registry.get_dependency_chain(comp_name)
        print(f"  {comp_name}: {' → '.join(chain)}")
    
    # Show resource requirements
    all_components = [c.name for c in registry.get_all_components()]
    total_resources = registry.get_total_resource_requirement(all_components)
    print(f"\nTotal resource requirement: {total_resources}MB")


def demo_resource_monitor():
    """Demo 2: Resource Monitor."""
    print_section("Demo 2: Resource Monitor")
    
    monitor = get_resource_monitor()
    
    # Get current snapshot
    snapshot = monitor.get_current_snapshot()
    print("Current system resources:")
    print(f"  Total memory: {snapshot.memory_total_mb}MB")
    print(f"  Used memory: {snapshot.memory_used_mb}MB ({snapshot.memory_percent:.1f}%)")
    print(f"  Available memory: {snapshot.memory_available_mb}MB")
    print(f"  CPU usage: {snapshot.cpu_percent:.1f}%")
    
    # Get loading recommendation
    components = ["knowledge_graph", "sandbox", "browser", "web_search"]
    requirements = {
        "knowledge_graph": 100,
        "sandbox": 500,
        "browser": 500,
        "web_search": 10
    }
    
    print(f"\nComponent loading recommendation:")
    print(f"  Components to load: {', '.join(components)}")
    print(f"  Total requirement: {sum(requirements.values())}MB")
    
    recommendation = monitor.get_recommendation(components, requirements)
    print(f"\n{monitor.format_recommendation(recommendation)}")
    
    # Start monitoring
    print("\nStarting background monitoring...")
    monitor.start_monitoring(interval=1.0)
    print("Monitoring for 3 seconds...")
    time.sleep(3)
    
    snapshots = monitor.get_snapshots(last_n=3)
    print(f"\nCollected {len(snapshots)} snapshots")
    
    avg_cpu, avg_memory = monitor.get_average_usage(last_n=3)
    print(f"Average CPU: {avg_cpu:.1f}%")
    print(f"Average Memory: {avg_memory:.1f}%")
    
    monitor.stop_monitoring()


def demo_startup_detection():
    """Demo 3: Startup Detection."""
    print_section("Demo 3: Startup Detection")
    
    detection = get_startup_detection()
    
    # Detect intent
    intent = detection.detect_intent()
    print(detection.format_intent())
    
    # Get recommended components
    recommended = detection.get_recommended_components()
    print(f"\nRecommended components ({len(recommended)}):")
    for comp in recommended:
        print(f"  • {comp}")
    
    # Get essential components
    essentials = detection.get_essential_components()
    print(f"\nEssential components ({len(essentials)}):")
    for comp in essentials:
        print(f"  ✓ {comp}")


def demo_error_isolation():
    """Demo 4: Error Isolation."""
    print_section("Demo 4: Error Isolation")
    
    isolation = get_error_isolation()
    
    # Test successful load
    print("Test 1: Successful load")
    def successful_loader():
        time.sleep(0.1)
        return "Success!"
    
    success, result, error = isolation.safe_load(
        "test_component_1",
        successful_loader,
        on_success=lambda r: print(f"  ✓ Loaded successfully: {r}"),
        on_failure=lambda e: print(f"  ✗ Failed: {e}")
    )
    
    # Test failed load
    print("\nTest 2: Failed load")
    def failing_loader():
        raise ValueError("Simulated error")
    
    success, result, error = isolation.safe_load(
        "test_component_2",
        failing_loader,
        on_success=lambda r: print(f"  ✓ Loaded successfully: {r}"),
        on_failure=lambda e: print(f"  ✗ Failed: {e}")
    )
    
    # Show errors
    if isolation.has_errors():
        print("\n" + isolation.format_error_report())


def demo_lazy_loading():
    """Demo 5: Lazy Loading."""
    print_section("Demo 5: Lazy Loading")
    
    loader = get_lazy_loader()
    registry = get_component_registry()
    
    print("Loading components lazily with progress tracking...")
    
    components_to_load = ["config", "logger", "database"]
    
    for comp_name in components_to_load:
        print(f"\nLoading {comp_name}...")
        
        def progress_callback(name, progress):
            if progress >= 0:
                bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                print(f"  [{bar}] {progress:.0f}%", end="\r")
        
        success, instance, error = loader.load_component(
            comp_name,
            on_progress=progress_callback
        )
        
        if success:
            comp = registry.get_component(comp_name)
            print(f"  ✓ Loaded in {comp.load_time_ms:.1f}ms")
        else:
            print(f"  ✗ Failed: {error}")


def demo_parallel_loading():
    """Demo 6: Parallel Loading."""
    print_section("Demo 6: Parallel Loading")
    
    loader = get_parallel_loader()
    registry = get_component_registry()
    
    components = ["config", "logger", "guardian", "database", "network"]
    
    # Show load plan
    print("Load plan:")
    print(loader.format_load_plan(components))
    
    # Load in parallel
    print("\nLoading components in parallel...")
    start_time = time.time()
    
    results = loader.load_components_parallel(components)
    
    duration = (time.time() - start_time) * 1000
    
    print(f"\nParallel loading completed in {duration:.1f}ms")
    
    for comp_name, (success, instance, error) in results.items():
        comp = registry.get_component(comp_name)
        if success:
            print(f"  ✓ {comp_name}: {comp.load_time_ms:.1f}ms")
        else:
            print(f"  ✗ {comp_name}: {error}")


async def demo_smart_startup():
    """Demo 7: Smart Startup."""
    print_section("Demo 7: Smart Startup Orchestration")
    
    startup = get_smart_startup()
    
    print("Executing smart startup sequence...")
    print("(This will load essential components in optimal order)")
    print()
    
    # Track progress
    def progress_callback(phase, progress):
        if progress >= 0 and progress % 25 == 0:
            print(f"  {phase}: {progress:.0f}%")
    
    # Execute startup
    report = await startup.startup_async(on_progress=progress_callback)
    
    print("\nStartup Report:")
    print(f"  Total duration: {report.total_duration_ms:.1f}ms ({report.total_duration_ms / 1000:.2f}s)")
    print(f"  Status: {'✓ SUCCESS' if report.success else '⚠ PARTIAL SUCCESS'}")
    print(f"  Phases: {len(report.phases)}")
    
    print("\nPhase breakdown:")
    for phase in report.phases:
        status = "✓" if phase.success else "✗"
        print(f"  {status} {phase.name}: {phase.duration_ms:.1f}ms")
        if phase.components:
            print(f"     ({len(phase.components)} components)")
    
    print(f"\nComponents loaded: {len(report.successful_components)}")
    for comp in sorted(report.successful_components):
        print(f"  ✓ {comp}")
    
    if report.failed_components:
        print(f"\nComponents failed: {len(report.failed_components)}")
        for comp in sorted(report.failed_components):
            print(f"  ✗ {comp}")


def demo_profiling():
    """Demo 8: Startup Profiling."""
    print_section("Demo 8: Startup Profiling")
    
    profiler = get_startup_profiler()
    
    # Create profile
    print("Creating startup profile...")
    profile = profiler.create_profile(total_duration_ms=2500)
    
    # Show profile
    print("\n" + profiler.format_profile(profile))
    
    # Save profile
    print("\nSaving profile to disk...")
    filepath = profiler.save_profile(profile)
    print(f"Profile saved to: {filepath}")
    
    # Load profile
    print("\nLoading profile from disk...")
    loaded_profile = profiler.load_profile(filepath)
    print(f"Loaded profile from {loaded_profile.timestamp}")


async def main():
    """Main demo function."""
    print("\n" + "=" * 60)
    print("  Smart Component Auto-Loading System Demo")
    print("=" * 60)
    
    demos = [
        ("Component Registry", demo_component_registry),
        ("Resource Monitor", demo_resource_monitor),
        ("Startup Detection", demo_startup_detection),
        ("Error Isolation", demo_error_isolation),
        ("Lazy Loading", demo_lazy_loading),
        ("Parallel Loading", demo_parallel_loading),
    ]
    
    # Run synchronous demos
    for name, demo_func in demos:
        try:
            demo_func()
            input("\nPress Enter to continue to next demo...")
        except Exception as e:
            print(f"\nError in demo: {e}")
            import traceback
            traceback.print_exc()
    
    # Run async demos
    async_demos = [
        ("Smart Startup", demo_smart_startup),
        ("Profiling", demo_profiling),
    ]
    
    for name, demo_func in async_demos:
        try:
            await demo_func()
            input("\nPress Enter to continue to next demo...")
        except Exception as e:
            print(f"\nError in demo: {e}")
            import traceback
            traceback.print_exc()
    
    print_section("Demo Complete!")
    print("All demos completed successfully!")
    print("\nFor more information, see SMART_STARTUP_README.md")


if __name__ == "__main__":
    asyncio.run(main())
