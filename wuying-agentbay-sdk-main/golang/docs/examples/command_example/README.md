# Command Execution Example

This example demonstrates how to use the command execution features of the AgentBay SDK for Golang.

## Features Demonstrated

- Executing shell commands
- Setting custom timeouts for commands
- Running Python code
- Running JavaScript code
- Executing multi-line command sequences

## Running the Example

1. Make sure you have installed the AgentBay SDK:

```bash
go get github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay
```

2. Set your API key as an environment variable (recommended):

```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Run the example:

```bash
go run main.go
```

## Code Explanation

The example demonstrates different ways to execute commands:

1. Basic shell command execution
2. Command execution with custom timeout
3. Running Python code
4. Running JavaScript code with custom timeout
5. Executing a multi-line shell command sequence

The code also demonstrates proper session cleanup using defer.

For more details on command execution, see the [Command API Reference](../../api-reference/command.md) and [Command Execution Tutorial](../../tutorials/command-execution.md). 