# ContextManager API Reference

The `ContextManager` class provides functionality for managing contexts within a session. It enables you to interact with the contexts that are synchronized to the session, including reading and writing data, and managing file operations.

## 📖 Related Tutorial

- [Data Persistence Guide](../../../docs/guides/common-features/basics/data-persistence.md) - Detailed tutorial on context management and data persistence

## Overview

The `ContextManager` is accessed through a session instance (`session.Context`) and provides functionality for managing contexts within that session.

## Data Types

```go
type ContextStatusData struct {
	ContextId    string  // The ID of the context
	Path         string  // The path where the context is mounted
	ErrorMessage string  // Error message if the operation failed
	Status       string  // Status of the synchronization task
	StartTime    int64   // Start time of the task (Unix timestamp)
	FinishTime   int64   // Finish time of the task (Unix timestamp)
	TaskType     string  // Type of the task (e.g., "upload", "download")
}
```

## Result Types

```go
type ContextInfoResult struct {
	models.ApiResponse              // Embedded ApiResponse struct
	ContextStatusData []ContextStatusData  // Array of context status data objects
}
```

```go
type ContextSyncResult struct {
	models.ApiResponse  // Embedded ApiResponse struct
	Success bool        // Indicates whether the synchronization was successful
}
```

## Methods

### Info

Gets information about context synchronization status for the current session.

```go
Info() (*ContextInfoResult, error)
```

