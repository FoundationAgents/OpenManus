# Agent Class API Reference

The `Agent` class provides AI-powered capabilities for executing tasks, checking task status, and terminating tasks within a session. It enables natural language task execution and monitoring.

**⚠️ Important Note**: The Agent functionality is verified on the `windows_latest` system image.

## 📖 Related Tutorial

- [Agent Modules Guide](../../../docs/guides/common-features/advanced/agent-modules.md) - Detailed tutorial on AI-powered automation with Agent modules

## Constructor

### new Agent()

```typescript
constructor(session: McpSession)
```

**Parameters:**
- `session` (McpSession): The Session instance that this Agent belongs to.

## Methods

### executeTask

Executes a specific task described in human language.

```typescript
executeTask(task: string, maxTryTimes: number): Promise<ExecutionResult>
```

**Parameters:**
- `task` (string): Task description in human language.
- `maxTryTimes` (number): Maximum number of retry attempts.

**Returns:**
- `Promise<ExecutionResult>`: A promise that resolves to a result object containing success status, task ID, task status, and error message if any.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Create a session with Windows image (required for Agent functionality)
async function executeAgentTask() {
  try {
    const params = { imageId: "windows_latest" };
    const createResult = await agentBay.create(params);
    if (createResult.success) {
      const session = createResult.session;
      console.log(`Session created successfully with ID: ${session.getSessionId()}`);

      // Execute a task using the Agent
      const taskDescription = "Find the current weather in New York City";
      const executionResult = await session.agent.executeTask(taskDescription, 10);

      if (executionResult.success) {
        console.log(`Task completed successfully with status: ${executionResult.taskStatus}`);
        console.log(`Task ID: ${executionResult.taskId}`);
      } else {
        console.log(`Task failed: ${executionResult.errorMessage}`);
        // If we have a task ID, we can try to get more detailed status
        if (executionResult.taskId) {
          const statusResult = await session.agent.getTaskStatus(executionResult.taskId);
          if (statusResult.success) {
            console.log(`Task status details: ${statusResult.output}`);
          }
        }
      }
    } else {
      console.log(`Failed to create session: ${createResult.errorMessage}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

executeAgentTask();
```

### getTaskStatus

Gets the status of the task with the given task ID.

```typescript
getTaskStatus(taskId: string): Promise<QueryResult>
```

**Parameters:**
- `taskId` (string): Task ID

**Returns:**
- `Promise<QueryResult>`: A promise that resolves to a result object containing success status, output, and error message if any.

**Example:**
```typescript
// Get the status of a specific task
async function checkTaskStatus(taskId: string) {
  try {
    const statusResult = await session.agent.getTaskStatus(taskId);
    
    if (statusResult.success) {
      console.log(`Task output: ${statusResult.output}`);
    } else {
      console.log(`Failed to get task status: ${statusResult.errorMessage}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

checkTaskStatus("task_12345");
```

### terminateTask

Terminates a task with a specified task ID.

```typescript
terminateTask(taskId: string): Promise<ExecutionResult>
```

**Parameters:**
- `taskId` (string): The ID of the running task.

**Returns:**
- `Promise<ExecutionResult>`: A promise that resolves to a result object containing success status, task ID, task status, and error message if any.

**Example:**
```typescript
// Terminate a running task
async function terminateAgentTask(taskId: string) {
  try {
    const terminateResult = await session.agent.terminateTask(taskId);
    
    if (terminateResult.success) {
      console.log(`Task terminated successfully with status: ${terminateResult.taskStatus}`);
    } else {
      console.log(`Failed to terminate task: ${terminateResult.errorMessage}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

terminateAgentTask("task_12345");
```