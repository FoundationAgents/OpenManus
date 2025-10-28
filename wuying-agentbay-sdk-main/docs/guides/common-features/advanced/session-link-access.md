# Session Link Access

This guide shows you how to use `get_link()` to connect to your AgentBay cloud sessions.

> **⚠️ Important Notice**: The Session Link feature is currently in whitelist-only access. To request access to this feature, please send your application to agentbay_dev@alibabacloud.com. For product feedback or suggestions, please submit through the [Alibaba Cloud ticket system](https://smartservice.console.aliyun.com/service/list).

## 📋 Table of Contents

- [🎯 What is a Session Link?](#-what-is-a-session-link)
- [🚀 Use Cases and Examples](#-use-cases-and-examples)
- [📖 API Reference](#-api-reference)
- [📖 Advanced Topics](#-advanced-topics)

---

## 🎯 What is a Session Link?

### Simple Explanation

When you create an AgentBay session, you're starting a virtual computer in the cloud. If you need to **directly connect** external tools (like Playwright, your local browser, or WebSocket clients) to services running inside the session, you'll need a **Session Link**.

Think of it this way:
- 🏠 **Session** = A house in the cloud running services
- 🔗 **Session Link** = The direct address to access those services
- 💻 **Your local tools** = Need this address to connect to services inside

Session Link provides the **direct network access URL** to services in your cloud session.

### What Can `get_link()` Do?

The `get_link()` method returns a URL that enables **direct connections** to services in your session:

1. ✅ **Control a cloud browser** with Playwright/Puppeteer (browser automation via CDP)
2. ✅ **Access web applications** running in your session (like dev servers on custom ports)
3. ✅ **Connect to custom services** in the cloud (like WebSocket servers, databases)

---

## 🚀 Use Cases and Examples

For practical examples and step-by-step guides, see the **[Session Link Use Cases](../use-cases/session-link-use-cases.md)** document, which covers:

1. **Browser Automation** - Control cloud browsers with Playwright/Puppeteer
2. **Access Web Applications** - Access web services running in cloud sessions
3. **Connect to Custom Services** - Connect to custom ports and services

The use cases document includes:
- Complete working code examples
- Quick selection guide to choose the right approach
- Common mistakes and how to avoid them

---

## 📖 API Reference

### Method Signature

```python
def get_link(
    protocol_type: Optional[str] = None,
    port: Optional[int] = None
) -> Result[str]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protocol_type` | `str` | No | Protocol type: `"https"` or `"wss"`. If not specified, defaults to WSS for browser CDP endpoint |
| `port` | `int` | No | Port number in range [30100, 30199] for custom services |

### Return Value

Returns a `Result[str]` object containing:
- `success`: Boolean indicating if the operation succeeded
- `data`: The session link URL (wss:// or https://)
- `error_message`: Error description if `success` is False
- `request_id`: Unique identifier for the API request


### Usage Patterns

The `get_link()` method supports three main usage patterns:

| Pattern | Call Syntax | Returns | Use Case |
|---------|-------------|---------|----------|
| Browser CDP | `get_link()` | `wss://...` | Browser automation with Playwright/Puppeteer |
| HTTPS Service | `get_link("https", port)` | `https://...` | Access web applications via HTTPS |
| WebSocket Service | `get_link(port=port)` | `wss://...` | Connect to custom WebSocket services |

> **📘 For detailed examples and complete code**, see the [Session Link Use Cases Guide](../use-cases/session-link-use-cases.md).

### Quick Reference

**Browser Automation**:
```python
# MUST initialize browser first!
await session.browser.initialize_async(BrowserOption())
await asyncio.sleep(10)  # Wait for browser startup

link = session.get_link()  # Returns CDP endpoint
```

**Web Application Access**:
```python
link = session.get_link(protocol_type="https", port=30150)
# Returns: https://gateway.../request_ai/.../path/
```

**Custom Service Connection**:
```python
link = session.get_link(port=30180)
# Returns: wss://gateway.../websocket_ai/...
```

### Parameter Constraints

- **Port Range**: Must be in [30100, 30199]
- **Protocol Types**: Only `"https"` and `"wss"` are supported
- **Browser CDP**: Requires Browser Use image (e.g., `browser_latest`)
- **Protocol + Port**: If `protocol_type` is specified, `port` must also be provided

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "port is not valid" | `protocol_type` specified without `port` | Always provide `port` when using `protocol_type` |
| "Port must be in [30100, 30199]" | Port outside valid range | Use a port in the valid range |
| "http not supported" | Using `protocol_type="http"` | Use `"https"` instead |
| "only BrowserUse image support cdp" | Non-browser image with no parameters | Use `browser_latest` image or specify port |

---

## 📖 Advanced Topics

### Asynchronous Operations

For async applications, use `get_link_async()`:

```python
import asyncio
import os
from agentbay import AgentBay

async def get_multiple_links():
    api_key = os.environ.get("AGENTBAY_API_KEY")
    agent_bay = AgentBay(api_key=api_key)
    session = agent_bay.create().session
    
    try:
        # Get multiple links in parallel
        tasks = [
            session.get_link_async(),  # Default WebSocket
            session.get_link_async(protocol_type="https", port=30199),  # HTTPS
            session.get_link_async(port=30150)  # WebSocket with port
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Link {i+1} failed: {result}")
            elif result.success:
                print(f"Link {i+1}: {result.data}")
    finally:
        agent_bay.delete(session)

if __name__ == "__main__":
    asyncio.run(get_multiple_links())
```

### Best Practices

#### 1. Parameter Validation

```python
def safe_get_link(session, protocol_type=None, port=None):
    """Safely get session link with validation"""
    if protocol_type is not None and port is None:
        raise ValueError("protocol_type requires port parameter")
    
    if port is not None and not (30100 <= port <= 30199):
        raise ValueError(f"Port {port} outside valid range [30100, 30199]")
    
    return session.get_link(protocol_type=protocol_type, port=port)
```

#### 2. Error Handling

```python
def robust_get_link(session, protocol_type=None, port=None):
    """Get link with comprehensive error handling"""
    try:
        result = session.get_link(protocol_type=protocol_type, port=port)
        
        if result.success:
            print(f"Link: {result.data}")
            print(f"Request ID: {result.request_id}")
            return result.data
        else:
            print(f"API error: {result.error_message}")
            return None
    
    except Exception as e:
        print(f"Exception: {e}")
        return None
```

#### 3. Link Caching

```python
class SessionLinkManager:
    """Cache links to avoid repeated API calls"""
    
    def __init__(self, session):
        self.session = session
        self.cache = {}
    
    def get_cached_link(self, protocol_type=None, port=None):
        key = f"{protocol_type}:{port}"
        
        if key not in self.cache:
            result = self.session.get_link(
                protocol_type=protocol_type, 
                port=port
            )
            if result.success:
                self.cache[key] = result.data
        
        return self.cache.get(key)
```

### Troubleshooting

#### Link Not Accessible

If the link is generated successfully but you cannot access it:

```python
# Check 1: Verify the service is running on the specified port
result = session.command.execute_command("netstat -tuln | grep 30150")
if result.success:
    print(f"Port status: {result.output}")
else:
    print("Service may not be running on the specified port")

# Check 2: Verify the session is still active
info_result = session.info()
if info_result.success:
    print(f"Session ID: {info_result.data.session_id}")
    print(f"Session status: Active")
else:
    print(f"Session may have been terminated: {info_result.error_message}")
```

#### Connection Timeouts

If connections to the link time out:

```python
# Check 1: Verify network connectivity to the gateway domain
# Extract domain from link for testing
link_result = session.get_link(protocol_type="https", port=30150)
if link_result.success:
    import urllib.parse
    parsed = urllib.parse.urlparse(link_result.data)
    print(f"Gateway domain: {parsed.netloc}")
    # Test connectivity: ping or curl the domain

# Check 2: Confirm the session hasn't been terminated
info_result = session.info()
if not info_result.success:
    print("Session may have been terminated")
    print("Create a new session and try again")

# Check 3: Review VPC and subnet configurations (for VPC sessions)
# If using VPC mode, ensure:
# - Security groups allow traffic on the specified port
# - Network ACLs permit inbound/outbound connections
# - Route tables are correctly configured
```

### Debugging Helper Function

When troubleshooting link issues, use this comprehensive debugging function.

**Note**: This is a helper function example, not a built-in SDK method. Copy the complete function code below into your script to use it.

#### How to Use

1. **Copy the entire function definition** from the code block below
2. **Paste it into your Python script** before calling it
3. **Call the function** with your session object: `debug_session_links(session)`

#### Function Code

```python
def debug_session_links(session):
    """Debug session link generation and accessibility."""
    print(f"Debugging session: {session.session_id}")
    print("=" * 70)
    
    # Step 1: Get session info
    print("\n[Step 1] Checking session status...")
    info_result = session.info()
    if info_result.success:
        info = info_result.data
        print(f"✅ Session ID: {info.session_id}")
        print(f"✅ Resource Type: {info.resource_type}")
        print(f"✅ Resource ID: {info.resource_id}")
        print(f"✅ Resource URL: {info.resource_url[:100]}...")
    else:
        print(f"❌ Failed to get session info: {info_result.error_message}")
        return
    
    # Step 2: Test different link types
    print("\n[Step 2] Testing different link configurations...")
    test_cases = [
        ("Default WebSocket", None, None),
        ("WebSocket with port 30150", None, 30150),
        ("HTTPS on port 30199", "https", 30199),
        ("WebSocket Secure on port 30199", "wss", 30199),
    ]
    
    for name, protocol, port in test_cases:
        try:
            if protocol is None and port is None:
                result = session.get_link()
            elif protocol is None:
                result = session.get_link(port=port)
            else:
                result = session.get_link(protocol_type=protocol, port=port)
            
            if result.success:
                url_preview = result.data[:80] + "..." if len(result.data) > 80 else result.data
                print(f"✅ {name}: {url_preview}")
            else:
                print(f"❌ {name}: {result.error_message}")
        
        except Exception as e:
            print(f"❌ {name}: Exception - {e}")
    
    print("\n" + "=" * 70)
    print("Debugging complete!")
```

#### Usage Example

After copying the function definition above, you can use it like this:

```python
import os
from agentbay import AgentBay

# (Paste the debug_session_links function definition here)

# Now use the function
api_key = os.environ.get("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)
session = agent_bay.create().session

# Call the debugging function
debug_session_links(session)

# Cleanup
agent_bay.delete(session)
```

**Expected Output**:
```
Debugging session: session-abc123
======================================================================

[Step 1] Checking session status...
✅ Session ID: session-abc123
✅ Resource Type: container
✅ Resource ID: res-abc123
✅ Resource URL: wss://gateway.../websocket_ai/...

[Step 2] Testing different link configurations...
❌ Default WebSocket: no port specified, cdp default, but only BrowserUse image support cdp
✅ WebSocket with port 30150: wss://gateway.../websocket_ai/...
✅ HTTPS on port 30199: https://gateway.../request_ai/.../path/
✅ WebSocket Secure on port 30199: wss://gateway.../websocket_ai/...

======================================================================
Debugging complete!
```

### Link Format Details

#### WebSocket Secure (wss://)

```
wss://gw-cn-hangzhou-ai-linux.wuyinggw.com:8008/websocket_ai/{token}
 │    │                                        │     │              │
 │    └─ Gateway domain                        │     └─ Endpoint    └─ Auth token
 │                                             └─ Gateway port
 └─ Protocol (WebSocket Secure)
```

**Use**: Chrome DevTools Protocol (CDP) endpoint for browser automation, or WebSocket services with custom ports

#### HTTPS

```
https://gw-cn-hangzhou-ai-linux.wuyinggw.com:8008/request_ai/{token}/path/
 │     │                                        │     │           │        │
 │     └─ Gateway domain                        │     └─ Endpoint └─ Token └─ Path suffix
 │                                             └─ Gateway port
 └─ Protocol (HTTPS)
```

**Use**: HTTP/HTTPS access to web applications and services running in the session

---

## Related Resources

- [Session Management Guide](../basics/session-management.md)
- [Advanced Features Guide](README.md)

## Getting Help

If you encounter issues:

1. Check this documentation for solutions
2. Search [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
3. Contact support with detailed error information

Remember: Session Link Access is your gateway to cloud session connectivity! 🔗
