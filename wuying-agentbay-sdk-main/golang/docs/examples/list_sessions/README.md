# List Sessions Example (Golang)

This example demonstrates how to use the `List()` API to query and filter sessions in AgentBay.

## Prerequisites

1. **Set API Key**:
   ```bash
   export AGENTBAY_API_KEY='your-api-key-here'
   ```

2. **Install SDK** (if not already done):
   ```bash
   go get github.com/aliyun/wuying-agentbay-sdk/golang
   ```

## Running the Example

```bash
cd /path/to/wuying-agentbay-sdk/golang/docs/examples/list_sessions
go run main.go
```

## Key Features

- List all sessions
- Filter by single or multiple labels
- Pagination support
- Iterate through all pages

## API Usage

```go
import "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"

client, _ := agentbay.NewAgentBay(apiKey, nil)

// List all sessions
result, err := client.List(nil, nil, nil)

// Filter by labels
result, err = client.List(map[string]string{"project": "my-project"}, nil, nil)

// With pagination
page := 1
limit := int32(10)
result, err = client.List(
    map[string]string{"project": "my-project"},
    &page,
    &limit,
)
```

## Related Documentation

- [Session Management Guide](../../../../docs/guides/common-features/basics/session-management.md)
- [AgentBay API Reference](../../api/agentbay.md)

