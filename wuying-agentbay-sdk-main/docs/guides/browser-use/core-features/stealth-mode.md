# Browser Stealth Mode Guide

**💡 Note: Stealth Mode is designed for legitimate automation scenarios such as testing, research, and authorized data collection. When implementing these features, consider following web standards and best practices to ensure sustainable and respectful interactions with target websites.**

---


## Overview

Stealth Mode is an core feature of the AgentBay SDK, designed to help developers create browser sessions that are harder to detect by anti-bot systems. By simulating various, realistic user browser fingerprints and human-like behavior patterns, Stealth Mode helps your automated tasks behave more like regular browsing rather than script browsing.


## Key Features

### Browser Fingerprint Randomized
Stealth Mode supports to randomize browser fingerprints and can be configured when initializing a browser via AgentBay AIBrowser API. The `BrowserFingerprint` options include:
- **Devices**: Specify desktop or mobile device
- **Operating Systems**: Specify operating systems like windows, macos, linux, ios, android
- **Locales**: Customize browser language and locale settings (e.g. zh-CN, en-US, fr-FR)

When the `use_stealth` and `BrowserFingerprint` option are both set, AgentBay AIBrowser will rotate the browser fingerprints releated to these options.


## Python Implementation

### Basic Usage

```python
import os
import asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption, BrowserFingerprint
from playwright.async_api import async_playwright

async def stealth_example():
    # Initialize AgentBay client
    api_key = os.getenv("AGENTBAY_API_KEY")
    agent_bay = AgentBay(api_key=api_key)
    
    # Create session
    params = CreateSessionParams(image_id="browser_latest")
    session_result = agent_bay.create(params)
    
    if session_result.success:
        session = session_result.session
        
        # Configure browser fingerprint
        browser_fingerprint = BrowserFingerprint(
            devices=["desktop"],
            operating_systems=["windows"],
            locales=["zh-CN", "zh", "en-US"]
        )
        
        # Enable stealth mode
        browser_option = BrowserOption(
            use_stealth=True,
            fingerprint=browser_fingerprint
        )
        
        # Initialize browser
        if await session.browser.initialize_async(browser_option):
            endpoint_url = session.browser.get_endpoint_url()
            
            # Connect using Playwright
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                context = browser.contexts[0]
                page = await context.new_page()
                
                # Verify user agent
                await page.goto("https://httpbin.org/user-agent")
                response = await page.evaluate("() => JSON.parse(document.body.textContent)")
                print(f"User Agent: {response.get('user-agent')}")
                
                # Check navigator properties
                nav_info = await page.evaluate("""
                    () => ({
                        platform: navigator.platform,
                        language: navigator.language,
                        languages: navigator.languages,
                        webdriver: navigator.webdriver
                    })
                """)
                
                print(f"Platform: {nav_info.get('platform')}")
                print(f"Language: {nav_info.get('language')}")
                print(f"WebDriver: {nav_info.get('webdriver')}")
                
                await browser.close()
        
        # Clean up session
        agent_bay.delete(session)

if __name__ == "__main__":
    asyncio.run(stealth_example())
```


## TypeScript Implementation

### Basic Usage

