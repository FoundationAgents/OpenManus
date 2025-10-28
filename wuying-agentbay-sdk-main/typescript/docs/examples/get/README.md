# Get API Example

This example demonstrates how to use the `get` API to retrieve a session by its ID.

## Description

The `get` API allows you to retrieve a session object by providing its session ID. This is useful when you have a session ID from a previous operation and want to access or manage that session.

## Prerequisites

- Node.js 16 or higher
- TypeScript 4.5 or higher
- Valid API key set in `AGENTBAY_API_KEY` environment variable
- wuying-agentbay-sdk package installed

## Installation

```bash
npm install wuying-agentbay-sdk
# or
yarn add wuying-agentbay-sdk
```

## Usage

```bash
# Set your API key
export AGENTBAY_API_KEY="your-api-key-here"

# Compile and run the example
npx ts-node main.ts
```

## Code Example

```typescript
import { AgentBay } from "wuying-agentbay-sdk";

async function main() {
  // Initialize AgentBay client
  const apiKey = process.env.AGENTBAY_API_KEY;
  const agentBay = new AgentBay({ apiKey });

  // Retrieve a session by ID
  const sessionId = "your-session-id";
  const result = await agentBay.get(sessionId);

  if (result.success && result.session) {
    console.log(`Retrieved session: ${result.session.sessionId}`);
    console.log(`Request ID: ${result.requestId}`);
    // Use the session for further operations
    // ...
  } else {
    console.error(`Failed to get session: ${result.errorMessage}`);
  }
}

main();
```

## API Reference

### get

```typescript
async get(sessionId: string): Promise<SessionResult>
```

Get a session by its ID.

**Parameters:**
- `sessionId` (string): The ID of the session to retrieve

**Returns:**
- `Promise<SessionResult>`: Promise resolving to result object containing:
  - `success` (boolean): Whether the operation succeeded
  - `session` (Session): The Session instance if successful
  - `requestId` (string): The API request ID
  - `errorMessage` (string): Error message if failed

## Expected Output

```
Creating a session...
Created session with ID: session-xxxxxxxxxxxxx

Retrieving session using Get API...
Successfully retrieved session:
  Session ID: session-xxxxxxxxxxxxx
  Request ID: DAD825FE-2CD8-19C8-BB30-CC3BA26B9398

Session is ready for use

Cleaning up...
Session session-xxxxxxxxxxxxx deleted successfully
```

## Notes

- The session ID must be valid and from an existing session
- The get API internally calls the GetSession API endpoint
- The returned session object can be used for all session operations (commands, files, etc.)
- Always clean up sessions when done to avoid resource waste

## Error Handling

The `get` method returns a `SessionResult` object with error information:

1. **Empty session_id**: Result will have `success: false`
   ```typescript
   const result = await agentBay.get("");
   if (!result.success) {
     console.error(`Error: ${result.errorMessage}`);  // "session_id is required"
   }
   ```

2. **Non-existent session**: Result will have `success: false`
   ```typescript
   const result = await agentBay.get("non-existent-session-id");
   if (!result.success) {
     console.error(`Error: ${result.errorMessage}`);  // "Failed to get session..."
   }
   ```

## TypeScript Support

This example is fully typed with TypeScript. The `get` method returns a typed `SessionResult` object with full IDE autocomplete support.

```typescript
import { AgentBay, Session } from "wuying-agentbay-sdk";

const agentBay = new AgentBay({ apiKey: "your-key" });
const session: Session = await agentBay.get("session-id");
// TypeScript knows all methods and properties of session
```

