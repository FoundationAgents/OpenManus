# ContextManager API Reference

The `ContextManager` class provides functionality for managing contexts within a session. It enables you to interact with the contexts that are synchronized to the session, including reading and writing data, and managing file operations.

## 📖 Related Tutorial

- [Data Persistence Guide](../../../docs/guides/common-features/basics/data-persistence.md) - Detailed tutorial on context management and data persistence

## Overview

The `ContextManager` is accessed through a session instance (`session.context`) and provides functionality for managing contexts within that session.

## Data Types

```typescript
interface ContextStatusData {
  contextId: string;     // The ID of the context
  path: string;          // The path where the context is mounted
  errorMessage: string;  // Error message if the operation failed
  status: string;        // Status of the synchronization task
  startTime: number;     // Start time of the task (Unix timestamp)
  finishTime: number;    // Finish time of the task (Unix timestamp)
  taskType: string;      // Type of the task (e.g., "upload", "download")
}
```

## Result Types

```typescript
interface ContextInfoResult extends ApiResponse {
  requestId: string;  // The request ID
  contextStatusData: ContextStatusData[];  // Array of context status data objects
}
```

```typescript
interface ContextSyncResult extends ApiResponse {
  requestId: string;  // The request ID
  success: boolean;   // Indicates whether the synchronization was successful
}
```

## Methods

### info

Gets information about context synchronization status for the current session.

```typescript
info(): Promise<ContextInfoResult>
```

