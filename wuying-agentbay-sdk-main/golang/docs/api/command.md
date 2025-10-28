# Command Class API Reference

The `Command` class provides methods for executing commands within a session in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Command Execution Guide](../../../docs/guides/common-features/basics/command-execution.md) - Detailed tutorial on executing shell commands

## Methods

### ExecuteCommand

Executes a shell command in the cloud environment.

```go
ExecuteCommand(command string, timeoutMs ...int) (*CommandResult, error)
```

**Parameters:**
- `command` (string): The command to execute.
- `timeoutMs` (int, optional): The timeout for the command execution in milliseconds. Default is 1000ms.

**Returns:**
- `*CommandResult`: A result object containing the command output and RequestID.
- `error`: An error if the command execution fails.

**CommandResult Structure:**
```go
type CommandResult struct {
    // Embedded API response with RequestID and common methods
    models.ApiResponse
    // Output contains the command execution output
    Output    string
}
```

**Note:** `CommandResult` embeds `models.ApiResponse` which provides the `RequestID` field and common API response methods.

**Usage Examples:**

```go
package main

import (
    "fmt"
    agentbay "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
    // Initialize AgentBay and create session
    ab, err := agentbay.NewAgentBay("your-api-key", nil)
    if err != nil {
        panic(err)
    }
    // Use code_latest image which supports command execution
    sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
    sessionResult, err := ab.Create(sessionParams)
    if err != nil {
        panic(err)
    }
    session := sessionResult.Session

    // Execute a command with default timeout (1000ms)
    result, err := session.Command.ExecuteCommand("ls -la")
    if err != nil {
        fmt.Printf("Error executing command: %v\n", err)
        return
    }
    fmt.Printf("Command output:\n%s\n", result.Output)
    // Expected output: Directory listing showing files and folders
    // Sample output: "总计 100\ndrwxr-x--- 16 wuying wuying 4096..."
    fmt.Printf("Request ID: %s\n", result.RequestID)
    // Expected: A valid UUID-format request ID

    // Execute a command with custom timeout (5000ms)
    resultWithTimeout, err := session.Command.ExecuteCommand("sleep 2 && echo 'Done'", 5000)
    if err != nil {
        fmt.Printf("Error executing command: %v\n", err)
        return
    }
    fmt.Printf("Command output: %s\n", resultWithTimeout.Output)
    // Expected output: "Done\n"
    // The command waits 2 seconds then outputs "Done"
    fmt.Printf("Request ID: %s\n", resultWithTimeout.RequestID)
    // Expected: A valid UUID-format request ID
    
    // Note: If a command exceeds its timeout, it will return an error
    // Example: session.Command.ExecuteCommand("sleep 3", 1000)
    // Returns error: "command execution failed: Execution failed. Error code:-1 Error message: [timeout]"
}
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the Command class.
- [Code Class](code.md): For executing Python and JavaScript code.
- [FileSystem Class](filesystem.md): Provides methods for file operations within a session.