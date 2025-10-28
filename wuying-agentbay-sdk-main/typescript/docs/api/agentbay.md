# AgentBay Class API Reference

The `AgentBay` class is the main entry point for interacting with the AgentBay cloud environment. It provides methods for creating, retrieving, listing, and deleting sessions.

## 📖 Related Tutorials

- [SDK Configuration Guide](../../../docs/guides/common-features/configuration/sdk-configuration.md) - Detailed tutorial on configuring the SDK
- [VPC Sessions Guide](../../../docs/guides/common-features/advanced/vpc-sessions.md) - Tutorial on creating sessions in VPC environments
- [Session Link Access Guide](../../../docs/guides/common-features/advanced/session-link-access.md) - Tutorial on accessing sessions via links

## Constructor

### new AgentBay()

```typescript
constructor(options: { apiKey?: string; config?: Config } = {})
```

**Parameters:**
- `options` (object): Configuration options object
  - `apiKey` (string, optional): The API key for authentication. If not provided, the SDK will look for the `AGENTBAY_API_KEY` environment variable.
  - `config` (Config, optional): Custom configuration object containing endpoint and timeout_ms. If not provided, default configuration is used.

**Throws:**
- `Error`: If no API key is provided and `AGENTBAY_API_KEY` environment variable is not set.

## Properties

### context

A `ContextService` instance for managing persistent contexts. See the [Context API Reference](context.md) for more details.

## Methods


Creates a new session in the AgentBay cloud environment.


```typescript
create(params?: CreateSessionParams): Promise<SessionResult>
```

**Parameters:**
- `params` (CreateSessionParams, optional): Parameters for session creation.

**Returns:**
- `Promise<SessionResult>`: A promise that resolves to a result object containing the new Session instance, success status, request ID, and error message if any.

**Behavior:**
- When `params` includes valid `PersistenceDataList`, after creating the session, the API will check `session.context.info` to retrieve ContextStatusData.
- It will continuously monitor all data items' Status in ContextStatusData until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The Create operation only returns after context status checking completes.

**Throws:**
- `Error`: If the session creation fails.

**Example:**
```typescript
import { AgentBay, CreateSessionParams } from 'wuying-agentbay-sdk';
import { ContextSync, SyncPolicy } from 'wuying-agentbay-sdk/context-sync';

// Initialize the SDK with default configuration
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Or initialize with custom configuration
const agentBayWithConfig = new AgentBay({
  apiKey: 'your_api_key',
  config: {
    endpoint: 'https://agentbay.example.com',
    timeout_ms: 30000
  }
});

// Create a session with default parameters
async function createDefaultSession() {
  const result = await agentBay.create();
  if (result.success) {
    console.log(`Created session with ID: ${result.session.sessionId}`);
    return result.session;
  }
  throw new Error(`Failed to create session: ${result.errorMessage}`);
}

// Create a session with custom parameters
async function createCustomSession() {
  const params: CreateSessionParams = {
    imageId: 'linux_latest',
    labels: { project: 'demo', environment: 'testing' }
  };
  
  const result = await agentBay.create(params);
  if (result.success) {
    console.log(`Created custom session with ID: ${result.session.sessionId}`);
    return result.session;
  }
  throw new Error(`Failed to create session: ${result.errorMessage}`);
}

// RECOMMENDED: Create a session with context synchronization
async function createSessionWithSync() {
  const contextSync = new ContextSync({
    contextId: 'your_context_id',
    path: '/mnt/persistent',
    policy: SyncPolicy.default()
  });
  
  const params: CreateSessionParams = {
    imageId: 'linux_latest',
    contextSync: [contextSync]
  };
  
  const result = await agentBay.create(params);
  if (result.success) {
    console.log(`Created session with context sync: ${result.session.sessionId}`);
    return result.session;
  }
  throw new Error(`Failed to create session: ${result.errorMessage}`);
}
```

### get

Retrieves a session by its ID.

```typescript
get(sessionId: string): Promise<SessionResult>
```

**Parameters:**
- `sessionId` (string): The ID of the session to retrieve.

**Returns:**
- `Promise<SessionResult>`: A promise that resolves to a result object containing the Session instance, request ID, success status, and error message if any.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function getSessionExample() {
  const agentBay = new AgentBay({ apiKey: 'your_api_key' });

  const createResult = await agentBay.create();
  if (!createResult.success) {
    console.error(`Failed to create session: ${createResult.errorMessage}`);
    return;
  }

  const sessionId = createResult.session.sessionId;
  console.log(`Created session with ID: ${sessionId}`);
  // Output: Created session with ID: session-xxxxxxxxxxxxxx

  const result = await agentBay.get(sessionId);
  if (result.success) {
    console.log(`Successfully retrieved session: ${result.session.sessionId}`);
    // Output: Successfully retrieved session: session-xxxxxxxxxxxxxx
    console.log(`Request ID: ${result.requestId}`);
    // Output: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    
    const deleteResult = await result.session.delete();
    if (deleteResult.success) {
      console.log(`Session ${sessionId} deleted successfully`);
      // Output: Session session-xxxxxxxxxxxxxx deleted successfully
    }
  } else {
    console.error(`Failed to get session: ${result.errorMessage}`);
  }
}

