# UI Interaction Example

This example demonstrates how to use the UI interaction features of the AgentBay SDK for TypeScript.

## Features Demonstrated

- Creating a session with a mobile image
- Taking screenshots
- Getting all UI elements
- Getting clickable UI elements
- Sending key events
- Inputting text
- Clicking on screen positions
- Performing swipe gestures
- Saving screenshots to local files

## Running the Example

1. Make sure you have installed the AgentBay SDK:

```bash
npm install wuying-agentbay-sdk
```

2. Set your API key as an environment variable (recommended):

```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Compile and run the example:

```bash
# Compile TypeScript
cd ui-example
npx ts-node ui-example.ts
```

## Code Explanation

The example demonstrates UI interactions in a remote session:

1. Create a new session with a mobile image
2. Take screenshots of the remote environment
3. Get all UI elements from the screen
4. Find clickable UI elements
5. Send key events to the environment
6. Input text
7. Perform mouse click operations
8. Simulate touch and swipe gestures
9. Take a second screenshot after interactions
10. Clean up by deleting the session

The example also includes a helper function to parse bounds strings from UI elements, which helps determine element positions for interactions.

UI interaction capabilities are particularly useful for:

- Automated testing of mobile applications
- Building mobile app automation tools
- Creating mobile app demos
- Implementing mobile device control applications
- Developing UI testing frameworks

For more details on UI interaction, see the [UI API Reference](../../api-reference/ui.md).
