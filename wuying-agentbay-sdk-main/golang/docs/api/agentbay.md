# AgentBay Class API Reference

The `AgentBay` class is the main entry point for interacting with the AgentBay cloud environment. It provides methods for creating, retrieving, listing, and deleting sessions.

## 📖 Related Tutorials

- [SDK Configuration Guide](../../../docs/guides/common-features/configuration/sdk-configuration.md) - Detailed tutorial on configuring the SDK
- [VPC Sessions Guide](../../../docs/guides/common-features/advanced/vpc-sessions.md) - Tutorial on creating sessions in VPC environments
- [Session Link Access Guide](../../../docs/guides/common-features/advanced/session-link-access.md) - Tutorial on accessing sessions via links

## Constructor

### NewAgentBay

```go
func NewAgentBay(apiKey string, opts ...Option) (*AgentBay, error)
```

**Parameters:**
- `apiKey` (string): The API key for authentication. If empty, the SDK will look for the `AGENTBAY_API_KEY` environment variable.
- `opts` (...Option, optional): Optional configuration options. Use `WithConfig(*Config)` to provide custom configuration containing RegionID, Endpoint, and TimeoutMs. If not provided, default configuration is used.

**Returns:**
- `*AgentBay`: A new AgentBay instance.
- `error`: An error if initialization fails.

**Raises:**
- `error`: If no API key is provided and `AGENTBAY_API_KEY` environment variable is not set.

## Properties

### Context

The `Context` field provides access to a `ContextService` instance for managing persistent contexts. See the [Context API Reference](context.md) for more details.

## Methods


Creates a new session in the AgentBay cloud environment.


```go
Create(params *CreateSessionParams) (*SessionResult, error)
```

**Parameters:**
- `params` (*CreateSessionParams, optional): Parameters for session creation. If nil, default parameters will be used.

**Returns:**
- `*SessionResult`: A result object containing the new Session instance and RequestID.
- `error`: An error if the session creation fails.

