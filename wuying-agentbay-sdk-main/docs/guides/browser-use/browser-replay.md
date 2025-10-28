# Browser Replay Guide

This guide covers how to use AgentBay's built-in browser replay feature to capture browser interactions and replay them for debugging, documentation, or compliance purposes.

## Overview

AgentBay provides automatic browser replay capabilities for browser sessions, powered by the **rrweb** (record and replay the web) framework. This allows you to:

- 🎥 **Record all browser interactions** automatically with high fidelity
- 📊 **Monitor user interactions** for compliance and training
- 🐛 **Debug complex workflows** by reviewing detailed replays
- 🔍 **Analyze user behavior** with frame-by-frame precision

### Why rrweb?

rrweb is a modern, open-source solution that offers several advantages over traditional screen recording:

- **Precise DOM capture** - Records actual DOM changes, not just visual pixels
- **Efficient storage** - Only captures changes, resulting in smaller file sizes
- **Cross-platform compatibility** - Works consistently across different browsers and devices
- **Interactive replay** - Allows pausing, seeking, and step-by-step analysis
- **Event-based recording** - Captures incremental changes rather than full page snapshots

**Note:** rrweb focuses on DOM and user interaction recording. AgentBay enhances this with additional console and network monitoring capabilities.

## Quick Start

### 1. Enable Browser Replay

To enable browser replay, set `enable_browser_replay=True` when creating a session:

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Create session with browser replay enabled
params = CreateSessionParams(
    image_id="browser_latest",
    enable_browser_replay=True,  # 🎬 Enable browser replay
)

result = agent_bay.create(params)
session = result.session
```

### 2. Perform Browser Operations

Once browser replay is enabled, all browser interactions will be automatically captured:

```python
from agentbay.browser import BrowserOption
from playwright.sync_api import sync_playwright

# Initialize browser
browser = session.browser
browser.initialize(BrowserOption())
endpoint_url = browser.get_endpoint_url()

# All operations will be recorded
with sync_playwright() as p:
    playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
    # Create a new page with default context
    default_context = playwright_browser.contexts[0]
    page = default_context.new_page()

    # These actions will be recorded
    page.goto("https://example.com")
    page.fill("input[name='search']", "AgentBay")
    page.click("button[type='submit']")

    page.close()
```

### 3. Replay Files Storage

Browser replay files are automatically generated and stored by the system. These files can be accessed through the [AgentBay CONSOLE](https://agentbay.console.aliyun.com/session-log) website.

## Browser Replay Details

### What Gets Captured

The browser replay captures information using rrweb's advanced recording capabilities, enhanced with additional monitoring:

  - ✅ **DOM mutations** - Element changes, additions, removals, and CSS modifications
  - ✅ **Console output** - Logs, errors, warnings, and debug messages
  - ✅ **Network activity** - HTTP requests, API calls, and WebSocket connections


## Use Cases

### 1. Automated Testing

Record test execution for debugging failed tests:

```python
def run_test_with_replay():
    # Create session with browser replay
    params = CreateSessionParams(
        image_id="browser_latest",
        enable_browser_replay=True,
        labels={"test_type": "ui_automation", "replay": "enabled"}
    )

    session = agent_bay.create(params).session

    try:
        # Run your test - all actions will be recorded
        run_ui_test(session)
        print("Test completed - replay files generated for review")
    except Exception as e:
        # Test failed - replay files can help debug
        print(f"Test failed: {e}")
        print("Browser replay files are available for debugging")
    finally:
        agent_bay.delete(session)
```

### 2. User Journey Documentation

Record user workflows for documentation:

```python
def document_user_journey():
    params = CreateSessionParams(
        image_id="browser_latest",
        enable_browser_replay=True,
        labels={"purpose": "documentation", "workflow": "user_onboarding"}
    )

    session = agent_bay.create(params).session

    # Perform the user journey steps
    simulate_user_onboarding(session)

    print("User journey recorded - replay files generated for documentation")

    agent_bay.delete(session)
```

### 3. Compliance and Auditing

Record sessions for compliance purposes:

```python
def compliance_session():
    params = CreateSessionParams(
        image_id="browser_latest",
        enable_browser_replay=True,
        labels={
            "compliance": "SOX",
            "auditor": "external",
            "session_type": "compliance_check"
        }
    )

    session = agent_bay.create(params).session

    # Perform compliance-sensitive operations
    perform_financial_operations(session)

    print("Compliance operations recorded for audit trail")

    agent_bay.delete(session)
```

## Best Practices

### Performance Considerations

1. **Session Duration**: Longer sessions create larger recording files
2. **Resolution**: Higher resolution = larger files but better quality
3. **Activity Level**: More interactions = more data to record

### Security Considerations

1. **Sensitive Data**: Be aware that browser replay captures all visible content
2. **Session Access**: Control who can create sessions with replay enabled
3. **Label Management**: Use proper labels for categorizing and tracking replay sessions

## Troubleshooting

### Common Issues

**Browser replay not working:**
```python
# Verify that replay is enabled
if hasattr(session, 'enableBrowserReplay'):
    print(f"Browser replay enabled: {session.enableBrowserReplay}")
else:
    print("Browser replay not enabled - check session parameters")
```

**Session creation with replay fails:**
```python
# Check session parameters
params = CreateSessionParams(
    image_id="browser_latest",  # Must use browser image
    enable_browser_replay=True,         # Enable replay
    labels={"replay": "enabled"}
)
```

## Advanced Features

### Session Context and Metadata

Add context to your browser replay sessions using session labels:

```python
params = CreateSessionParams(
    image_id="browser_latest",
    enable_browser_replay=True,
    labels={
        "replay_purpose": "bug_reproduction",
        "bug_id": "ISSUE-1234",
        "user_id": "test_user_001",
        "test_environment": "staging",
        "browser_version": "chrome_latest"
    }
)
```

This metadata helps with session organization and tracking but does not affect the replay functionality itself.

## Example: Complete Browser Replay Workflow

Here's a complete example that demonstrates the full browser replay workflow:

```python
#!/usr/bin/env python3
"""Complete browser replay workflow example"""

import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser import BrowserOption
from playwright.sync_api import sync_playwright

def complete_replay_workflow():
    # Initialize
    agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))

    # 1. Create session with browser replay
    params = CreateSessionParams(
        image_id="browser_latest",
        enable_browser_replay=True,
        labels={"example": "complete_workflow", "replay": "enabled"}
    )

    session = agent_bay.create(params).session
    print(f"✅ Session created: {session.session_id}")
    print(f"📹 Browser replay enabled: {session.enableBrowserReplay}")

    try:
        # 2. Perform browser operations
        browser = session.browser
        browser.initialize(BrowserOption())

        with sync_playwright() as p:
            playwright_browser = p.chromium.connect_over_cdp(browser.get_endpoint_url())
            # Create a new page with default context
            default_context = playwright_browser.contexts[0]
            page = default_context.new_page()

            # All interactions will be captured
            page.goto("https://example.com")
            page.click("a[href='#']")  # Example interaction
            time.sleep(2)

            page.close()
            playwright_browser.close()

        print("✅ Browser operations completed - replay files generated")

    finally:
        # 3. Cleanup
        agent_bay.delete(session)
        print("✅ Session cleaned up")

if __name__ == "__main__":
    complete_replay_workflow()
```
## 📚 Related Guides

- [Browser Use Overview](README.md) - Complete browser automation features
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
