# UI Interaction Example

This example demonstrates how to use the UI interaction features of the AgentBay SDK for Golang.

## Features Demonstrated

- Taking screenshots
- Getting UI elements
- Sending key events
- Performing mouse operations
- Simulating touch operations
- Handling UI element selection

## Running the Example

1. Make sure you have installed the AgentBay SDK:

```bash
go get github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay
```

2. Set your API key as an environment variable (recommended):

```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Run the example:

```bash
go run main.go
```

## Code Explanation

The example demonstrates UI interactions in a remote session:

1. Create a new session with appropriate image
2. Take screenshots of the remote environment
3. Get all UI elements from the screen
4. Find clickable UI elements
5. Send key events to the environment
6. Perform mouse click operations
7. Simulate touch and swipe gestures
8. Clean up by deleting the session

UI interaction capabilities are particularly useful for:

- Automated testing of applications
- Building RPA (Robotic Process Automation) solutions
- Creating assistive technologies
- Implementing remote control applications
- Developing UI testing frameworks

For more details on UI interaction, see the [UI API Reference](../../api-reference/ui.md). 