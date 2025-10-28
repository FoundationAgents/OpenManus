# Session Creation and Management Example

This example demonstrates comprehensive session creation and management using the Wuying AgentBay SDK. It covers various session types and configurations:

## Features Demonstrated

### 1. Basic Session Management
- Initializing the AgentBay client
- Creating a session with default parameters
- Listing all available sessions
- Creating multiple sessions
- Deleting sessions
- Verifying session deletion

### 2. Session with Labels
- Creating sessions with custom labels for organization
- Using labels for project management and environment tracking
- Retrieving and displaying session labels

### 3. Mobile Configuration Sessions
- **Resolution Control**: Locking screen resolution for consistent testing
  - `LockResolution: true` - Locks display resolution to prevent changes
  - `LockResolution: false` - Allows flexible resolution adjustments
- **Package Management**: Configuring app access control
  - Whitelist configuration - Only specified apps are allowed to run
  - Blacklist configuration - Specified apps are blocked/hidden

## Running the Example

```bash
cd session_creation
go run main.go
```

Make sure you have set the `AGENTBAY_API_KEY` environment variable or replace the placeholder in the code with your actual API key.
