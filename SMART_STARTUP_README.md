# Smart Component Auto-Loading System

## Overview

The Smart Component Auto-Loading System is an intelligent component management system that optimizes application startup by:

- Loading only essential components at startup
- Detecting user intent and loading relevant components
- Loading components in parallel where possible
- Monitoring system resources to prevent overload
- Providing lazy loading for optional components
- Isolating component failures to prevent system crashes
- Profiling startup performance for optimization

## Architecture

### Core Components

#### 1. Component Registry (`app/core/component_registry.py`)

Central registry for all system components with metadata:

```python
from app.core.component_registry import get_component_registry

registry = get_component_registry()

# Get component metadata
component = registry.get_component("knowledge_graph")

# Check if component is loaded
is_loaded = registry.is_loaded("knowledge_graph")

# Get dependency chain
chain = registry.get_dependency_chain("database")
```

**Component Types:**
- CORE: Essential system components
- UI: User interface components
- TOOL: Tool components (web search, browser, etc.)
- MEMORY: Memory/storage components
- EXECUTION: Execution environments (sandbox)
- NETWORK: Network-related components
- SECURITY: Security components (guardian)
- STORAGE: Storage/persistence components
- INTEGRATION: Integration components (MCP)

**Component Status:**
- NOT_LOADED: Component not yet loaded
- LOADING: Component is currently loading
- LOADED: Component successfully loaded
- FAILED: Component failed to load
- DISABLED: Component is disabled

#### 2. Resource Monitor (`app/core/resource_monitor.py`)

Monitors system resources and provides loading recommendations:

```python
from app.core.resource_monitor import get_resource_monitor

monitor = get_resource_monitor()

# Get current resource snapshot
snapshot = monitor.get_current_snapshot()
print(f"Available memory: {snapshot.memory_available_mb}MB")
print(f"CPU usage: {snapshot.cpu_percent}%")

# Get loading recommendation
components = ["knowledge_graph", "sandbox", "browser"]
requirements = {"knowledge_graph": 100, "sandbox": 500, "browser": 500}
recommendation = monitor.get_recommendation(components, requirements)

print(f"Recommended: {recommendation.recommended_components}")
print(f"Skip: {recommendation.skip_components}")

# Start background monitoring
monitor.start_monitoring(interval=5.0)
```

#### 3. Error Isolation (`app/core/error_isolation.py`)

Isolates component failures to prevent system crashes:

```python
from app.core.error_isolation import get_error_isolation

isolation = get_error_isolation()

# Safely load a component
success, instance, error = isolation.safe_load(
    "my_component",
    loader_func=lambda: import_and_init_component(),
    on_success=lambda result: print("Component loaded!"),
    on_failure=lambda err: print(f"Failed: {err}")
)

# Check if component can be retried
can_retry = isolation.can_retry("my_component")

# Get error details
error_info = isolation.get_error("my_component")
```

#### 4. Lazy Loader (`app/core/lazy_loader.py`)

Loads components on-demand when first accessed:

```python
from app.core.lazy_loader import get_lazy_loader

loader = get_lazy_loader()

# Load a component
success, instance, error = loader.load_component(
    "knowledge_graph",
    on_progress=lambda comp, progress: print(f"{comp}: {progress}%")
)

# Load multiple components
results = loader.load_components(["comp1", "comp2", "comp3"])

# Unload a component
loader.unload_component("knowledge_graph")
```

#### 5. Parallel Loader (`app/core/parallel_loader.py`)

Loads independent components in parallel:

```python
from app.core.parallel_loader import get_parallel_loader

loader = get_parallel_loader()

# Load components in parallel
components = ["network", "guardian", "database", "code_editor"]
results = loader.load_components_parallel(components)

# Get load plan
plan = loader.get_load_plan(components)
print(f"Estimated time: {plan['estimated_time_seconds']}s")
print(f"Levels: {len(plan['load_order'])}")

# Format load plan
print(loader.format_load_plan(components))
```

#### 6. Startup Detection (`app/core/startup_detection.py`)

Detects user intent and determines which components to load:

```python
from app.core.startup_detection import get_startup_detection

detection = get_startup_detection()

# Detect user intent
intent = detection.detect_intent()
print(f"Intent: {intent.intent_type}")
print(f"Confidence: {intent.confidence * 100}%")
print(f"Required: {intent.required_components}")
print(f"Optional: {intent.optional_components}")

# Get recommended components
components = detection.get_recommended_components()

# Get essential components only
essentials = detection.get_essential_components()
```

