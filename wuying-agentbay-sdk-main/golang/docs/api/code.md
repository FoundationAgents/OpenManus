# Code Module - Go

The Code module handles code execution operations in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Code Execution Guide](../../../docs/guides/codespace/code-execution.md) - Detailed tutorial on executing code in cloud environments

## Methods

### RunCode

Executes code in a specified programming language with a timeout.

```go
RunCode(code string, language string, timeoutS ...int) (*CodeResult, error)
```

**Parameters:**
- `code` (string): The code to execute.
- `language` (string): The programming language of the code. Must be either 'python' or 'javascript'.
- `timeoutS` (int, optional): The timeout for the code execution in seconds. Default is 60s. Note: Due to gateway limitations, each request cannot exceed 60 seconds.

**Returns:**
- `*CodeResult`: A result object containing the execution output and request ID.
- `error`: An error object if the operation fails.

**Important Note:**
The `RunCode` method requires a session created with the `code_latest` image to function properly. If you encounter errors indicating that the tool is not found, make sure to create your session with `ImageId: "code_latest"` in the `CreateSessionParams`.

**Usage Example:**

```go
package main

import (
    "fmt"
    "os"
    
    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
    // Initialize AgentBay with API key
    client, err := agentbay.NewAgentBay("your_api_key", nil)
    if err != nil {
        fmt.Printf("Error initializing AgentBay client: %v\n", err)
        os.Exit(1)
    }

    // Create a session with code_latest image
    params := &agentbay.CreateSessionParams{
        ImageId: "code_latest",
    }
    sessionResult, err := client.Create(params)
    if err != nil {
        fmt.Printf("Error creating session: %v\n", err)
        os.Exit(1)
    }
    session := sessionResult.Session

    // Execute Python code
    pythonCode := `
print("Hello from Python!")
result = 2 + 3
print(f"Result: {result}")
`
    codeResult, err := session.Code.RunCode(pythonCode, "python")
    if err != nil {
        fmt.Printf("Error executing Python code: %v\n", err)
    } else {
        fmt.Printf("Python code output:\n%s\n", codeResult.Output)
        // Expected output:
        // Hello from Python!
        // Result: 5
        fmt.Printf("Request ID: %s\n", codeResult.RequestID)
        // Expected: A valid UUID-format request ID
    }

    // Execute JavaScript code with custom timeout
    jsCode := `
console.log("Hello from JavaScript!");
const result = 2 + 3;
console.log("Result:", result);
`
    jsResult, err := session.Code.RunCode(jsCode, "javascript", 30)
    if err != nil {
        fmt.Printf("Error executing JavaScript code: %v\n", err)
    } else {
        fmt.Printf("JavaScript code output:\n%s\n", jsResult.Output)
        // Expected output:
        // Hello from JavaScript!
        // Result: 5
        fmt.Printf("Request ID: %s\n", jsResult.RequestID)
        // Expected: A valid UUID-format request ID
    }
}
```

## Error Handling

The RunCode method returns an error if:
- The specified language is not supported (only 'python' and 'javascript' are supported)
- The code execution fails in the cloud environment
- Network or API communication errors occur

## Types

### CodeResult

```go
type CodeResult struct {
    ApiResponse  // Embedded ApiResponse containing RequestID
    Output string // The execution output
}
``` 