getSessionExample();
```


```typescript
listByLabels(params?: ListSessionParams): Promise<SessionListResult>
```

**Parameters:**
- `params` (ListSessionParams, optional): Parameters including labels and pagination options. If not provided, defaults will be used (labels `{}`, maxResults `10`).

**Returns:**
- `Promise<SessionListResult>`: A promise that resolves to a result object containing the filtered sessions, pagination information, and request ID.

**Throws:**
- `Error`: If the session listing fails.

**Example:**
```typescript
import { AgentBay, ListSessionParams } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// List sessions by labels with pagination
async function listSessionsByLabels() {
  // Create pagination parameters
  const params: ListSessionParams = {
    maxResults: 10,  // Maximum results per page
    nextToken: '',   // Token for the next page, empty for the first page
    labels: { environment: 'production', project: 'demo' }  // Filter labels
  };
  
  // Get the first page of results
  const result = await agentBay.listByLabels(params);
  
  // Process the results
  if (result.success) {
    // Print the current page sessions
    console.log(`Found ${result.data.length} sessions:`);
    result.data.forEach(session => {
      console.log(`Session ID: ${session.sessionId}`);
    });
    
    // Print pagination information
    console.log(`Total count: ${result.totalCount}`);
    console.log(`Max results per page: ${result.maxResults}`);
    console.log(`Next token: ${result.nextToken}`);
    
    // If there is a next page, retrieve it
    if (result.nextToken) {
      const nextParams = {
        ...params,
        nextToken: result.nextToken
      };
      const nextPageResult = await agentBay.listByLabels(nextParams);
      // Process the next page...
    }
  }
}

listSessionsByLabels();
```

### list

Returns paginated list of Sessions filtered by labels.

```typescript
list(labels?: Record<string, string>, page?: number, limit?: number): Promise<SessionListResult>
```

**Parameters:**
- `labels` (Record<string, string>, optional): Labels to filter Sessions. Defaults to empty object (returns all sessions).
- `page` (number, optional): Page number for pagination (starting from 1). Defaults to undefined (returns first page).
- `limit` (number, optional): Maximum number of items per page. Defaults to 10.

**Returns:**
- `Promise<SessionListResult>`: A promise that resolves to a paginated list of session IDs that match the labels, including requestId, success status, and pagination information.

**Key Features:**
- **Simple Interface**: Pass labels directly as an object parameter
- **Pagination Support**: Use `page` and `limit` parameters for easy pagination
- **Request ID**: All responses include a `requestId` for tracking and debugging
- **Flexible Filtering**: Filter by any combination of labels or list all sessions

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

const agentBay = new AgentBay('your_api_key');

async function listSessions() {
  // List all sessions
  let result = await agentBay.list();

  // List sessions with specific labels
  result = await agentBay.list({ project: 'demo' });

  // List sessions with pagination (page 2, 10 items per page)
  result = await agentBay.list({ 'my-label': 'my-value' }, 2, 10);

  if (result.success) {
    for (const sessionId of result.sessionIds) {
      console.log(`Session ID: ${sessionId}`);
    }
    console.log(`Total count: ${result.totalCount}`);
    console.log(`Request ID: ${result.requestId}`);
  } else {
    console.error(`Error: ${result.errorMessage}`);
  }
}

listSessions();
```

### delete

```typescript
delete(session: Session, syncContext?: boolean): Promise<DeleteResult>
```

**Parameters:**
- `session` (Session): The session to delete.
- `syncContext` (boolean, optional): If true, the API will trigger a file upload via `session.context.sync` before actually releasing the session. Default is false.

**Returns:**
- `Promise<DeleteResult>`: A promise that resolves to a result object containing success status, request ID, and error message if any.

**Behavior:**
- When `syncContext` is true, the API will first call `session.context.sync` to trigger file upload.
- It will then check `session.context.info` to retrieve ContextStatusData and monitor all data items' Status.
- The API waits until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The session deletion only proceeds after context sync status checking completes.

**Throws:**
- `Error`: If the session deletion fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Create and delete a session
async function createAndDeleteSession() {
  try {
    // Create a session
    const createResult = await agentBay.create();
    if (createResult.success) {
      const session = createResult.session;
      console.log(`Created session with ID: ${session.sessionId}`);
      
      // Use the session for operations...
      
      // Delete the session when done
      const deleteResult = await agentBay.delete(session);
      if (deleteResult.success) {
        console.log('Session deleted successfully');
      } else {
        console.log(`Failed to delete session: ${deleteResult.errorMessage}`);
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

createAndDeleteSession();
```
