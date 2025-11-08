# Workflow Manager Implementation

This document describes the implementation of the Workflow Manager system for the multi-agent framework.

## Overview

The Workflow Manager provides a comprehensive system for defining, executing, and managing complex workflows with support for:
- YAML/JSON workflow definitions
- DAG (Directed Acyclic Graph) execution with dependency resolution
- Parallel execution of independent nodes
- Retry policies with exponential backoff
- Conditional execution
- Loop constructs (foreach, while)
- Event hooks and callbacks
- State persistence and checkpointing
- Resume/restart semantics
- UI visualization and monitoring

## Architecture

### Core Components

#### 1. Models (`app/workflows/models.py`)
Pydantic models defining the workflow structure:
- **WorkflowDefinition**: Complete workflow specification
- **WorkflowNode**: Individual workflow node with configuration
- **NodeType**: Enum for node types (agent, tool, service, condition, loop, etc.)
- **NodeStatus**: Enum for execution status (pending, running, completed, failed, etc.)
- **RetryPolicy**: Configuration for retry logic
- **Condition**: Conditional execution specification
- **LoopConfig**: Loop configuration (foreach/while)
- **WorkflowExecutionState**: Runtime execution state
- **NodeExecutionResult**: Result of node execution

#### 2. Parser (`app/workflows/parser.py`)
Parse workflow definitions from YAML/JSON files:
- **WorkflowParser**: Static methods for parsing and serialization
  - `parse_file()`: Load from YAML/JSON file
  - `parse_dict()`: Parse from dictionary
  - `to_yaml()`, `to_json()`: Export to formats

#### 3. DAG (`app/workflows/dag.py`)
DAG construction and validation:
- **WorkflowDAG**: Directed acyclic graph representation
  - Cycle detection
  - Reachability validation
  - Topological ordering
  - Dependency resolution
  - Execution level calculation for parallelism

#### 4. Callbacks (`app/workflows/callbacks.py`)
Event system for monitoring and integration:
- **CallbackManager**: Manages event callbacks
- **EventType**: Enum for workflow events
- **WorkflowEvent**: Event data structure
- **LoggingCallback**: Built-in logging callback
- **MetricsCallback**: Built-in metrics collection

#### 5. State Management (`app/workflows/state.py`)
Persistence and versioning:
- **StateManager**: Workflow execution state persistence
  - Save/load state
  - Checkpoint creation and management
  - Export/import state
- **VersioningEngine**: Workflow definition versioning
- **BackupManager**: Backup and restore functionality

#### 6. Executor (`app/workflows/executor.py`)
Workflow execution engine:
- **NodeExecutor**: Executes individual nodes
  - Agent execution
  - Tool execution
  - Service calls
  - Context variable substitution
- **WorkflowExecutor**: Main execution coordinator
  - Parallel execution
  - Retry with exponential backoff
  - Conditional execution
  - Loop processing (foreach, while)
  - Timeout handling
  - Pause/resume/cancel

#### 7. Manager (`app/workflows/manager.py`)
High-level workflow management:
- **WorkflowManager**: Main API for workflow operations
  - Load workflows from files or dictionaries
  - Execute workflows
  - Register agents/tools/services
  - State management integration
  - Callback management
  - Auto-checkpointing

### UI Components

#### 1. Workflow Visualizer (`app/ui/workflows/workflow_visualizer.py`)
DAG visualization using QGraphicsView:
- **WorkflowVisualizer**: Widget for visualizing workflows
  - Node display with type-specific colors
  - Status highlighting (pending, running, completed, failed)
  - Dependency edges
  - Zoom controls

#### 2. Workflow Editor (`app/ui/workflows/workflow_editor.py`)
Main workflow interface:
- **WorkflowEditor**: Complete workflow editing/execution UI
  - Load workflows from files
  - Visualize DAG
  - Execute with real-time monitoring
  - Pause/resume/cancel controls
  - Node status table
  - Execution log
  - Progress tracking

