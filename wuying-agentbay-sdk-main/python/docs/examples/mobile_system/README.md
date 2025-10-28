# Mobile System Example

This example demonstrates how to use the mobile system features of the AgentBay SDK for Python.

## Features Demonstrated

- Creating a session with a mobile image
- Getting installed applications
- Starting and stopping applications
- Getting clickable UI elements
- Getting all UI elements with hierarchy information
- Sending key events
- Input text
- Swipe screen gestures
- Click screen operations
- Taking screenshots
- Starting applications with specific activities

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

The example demonstrates mobile system operations:

1. Create a new session with a mobile image
2. Get a list of installed applications
3. Start an application using a package name
4. Stop an application
5. Interact with the UI using various methods:
   - Get clickable UI elements
   - Get all UI elements with their hierarchy
   - Send key events (HOME key)
   - Input text
   - Perform swipe gestures
   - Perform click operations
6. Take screenshots
7. Start an application with a specific activity
8. Clean up by deleting the session

Mobile system features are particularly useful for:

- Mobile application testing
- Automated UI testing
- Creating mobile app demos
- Building mobile app automation tools
- Implementing mobile device control applications

For more details on mobile system features, see the [Application API Reference](../../api-reference/application.md) and [UI API Reference](../../api-reference/ui.md).
