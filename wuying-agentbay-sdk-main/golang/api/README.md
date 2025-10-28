# AgentBay API Client for Go

This directory contains the Go client for the AgentBay API, which provides access to the Model Context Protocol (MCP) functionality.

## Structure

- `client/`: Contains the API client implementation and model definitions
  - Client implementation for making API calls
  - Request and response models for all API operations

## Usage

To use the API client in your Go code:

```go
package main

import (
	"fmt"
	
	openapiutil "github.com/alibabacloud-go/darabonba-openapi/v2/utils"
	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
)

func main() {
	// Create a new client
	config := &openapiutil.Config{
		// Configure your endpoint
		Endpoint: "your-endpoint.example.com",
	}
	
	apiClient, err := client.NewClient(config)
	if err != nil {
		panic(err)
	}
	
	// Example: Create an MCP session
	request := &client.CreateMcpSessionRequest{
		// Set your request parameters
	}
	
	response, err := apiClient.CreateMcpSession(request)
	if err != nil {
		panic(err)
	}
	
	// Process the response
	fmt.Println("Session created successfully")
}
```

## Available Operations

The client provides the following operations:

- `CreateMcpSession`: Create a new MCP session
- `ReleaseMcpSession`: Release an MCP session
- `CallMcpTool`: Call an MCP tool
- `GetMcpResource`: Get an MCP resource
- `ListMcpTools`: List available MCP tools

For more details, refer to the method documentation in the client code.