**Intent Types:**
- **general**: General usage
- **existing_project**: Continuing work on existing project
- **code_editing**: Code editing and execution
- **web_research**: Web research and data gathering
- **collaboration**: Collaborative development

#### 7. Smart Startup (`app/core/smart_startup.py`)

Main orchestrator for intelligent component loading:

```python
from app.core.smart_startup import get_smart_startup

startup = get_smart_startup()

# Execute startup (async recommended)
import asyncio

async def main():
    report = await startup.startup_async(
        on_progress=lambda phase, progress: print(f"{phase}: {progress}%")
    )
    
    print(f"Total time: {report.total_duration_ms}ms")
    print(f"Successful: {len(report.successful_components)}")
    print(f"Failed: {len(report.failed_components)}")

asyncio.run(main())
```

**Startup Phases:**
1. Resource Monitoring - Start resource monitoring
2. Intent Detection - Detect user intent
3. Load Essentials - Load essential components in parallel
4. Load Recommended - Load recommended components based on intent
5. Finalize - Complete startup and log report

#### 8. Startup Profiler (`app/profiling/startup_profiler.py`)

Profiles startup performance and provides optimization recommendations:

```python
from app.profiling.startup_profiler import get_startup_profiler

profiler = get_startup_profiler()

# Create profile after startup
profile = profiler.create_profile(total_duration_ms=2500)

# Print profile
print(profiler.format_profile(profile))

# Save profile to disk
filepath = profiler.save_profile(profile)

# Load profile
loaded_profile = profiler.load_profile(filepath)

# Compare profiles
comparison = profiler.compare_profiles(profile1, profile2)
print(f"Duration diff: {comparison['duration_diff_ms']}ms")
print(f"Improvement: {comparison['improvement']}")
```

#### 9. Component Visibility Controller (`app/ui/component_visibility.py`)

Controls visibility of GUI components based on loading status:

```python
from app.ui.component_visibility import get_component_visibility_controller

controller = get_component_visibility_controller()

# Register a dock widget
controller.register_dock(
    "knowledge_graph",
    knowledge_graph_dock,
    on_load=lambda name: load_component_on_demand(name)
)

# Update component visibility
controller.update_component_visibility("knowledge_graph")

# Update all components
controller.update_all_components()

# Show only loaded components
controller.show_only_loaded()

# Update progress during loading
controller.update_progress("knowledge_graph", 50.0)
```

## Configuration

Configuration is stored in `config/components.toml`:

```toml
[startup]
enabled = true
target_startup_time = 3.0
max_parallel_workers = 4
min_available_memory_mb = 512
max_cpu_percent = 80.0

[components.config]
required = true
load_priority = 1
resource_mb = 1

[components.knowledge_graph]
optional = true
load_priority = 7
resource_mb = 100
lazy_load = true
```

## Usage

### Automatic Startup

The smart startup system is automatically integrated with the main application:

```python
# In app/system_startup.py
from app.core.smart_startup import get_smart_startup

startup = get_smart_startup()
report = await startup.startup_async()
```

### Manual Component Loading

Load components on-demand:

```python
from app.core.lazy_loader import get_lazy_loader

loader = get_lazy_loader()

# Load when user clicks "Open Knowledge Graph"
success, instance, error = loader.load_component("knowledge_graph")

if success:
    # Show component in UI
    show_knowledge_graph_panel(instance)
else:
    # Show error message
    show_error_dialog(f"Failed to load: {error}")
```

### Custom Component Registration

Register custom components:

```python
from app.core.component_registry import (
    get_component_registry,
    ComponentMetadata,
    ComponentType
)

registry = get_component_registry()

registry.register_component(ComponentMetadata(
    name="my_custom_component",
    component_type=ComponentType.TOOL,
    dependencies=["config", "network"],
    optional=True,
    resource_requirement_mb=50,
    load_priority=8,
    module_path="app.custom.my_component",
    description="My custom component"
))
```

## Performance Targets

