# Call For User

The Call For User feature handles scenarios where browser automation encounters situations that require human intervention. This includes authentication challenges, complex verification processes, or security measures that cannot be automatically resolved by the system.

> **Use Cases:** This feature is triggered when the browser encounters user information requests, authentication challenges, or other scenarios that require manual human interaction to proceed.

## When Call For User is Triggered

The system automatically triggers a "wuying-call-for-user" message when it encounters:

- **Authentication challenges** that cannot be automatically resolved
- **Complex verification processes** that need user input
- **Security measures** that require manual verification
- **User information requests** that need human intervention
- **Situations** where automated solutions are insufficient

## Event Monitoring

Monitor Call For User events through console messages to implement custom handling logic:

```python
def handle_console(msg):
    print(f"🔍 Received console message: {msg.text}")
    # Parse JSON message
    try:
        message_data = json.loads(msg.text)
        message_type = message_data.get('type', '')
    except (json.JSONDecodeError, AttributeError):
        # If not JSON, treat as plain text
        message_type = msg.text

    if message_type == "wuying-call-for-user":
        # Open browser for user interaction
        import webbrowser
        webbrowser.open(info.resource_url)
        # Wait for user to complete interaction
        time.sleep(20)

page.on("console", handle_console)
```

## Handling User Intervention

When a Call For User event is triggered, the recommended flow is:

1. **Parse the console message** to identify the message type
2. **Open the session resource URL** in a browser for user interaction
3. **Allow the user to interact** with the browser to complete the required action
4. **Wait for completion** (typically 20-30 seconds)
5. **Continue with automation** flow

## Configuration

The Call For User feature works automatically with any browser session. No special configuration is required:

```python
params = CreateSessionParams(
    image_id="browser_latest",  # Specify the image ID
)
session_result = agent_bay.create(params)

if session_result.success:
    session = session_result.session
    print(f"Session created with ID: {session.session_id}")

    # Get session info to access resource URL
    result = session.info()
    info = result.data
    print(f"session resource url is {info.resource_url}")

    # Call For User is automatically enabled
    if await session.browser.initialize_async(BrowserOption()):
        print("Browser initialized successfully")
```

## Usage Tips

- **Monitor console events** to detect when user intervention is needed
- **Implement proper waiting** mechanisms (20-30 seconds) for user interaction
- **Handle URL escaping** for special characters in resource URLs
- **Provide clear feedback** to users about what action is required
- **Plan for user interaction time** in your automation workflows


## 📚 Related Guides

- [CAPTCHA Resolution](captcha.md) - Automatic CAPTCHA handling
- [Session Management](../../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Browser Use Overview](../README.md) - Complete browser automation features

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
