# Session Creation and Management Example

This example demonstrates comprehensive session creation and management using the Wuying AgentBay SDK. It covers various session types and configurations:

## Features Demonstrated

### 1. Basic Session Management
- Initializing the AgentBay client
- Creating a session with default parameters
- Listing all available sessions
- Deleting sessions
- Verifying session deletion

### 2. Session with Labels
- Creating sessions with custom labels for organization
- Retrieving and displaying session labels
- Using labels for project management and environment tracking

### 3. Context-Enabled Sessions
- Creating sessions with predefined contexts
- Context synchronization during session creation
- Managing persistent data across sessions

### 4. Context Synchronization
- Advanced context management with multiple contexts
- Listing and managing synchronized contexts
- Understanding context states and availability

### 5. Browser Context Sessions
- Creating sessions with browser-specific contexts
- Persistent browser data (cookies, localStorage, etc.)
- Context synchronization on session deletion

### 6. Mobile Configuration Sessions 
- Creating mobile sessions with app management rules
- Resolution Control: Locking screen resolution for consistent testing
- Package Management: Configuring allowed app packages
- Mobile-specific session parameters and cleanup


This example is useful for understanding the complete session lifecycle, advanced configuration options, and mobile-specific session management.

## Running the Example

```bash
cd session_creation
python main.py
```

Make sure you have set the `AGENTBAY_API_KEY` environment variable or replace the placeholder in the code with your actual API key.
