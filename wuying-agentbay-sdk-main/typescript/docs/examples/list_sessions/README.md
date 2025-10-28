# List Sessions Example (TypeScript)

This example demonstrates how to use the `list()` API to query and filter sessions in AgentBay.

## Prerequisites

1. **Install dependencies**:
   ```bash
   npm install wuying-agentbay-sdk
   npm install -D typescript ts-node @types/node
   ```

2. **Set API Key**:
   ```bash
   export AGENTBAY_API_KEY='your-api-key-here'
   ```

## Running the Example

```bash
cd /path/to/wuying-agentbay-sdk/typescript/docs/examples/list_sessions
npx ts-node main.ts
```

## Key Features

- List all sessions
- Filter by single or multiple labels
- Pagination support
- Iterate through all pages

## API Usage

```typescript
import { AgentBay } from "wuying-agentbay-sdk";

const agentBay = new AgentBay(apiKey);

// List all sessions
const result = await agentBay.list();

// Filter by labels
const filtered = await agentBay.list({ project: "my-project" });

// With pagination
const page1 = await agentBay.list({ project: "my-project" }, 1, 10);
const page2 = await agentBay.list({ project: "my-project" }, 2, 10);
```

## Related Documentation

- [Session Management Guide](../../../../docs/guides/common-features/basics/session-management.md)
- [AgentBay API Reference](../../api/agentbay.md)

