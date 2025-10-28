# Context API Reference

The Context API provides functionality for managing persistent storage contexts in the AgentBay cloud environment. Contexts allow you to persist data across sessions and reuse it in future sessions.

## Context Struct

The `Context` struct represents a persistent storage context in the AgentBay cloud environment.

### Properties

```go
ID  // The unique identifier of the context
Name  // The name of the context
CreatedAt  // Date and time when the Context was created
LastUsedAt  // Date and time when the Context was last used
```

## ContextService Struct

The `ContextService` struct provides methods for managing persistent contexts in the AgentBay cloud environment.

### List

Lists all available contexts with pagination support.

```go
List(params *ContextListParams) (*ContextListResult, error)
```

**Parameters:**
- `params` (*ContextListParams, optional): Pagination parameters. If nil, default values are used (MaxResults=10).

**Returns:**
- `*ContextListResult`: A result object containing the list of Context objects, pagination info, and RequestID.
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
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// List all contexts (using default pagination)
	result, err := client.Context.List(nil)
	if err != nil {
		fmt.Printf("Error listing contexts: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Found %d contexts:\n", len(result.Contexts))
	// Expected: Found X contexts (where X is the number of contexts, max 10 by default)
	fmt.Printf("Request ID: %s\n", result.RequestID)
	// Expected: A valid UUID-format request ID
	for i, context := range result.Contexts {
		if i < 3 { // Show first 3 contexts
			fmt.Printf("Context ID: %s, Name: %s\n", context.ID, context.Name)
			// Expected output: Context ID: SdkCtx-xxx, Name: xxx
		}
	}
}
```

### Get

Gets a context by name. Optionally creates it if it doesn't exist.

```go
Get(name string, create bool) (*ContextResult, error)
```

**Parameters:**
- `name` (string): The name of the context to get.
- `create` (bool): Whether to create the context if it doesn't exist.

**Returns:**
- `*ContextResult`: A result object containing the Context object and RequestID.
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
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Get a context, creating it if it doesn't exist
	result, err := client.Context.Get("my-persistent-context", true)
	if err != nil {
		fmt.Printf("Error getting context: %v\n", err)
		os.Exit(1)
	}

	context := result.Context
	fmt.Printf("Context ID: %s, Name: %s\n", context.ID, context.Name)
	// Expected output: Context ID: SdkCtx-xxx, Name: my-persistent-context
	fmt.Printf("Request ID: %s\n", result.RequestID)
	// Expected: A valid UUID-format request ID
}
```

### Create

Creates a new context.

```go
Create(name string) (*ContextCreateResult, error)
```

**Parameters:**
- `name` (string): The name of the context to create.

**Returns:**
- `*ContextCreateResult`: A result object containing the created Context ID and RequestID.
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
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a new context
	result, err := client.Context.Create("my-new-context")
	if err != nil {
		fmt.Printf("Error creating context: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Created context with ID: %s\n", result.ContextID)
	// Expected output: Created context with ID: SdkCtx-xxx
	fmt.Printf("Request ID: %s\n", result.RequestID)
	// Expected: A valid UUID-format request ID
}
```

### Update

Updates an existing context.

```go
Update(context *Context) (*ContextModifyResult, error)
```

**Parameters:**
- `context` (*Context): The context object to update.

**Returns:**
- `*ContextModifyResult`: A result object containing success status and RequestID.
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
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Get an existing context
	result, err := client.Context.Get("my-context", false)
	if err != nil {
		fmt.Printf("Error getting context: %v\n", err)
		os.Exit(1)
	}

	context := result.Context
	
	// Update the context name
	context.Name = "my-updated-context"
	
	// Save the changes
	updateResult, err := client.Context.Update(context)
	if err != nil {
		fmt.Printf("Error updating context: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Context updated successfully, Success: %v\n", updateResult.Success)
	// Expected output: Context updated successfully, Success: true
	fmt.Printf("Request ID: %s\n", updateResult.RequestID)
	// Expected: A valid UUID-format request ID
}
```

### Delete

Deletes a context.

```go
Delete(context *Context) (*ContextDeleteResult, error)
```

**Parameters:**
- `context` (*Context): The context object to delete.

**Returns:**
- `*ContextDeleteResult`: A result object containing success status and RequestID.
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
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Get an existing context
	result, err := client.Context.Get("my-context", false)
	if err != nil {
		fmt.Printf("Error getting context: %v\n", err)
		os.Exit(1)
	}

	context := result.Context
	
	// Delete the context
	deleteResult, err := client.Context.Delete(context)
	if err != nil {
		fmt.Printf("Error deleting context: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Context deleted successfully, Success: %v\n", deleteResult.Success)
	// Expected output: Context deleted successfully, Success: true
	fmt.Printf("Request ID: %s\n", deleteResult.RequestID)
	// Expected: A valid UUID-format request ID
}
```

### GetFileDownloadUrl

Gets a presigned download URL for a file in a context.

```go
GetFileDownloadUrl(contextID string, filePath string) (*ContextFileUrlResult, error)
```

**Parameters:**
- `contextID` (string): The ID of the context.
- `filePath` (string): The path to the file in the context.

**Returns:**
- `*ContextFileUrlResult`: A result object containing the presigned URL, expire time, and RequestID.
- `error`: An error if the operation fails.

### GetFileUploadUrl

Gets a presigned upload URL for a file in a context.

```go
GetFileUploadUrl(contextID string, filePath string) (*ContextFileUrlResult, error)
```

**Parameters:**
- `contextID` (string): The ID of the context.
- `filePath` (string): The path to the file in the context.

**Returns:**
- `*ContextFileUrlResult`: A result object containing the presigned URL, expire time, and RequestID.
- `error`: An error if the operation fails.

### ListFiles

Lists files under a specific folder path in a context.

```go
ListFiles(contextID string, parentFolderPath string, pageNumber int32, pageSize int32) (*ContextFileListResult, error)
```

**Parameters:**
- `contextID` (string): The ID of the context.
- `parentFolderPath` (string): The parent folder path to list files from.
- `pageNumber` (int32): The page number for pagination.
- `pageSize` (int32): The number of items per page.

**Returns:**
- `*ContextFileListResult`: A result object containing the list of files and RequestID.
- `error`: An error if the operation fails.

### DeleteFile

Deletes a file in a context.

```go
DeleteFile(contextID string, filePath string) (*ContextFileDeleteResult, error)
```

**Parameters:**
- `contextID` (string): The ID of the context.
- `filePath` (string): The path to the file to delete.

**Returns:**
- `*ContextFileDeleteResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

## Related Resources

- [Session API Reference](session.md)
- [ContextManager API Reference](context-manager.md) 