**Behavior:**
- When `params` includes valid `PersistenceDataList`, after creating the session, the API will check `session.Context.Info()` to retrieve ContextStatusData.
- It will continuously monitor all data items' Status in ContextStatusData until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The Create operation only returns after context status checking completes.

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK with default configuration
	client, err := agentbay.NewAgentBay("")
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}
	// Result: Success: Created client with default config

	// Or initialize with custom configuration
	config := &agentbay.Config{
		RegionID:  "cn-hangzhou",
		Endpoint:  "",
		TimeoutMs: 30000,
	}
	clientWithConfig, err := agentbay.NewAgentBay("", agentbay.WithConfig(config))
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}
	// Result: Success: Created client with custom config (RegionID: cn-hangzhou)

	// Create a session with default parameters
	defaultResult, err := client.Create(nil)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Created session with ID: %s\n", defaultResult.Session.SessionID)
	// Result: Success: Created session with ID: session-xxxxxxxxxxxxxxx
	// Result: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

	// Create a session with custom parameters
	labels := map[string]string{
		"project":     "demo",
		"environment": "testing",
	}
	params := &agentbay.CreateSessionParams{
		ImageId: "windows_latest",
		Labels:  labels,
	}
	customResult, err := client.Create(params)
	if err != nil {
		fmt.Printf("Error creating custom session: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Created custom session with ID: %s\n", customResult.Session.SessionID)
	// Result: Success: Created custom session with ID: session-xxxxxxxxxxxxxxx
	// Result: Image ID: windows_latest
	// Result: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

	// RECOMMENDED: Create a session with context synchronization
	// First, create a context
	contextResult, err := client.Context.Create("my-context")
	if err != nil {
		fmt.Printf("Error creating context: %v\n", err)
		os.Exit(1)
	}
	// Result: Success: Created context with ID: SdkCtx-xxxxxxxxxxxxxxx

	contextSync := &agentbay.ContextSync{
		ContextID: contextResult.ContextID,
		Path:      "/home/wuying",
		Policy:    agentbay.NewSyncPolicy(),
	}
	syncParams := &agentbay.CreateSessionParams{
		ImageId:     "windows_latest",
		ContextSync: []*agentbay.ContextSync{contextSync},
	}
	syncResult, err := client.Create(syncParams)
	if err != nil {
		fmt.Printf("Error creating session with context sync: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Created session with context sync: %s\n", syncResult.Session.SessionID)
	// Result: Waiting for context synchronization to complete...
	// Result: Context SdkCtx-xxxxxxxxxxxxxxx status: Preparing, path: /home/wuying
	// Result: Context SdkCtx-xxxxxxxxxxxxxxx status: Success, path: /home/wuying
	// Result: Context synchronization completed successfully
	// Result: Success: Created session with context sync: session-xxxxxxxxxxxxxxx
}
```

### Get

Retrieves a session by its ID.

```go
Get(sessionID string) (*SessionResult, error)
```

**Parameters:**
- `sessionID` (string): The ID of the session to retrieve.

**Returns:**
- `*SessionResult`: A result object containing the Session instance, request ID, success status, and error message if any.
- `error`: Always returns nil. Errors are indicated via SessionResult.Success and SessionResult.ErrorMessage fields.

**Example:**
```go
package main

import (
	"fmt"
	"log"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	client, err := agentbay.NewAgentBay("")
	if err != nil {
		log.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	createResult, err := client.Create(nil)
	if err != nil {
		log.Fatalf("Failed to create session: %v", err)
	}
	sessionID := createResult.Session.SessionID
	fmt.Printf("Created session with ID: %s\n", sessionID)
	// Output: Created session with ID: session-xxxxxxxxxxxxxx

	result, err := client.Get(sessionID)
	if err != nil {
		log.Fatalf("Failed to get session: %v", err)
	}
	
	if result.Success {
		fmt.Printf("Successfully retrieved session: %s\n", result.Session.SessionID)
		// Output: Successfully retrieved session: session-xxxxxxxxxxxxxx
		fmt.Printf("Request ID: %s\n", result.RequestID)
		// Output: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
		
		deleteResult, err := result.Session.Delete()
		if err != nil {
			log.Fatalf("Failed to delete session: %v", err)
		}
		if deleteResult.Success {
			fmt.Printf("Session %s deleted successfully\n", sessionID)
			// Output: Session session-xxxxxxxxxxxxxx deleted successfully
		}
	} else {
		fmt.Printf("Failed to get session: %s\n", result.ErrorMessage)
	}
}
```


Lists all available sessions cached in the current client instance.




Lists sessions filtered by the provided labels. It returns sessions that match all the specified labels. This method supports pagination to handle large result sets efficiently.


```go
ListByLabels(params *ListSessionParams) (*SessionListResult, error)
```

**Parameters:**
- `params` (*ListSessionParams, optional): Parameters for filtering sessions by labels. If nil, all sessions will be returned.

**Returns:**
- `*SessionListResult`: A result object containing the filtered sessions, pagination information, and RequestID.
- `error`: An error if the session listing fails.

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

	// Create pagination parameters
	labels := map[string]string{
		"environment": "production",
		"project":     "demo",
	}
	params := &agentbay.ListSessionParams{
		MaxResults: 10,
		NextToken:  "",
		Labels:     labels,
	}

	// Get the first page of results
	result, err := client.ListByLabels(params)
	if err != nil {
		fmt.Printf("Error listing sessions by labels: %v\n", err)
		os.Exit(1)
	}
	// Result: API Call: ListSession
	// Result: Request: Labels={"environment":"production","project":"demo"}, MaxResults=10

	// Process the results
	fmt.Printf("Found %d sessions:\n", len(result.Sessions))
	for _, session := range result.Sessions {
		fmt.Printf("Session ID: %s\n", session.SessionID)
	}
	// Result: Found N sessions (depends on actual sessions matching the labels)

	// Print pagination information
	fmt.Printf("Total count: %d\n", result.TotalCount)
	fmt.Printf("Max results per page: %d\n", result.MaxResults)
	fmt.Printf("Next token: %s\n", result.NextToken)
	// Result: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

	// If there is a next page, retrieve it
	if result.NextToken != "" {
		params.NextToken = result.NextToken
		nextPageResult, err := client.ListByLabels(params)
		if err != nil {
			fmt.Printf("Error retrieving next page: %v\n", err)
			os.Exit(1)
		}
		// Process the next page...
	}
}
```

### List

Returns paginated list of Sessions filtered by labels.

```go
List(labels map[string]string, page *int, limit *int32) (*SessionListResult, error)
```

**Parameters:**
- `labels` (map[string]string, optional): Labels to filter Sessions. Can be nil for no filtering (returns all sessions).
- `page` (*int, optional): Page number for pagination (starting from 1). nil or 0 returns the first page.
- `limit` (*int32, optional): Maximum number of items per page. nil or 0 uses default of 10.

**Returns:**
- `*SessionListResult`: Paginated list of session IDs that match the labels, including RequestID and pagination information.
- `error`: An error if the operation fails.

**Key Features:**
- **Simple Interface**: Pass labels directly as a map parameter
- **Pagination Support**: Use `page` and `limit` parameters for easy pagination
- **Request ID**: All responses include a RequestID for tracking and debugging
- **Flexible Filtering**: Filter by any combination of labels or list all sessions

**Example:**
```go
package main

import (
	"fmt"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	client, _ := agentbay.NewAgentBay("your_api_key", nil)

	// List all sessions
	result, err := client.List(nil, nil, nil)

	// List sessions with specific labels
	result, err = client.List(map[string]string{"project": "demo"}, nil, nil)

	// List sessions with pagination (page 2, 10 items per page)
	page := 2
	limit := int32(10)
	result, err = client.List(map[string]string{"my-label": "my-value"}, &page, &limit)

	if err == nil {
		for _, sessionId := range result.SessionIds {
			fmt.Printf("Session ID: %s\n", sessionId)
		}
		fmt.Printf("Total count: %d\n", result.TotalCount)
		fmt.Printf("Request ID: %s\n", result.RequestID)
	}
}
```

### Delete

Deletes a session from the AgentBay cloud environment.

```go
Delete(session *Session, syncContext ...bool) (*DeleteResult, error)
```

**Parameters:**
- `session` (*Session): The session to delete.
- `syncContext` (bool, optional): If true, the API will trigger a file upload via `session.Context.Sync()` before actually releasing the session. Default is false.

**Returns:**
- `*DeleteResult`: A result object containing success status and RequestID.
- `error`: An error if the session deletion fails.

**Behavior:**
- When `syncContext` is true, the API will first call `session.Context.Sync()` to trigger file upload.
- It will then check `session.Context.Info()` to retrieve ContextStatusData and monitor all data items' Status.
- The API waits until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The session deletion only proceeds after context sync status checking completes.

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

	// Create a context first
	contextResult, err := client.Context.Create("test-context")
	if err != nil {
		fmt.Printf("Error creating context: %v\n", err)
		os.Exit(1)
	}
	// Result: Success: Created context with ID: SdkCtx-xxxxxxxxxxxxxxx

	// Create a session with context synchronization
	contextSync := &agentbay.ContextSync{
		ContextID: contextResult.ContextID,
		Path:      "/home/wuying",
		Policy:    agentbay.NewSyncPolicy(),
	}
	params := &agentbay.CreateSessionParams{
		ImageId:     "windows_latest",
		ContextSync: []*agentbay.ContextSync{contextSync},
	}

	createResult, err := client.Create(params)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}

	session := createResult.Session
	fmt.Printf("Created session with ID: %s\n", session.SessionID)
	// Result: Created session with context sync: session-xxxxxxxxxxxxxxx

	// Use the session for operations...

	// Delete the session with context synchronization
	deleteResult, err := client.Delete(session, true)
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Session deleted successfully with synchronized context")
	fmt.Printf("Request ID: %s\n", deleteResult.RequestID)
	// Result: Triggering context synchronization before session deletion...
	// Result: Context sync completed successfully
	// Result: Success: Session deleted successfully with synchronized context
	// Result: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
}
```