# Context Synchronization Example

This example demonstrates how to use the Context Synchronization features of the AgentBay SDK for Golang.

## Features Demonstrated

- Creating and retrieving contexts
- Creating basic context sync configurations
- Creating advanced context sync configurations with policies
- Working with upload, download, and delete policies
- Using whitelist and blacklist configurations
- Creating sessions with multiple context synchronizations
- Managing context synchronization from a session
- Using the builder pattern for sync configurations

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

The example demonstrates a full lifecycle of context synchronization:

1. Create a new persistent context
2. Create basic and advanced context sync configurations
3. Configure upload, download, and delete policies
4. Set up whitelist and blacklist rules
5. Add multiple context sync configurations to a session
6. Create a session with context synchronizations
7. Interact with the context manager from a session
8. Use the builder pattern for creating context sync configurations
9. Clean up resources (session and context)

For more details on context synchronization, see the [Context API Reference](../../api-reference/context.md) and [Data Persistence Tutorial](../../tutorials/data-persistence.md). 