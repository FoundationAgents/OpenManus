# Session Struct

The `Session` struct represents a session in the AgentBay cloud environment. It provides methods for managing file systems, executing commands, and more.

## 📖 Related Tutorial

- [Session Management Guide](../../../docs/guides/common-features/basics/session-management.md) - Detailed tutorial on session lifecycle and management

## Properties

```go
AgentBay  // The AgentBay client instance
SessionID  // The ID of this session
ImageId  // The image ID used when creating this session
IsVpcEnabled  // Whether this session uses VPC resources
NetworkInterfaceIP  // Network interface IP for VPC sessions
HttpPortNumber  // HTTP port for VPC sessions
FileSystem  // The FileSystem instance for this session
Command  // The Command instance for this session
Code  // The Code instance for this session
Oss  // The Oss instance for this session
UI  // The UI instance for this session
Application  // The ApplicationManager instance for this session
Window  // The WindowManager instance for this session
Agent  // The Agent instance for this session
Context  // The ContextManager instance for this session
McpTools []McpTool  // MCP tools available for this session
```

**Accessor Methods:**
```go
IsVpc() bool  // Returns whether this session uses VPC resources
NetworkInterfaceIp() string  // Returns the network interface IP for VPC sessions
HttpPort() string  // Returns the HTTP port for VPC sessions
```

## Methods

### Delete

Deletes this session.

```go
Delete(syncContext ...bool) (*DeleteResult, error)
```

**Parameters:**
- `syncContext` (bool, optional): If true, the API will trigger a file upload via `Context.Sync()` before actually releasing the session. Default is false.

**Returns:**
- `*DeleteResult`: A result object containing success status and RequestID.
- `error`: An error if the session deletion fails.

**Behavior:**
- When `syncContext` is true, the API will first call `Context.Sync()` to trigger file upload.
- It will then check `Context.Info()` to retrieve ContextStatusData and monitor only upload task items' Status.
- The API waits until all upload tasks show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status upload tasks will have their error messages printed.
- The session deletion only proceeds after context sync status checking for upload tasks completes.

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
	client, err := agentbay.NewAgentBay("your_api_key")
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
	fmt.Printf("Session created with ID: %s\n", session.SessionID)
	// Output: Session created with ID: session-04bdwfj7u20b0o113

	// Use the session...

	// Delete the session with context synchronization
	deleteResult, err := session.Delete(true)
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Session deleted successfully with synchronized context")
	// Output: Session deleted successfully with synchronized context
	fmt.Printf("Request ID: %s\n", deleteResult.RequestID)
	// Output: Request ID: 863E5FCC-BBD2-12C2-BE98-8519BB5AF1F7
}
```

### SetLabels

Sets labels for this session.

```go
SetLabels(labels map[string]string) (*models.Response, error)
```

**Parameters:**
- `labels` (map[string]string): Key-value pairs representing the labels to set.

**Returns:**
- `*models.Response`: A response object containing RequestID and status information.
- `error`: An error if setting labels fails.

**Example:**
```go
// Set session labels
labels := map[string]string{
	"project":     "demo",
	"environment": "testing",
	"version":     "1.0.0",
}

response, err := session.SetLabels(labels)
if err != nil {
	fmt.Printf("Error setting labels: %v\n", err)
	os.Exit(1)
}

fmt.Println("Labels set successfully")
// Output: Labels set successfully
fmt.Printf("Request ID: %s\n", response.RequestID)
// Output: Request ID: 010A3CC9-F3FB-1EC3-A540-19E8BBEAEF42
```

### GetLabels

Gets the labels for this session.

```go
GetLabels() (*LabelResult, error)
```

**Returns:**
- `*LabelResult`: A result object containing the labels data, request ID, and success status.
- `error`: An error if getting labels fails.

**Example:**
```go
// Get session labels
result, err := session.GetLabels()
if err != nil {
	fmt.Printf("Error getting labels: %v\n", err)
	os.Exit(1)
}

