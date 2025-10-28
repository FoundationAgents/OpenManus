# Application and Window Management Example

This example demonstrates how to use the Application and Window Management features of the AgentBay SDK for Golang.

## Features Demonstrated

- Getting installed applications on a remote session
- Listing visible applications
- Listing root windows
- Getting the active window
- Window manipulation operations (activate, maximize, minimize, restore, resize)
- Focus mode management

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

The example demonstrates a full lifecycle of application and window management:

1. Create a new session with a Linux image
2. Get installed applications
3. List visible applications
4. List root windows
5. Get the active window
6. Perform window operations (activate, maximize, minimize, restore, resize)
7. Enable and disable focus mode
8. Clean up by deleting the session

This example is useful for automation scenarios where you need to manipulate application windows programmatically, such as:

- Creating automated testing workflows
- Building assistive technologies
- Developing screen sharing and remote control applications
- Automating UI interactions

For more details on window management, see the [Window API Reference](../../api-reference/window.md) and [Application API Reference](../../api-reference/application.md).
