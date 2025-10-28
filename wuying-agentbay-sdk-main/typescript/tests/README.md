# AgentBay SDK Tests (TypeScript)

This directory contains tests for the TypeScript implementation of the AgentBay SDK. The tests are organized by component to make them easier to maintain and run.

## Test Structure

The tests are organized as follows:

```
typescript/tests/
├── unit/
│   ├── agent-bay.test.ts      # Tests for AgentBay client core functionality
│   ├── session.test.ts        # Tests for Session functionality
│   ├── command.test.ts        # Tests for Command functionality
│   ├── filesystem.test.ts     # Tests for FileSystem functionality
│   ├── adb.test.ts            # Tests for Adb functionality
│   ├── context.test.ts        # Tests for Context functionality
│   ├── application.test.ts    # Tests for Application functionality
│   └── window.test.ts         # Tests for Window functionality
├── integration/
│   └── context-persistence.test.ts  # Integration tests for context persistence
└── utils/
    └── test-helpers.ts        # Common test utilities and helper functions
```

## Running Tests

### Running All Tests

To run all tests, use the following command from the root of the project:

```bash
cd typescript
npm test
```

### Running Tests for a Specific Component

To run tests for a specific component, use the following command:

```bash
cd typescript
npx jest tests/unit/agent-bay.test.ts  # Run AgentBay client tests
npx jest tests/unit/session.test.ts    # Run Session tests
npx jest tests/unit/command.test.ts    # Run Command tests
# ... and so on
```

### Running Integration Tests

To run integration tests, use the following command:

```bash
cd typescript
npx jest tests/integration
```

### Running Tests with Coverage

To run tests with coverage reporting:

```bash
cd typescript
npm run test:coverage
```

## Test Environment

The tests require an API key to connect to the AgentBay service. You can set the API key using the `AGENTBAY_API_KEY` environment variable:

```bash
export AGENTBAY_API_KEY="your-api-key"
```

If the API key is not set, the tests will use a default value of "akm-xxx", which may not work in a production environment.

## Test Components

### Unit Tests

#### AgentBay Client Tests

Tests the core functionality of the AgentBay client, including:
- Initialization with API key
- Creating, listing, and deleting sessions
- Listing sessions by labels

#### Session Tests

Tests the functionality of the Session object, including:
- Session properties
- Session deletion
- Session information retrieval

#### Command Tests

Tests the Command functionality, including:
- Executing commands
- Error handling for command execution

#### FileSystem Tests

Tests the FileSystem functionality, including:
- Reading files
- Writing files
- Error handling for file operations

#### Adb Tests

Tests the Adb functionality, including:
- Executing ADB shell commands
- Error handling for ADB operations

#### Context Tests

Tests the Context functionality, including:
- Creating, listing, updating, and deleting contexts
- Error handling for context operations

#### Application Tests

Tests the Application functionality, including:
- Getting installed applications
- Listing visible applications

#### Window Tests

Tests the Window functionality, including:
- Listing root windows
- Getting the active window
- Window operations (activate, maximize, minimize, restore, resize)
- Focus mode

### Integration Tests

#### Context Persistence Integration Test

Tests the integration between different components, including:
- Context persistence across sessions
- File isolation between contexts
