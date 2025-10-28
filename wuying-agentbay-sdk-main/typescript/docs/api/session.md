# Session Class

The `Session` class represents a session in the AgentBay cloud environment. It provides methods for managing file systems, executing commands, and more.

## 📖 Related Tutorial

- [Session Management Guide](../../../docs/guides/common-features/basics/session-management.md) - Detailed tutorial on session lifecycle and management

## Properties

```typescript
sessionId: string                    // The ID of this session
fileSystem: FileSystem               // The FileSystem instance for this session
command: Command                     // The Command instance for this session
code: Code                          // The Code instance for this session
oss: Oss                            // The Oss instance for this session
application: Application            // The Application instance for this session
window: WindowManager               // The WindowManager instance for this session
ui: UI                              // The UI instance for this session
context: ContextManager             // The ContextManager instance for this session
browser: Browser                    // The Browser instance for this session
agent: Agent                        // The Agent instance for this session
isVpc: boolean                      // Whether this session uses VPC resources
networkInterfaceIp: string          // Network interface IP for VPC sessions
httpPort: string                    // HTTP port for VPC sessions
mcpTools: McpTool[]                 // MCP tools available for this session
```

**Note:** The `agentBay` property is private and not part of the public API.

## Methods

### delete

Deletes this session.

```typescript
delete(syncContext?: boolean): Promise<DeleteResult>
```

**Parameters:**
- `syncContext` (boolean, optional): If true, the API will trigger a file upload via `this.context.sync` before actually releasing the session. Default is false.

**Returns:**
- `Promise<DeleteResult>`: A promise that resolves to a result object containing success status, request ID, and error message if any.

