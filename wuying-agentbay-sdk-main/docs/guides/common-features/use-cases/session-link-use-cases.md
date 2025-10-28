# Session Link Use Cases

This document provides practical use cases for Session Link Access, showing you how to connect external tools to services running in your AgentBay cloud sessions.

> **⚠️ Important Notice**: The Session Link feature is currently in whitelist-only access. To request access to this feature, please send your application to agentbay_dev@alibabacloud.com. For product feedback or suggestions, please submit through the [Alibaba Cloud ticket system](https://smartservice.console.aliyun.com/service/list).

## 📋 Table of Contents

- [Overview](#overview)
- [Use Case 1: Browser Automation](#use-case-1-browser-automation-)
- [Use Case 2: Access Web Applications](#use-case-2-access-web-applications-)
- [Use Case 3: Connect to Custom Services](#use-case-3-connect-to-custom-services-)
- [Quick Selection Guide](#quick-selection-guide)
- [Complete Code Examples](#complete-code-examples)

---

## Overview

Session Link provides **direct network access URLs** to services in your cloud session. The `get_link()` method enables three main scenarios:

1. ✅ **Control a cloud browser** with Playwright/Puppeteer (browser automation via CDP)
2. ✅ **Access web applications** running in your session (like dev servers on custom ports)
3. ✅ **Connect to custom services** in the cloud (like WebSocket servers, databases)

---

## Use Case 1: Browser Automation 🤖

### Your Need
I want to control a cloud browser with Playwright/Puppeteer for automation tasks.

### Solution
Call `get_link()` **with no parameters**. It returns a browser control address (CDP endpoint).

### Minimal Code

```python
import asyncio
from agentbay import AgentBay, CreateSessionParams
from agentbay.browser.browser import BrowserOption
from playwright.async_api import async_playwright

async def main():
    # 1. Create session (MUST use Browser Use image)
    agent_bay = AgentBay(api_key="your_api_key")
    session = agent_bay.create(
        CreateSessionParams(image_id="browser_latest")  # or other Browser Use images
    ).session

    # 2. Initialize browser and wait for it to be ready
    await session.browser.initialize_async(BrowserOption())
    await asyncio.sleep(10)  # Wait for browser to be fully ready

    # 3. Get browser control address
    link = session.get_link()
    print(f"Browser address: {link.data}")
    # Output: wss://gateway.../websocket_ai/...

    # 4. Connect with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(link.data)
        page = await browser.new_page()
        await page.goto("https://example.com")
        # Now you can control the cloud browser!
        await browser.close()
    
    # 5. Cleanup
    agent_bay.delete(session)

asyncio.run(main())
```

### Key Points
- ✅ MUST use Browser Use image (e.g., `browser_latest` or custom Browser Use images)
- ✅ No parameters needed (or use `protocol_type="wss"`)
- ✅ Returns a WebSocket URL starting with `wss://`

### Who Is This For?
- Browser automation testing
- Web scraping with headless browsers
- RPA automation workflows

---

## Use Case 2: Access Web Applications 🌐

### Your Need
I'm running a web service in the cloud session (like `npm run dev`) and want to access it from my local browser.

### Solution
Call `get_link(protocol_type="https", port=port_number)` to get an HTTPS URL.

### Minimal Code

```python
from agentbay import AgentBay

# 1. Create session (any image works)
agent_bay = AgentBay(api_key="your_api_key")
session = agent_bay.create().session

# 2. Start a web server in the cloud (port 30150)
session.file_system.write_file(
    "/tmp/index.html", 
    "<h1>Hello from Cloud!</h1>"
)
session.command.execute_command(
    "cd /tmp && python3 -m http.server 30150 &"
)

# 3. Get access URL
link = session.get_link(protocol_type="https", port=30150)
print(f"Web app URL: {link.data}")
# Output: https://gateway.../request_ai/.../path/

# 4. Open this URL in your browser to access the cloud web service!
```

### Key Points
- ✅ MUST specify both `protocol_type="https"` and `port`
- ✅ Port number MUST be in **30100-30199** range
- ✅ Returns an HTTPS URL you can open in a browser

### Who Is This For?
- Debugging frontend projects in the cloud (React/Vue dev servers)
- Viewing web apps running in the cloud

---

## Use Case 3: Connect to Custom Services 🔌

### Your Need
I'm running a custom service in the cloud and want to connect to it from my local machine.

### Solution
Call `get_link(port=port_number)` to get a WebSocket URL.

### Minimal Code

```python
from agentbay import AgentBay

# 1. Create session
agent_bay = AgentBay(api_key="your_api_key")
session = agent_bay.create().session

# 2. Start a service in the cloud (port 30180)
session.command.execute_command(
    "python3 -m http.server 30180 &"
)

# 3. Get connection URL
link = session.get_link(port=30180)
print(f"Service URL: {link.data}")
# Output: wss://gateway.../websocket_ai/...

# 4. Connect from your local code
# (Use appropriate client based on your service type)
```

### Key Points
- ✅ Only pass `port`, don't pass `protocol_type`
- ✅ Port number MUST be in **30100-30199** range
- ✅ Returns a WebSocket URL (wss://)

### Who Is This For?
- Connecting to custom WebSocket services
- Accessing database services (via port forwarding)
- Debugging network services

---

## Quick Selection Guide

### Decision Tree

```
Question: What do you want to do?
    ↓
├─ A. Control a browser → [Use Case 1] No parameters
├─ B. Access a web page → [Continue to Question 2]
└─ C. Connect to other services → [Continue to Question 3]

Question 2: This web page is...
├─ Running in the cloud session → [Use Case 2] HTTPS + port
└─ External website → ⚠️  No need for get_link, access directly

Question 3: This service is...
├─ HTTP/HTTPS service → [Use Case 2] HTTPS + port
├─ WebSocket or other → [Use Case 3] Port only
└─ Other protocols → ⚠️  Only HTTPS and WSS are supported
```

### Quick Reference Table

| Your Need | How to Call | protocol_type | port | Image Required |
|-----------|------------|---------------|------|----------------|
| Browser automation (CDP) | `get_link()` | Don't pass | Don't pass | Browser Use image |
| Access web app | `get_link("https", 30150)` | `"https"` | 30100-30199 | Any |
| WebSocket service | `get_link(port=30150)` | Don't pass | 30100-30199 | Any |
| Custom HTTPS service | `get_link("https", 30150)` | `"https"` | 30100-30199 | Any |

### Common Mistakes

| You Write | What Happens | Correct Way |
|-----------|--------------|-------------|
| `get_link("https")` | ❌ Error: "port is not valid" | `get_link("https", 30150)` |
| `get_link(port=8080)` | ❌ Error: "Port must be in 30100-30199" | `get_link(port=30150)` |
| `get_link("http", 30150)` | ❌ Error: "http not supported" | `get_link("https", 30150)` |
| Non-Browser Use image + `get_link()` | ❌ Error: "only BrowserUse image support cdp" | Use Browser Use image (e.g., `browser_latest`) |

---

## Complete Code Examples

These are complete, tested examples you can copy and run directly.

### Example 1: Browser Automation Complete Flow

**Goal**: Control a cloud browser with Playwright and visit a website

```python
import asyncio
import os
from agentbay import AgentBay, CreateSessionParams
from playwright.async_api import async_playwright

async def browser_automation_example():
    """Complete browser automation example"""
    
    # 1. Initialize (get API key from environment variable)
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Error: AGENTBAY_API_KEY environment variable is not set")
        print("Please set it using: export AGENTBAY_API_KEY=your_api_key")
        return
    
    agent_bay = AgentBay(api_key=api_key)
    session = None
    
    try:
        # 2. Create Browser Use session
        print("Creating cloud browser session...")
        session_result = agent_bay.create(
            CreateSessionParams(image_id="browser_latest")
        )
        
        if not session_result.success:
            print(f"❌ Failed: {session_result.error_message}")
            return
        
        session = session_result.session
        print(f"✅ Session created: {session.session_id}")
        
        # 3. Initialize browser
        print("\nInitializing browser...")
        from agentbay.browser.browser import BrowserOption
        init_ok = await session.browser.initialize_async(BrowserOption())
        if not init_ok:
            print("❌ Browser initialization failed")
            return
        print("✅ Browser initialized")
        
        # Wait for browser to be ready
        print("Waiting for browser to be ready...")
        await asyncio.sleep(10)
        
        # 4. Get browser CDP address
        print("\nGetting browser control address...")
        link_result = session.get_link()
        
        if not link_result.success:
            print(f"❌ Failed: {link_result.error_message}")
            return
        
        cdp_url = link_result.data
        print(f"✅ CDP URL: {cdp_url[:60]}...")
        
        # 5. Connect with Playwright and control browser
        print("\nConnecting to browser...")
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print("✅ Connected to browser!")
            
            # Create new page
            page = await browser.new_page()
            
            # Visit Alibaba Cloud website
            print("\nVisiting https://www.aliyun.com ...")
            await page.goto("https://www.aliyun.com")
            title = await page.title()
            print(f"✅ Page title: {title}")
            
            # Close browser
            await browser.close()
            print("✅ Browser closed")
        
        print("\n🎉 SUCCESS: Browser automation completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 6. Cleanup
        if session:
            print("\nCleaning up...")
            agent_bay.delete(session)
            print("✅ Session deleted")

if __name__ == "__main__":
    asyncio.run(browser_automation_example())
```

**Before Running**:
1. Install dependencies: `pip install wuying-agentbay-sdk playwright`
2. Install browser: `playwright install chromium`
3. Set your API key: `export AGENTBAY_API_KEY=your_api_key`

**Expected Output**:
```
Creating cloud browser session...
✅ Session created: session-abc123

Getting browser control address...
✅ CDP URL: wss://gateway.../websocket_ai/...

Connecting to browser...
✅ Connected to browser!

Visiting https://www.aliyun.com ...
✅ Page title: 阿里云-计算，为了无法计算的价值
✅ Browser closed

🎉 SUCCESS: Browser automation completed!

Cleaning up...
✅ Session deleted
```

---

### Example 2: Access Cloud Web Application

**Goal**: Start an HTTP server in the cloud and access it from local browser

```python
import time
import os
from agentbay import AgentBay

def web_app_access_example():
    """Complete web application access example"""
    
    # 1. Initialize (get API key from environment variable)
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Error: AGENTBAY_API_KEY environment variable is not set")
        print("Please set it using: export AGENTBAY_API_KEY=your_api_key")
        return
    
    agent_bay = AgentBay(api_key=api_key)
    session = None
    
    try:
        # 2. Create session (any image works)
        print("Creating session...")
        session = agent_bay.create().session
        print(f"✅ Session ID: {session.session_id}")
        
        # 3. Create a simple HTML file in the cloud
        print("\nCreating HTML file in cloud...")
        session.file_system.write_file(
            "/tmp/index.html",
            "<h1>Hello from AgentBay Cloud!</h1><p>Running on port 30150</p>"
        )
        print("✅ HTML file created")
        
        # 4. Start HTTP server on port 30150
        print("\nStarting HTTP server...")
        port = 30150
        session.command.execute_command(
            f"cd /tmp && nohup python3 -m http.server {port} > /dev/null 2>&1 &"
        )
        time.sleep(3)  # Wait for server to start
        print(f"✅ HTTP server started on port {port}")
        
        # 5. Get access URL
        print("\nGetting access URL...")
        link_result = session.get_link(protocol_type="https", port=port)
        
        if not link_result.success:
            print(f"❌ Failed: {link_result.error_message}")
            return
        
        web_url = link_result.data
        print(f"✅ Web URL: {web_url}")
        
        print("\n" + "=" * 70)
        print("🎉 SUCCESS: Web application is accessible!")
        print("=" * 70)
        print(f"\n👉 Open this URL in your browser:")
        print(f"   {web_url}")
        print(f"\nSession will stay alive for 30 seconds...")
        
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 6. Cleanup
        if session:
            print("\nCleaning up...")
            agent_bay.delete(session)
            print("✅ Session deleted")

if __name__ == "__main__":
    web_app_access_example()
```

**Key Points**:
- Port must be in 30100-30199 range
- Must pass both `protocol_type` and `port`
- Returned URL can be opened directly in browser

---

### Example 3: Custom Port Access

**Goal**: Demonstrate port parameter usage for custom services

```python
import time
import os
from agentbay import AgentBay

def custom_port_example():
    """Custom port access example"""
    
    # 1. Initialize (get API key from environment variable)
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Error: AGENTBAY_API_KEY environment variable is not set")
        print("Please set it using: export AGENTBAY_API_KEY=your_api_key")
        return
    
    agent_bay = AgentBay(api_key=api_key)
    session = None
    
    try:
        # 2. Create session
        print("Creating session...")
        session = agent_bay.create().session
        print(f"✅ Session ID: {session.session_id}")
        
        # 3. Start a service on custom port 30180
        print("\nStarting service on port 30180...")
        port = 30180
        session.command.execute_command(
            f"cd /tmp && nohup python3 -m http.server {port} > /dev/null 2>&1 &"
        )
        time.sleep(3)
        print(f"✅ Service started on port {port}")
        
        # 4. Get link with custom port
        print("\nGetting link with custom port...")
        link_result = session.get_link(port=port)
        
        if not link_result.success:
            print(f"❌ Failed: {link_result.error_message}")
            return
        
        service_url = link_result.data
        print(f"✅ Service URL: {service_url[:80]}...")
        print(f"✅ Protocol: {service_url.split('://')[0]}://")
        
        # Verify protocol
        if service_url.startswith("wss://"):
            print("✅ Confirmed: WebSocket Secure (wss://) URL")
        
        print("\n🎉 SUCCESS: Custom port link obtained!")
        print(f"\nKey findings:")
        print(f"  - Port: {port}")
        print(f"  - Protocol: wss://")
        print(f"  - Port range: 30100-30199")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 5. Cleanup
        if session:
            print("\nCleaning up...")
            agent_bay.delete(session)
            print("✅ Session deleted")

if __name__ == "__main__":
    custom_port_example()
```

**Note**: These examples have been tested and verified with real AgentBay API calls.

---

## Related Resources

- [Session Link Access Guide](../advanced/session-link-access.md) - Complete API documentation and advanced topics
- [Session Management Guide](../basics/session-management.md) - Session lifecycle management
- [Session Information Use Cases](session-info-use-cases.md) - Other session-related use cases

## Getting Help

If you encounter issues:

1. Check the [Session Link Access Guide](../advanced/session-link-access.md) for detailed documentation
2. Search [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
3. Contact support with detailed error information

Remember: Session Link Access is your gateway to cloud session connectivity! 🔗

## 📚 Related Guides

- [Session Link Access](../advanced/session-link-access.md) - Session connectivity and URL generation
- [Session Management](../basics/session-management.md) - Session lifecycle and configuration
- [Browser Use Overview](../../browser-use/README.md) - Browser automation features

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
