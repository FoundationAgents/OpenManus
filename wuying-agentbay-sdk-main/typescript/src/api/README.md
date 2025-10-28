# AgentBay API Client for TypeScript

This directory contains the TypeScript client for the AgentBay API, which provides access to the Model Context Protocol (MCP) functionality.

## Structure

- `client.ts`: The main API client implementation
- `models/`: Contains TypeScript model definitions for all API requests and responses
- `index.ts`: Exports the client and models for easy importing

## Usage

To use the API client in your TypeScript code:

```typescript
import { Client as ApiClient } from 'agentbay-sdk/api';
// Or import from the root
import { Client as ApiClient } from 'agentbay-sdk';

// Create a new client
const config = {
  // Configure your endpoint
  endpoint: 'your-endpoint.example.com',
};

const apiClient = new ApiClient(config);

// Example: Create an MCP session
const request = {
  // Set your request parameters
};

async function createSession() {
  try {
    const response = await apiClient.createMcpSession(request);
    log('Session created successfully');
    return response;
  } catch (error) {
    logError('Failed to create session:', error);
    throw error;
  }
}
```

## Available Operations

The client provides the following operations:

- `createMcpSession`: Create a new MCP session
- `releaseMcpSession`: Release an MCP session
- `callMcpTool`: Call an MCP tool
- `getMcpResource`: Get an MCP resource
- `listMcpTools`: List available MCP tools
- `applyMqttToken`: Get an STS token
- `handleAIEngineMessage`: Handle messages from AI Engine

For more details, refer to the method documentation in the client code.