**Behavior:**
- When `syncContext` is true, the API will first call `context.sync` to trigger file upload.
- It will then check `context.info` to retrieve ContextStatusData and monitor only upload task items' Status.
- The API waits until all upload tasks show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status upload tasks will have their error messages printed.
- The session deletion only proceeds after context sync status checking for upload tasks completes.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Create and delete a session
async function createAndDeleteSession() {
  try {
    const result = await agentBay.create();
    if (result.success) {
      const session = result.session;
      console.log(`Session created with ID: ${session.sessionId}`);

      // Use the session...

      // Delete the session with context synchronization
      const deleteResult = await session.delete(true);
      if (deleteResult.success) {
        console.log('Session deleted successfully with synchronized context');
      } else {
        console.log(`Failed to delete session: ${deleteResult.errorMessage}`);
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

createAndDeleteSession();
```

### setLabels

Sets labels for this session.

```typescript
setLabels(labels: Record<string, string>): Promise<OperationResult>
```

**Parameters:**
- `labels` (Record<string, string>): Key-value pairs representing the labels to set.

**Returns:**
- `Promise<OperationResult>`: A promise that resolves to a result object containing success status, request ID, and error message if any.

**Example:**
```typescript
// Set session labels
async function setSessionLabels(session) {
  try {
    const labels = {
      project: 'demo',
      environment: 'testing',
      version: '1.0.0'
    };

    const result = await session.setLabels(labels);
    console.log(`Labels set successfully, request ID: ${result.requestId}`);
    return result;
  } catch (error) {
    console.error(`Failed to set labels: ${error}`);
    throw error;
  }
}
```

### getLabels

Gets the labels for this session.

```typescript
getLabels(): Promise<OperationResult>
```

**Returns:**
- `Promise<OperationResult>`: A promise that resolves to a result object containing success status, request ID, error message if any, and the labels data.

**Example:**
```typescript
// Get session labels
async function getSessionLabels(session) {
  try {
    const result = await session.getLabels();
    if (result.success) {
      console.log(`Session labels: ${JSON.stringify(result.data)}`);
      console.log(`Request ID: ${result.requestId}`);
      return result.data;
    } else {
      console.log(`Failed to get labels: ${result.errorMessage}`);
      return null;
    }
  } catch (error) {
    console.error(`Failed to get labels: ${error}`);
    throw error;
  }
}
```

### info

Gets information about this session.

```typescript
info(): Promise<InfoResult>
```

**Returns:**
- `Promise<InfoResult>`: A promise that resolves to a result object containing session information, request ID, and success status.

**Example:**
```typescript
// Get session information
async function getSessionInfo(session) {
  try {
    const result = await session.info();
    console.log(`Session ID: ${result.data.sessionId}`);
    console.log(`Resource URL: ${result.data.resourceUrl}`);
    console.log(`Request ID: ${result.requestId}`);
    return result.data;
  } catch (error) {
    console.error(`Failed to get session info: ${error}`);
    throw error;
  }
}
```

### getLink

Gets a link for this session.

```typescript
getLink(protocolType?: string, port?: number): Promise<LinkResult>
```

**Parameters:**
- `protocolType` (string, optional): The protocol type for the link.
- `port` (number, optional): The port for the link. Must be an integer in the range [30100, 30199].

**Returns:**
- `Promise<LinkResult>`: A promise that resolves to a result object containing the session link, request ID, and success status.

**Throws:**
- `Error`: If the port value is not an integer or is outside the valid range [30100, 30199].

**Example:**
```typescript
// Get session link
async function getSessionLink(session) {
  try {
    const result = await session.getLink();
    console.log(`Session link: ${result.data}`);
    console.log(`Request ID: ${result.requestId}`);

    // Get link with specific protocol and port (port must be in range [30100, 30199])
    const customResult = await session.getLink('https', 30150);
    console.log(`Custom link: ${customResult.data}`);

    return result.data;
  } catch (error) {
    console.error(`Failed to get link: ${error}`);
    throw error;
  }
}
```

### getLinkAsync

Asynchronously gets a link for this session.

```typescript
getLinkAsync(protocolType?: string, port?: number): Promise<LinkResult>
```

**Parameters:**
- `protocolType` (string, optional): The protocol type for the link.
- `port` (number, optional): The port for the link. Must be an integer in the range [30100, 30199].

**Returns:**
- `Promise<LinkResult>`: A promise that resolves to a result object containing the session link, request ID, and success status.

**Throws:**
- `Error`: If the port value is not an integer or is outside the valid range [30100, 30199].

**Example:**
```typescript
// Get session link asynchronously
async function getSessionLinkAsync(session) {
  try {
    const result = await session.getLinkAsync();
    console.log(`Session link: ${result.data}`);
    console.log(`Request ID: ${result.requestId}`);

    // Get link with specific protocol and port (port must be in range [30100, 30199])
    const customResult = await session.getLinkAsync('https', 30150);
    console.log(`Custom link: ${customResult.data}`);

    return result.data;
  } catch (error) {
    console.error(`Failed to get link: ${error}`);
    throw error;
  }
}
```

### listMcpTools

Lists MCP tools available for this session.

```typescript
listMcpTools(imageId?: string): Promise<McpToolsResult>
```

**Parameters:**
- `imageId` (string, optional): The image ID to list tools for. Defaults to "linux_latest".

**Returns:**
- `Promise<McpToolsResult>`: A promise that resolves to a result object containing success status, request ID, and the list of MCP tools.

**Example:**
```typescript
// List MCP tools
async function listMcpTools(session) {
  try {
    const result = await session.listMcpTools();
    console.log(`Found ${result.tools.length} MCP tools`);
    console.log(`Request ID: ${result.requestId}`);

    for (const tool of result.tools) {
      console.log(`Tool: ${tool.name} - ${tool.description}`);
    }

    return result.tools;
  } catch (error) {
    console.error(`Failed to list MCP tools: ${error}`);
    throw error;
  }
}
```

## Related Resources

- [FileSystem API Reference](filesystem.md)
- [Command API Reference](command.md)
- [UI API Reference](ui.md)
- [Window API Reference](window.md)
- [OSS API Reference](oss.md)
- [Application API Reference](application.md)
- [Context API Reference](context-manager.md)