**Returns:**
- `*ContextInfoResult`: A result object containing the context status data and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay(os.Getenv("AGENTBAY_API_KEY"), nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session
	createResult, err := client.Create(nil)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	
	session := createResult.Session
	defer session.Delete()
	
	// Get context synchronization information
	infoResult, err := session.Context.Info()
	if err != nil {
		fmt.Printf("Error getting context info: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Request ID: %s\n", infoResult.RequestID)
	fmt.Printf("Context status data count: %d\n", len(infoResult.ContextStatusData))
	for _, item := range infoResult.ContextStatusData {
		fmt.Printf("  Context %s: Status=%s, Path=%s, TaskType=%s\n",
			item.ContextId, item.Status, item.Path, item.TaskType)
	}
}

// Expected output:
// Request ID: 41FC3D61-4AFB-1D2E-A08E-5737B2313234
// Context status data count: 0
```

### InfoWithParams

Gets information about context synchronization status with optional filter parameters.

```go
InfoWithParams(contextId, path, taskType string) (*ContextInfoResult, error)
```

**Parameters:**
- `contextId` (string): Optional. The ID of the context to get information for.
- `path` (string): Optional. The path where the context is mounted.
- `taskType` (string): Optional. The type of task to get information for (e.g., "upload", "download").

**Returns:**
- `*ContextInfoResult`: A result object containing the context status data and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
// Get info for a specific context and path
infoResult, err := session.Context.InfoWithParams(
	"SdkCtx-04bdw8o39bq47rv1t",
	"/mnt/persistent",
	"",
)
if err != nil {
	fmt.Printf("Error getting context info: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Request ID: %s\n", infoResult.RequestID)
for _, item := range infoResult.ContextStatusData {
	fmt.Printf("  Context %s: Status=%s\n", item.ContextId, item.Status)
}

// Expected output when no sync tasks are found:
// Request ID: EB18A2D5-3C51-1F50-9FF1-8543CA328772
// Context status data count: 0
```

### Sync

Synchronizes a context with the session (without waiting for completion).

```go
Sync() (*ContextSyncResult, error)
```

**Returns:**
- `*ContextSyncResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
// Trigger context synchronization
syncResult, err := session.Context.Sync()
if err != nil {
	fmt.Printf("Error synchronizing context: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Sync triggered - Success: %v\n", syncResult.Success)
fmt.Printf("Request ID: %s\n", syncResult.RequestID)

// Expected output:
// Sync triggered - Success: true
// Request ID: 8D845246-2279-13E5-8F15-9DE68CB1B686
```

### SyncWithParams

Synchronizes a context with the session with optional parameters (without waiting for completion).

```go
SyncWithParams(contextId, path, mode string) (*ContextSyncResult, error)
```

**Parameters:**
- `contextId` (string): Optional. The ID of the context to synchronize.
- `path` (string): Optional. The path where the context should be mounted.
- `mode` (string): Optional. The synchronization mode (e.g., "upload", "download"). Defaults to "upload" if empty.

**Returns:**
- `*ContextSyncResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay(os.Getenv("AGENTBAY_API_KEY"), nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session
	createResult, err := client.Create(nil)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	
	session := createResult.Session
	defer session.Delete()
	
	// Get or create a context
	contextResult, err := client.Context.Get("my-context", true)
	if err != nil {
		fmt.Printf("Error getting context: %v\n", err)
		os.Exit(1)
	}
	
	// Synchronize the context with specific parameters
	syncResult, err := session.Context.SyncWithParams(
		contextResult.ContextID,
		"/mnt/persistent",
		"upload",
	)
	if err != nil {
		fmt.Printf("Error synchronizing context: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Sync triggered - Success: %v\n", syncResult.Success)
	fmt.Printf("Request ID: %s\n", syncResult.RequestID)
}

// Expected output:
// Sync triggered - Success: true
// Request ID: 8D845246-2279-13E5-8F15-9DE68CB1B686
```

### SyncWithCallback

Synchronizes a context with support for both synchronous (blocking) and asynchronous (callback) modes.

```go
SyncWithCallback(contextId, path, mode string, callback SyncCallback, maxRetries int, retryInterval int) (*ContextSyncResult, error)
```

**Parameters:**
- `contextId` (string): Optional. The ID of the context to synchronize.
- `path` (string): Optional. The path where the context should be mounted.
- `mode` (string): Optional. The synchronization mode (e.g., "upload", "download"). Defaults to "upload" if empty.
- `callback` (SyncCallback): Optional. If provided, the function runs in background and calls callback when complete. If nil, waits for completion before returning.
- `maxRetries` (int): Maximum number of retries for polling completion status.
- `retryInterval` (int): Milliseconds to wait between retries.

**Returns:**
- `*ContextSyncResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**Example (Synchronous mode - waits for completion):**
```go
// Synchronous mode: callback is nil, so it waits for completion
syncResult, err := session.Context.SyncWithCallback(
	contextResult.ContextID,
	"/mnt/persistent",
	"upload",
	nil,  // No callback - synchronous mode
	10,   // maxRetries
	1000, // retryInterval in milliseconds
)
if err != nil {
	fmt.Printf("Error in SyncWithCallback: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Sync completed - Success: %v\n", syncResult.Success)
fmt.Printf("Request ID: %s\n", syncResult.RequestID)

// Expected output:
// No sync tasks found
// Sync completed - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
```

**Example (Asynchronous mode - with callback):**
```go
// Asynchronous mode: with callback, returns immediately
syncResult, err := session.Context.SyncWithCallback(
	contextResult.ContextID,
	"/mnt/persistent",
	"upload",
	func(success bool) {
		if success {
			fmt.Println("Context sync completed successfully")
		} else {
			fmt.Println("Context sync failed or timed out")
		}
	},
	150,  // maxRetries
	1500, // retryInterval in milliseconds
)
if err != nil {
	fmt.Printf("Error in SyncWithCallback: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Sync triggered - Success: %v\n", syncResult.Success)
fmt.Printf("Request ID: %s\n", syncResult.RequestID)
// ... callback will be called asynchronously when sync completes

// Expected output:
// Sync triggered - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
// Context sync completed successfully  (printed by callback after completion)
```

## Complete Usage Example

```go
package main

import (
	"fmt"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay(os.Getenv("AGENTBAY_API_KEY"), nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session
	createResult, err := client.Create(nil)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	
	session := createResult.Session
	defer session.Delete()
	
	fmt.Printf("Session created: %s\n", session.GetSessionId())
	
	// Get or create a context
	contextResult, err := client.Context.Get("my-persistent-context", true)
	if err != nil {
		fmt.Printf("Error getting context: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Context ID: %s\n", contextResult.ContextID)
	
	// Check initial context status
	infoResult, err := session.Context.Info()
	if err != nil {
		fmt.Printf("Error getting context info: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Initial context status data count: %d\n", len(infoResult.ContextStatusData))
	
	// Synchronize context and wait for completion
	syncResult, err := session.Context.SyncWithCallback(
		contextResult.ContextID,
		"/mnt/persistent",
		"upload",
		nil,  // nil callback means synchronous mode
		10,   // maxRetries
		1000, // retryInterval in ms
	)
	if err != nil {
		fmt.Printf("Error in sync: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Sync completed - Success: %v\n", syncResult.Success)
	fmt.Printf("Request ID: %s\n", syncResult.RequestID)
	
	// Check final context status
	finalInfo, err := session.Context.InfoWithParams(
		contextResult.ContextID,
		"/mnt/persistent",
		"",
	)
	if err != nil {
		fmt.Printf("Error getting final context info: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Printf("Final context status data count: %d\n", len(finalInfo.ContextStatusData))
	for _, item := range finalInfo.ContextStatusData {
		fmt.Printf("  Context %s: Status=%s, TaskType=%s\n",
			item.ContextId, item.Status, item.TaskType)
	}
}

// Expected output:
// Session created: session-04bdwfj7u1sew7t4f
// Context ID: SdkCtx-04bdw8o39bq47rv1t
// Initial context status data count: 0
// No sync tasks found
// Sync completed - Success: true
// Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
// Final context status data count: 0
```

## Notes

- The `ContextManager` is designed to work with contexts synchronized to a session. It is different from the `ContextService` (accessible via `client.Context`) which manages contexts globally.
- `Info()` and `InfoWithParams()` return information about the current synchronization tasks for contexts in the session.
- `Sync()` and `SyncWithParams()` trigger the synchronization but return immediately without waiting for completion.
- `SyncWithCallback()` provides a dual-mode interface: if callback is nil, it waits for completion (synchronous mode); if callback is provided, it returns immediately and calls the callback when complete (asynchronous mode).
- Synchronization polling checks the status every `retryInterval` milliseconds for up to `maxRetries` attempts.
- Empty `ContextStatusData` arrays are normal when there are no active sync tasks.
