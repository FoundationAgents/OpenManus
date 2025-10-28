# Models Package

This package contains shared data models used across the AgentBay SDK.

## Key Components

- `ApiResponse`: Base structure that includes a RequestID field, which is embedded in all API responses.

## Usage

This package is designed to be imported by other packages within the SDK to avoid import cycles 
while maintaining code reuse. It should contain only data structures and related methods, 
without dependencies on other packages in the SDK.

```go
import "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"

type MyResult struct {
    models.ApiResponse  // Embed the ApiResponse
    Data string         // Add custom fields
}
```

## Design Rationale

The models package helps to avoid import cycles by providing a central location for shared data structures
that can be imported by any other package without creating circular dependencies. 