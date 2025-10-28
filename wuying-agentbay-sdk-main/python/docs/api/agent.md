# Agent Class API Reference

The `Agent` class provides AI-powered capabilities for executing tasks, checking task status, and terminating tasks within a session. It enables natural language task execution and monitoring.

**⚠️ Important Note**: The Agent functionality is verified on the `windows_latest` system image.

## 📖 Related Tutorial

- [Agent Modules Guide](../../../docs/guides/common-features/advanced/agent-modules.md) - Detailed tutorial on AI-powered automation with Agent modules

## Constructor

### Agent

```python
Agent(session)
```

**Parameters:**
- `session` (Session): The Session instance that this Agent belongs to.

## Methods

### execute_task

Executes a specific task described in human language.

```python
execute_task(task: str, max_try_times: int) -> ExecutionResult
```

**Parameters:**
- `task` (str): Task description in human language.
- `max_try_times` (int): Maximum number of retry attempts.

**Returns:**
- `ExecutionResult`: Result object containing success status, task ID, task status, and error message if any.

**Example:**
```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create a session with windows_latest image
from agentbay.session_params import CreateSessionParams
params = CreateSessionParams(image_id="windows_latest")
session_result = agent_bay.create(params)
if session_result.success:
    session = session_result.session
    
    # Execute a task using the Agent
    task_description = "Find the current weather in New York City"
    execution_result = session.agent.execute_task(task_description, max_try_times=10)
    
    if execution_result.success:
        print(f"Task completed successfully with status: {execution_result.task_status}")
        print(f"Task completed successfully with result: {execution_result.task_result}")
        print(f"Task ID: {execution_result.task_id}")
    else:
        print(f"Task failed: {execution_result.error_message}")
```

### get_task_status

Gets the status of the task with the given task ID.

```python
get_task_status(task_id: str) -> QueryResult
```

**Parameters:**
- `task_id` (str): Task ID

**Returns:**
- `QueryResult`: Result object containing success status, output, and error message if any.

**Example:**
```python
# Get the status of a specific task
task_id = "task_12345"
status_result = session.agent.get_task_status(task_id)

if status_result.success:
    print(f"Task output: {status_result.output}")
else:
    print(f"Failed to get task status: {status_result.error_message}")
```

### terminate_task

Terminates a task with a specified task ID.

```python
terminate_task(task_id: str) -> ExecutionResult
```

**Parameters:**
- `task_id` (str): The ID of the running task.

**Returns:**
- `ExecutionResult`: Result object containing success status, task ID, task status, and error message if any.

**Example:**
```python
# Terminate a running task
task_id = "task_12345"
terminate_result = session.agent.terminate_task(task_id)

if terminate_result.success:
    print(f"Task terminated successfully with status: {terminate_result.task_status}")
else:
    print(f"Failed to terminate task: {terminate_result.error_message}")
```