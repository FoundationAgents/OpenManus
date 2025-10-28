# AgentBay SDK Tests

This directory contains tests for the AgentBay SDK. The tests are organized by component to make them easier to maintain and run.

## Test Structure

The tests are organized as follows:

```
golang/tests/
├── pkg/
│   ├── agentbay/
│   │   ├── agentbay_test.go      # Tests for AgentBay client core functionality
│   │   ├── session_test.go       # Tests for Session functionality
│   │   ├── command_test.go       # Tests for Command functionality
│   │   ├── filesystem_test.go    # Tests for FileSystem functionality
│   │   ├── adb_test.go           # Tests for Adb functionality
│   │   ├── context_test.go       # Tests for Context functionality
│   │   ├── application_test.go   # Tests for Application functionality
│   │   └── window_test.go        # Tests for Window functionality
│   └── integration/
│       └── context_persistence_integration_test.go  # Integration tests for context persistence
```

## Running Tests

### Running All Tests

To run all tests, use the following command from the root of the project:

```bash
cd golang
go test ./tests/...
```

### Running Tests for a Specific Component

To run tests for a specific component, use the following command:

```bash
cd golang
go test ./tests/pkg/agentbay/agentbay_test.go  # Run AgentBay client tests
go test ./tests/pkg/agentbay/session_test.go   # Run Session tests
go test ./tests/pkg/agentbay/command_test.go   # Run Command tests
# ... and so on
```

### Running Integration Tests

To run integration tests, use the following command:

```bash
cd golang
go test ./tests/pkg/integration/...
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

#### Command Tests

Tests the Command functionality, including:
- Executing commands

#### FileSystem Tests

Tests the FileSystem functionality, including:
- Reading files

#### Adb Tests

Tests the Adb functionality, including:
- Executing ADB shell commands

#### Context Tests

Tests the Context functionality, including:
- Creating, listing, updating, and deleting contexts

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
