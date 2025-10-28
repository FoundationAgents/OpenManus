# Label Management Example

This example demonstrates how to use the label management features of the AgentBay SDK for Python.

## Features Demonstrated

- Creating sessions with custom labels
- Getting labels from a session
- Updating labels for a session
- Listing all sessions
- Filtering sessions by labels
- Retrieving label information from filtered sessions

## Running the Example

1. Make sure you have installed the AgentBay SDK:

```bash
pip install wuying-agentbay-sdk
```

2. Set your API key as an environment variable (recommended):

```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Run the example:

```bash
python main.py
```

## Code Explanation

The example demonstrates a full lifecycle of label management:

1. Create a session with initial labels
2. Retrieve the labels from the session
3. Create another session with different labels
4. Update the labels for the second session
5. Retrieve the updated labels
6. List all sessions
7. Filter sessions by label criteria
8. Clean up by deleting the sessions

Labels are useful for organizing and categorizing sessions, making it easier to find and manage them. You can use labels to:

- Group sessions by project
- Mark sessions with their purpose
- Tag sessions with version information
- Indicate session status
- Filter sessions based on any criteria

For more details on session management, see the [Session API Reference](../../api-reference/session.md) and [Session Management Tutorial](../../tutorials/session-management.md). 