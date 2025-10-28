# Browser Context Guide

Browser Context is a core feature of the AgentBay SDK that enables persistent browser state management across multiple sessions. It allows you to maintain cookies, cache, local storage, and other browser data between sessions, significantly reducing anti-bot friction and speeding up web page navigation.

## Overview

A Browser Context represents a persistent browser environment that stores browser state such as:
- Cookies
- Cache
- Local storage
- Session storage
- Browser preferences
- Installed extensions (when used with Extension Management)

## Key Benefits

1. **Reduced Anti-Bot Friction**: By maintaining browser state, websites recognize your sessions as returning users rather than new visitors
2. **Faster Page Loads**: Cached resources and cookies reduce page load times
3. **Session Continuity**: Continue where you left off across multiple sessions
4. **Consistent User Experience**: Maintain user preferences and settings

## Python Implementation

### Basic Usage

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext

# Initialize AgentBay client
agent_bay = AgentBay(api_key="your_api_key")

# Create or get a persistent context
context_result = agent_bay.context.get("my-browser-context", create=True)
context = context_result.context

# Create browser session with context
browser_context = BrowserContext(
    context_id=context.id,
    auto_upload=True
)

session_params = CreateSessionParams(
    image_id="browser-image-id",
    browser_context=browser_context
)

session_result = agent_bay.create(session_params)
session = session_result.session
```

### Cookie Persistence Example

```python
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.browser.browser import BrowserOption
from playwright.sync_api import sync_playwright

# Initialize AgentBay
agent_bay = AgentBay(api_key="your_api_key")

# Create persistent context
context_result = agent_bay.context.get("cookie-demo-context", create=True)
context = context_result.context

# First session - set cookies
browser_context = BrowserContext(
    context_id=context.id,
    auto_upload=True
)

params = CreateSessionParams(
    image_id="browser-image-id",
    browser_context=browser_context
)

session1 = agent_bay.create(params).session

# Set cookies in first session
session1.browser.initialize(BrowserOption())
endpoint_url = session1.browser.get_endpoint_url()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(endpoint_url)
    context_p = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context_p.new_page()
    
    # Navigate and set cookies
    page.goto("https://example.com")
    context_p.add_cookies([
        {
            "name": "session_cookie",
            "value": "session_value",
            "domain": "example.com",
            "path": "/",
        }
    ])
    
    browser.close()

# Delete first session with context sync
agent_bay.delete(session1, sync_context=True)

# Second session - verify cookies persist
session2 = agent_bay.create(params).session

# Check cookies in second session
session2.browser.initialize(BrowserOption())
endpoint_url2 = session2.browser.get_endpoint_url()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(endpoint_url2)
    context_p = browser.contexts[0] if browser.contexts else browser.new_context()
    
    # Verify cookies persist
    cookies = context_p.cookies()
    print(f"Persisted cookies: {cookies}")
    
    browser.close()
```

## TypeScript Implementation

### Basic Usage

```typescript
import { AgentBay, CreateSessionParams, BrowserContext } from 'wuying-agentbay-sdk';

// Initialize AgentBay client
const agentBay = new AgentBay({ apiKey: "your_api_key" });

// Create or get a persistent context
const contextResult = await agentBay.context.get("my-browser-context", true);
const context = contextResult.context;

// Create browser session with context
const browserContext: BrowserContext = {
    contextId: context.id,
    autoUpload: true
};

const params = new CreateSessionParams()
    .withImageId("browser-image-id")
    .withBrowserContext(browserContext);

const sessionResult = await agentBay.create(params);
const session = sessionResult.session;
```

### Cookie Persistence Example

```typescript
import { AgentBay, CreateSessionParams, BrowserContext, BrowserOption } from 'wuying-agentbay-sdk';
import { chromium } from 'playwright';

// Initialize AgentBay
const agentBay = new AgentBay({ apiKey: "your_api_key" });

// Create persistent context
const contextResult = await agentBay.context.get("cookie-demo-context", true);
const context = contextResult.context;

// First session - set cookies
const browserContext: BrowserContext = {
    contextId: context.id,
    autoUpload: true
};

const params = new CreateSessionParams()
    .withImageId("browser-image-id")
    .withBrowserContext(browserContext);

const session1 = (await agentBay.create(params)).session;

// Set cookies in first session
await session1.browser.initializeAsync(new BrowserOption());
const endpointUrl = session1.browser.getEndpointUrl();

const browser = await chromium.connectOverCDP(endpointUrl);
const contextP = browser.contexts()[0] || await browser.newContext();
const page = await contextP.newPage();

// Navigate and set cookies
await page.goto("https://example.com");
await contextP.addCookies([
    {
        name: "session_cookie",
        value: "session_value",
        domain: "example.com",
        path: "/",
    }
]);

await browser.close();

// Delete first session with context sync
await agentBay.delete(session1, true);

// Second session - verify cookies persist
const session2 = (await agentBay.create(params)).session;

// Check cookies in second session
await session2.browser.initializeAsync(new BrowserOption());
const endpointUrl2 = session2.browser.getEndpointUrl();

const browser2 = await chromium.connectOverCDP(endpointUrl2);
const contextP2 = browser2.contexts()[0] || await browser2.newContext();

// Verify cookies persist
const cookies = await contextP2.cookies();
console.log(`Persisted cookies: ${JSON.stringify(cookies)}`);

await browser2.close();
```

## Best Practices

1. **Use Descriptive Context Names**: Name your contexts based on their purpose (e.g., "ecommerce-scraping", "social-media-automation")
2. **Enable Auto Upload**: Set `auto_upload=True` to automatically synchronize browser data when sessions end
3. **Clean Up Resources**: Delete sessions when done to free up cloud resources
4. **Handle Errors Gracefully**: Implement proper error handling for context operations
5. **Reuse Contexts**: Reuse the same context across multiple sessions for continuity

## Advanced Features

### Context Synchronization Policies

You can customize how browser data is synchronized:

```python
from agentbay.context_sync import SyncPolicy

# Create custom sync policy
policy = SyncPolicy(
    upload=True,
    extract=True,
    white_list=["/cookies.json", "/storage/"],
    black_list=["/cache/large_files/"]
)

# Use with context sync
context_sync = ContextSync.new(
    context_id=context.id,
    path="/browser-data",
    policy=policy
)
```

### Multiple Contexts

You can use multiple contexts for different purposes:

```python
# Create separate contexts for different websites
ecommerce_context = agent_bay.context.get("ecommerce-site", create=True).context
social_context = agent_bay.context.get("social-media", create=True).context

# Use different contexts for different sessions
ecommerce_session_params = CreateSessionParams(
    browser_context=BrowserContext(ecommerce_context.id, True)
)

social_session_params = CreateSessionParams(
    browser_context=BrowserContext(social_context.id, True)
)
```

## Error Handling

Common errors and how to handle them:

```python
try:
    context_result = agent_bay.context.get("my-context", create=True)
    if not context_result.success:
        print(f"Failed to create context: {context_result.error_message}")
        
    session_result = agent_bay.create(session_params)
    if not session_result.success:
        print(f"Failed to create session: {session_result.error_message}")
        
except Exception as e:
    print(f"An error occurred: {e}")
```

## 📚 Related Guides

- [Extension Management](extension.md) - Browser extension integration
- [Data Persistence](../../common-features/basics/data-persistence.md) - Broader context management
- [Session Management](../../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Browser Use Overview](../README.md) - Complete browser automation features

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)