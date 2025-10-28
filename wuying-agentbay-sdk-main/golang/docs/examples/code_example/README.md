# Code Execution Example

This example demonstrates how to use the new **Code** module in the AgentBay SDK after the refactoring.

## What's New

In this refactored version:

- `RunCode` method has been moved from the `Command` module to a dedicated `Code` module
- Access code execution functionality via `session.Code.RunCode()` instead of `session.Command.RunCode()`
- The `Command` module now focuses only on shell command execution

## Features Demonstrated

1. **Python Code Execution**: Execute Python code in the cloud environment
2. **JavaScript Code Execution**: Execute JavaScript/Node.js code 
3. **Shell Command Execution**: Traditional command execution still works via `Command` module

## Usage

```go
// Create a session
session := /* ... create session ... */

// Execute Python code using the new Code module
codeResult, err := session.Code.RunCode(pythonCode, "python", 30)
if err != nil {
    log.Printf("Failed to run code: %v", err)
} else {
    fmt.Printf("Output: %s\n", codeResult.Output)
}

// Execute shell commands using the Command module
cmdResult, err := session.Command.ExecuteCommand("echo 'Hello!'", 5000)
```

## Running the Example

```bash
cd docs/examples/golang/code_example
go run main.go
```

Make sure you have set the `AGENTBAY_API_KEY` environment variable before running the example. 