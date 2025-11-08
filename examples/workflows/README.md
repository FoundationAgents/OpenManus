# Workflow Examples

This directory contains example workflow definitions demonstrating the capabilities of the Workflow Manager.

## Files

### simple_workflow.yaml
A basic sequential workflow with three steps. Good starting point for understanding workflow structure.

### example_workflow.yaml
A comprehensive data processing pipeline demonstrating:
- Agent, tool, and service nodes
- Parallel execution branches
- Conditional execution
- Loop constructs (foreach)
- Retry policies with exponential backoff
- Timeout handling
- Context variable substitution
- Error handling strategies

## Workflow Definition Structure

A workflow definition consists of:

### Metadata
```yaml
metadata:
  name: Workflow Name
  description: Description of what the workflow does
  version: 1.0.0
  author: Author name
  tags:
    - tag1
    - tag2
```

### Variables
Initial context variables:
```yaml
variables:
  var_name: value
```

### Nodes
Workflow nodes with their configuration:
```yaml
nodes:
  - id: unique_node_id
    type: agent|tool|service|condition|loop|parallel|sequence
    name: Display Name
    description: What this node does
    target: agent_or_tool_name
    depends_on:
      - dependency_id_1
      - dependency_id_2
    params:
      param1: value
      param2: $variable_reference
    condition:
      expression: "python_expression"
      context_vars: [var1, var2]
    loop:
      type: foreach|while
      items: variable_containing_list
      condition: "loop_condition"
      max_iterations: 100
    retry_policy:
      max_attempts: 3
      backoff_factor: 2.0
      initial_delay: 1.0
      max_delay: 60.0
    timeout: 300
    on_failure: continue|stop|node_id
```

### Start and End Nodes
```yaml
start_node: entry_node_id
end_nodes:
  - terminal_node_1
  - terminal_node_2
```

## Node Types

- **agent**: Executes an agent (async run method)
- **tool**: Executes a tool function
- **service**: Calls an external service
- **condition**: Conditional branching
- **loop**: Iterative execution
- **parallel**: Parallel execution of children
- **sequence**: Sequential execution of children

## Context Variables

Access previous node outputs using:
- `$variable_name` - substitutes from context
- `$node_<node_id>_output` - output from specific node

## Running Workflows

### Python API
```python
from app.workflows import WorkflowManager

# Create manager
manager = WorkflowManager()

# Load workflow
workflow_id = manager.load_workflow("path/to/workflow.yaml")

# Register agents/tools/services
executor = manager.active_executors.get(workflow_id)
if executor:
    executor.get_node_executor().register_agent("agent_name", agent_instance)

# Execute
state = await manager.execute_workflow(workflow_id)

# Check status
print(f"Status: {state.status}")
for node_id, result in state.node_results.items():
    print(f"{node_id}: {result.status}")
```

### UI
```python
from app.ui.workflows import WorkflowEditor

# Create editor widget
editor = WorkflowEditor()

# Load and visualize workflow
# Execute with UI controls
```

## Features Demonstrated

### Retry Logic
```yaml
retry_policy:
  max_attempts: 3
  backoff_factor: 2.0  # Exponential backoff
  initial_delay: 1.0
  max_delay: 60.0
```

### Conditional Execution
```yaml
condition:
  expression: "value > 10 and status == 'ready'"
  context_vars: [value, status]
```

### Loops
```yaml
loop:
  type: foreach
  items: data_list  # Context variable containing items
  max_iterations: 100
  item_var: item  # Variable name for current item
```

### Parallel Execution
Nodes with same dependencies and no interdependencies execute in parallel automatically.

### State Management
- Automatic checkpointing
- Resume after interruption
- Version control
- Backup/restore

## Testing

Run workflow tests:
```bash
pytest tests/workflows/ -v
```