**Returns:**
- `Promise<ContextInfoResult>`: A promise that resolves to a result object containing the context status data and request ID.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Create a session and get context info
async function getContextInfo() {
  try {
    // Create a session
    const result = await agentBay.create();
    if (result.success) {
      const session = result.session;
      
      try {
        // Get context synchronization information
        const infoResult = await session.context.info();
        console.log(`Request ID: ${infoResult.requestId}`);
        console.log(`Context status data count: ${infoResult.contextStatusData.length}`);
        
        if (infoResult.contextStatusData.length > 0) {
          infoResult.contextStatusData.forEach(item => {
            console.log(`  Context ${item.contextId}: Status=${item.status}, ` +
                       `Path=${item.path}, TaskType=${item.taskType}`);
          });
        } else {
          console.log('No context synchronization tasks found');
        }
      } finally {
        await session.delete();
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

getContextInfo();

// Expected output:
// Request ID: 41FC3D61-4AFB-1D2E-A08E-5737B2313234
// Context status data count: 0
// No context synchronization tasks found
```

### infoWithParams

Gets information about context synchronization status with optional filter parameters.

```typescript
infoWithParams(contextId?: string, path?: string, taskType?: string): Promise<ContextInfoResult>
```

**Parameters:**
- `contextId` (string, optional): The ID of the context to get information for.
- `path` (string, optional): The path where the context is mounted.
- `taskType` (string, optional): The type of task to get information for (e.g., "upload", "download").

**Returns:**
- `Promise<ContextInfoResult>`: A promise that resolves to a result object containing the context status data and request ID.

**Example:**
```typescript
// Get info for a specific context and path
const infoResult = await session.context.infoWithParams(
  'SdkCtx-04bdw8o39bq47rv1t',
  '/mnt/persistent'
);

console.log(`Request ID: ${infoResult.requestId}`);
infoResult.contextStatusData.forEach(item => {
  console.log(`  Context ${item.contextId}: Status=${item.status}`);
});

// Expected output when no sync tasks are found:
// Request ID: EB18A2D5-3C51-1F50-9FF1-8543CA328772
```

### sync

Synchronizes a context with the session. This method supports two modes:
- **Async mode (default)**: When called without a callback, it waits for the sync operation to complete.
- **Callback mode**: When a callback is provided, it returns immediately and calls the callback when complete.

```typescript
sync(
  contextId?: string,
  path?: string,
  mode?: string,
  callback?: SyncCallback,
  maxRetries?: number,
  retryInterval?: number
): Promise<ContextSyncResult>
```

**Parameters:**
- `contextId` (string, optional): The ID of the context to synchronize.
- `path` (string, optional): The path where the context should be mounted.
- `mode` (string, optional): The synchronization mode (e.g., "upload", "download").
- `callback` (SyncCallback, optional): Optional callback function `(success: boolean) => void`. If provided, the method runs in background and calls callback when complete.
- `maxRetries` (number, optional): Maximum number of retries for polling completion status. Default: 150.
- `retryInterval` (number, optional): Milliseconds to wait between retries. Default: 1500.

**Returns:**
- `Promise<ContextSyncResult>`: A promise that resolves to a result object containing success status and request ID.

**Example (Async mode - waits for completion):**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Synchronize context and wait for completion
async function syncContextExample() {
  try {
    // Create a session
    const result = await agentBay.create();
    if (result.success) {
      const session = result.session;
      
      try {
        // Get or create a context
        const contextResult = await agentBay.context.get('my-context', true);
        if (contextResult.context) {
          // Trigger context synchronization and wait for completion
          const syncResult = await session.context.sync(
            contextResult.context.id,
            '/mnt/persistent',
            'upload'
          );
          
          console.log(`Sync completed - Success: ${syncResult.success}`);
          console.log(`Request ID: ${syncResult.requestId}`);
        }
      } finally {
        await session.delete();
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

syncContextExample();

// Expected output:
// Sync completed - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
```

**Example (Callback mode - returns immediately):**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

const agentBay = new AgentBay({ apiKey: 'your_api_key' });

async function syncWithCallbackExample() {
  try {
    const result = await agentBay.create();
    if (result.success) {
      const session = result.session;
      
      try {
        const contextResult = await agentBay.context.get('my-context', true);
        
        // Trigger sync with callback - returns immediately
        const syncResult = await session.context.sync(
          contextResult.context.id,
          '/mnt/persistent',
          'upload',
          (success: boolean) => {
            if (success) {
              console.log('Context sync completed successfully');
            } else {
              console.log('Context sync failed or timed out');
            }
          },
          10,   // maxRetries
          1000  // retryInterval in milliseconds
        );
        
        console.log(`Sync triggered - Success: ${syncResult.success}`);
        console.log(`Request ID: ${syncResult.requestId}`);
        
        // Wait a bit for callback to be called
        await new Promise(resolve => setTimeout(resolve, 3000));
      } finally {
        await session.delete();
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

syncWithCallbackExample();

// Expected output:
// Sync triggered - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
// Context sync completed successfully  (printed by callback after completion)
```

## Complete Usage Example

```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function completeContextManagerExample() {
  // Initialize the SDK
  const agentBay = new AgentBay({ apiKey: 'your_api_key' });

  try {
    // Create a session
    const result = await agentBay.create();
    if (!result.success) {
      console.log(`Failed to create session: ${result.errorMessage}`);
      return;
    }

    const session = result.session;
    console.log(`Session created: ${session.getSessionId()}`);

    try {
      // Get or create a context
      const contextResult = await agentBay.context.get('my-persistent-context', true);
      if (!contextResult.context) {
        console.log('Failed to get context');
        return;
      }

      console.log(`Context ID: ${contextResult.context.id}`);

      // Check initial context status
      const infoResult = await session.context.info();
      console.log(`\nInitial context status data count: ${infoResult.contextStatusData.length}`);

      // Synchronize context and wait for completion
      const syncResult = await session.context.sync(
        contextResult.context.id,
        '/mnt/persistent',
        'upload'
      );

      console.log(`\nSync completed - Success: ${syncResult.success}`);
      console.log(`Request ID: ${syncResult.requestId}`);

      // Check final context status
      const finalInfo = await session.context.infoWithParams(
        contextResult.context.id,
        '/mnt/persistent'
      );

      console.log(`\nFinal context status data count: ${finalInfo.contextStatusData.length}`);
      finalInfo.contextStatusData.forEach(item => {
        console.log(`  Context ${item.contextId}: Status=${item.status}, TaskType=${item.taskType}`);
      });

    } finally {
      // Cleanup
      await session.delete();
      console.log('\nSession deleted');
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

completeContextManagerExample();

// Expected output:
// Session created: session-04bdwfj7u1sew7t4f
// Context ID: SdkCtx-04bdw8o39bq47rv1t
//
// Initial context status data count: 0
//
// Sync completed - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
//
// Final context status data count: 0
//
// Session deleted
```

## Notes

- The `ContextManager` is designed to work with contexts synchronized to a session. It is different from the `ContextService` (accessible via `agentBay.context`) which manages contexts globally.
- `info()` and `infoWithParams()` return information about the current synchronization tasks for contexts in the session.
- `sync()` is an async method. When called without a callback, it waits for synchronization to complete. When called with a callback, it returns immediately and calls the callback when complete.
- Synchronization polling checks the status every `retryInterval` milliseconds for up to `maxRetries` attempts.
- Empty `contextStatusData` arrays are normal when there are no active sync tasks.
- All methods return promises and should be called with `await`.
