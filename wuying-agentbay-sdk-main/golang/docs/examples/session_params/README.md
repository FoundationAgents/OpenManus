# Session Parameters Example

This example demonstrates how to use the session parameters features of the AgentBay SDK for Golang.

## Features Demonstrated

- Creating session parameters with custom labels
- Creating a session with custom labels
- Listing sessions by label filtering
- Implementing pagination with NextToken
- Cleaning up sessions

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

The example demonstrates session parameter usage:

1. Create session parameters with custom labels
2. Create a session using these parameters
3. List sessions filtered by a specific label
4. Demonstrate pagination by fetching the next page of results if available
5. Clean up by deleting the session

Session parameters allow you to customize how sessions are created and make it easier to find and manage them later. Custom labels are particularly useful for:

- Organizing sessions by project
- Tracking session owners
- Filtering sessions by purpose or state
- Implementing session management in multi-user environments

For more details on session parameters, see the [Session API Reference](../../api-reference/session.md) and [Session Management Tutorial](../../tutorials/session-management.md).