- **Startup time**: < 3 seconds on ASUS N76VZ
- **Essential components**: Load in < 2 seconds
- **Parallel efficiency**: > 2x speedup on 4+ cores
- **Memory overhead**: < 50MB for startup system itself
- **Component isolation**: No cascading failures

## Testing

Run tests:

```bash
# Test component registry
pytest tests/startup/test_component_registry.py

# Test resource monitor
pytest tests/startup/test_resource_monitor.py

# Test smart startup
pytest tests/startup/test_smart_startup.py

# Run all startup tests
pytest tests/startup/
```

## Performance Analysis

### View Startup Profile

After running the application, view the startup profile:

```python
from app.profiling.startup_profiler import get_startup_profiler
from pathlib import Path

profiler = get_startup_profiler()

# Load latest profile
profiles_dir = Path("./data/profiles")
latest_profile = sorted(profiles_dir.glob("startup_profile_*.json"))[-1]
profile = profiler.load_profile(latest_profile)

# Print formatted profile
print(profiler.format_profile(profile))
```

### Optimization Suggestions

The profiler provides automatic optimization suggestions:

- Bottleneck components (taking > 20% of startup time)
- Heavy components that should be lazy loaded
- Low parallelization efficiency
- Long dependency chains
- Components exceeding startup time target

## Best Practices

### 1. Component Design

- **Keep dependencies minimal**: Fewer dependencies enable more parallel loading
- **Lazy initialization**: Defer heavy initialization until component is first used
- **Resource awareness**: Specify accurate resource requirements
- **Graceful degradation**: Handle missing optional dependencies

### 2. Loading Strategy

- **Essential only**: Mark only truly essential components as required
- **Priority ordering**: Higher priority = loads earlier
- **Lazy loading**: Enable lazy_load for heavy/rarely-used components
- **Condition functions**: Use conditions to load components only when needed

### 3. Error Handling

- **Isolate failures**: Use error isolation for all component loading
- **Retry logic**: Allow retries for transient failures
- **Fallback options**: Provide fallback components or degraded mode
- **User feedback**: Show clear error messages and recovery options

### 4. Performance Optimization

- **Profile regularly**: Run profiler to identify bottlenecks
- **Monitor resources**: Watch resource usage during development
- **Parallel loading**: Ensure independent components can load in parallel
- **Lazy loading**: Move non-essential components to lazy loading

## Troubleshooting

### Startup Taking Too Long

1. Check startup profile for bottlenecks
2. Enable lazy loading for heavy components
3. Review dependency chains for optimization opportunities
4. Ensure parallel loading is working correctly

### Components Failing to Load

1. Check error isolation logs for error details
2. Verify all dependencies are loaded
3. Check resource availability
4. Review component conditions
5. Enable retry mechanism if failures are transient

### Memory Issues

1. Check resource monitor logs
2. Reduce number of components loaded at startup
3. Enable lazy loading for memory-intensive components
4. Increase min_available_memory_mb threshold

### GUI Components Not Showing

1. Verify component is loaded successfully
2. Check component visibility controller registration
3. Update component visibility after loading
4. Check for errors in component instantiation

## Future Enhancements

- **Smart caching**: Cache component initialization state
- **Progressive loading**: Show partial UI while components load
- **Cloud profiles**: Share startup profiles across team
- **A/B testing**: Test different loading strategies
- **Auto-optimization**: Automatically adjust loading based on usage patterns
- **Predictive loading**: Predict needed components based on user behavior

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Smart Startup System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │ Smart Startup   │────────▶│ Startup         │           │
│  │ Orchestrator    │         │ Detection       │           │
│  └────────┬────────┘         └─────────────────┘           │
│           │                                                  │
│           ├────────┬────────┬────────┬────────┐            │
│           ▼        ▼        ▼        ▼        ▼            │
│  ┌─────────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ Component   │ │Resource│ │Error │ │Lazy  │ │Para- │   │
│  │ Registry    │ │Monitor │ │Isola-│ │Loader│ │llel  │   │
│  │             │ │        │ │tion  │ │      │ │Loader│   │
│  └─────────────┘ └────────┘ └──────┘ └──────┘ └──────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │ Startup         │────────▶│ Component       │           │
│  │ Profiler        │         │ Visibility      │           │
│  └─────────────────┘         └─────────────────┘           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  GUI Components  │
                    └──────────────────┘
```

## License

Same as the main OpenManus project.
