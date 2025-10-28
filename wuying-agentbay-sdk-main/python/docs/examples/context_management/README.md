# Context Management Example

This example demonstrates how to use the Context Management features of the AgentBay SDK for Python.

## Features Demonstrated

- Listing all contexts
- Getting or creating a context
- Creating a session with a context
- Updating a context
- Deleting a context

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

The example demonstrates a full lifecycle of context management:

1. Initialize the AgentBay client with an API key
2. List all existing contexts to see what's available
3. Get an existing context by name, or create it if it doesn't exist
4. Create a session using the context
5. Update the context's properties
6. Clean up by deleting the session and context

For more details on context management, see the [Context API Reference](../../api-reference/context.md) and [Data Persistence Tutorial](../../tutorials/data-persistence.md). 