## Features

### 1. Declarative Workflow Definitions

Workflows are defined in YAML or JSON:

```yaml
metadata:
  name: Data Processing Pipeline
  description: Example workflow
  version: 1.0.0

variables:
  input_data: "source.csv"

nodes:
  - id: load_data
    type: agent
    name: Data Loader
    target: loader_agent
    params:
      file: $input_data

  - id: process_data
    type: tool
    name: Data Processor
    target: processor_tool
    depends_on:
      - load_data
    params:
      data: $node_load_data_output
    retry_policy:
      max_attempts: 3
      backoff_factor: 2.0

start_node: load_data
```

### 2. Node Types

- **agent**: Execute an agent with async `run()` method
- **tool**: Execute a callable tool/function
- **service**: Call external service
- **condition**: Conditional branching
- **loop**: Iterative execution
- **parallel**: Parallel execution group
- **sequence**: Sequential execution group

### 3. Dependency Resolution

The DAG engine automatically:
- Validates dependencies
- Detects cycles
- Determines execution order
- Enables parallel execution of independent nodes

### 4. Retry Logic

Configurable retry with exponential backoff:

```yaml
retry_policy:
  max_attempts: 5
  backoff_factor: 2.0
  initial_delay: 1.0
  max_delay: 60.0
  retry_on_errors:
    - TimeoutError
    - ConnectionError
```

### 5. Conditional Execution

Execute nodes based on conditions:

```yaml
condition:
  expression: "value > 10 and status == 'ready'"
  context_vars: [value, status]
```

### 6. Loops

Support for foreach and while loops:

```yaml
loop:
  type: foreach
  items: data_list
  max_iterations: 100
  item_var: item
```

### 7. Event System

Comprehensive event hooks:
- `WORKFLOW_START`, `WORKFLOW_COMPLETE`, `WORKFLOW_FAILED`
- `WORKFLOW_PAUSED`, `WORKFLOW_RESUMED`
- `NODE_START`, `NODE_COMPLETE`, `NODE_FAILED`
- `NODE_RETRY`, `NODE_SKIPPED`
- `STATE_CHECKPOINT`

### 8. State Management

- Automatic checkpointing during execution
- Resume from checkpoint after interruption
- Version control of workflow definitions
- Backup and restore capabilities
- Export/import state

### 9. Context Variables

Access workflow context and node outputs:
- `$variable_name`: Substitute from context
- `$node_<id>_output`: Access node output

## Usage

### Python API

```python
from app.workflows import WorkflowManager

# Create manager
manager = WorkflowManager()

# Load workflow
workflow_id = manager.load_workflow("workflow.yaml")

# Register agents/tools
# (Before execution or during setup)

# Execute workflow
state = await manager.execute_workflow(workflow_id)

# Check results
print(f"Status: {state.status}")
for node_id, result in state.node_results.items():
    print(f"{node_id}: {result.status.value}")
```

### With Callbacks

```python
from app.workflows import LoggingCallback, MetricsCallback, EventType

# Add logging
logging_cb = LoggingCallback(verbose=True)
manager.add_callback(logging_cb)

# Add metrics
metrics_cb = MetricsCallback()
manager.add_callback(metrics_cb)

# Custom callback
def on_node_complete(event):
    print(f"Node {event.node_id} completed!")

manager.add_callback(on_node_complete, EventType.NODE_COMPLETE)

# Execute and get metrics
state = await manager.execute_workflow(workflow_id)
metrics = metrics_cb.get_metrics()
```

### State Management

```python
# Save/load state
manager.save_state(workflow_id)
state = manager.load_state(workflow_id)

# Create checkpoint
manager.create_backup(workflow_id, name="before_critical_step")

# Resume from checkpoint
state = manager.restore_backup(backup_file)

# List versions
versions = manager.list_versions(workflow_id)
```

### UI

```python
from app.ui.workflows import WorkflowEditor

# Create editor
editor = WorkflowEditor()

# Show in window
editor.show()

# Or integrate in larger application
main_window.addWidget(editor)
```