fmt.Println("Session labels:")
// Parse the labels JSON string
var labels map[string]string
if err := json.Unmarshal([]byte(result.Labels), &labels); err == nil {
	for key, value := range labels {
		fmt.Printf("%s: %s\n", key, value)
	}
}
// Output: Session labels:
// environment: testing
// project: demo
// version: 1.0.0
```

### Info

Gets information about this session.

```go
Info() (*SessionInfo, error)
```

**Returns:**
- `*SessionInfo`: An object containing information about the session.
- `error`: An error if getting session information fails.

**Example:**
```go
// Get session information
infoResult, err := session.Info()
if err != nil {
	fmt.Printf("Error getting session info: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Session ID: %s\n", infoResult.Info.SessionId)
// Output: Session ID: session-04bdwfj7u20b0o115
fmt.Printf("Resource URL: %s\n", infoResult.Info.ResourceUrl)
// Output: Resource URL: https://pre-myspace-wuying.aliyun.com/app/InnoArchClub/mcp_container/mcp.html?authcode=...
fmt.Printf("App ID: %s\n", infoResult.Info.AppId)
// Output: App ID: mcp-server-ubuntu
```

### GetLink

Gets a link for this session.

```go
GetLink(protocolType *string, port *int32) (*LinkResult, error)
```

**Parameters:**
- `protocolType` (*string): The protocol type for the link. If nil, the default protocol will be used.
- `port` (*int32): The port for the link. If nil, the default port will be used. **Port must be an integer in the range [30100, 30199]**.

**Returns:**
- `*LinkResult`: A result object containing the link and request ID.
- `error`: An error if getting the link fails or if the port is outside the valid range.

**Port Range Validation:**
- Valid port range: **[30100, 30199]**
- If a port outside this range is provided, the method will return an error with the message: `"invalid port value: {port}. Port must be an integer in the range [30100, 30199]"`
- Common ports like 80, 443, 8080, etc. are **not allowed** and will result in validation errors

**Example:**
```go
// Get link with specific protocol and valid port
// Note: For ComputerUse images, port must be explicitly specified
protocolType := "https"
var validPort int32 = 30150  // Valid port in range [30100, 30199]
linkResult, err := session.GetLink(&protocolType, &validPort)
if err != nil {
	fmt.Printf("Error getting link: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Session link: %s (RequestID: %s)\n", linkResult.Link, linkResult.RequestID)
// Output: Session link: https://gw-cn-hangzhou-ai-linux.wuyinggw.com:8008/... (RequestID: 57D0226F-EF89-1C95-929F-577EC40A1F20)

// Example of invalid port usage (will fail)
var invalidPort int32 = 8080  // Invalid port - outside [30100, 30199] range
_, err = session.GetLink(nil, &invalidPort)
if err != nil {
	fmt.Printf("Expected error with invalid port: %v\n", err)
	// Output: invalid port value: 8080. Port must be an integer in the range [30100, 30199]
}
```

### ListMcpTools

Lists MCP tools available for this session.

```go
ListMcpTools() (*McpToolsResult, error)
```

**Returns:**
- `*McpToolsResult`: A result object containing the list of MCP tools and request ID.
- `error`: An error if listing MCP tools fails.

**Example:**
```go
// List MCP tools
toolsResult, err := session.ListMcpTools()
if err != nil {
	fmt.Printf("Error listing MCP tools: %v\n", err)
	os.Exit(1)
}

fmt.Printf("Found %d MCP tools\n", len(toolsResult.Tools))
// Output: Found 27 MCP tools
for i, tool := range toolsResult.Tools {
	if i < 3 {
		fmt.Printf("Tool: %s - %s\n", tool.Name, tool.Description)
	}
}
// Output: Tool: execute_command - Execute a command on the system
// Tool: read_file - Read contents of a file
// Tool: write_file - Write content to a file
```

## Session Creation with Extra Configurations

Sessions can be created with additional configurations for specific environments using the `ExtraConfigs` parameter in `CreateSessionParams`. This is particularly useful for mobile sessions that require app management rules and resolution settings.

### Mobile Session Configuration

For mobile sessions, you can configure app management rules and display settings using `MobileExtraConfig`:

```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create mobile configuration with whitelist
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.test.app",
			"com.trusted.service",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	// Create session parameters with mobile configuration
	params := agentbay.NewCreateSessionParams().
		WithImageId("mobile_latest").
		WithLabels(map[string]string{
			"project":     "mobile-testing",
			"config_type": "whitelist",
		}).
		WithExtraConfigs(extraConfigs)

	// Create the session
	result, err := client.Create(params)
	if err != nil {
		fmt.Printf("Error creating mobile session: %v\n", err)
		os.Exit(1)
	}

	session := result.Session
	fmt.Printf("Mobile session created with ID: %s\n", session.SessionID)

	// Use the session...

	// Clean up
	deleteResult, err := session.Delete()
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Session deleted (RequestID: %s)\n", deleteResult.RequestID)
}
```

### App Manager Rules

The `AppManagerRule` struct allows you to control which applications are allowed or blocked in mobile sessions:

#### Whitelist Configuration
```go
// Create whitelist rule - only specified apps are allowed
appRule := &models.AppManagerRule{
	RuleType: "White",
	AppPackageNameList: []string{
		"com.android.settings",
		"com.google.android.gms",
		"com.trusted.app",
	},
}
```

#### Blacklist Configuration
```go
// Create blacklist rule - specified apps are blocked
appRule := &models.AppManagerRule{
	RuleType: "Black",
	AppPackageNameList: []string{
		"com.malware.suspicious",
		"com.unwanted.adware",
		"com.blocked.app",
	},
}
```

### Mobile Extra Config Options

The `MobileExtraConfig` struct provides the following options:

- **`LockResolution`** (bool): When set to `true`, locks the display resolution to prevent changes during the session. When `false`, allows flexible resolution adjustments.
- **`AppManagerRule`** (*AppManagerRule): Defines the application access control rules for the mobile session.

### JSON Serialization

Extra configurations are automatically serialized to JSON when creating sessions. You can also manually serialize them for inspection:

```go
// Serialize extra configs to JSON
jsonStr, err := extraConfigs.ToJSON()
if err != nil {
	fmt.Printf("Error serializing extra configs: %v\n", err)
	return
}
fmt.Printf("Extra configs JSON: %s\n", jsonStr)

// Get JSON from session parameters
params := agentbay.NewCreateSessionParams().WithExtraConfigs(extraConfigs)
paramsJSON, err := params.GetExtraConfigsJSON()
if err != nil {
	fmt.Printf("Error getting extra configs JSON: %v\n", err)
	return
}
fmt.Printf("Session params JSON: %s\n", paramsJSON)
```

### Best Practices

1. **Use Appropriate Image IDs**: For mobile sessions with extra configs, use `mobile_latest` or specific mobile image IDs.

2. **Set Descriptive Labels**: Use labels to identify the configuration type and purpose:
   ```go
   WithLabels(map[string]string{
       "config_type": "whitelist",
       "security":    "enabled",
       "project":     "mobile-testing",
   })
   ```

3. **Test Configurations**: Validate your app package names and configuration settings in a test environment before production use.

4. **Handle Errors Gracefully**: Always check for errors when creating sessions with extra configurations, as invalid configurations may cause session creation to fail.

## Related Resources

- [FileSystem API Reference](filesystem.md)
- [Command API Reference](command.md)
- [UI API Reference](ui.md)
- [Window API Reference](window.md)
- [OSS API Reference](oss.md)
- [Application API Reference](application.md)
- [Context API Reference](context-manager.md)