```typescript
import { AgentBay, CreateSessionParams } from 'wuying-agentbay-sdk';
import { BrowserOption, BrowserFingerprint } from 'wuying-agentbay-sdk';
import { chromium } from 'playwright';

async function stealthExample(): Promise<void> {
    // Initialize AgentBay client
    const apiKey = process.env.AGENTBAY_API_KEY;
    const agentBay = new AgentBay({ apiKey });
    
    // Create session
    const params: CreateSessionParams = {
        imageId: "browser_latest"
    };
    const sessionResult = await agentBay.create(params);
    
    if (sessionResult.success && sessionResult.session) {
        const session = sessionResult.session;
        
        // Configure browser fingerprint
        const browserFingerprint: BrowserFingerprint = {
            devices: ["desktop"],
            operatingSystems: ["windows"],
            locales: ["zh-CN", "zh", "en-US"]
        };
        
        // Enable stealth mode
        const browserOption: BrowserOption = {
            useStealth: true,
            fingerprint: browserFingerprint
        };
        
        // Initialize browser
        const initialized = await session.browser.initializeAsync(browserOption);
        if (initialized) {
            const endpointUrl = await session.browser.getEndpointUrl();
            
            // Connect using Playwright
            const browser = await chromium.connectOverCDP(endpointUrl);
            const context = browser.contexts()[0];
            const page = await context.newPage();
            
            // Verify user agent
            await page.goto("https://httpbin.org/user-agent");
            const response = await page.evaluate(() => JSON.parse(document.body.textContent));
            console.log(`User Agent: ${response["user-agent"]}`);
            
            // Check navigator properties
            const navInfo = await page.evaluate(() => ({
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                webdriver: (navigator as any).webdriver
            }));
            
            console.log(`Platform: ${navInfo.platform}`);
            console.log(`Language: ${navInfo.language}`);
            console.log(`WebDriver: ${navInfo.webdriver}`);
            
            await browser.close();
        }
        
        // Clean up session
        await agentBay.delete(session);
    }
}

stealthExample().catch(console.error);
```

## Best Practices

### 1. Browser Context Usage

**💡 Note**: Always use the pre-created browser context provided by AgentBay SDK instead of creating new contexts.

```python
# ✅ Correct - Use the existing context
browser = await p.chromium.connect_over_cdp(endpoint_url)
context = browser.contexts[0]  # Use the default context
page = await context.new_page()
```

```python
# ❌ Incorrect - Creating new context will break stealth features
browser = await p.chromium.connect_over_cdp(endpoint_url)
context = await browser.new_context()
page = await context.new_page()
```

**Why this matters:**
- The AgentBay SDK pre-configures `contexts[0]` with stealth mode settings
- Creating a new context with `new_context()` bypasses these configurations
- This results in reduced anti-bot detection effectiveness and browser fingerprinting may not work properly

### 2. Fingerprint Configuration Strategy

#### User Agent vs Fingerprint Priority
Do not configure `user_agent` and `fingerprint` options simultaneously, as they conflict with each other.
When `user_agent` and `fingerprint` are both specified:
- the fingerprint randomization feature will be disabled
- the browser will use the custom user-agent string

```python
# ✅ Correct - Use fingerprint for automatic rotation
browser_option = BrowserOption(
    use_stealth=True,
    fingerprint=BrowserFingerprint(
        devices=["desktop"],
        operating_systems=["windows"]
    )
    # No user_agent specified - fingerprint rotation will work
)
```

```python
# ❌ Incorrect - user_agent overrides fingerprint rotation
browser_option = BrowserOption(
    use_stealth=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    fingerprint=BrowserFingerprint(
        devices=["desktop"],
        operating_systems=["windows"]
    )  # The fingerprint settings will be ignored
)
```


#### Device Type Selection
- **Desktop Scenario**: Use `["desktop"]` with `["windows", "macos", "linux"]`
- **Mobile Scenario**: Use `["mobile"]` with `["android", "ios"]`
- **Avoid Conflicts**: Don't mix desktop devices with mobile operating systems

```python
# ✅ Correct configuration
desktop_fingerprint = BrowserFingerprint(
    devices=["desktop"],
    operating_systems=["windows", "macos"]
)

# ❌ Incorrect configuration (device and OS mismatch)
wrong_fingerprint = BrowserFingerprint(
    devices=["desktop"],
    operating_systems=["android", "ios"]  # Mobile OS should not pair with desktop devices
)
```

## 📚 Related Guides

- [Browser Proxies](browser-proxies.md) - IP rotation and proxy configuration
- [CAPTCHA Resolution](captcha.md) - Automatic CAPTCHA handling
- [Browser Context](browser-context.md) - Cookie and session management
- [Browser Use Overview](../README.md) - Complete browser automation features

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)