## Testing

Comprehensive test suite covering:

1. **Model Tests** (`test_models.py`)
   - Validation
   - Constraints
   - Edge cases

2. **Parser Tests** (`test_parser.py`)
   - YAML/JSON parsing
   - Serialization
   - Error handling

3. **DAG Tests** (`test_dag.py`)
   - Graph construction
   - Cycle detection
   - Dependency validation
   - Execution ordering

4. **Executor Tests** (`test_executor.py`)
   - Simple workflows
   - Parallel execution
   - Retry logic
   - Conditionals
   - Loops
   - Timeout handling
   - Pause/resume/cancel

5. **State Tests** (`test_state.py`)
   - Persistence
   - Checkpoints
   - Versioning
   - Backup/restore

6. **Manager Tests** (`test_manager.py`)
   - Workflow loading
   - Export/import
   - Callback management

Run tests:
```bash
pytest tests/workflows/ -v
```

All 53 tests pass successfully.

## Examples

Example workflows provided in `examples/workflows/`:

1. **simple_workflow.yaml**: Basic sequential workflow
2. **example_workflow.yaml**: Comprehensive data processing pipeline
3. **workflow_example.py**: Usage examples and demonstrations

Run examples:
```bash
python -m examples.workflows.workflow_example
```

## Integration Points

### Agent Integration

Register agents for workflow execution:
```python
from app.agent import ReActAgent

agent = ReActAgent(...)
manager.register_agent(workflow_id, "agent_name", agent)
```

### Tool Integration

Register tools:
```python
from app.tool import some_tool

manager.register_tool(workflow_id, "tool_name", some_tool)
```

### Service Integration

Register external services:
```python
class APIService:
    async def call(self, **kwargs):
        # Make API call
        return result

manager.register_service(workflow_id, "api_service", APIService())
```

## Configuration

Workflow manager settings can be configured:
```python
manager = WorkflowManager(
    workspace_dir=Path("custom/workspace"),
    enable_auto_checkpoint=True,
    checkpoint_interval=60  # seconds
)
```

## Future Enhancements

Potential improvements:
1. Subworkflow support (nested workflows)
2. Dynamic workflow modification
3. Real-time collaboration
4. Workflow templates library
5. Visual workflow designer (drag-and-drop)
6. Performance profiling and optimization
7. Distributed execution
8. Integration with CI/CD systems
9. Workflow marketplace
10. Advanced scheduling (cron, triggers)

## Files Structure

```
app/workflows/
├── __init__.py           # Package exports
├── models.py             # Pydantic models
├── parser.py             # YAML/JSON parser
├── dag.py                # DAG construction
├── callbacks.py          # Event system
├── state.py              # State management
├── executor.py           # Execution engine
└── manager.py            # Main manager

app/ui/workflows/
├── __init__.py           # UI exports
├── workflow_visualizer.py # DAG visualization
└── workflow_editor.py    # Main UI

tests/workflows/
├── __init__.py
├── test_models.py
├── test_parser.py
├── test_dag.py
├── test_executor.py
├── test_state.py
└── test_manager.py

examples/workflows/
├── README.md
├── simple_workflow.yaml
├── example_workflow.yaml
└── workflow_example.py
```

## Summary

The Workflow Manager implementation provides a complete, production-ready system for managing complex multi-agent workflows with:
- ✅ YAML/JSON workflow definitions
- ✅ DAG validation and execution
- ✅ Parallel execution
- ✅ Retry policies with exponential backoff
- ✅ Conditional execution
- ✅ Loop constructs
- ✅ Event hooks and callbacks
- ✅ State persistence and checkpointing
- ✅ Resume/restart capabilities
- ✅ UI visualization and monitoring
- ✅ Comprehensive test coverage (53 tests)
- ✅ Example workflows and documentation

The system is fully integrated with the existing agent framework and ready for production use.
