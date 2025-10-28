# AgentBay AIBrowser Guide

Welcome to the AgentBay AIBrowser Guides! This provides complete functionality introduction and best practices for experienced developers.

## 🎯 Quick Navigation

- [Example](code-example.md) - Index for examples demonstrating core & advance features
- [Core Features](core-features.md) - Essential browser features and typical workflows
- [Advance Features](advance-features.md) - Advanced configuration and capabilities
- [Integrations](integrations.md) - Seamlessly weave with community tools and frameworks, extending your automation reach

## 🚀 What is AgentBay AIBrowser?

Agentbay AIBrowser is a managed platform for running headless/non-headless browsers at scale. It provides infrastructure to create and manage sessions, initialize browser instances, and allocate the underlying hardware resources on demand. It is designed for webpage automation scenarios such as filling out forms, simulating user actions, and orchestrating complex multi-step tasks across modern, dynamic websites.

The Agentbay AIBrowser API offers simple primitives to control browsers, practical utilities to create/manage sessions, and advanced AI capabilities to execute tasks described in natural language.

### Key Features

- Automation framework compatibility: Highly compatible with Playwright and Puppeteer via CDP
- Secure and scalable infrastructure: Managed sessions, isolation, and elastic resource allocation
- Observability: Session Replay, Session Inspector, and Live Mode for real-time debugging
- Advanced capabilities: Context management, IP proxy, and stealth/fingerprinting options
- AI-powered PageUseAgent: Execute natural-language tasks for complex web workflows
- Rich APIs: Clean primitives for sessions, browser lifecycle, and agent operations

### Quick Start (Python)

Below is a minimal, runnable example showing how to initialize the browser via the AgentBay Python SDK and drive it using Playwright over CDP. It follows the same flow as the reference example in `python/docs/examples/browser/visit_aliyun.py`.

Prerequisites:
- Set your API key: `export AGENTBAY_API_KEY=your_api_key`
- Install dependencies: `pip install wuying-agentbay-sdk playwright`
- Install Playwright browsers: `python -m playwright install chromium`

```python
import os
import asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from playwright.async_api import async_playwright

async def main():
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        raise RuntimeError("AGENTBAY_API_KEY environment variable not set")

    agent_bay = AgentBay(api_key=api_key)

    # Create a session (use an image with browser preinstalled)
    params = CreateSessionParams(image_id="browser_latest")
    session_result = agent_bay.create(params)
    if not session_result.success:
        raise RuntimeError(f"Failed to create session: {session_result.error_message}")

    session = session_result.session

    # Initialize browser (supports stealth, proxy, fingerprint, etc. via BrowserOption)
    ok = await session.browser.initialize_async(BrowserOption())
    if not ok:
        raise RuntimeError("Browser initialization failed")

    endpoint_url = session.browser.get_endpoint_url()

    # Connect Playwright over CDP and automate
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint_url)
        page = await browser.new_page()
        await page.goto("https://www.aliyun.com")
        print("Title:", await page.title())
        await browser.close()

    session.delete()

if __name__ == "__main__":
    asyncio.run(main())
```

First, the script authenticates by building an `AgentBay` client with your API key, establishing a trusted channel to the platform. 

Then it provisions a fresh execution environment by creating a session with a browser-enabled image, ensuring the necessary runtime is available. 

After that, the session’s browser is initialized with `BrowserOption()`, bringing up a remote browser instance ready for automation. 

Next, it retrieves the CDP endpoint URL via `get_endpoint_url()` and connects to it using Playwright’s `connect_over_cdp`, bridging your local code to the remote browser. 

Now, with a live connection established, the code opens a new page, navigates to a website, and can freely inspect or manipulate the DOM just like a local browser. 

Finally, when all work is complete, the session is explicitly deleted to release the allocated resources.

Key Browser APIs:
- `Browser.initialize(option: BrowserOption) -> bool` / `initialize_async(...)`: Start the browser instance for a session
- `Browser.get_endpoint_url() -> str`: Return CDP WebSocket endpoint; use with Playwright `connect_over_cdp`
- `Browser.is_initialized() -> bool`: Check if the browser is ready

## Basic Configurations

Sometimes the web needs a different mask and a different stage. By shaping the browser’s identity and canvas, you can coax sites to reveal the experience meant for a specific device class or audience. Here we’ll set a custom user agent and a precise viewport, then watch the page respond.

```python
import os
import asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption, BrowserViewport
from playwright.async_api import async_playwright

CUSTOM_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def main():
    agent_bay = AgentBay(api_key=os.environ["AGENTBAY_API_KEY"])  # first, authenticate

    params = CreateSessionParams(image_id="browser_latest")       # then, provision a browser-ready session
    result = agent_bay.create(params)
    if not result.success:
        raise RuntimeError(result.error_message)

    session = result.session

    # after that, define how the browser should look and feel
    option = BrowserOption(
        user_agent=CUSTOM_UA,                    # present ourselves with a custom identity
        viewport=BrowserViewport(width=1366, height=768),  # and stand on a stage sized like a common laptop
    )

    ok = await session.browser.initialize_async(option)
    if not ok:
        raise RuntimeError("Browser initialization failed")

    endpoint_url = session.browser.get_endpoint_url()      # now, discover the CDP doorway

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint_url)  # step through and take control
        page = await browser.new_page()

        await page.goto("https://www.whatismybrowser.com/detect/what-is-my-user-agent")
        # verify our new voice and our new stage
        ua = await page.evaluate("navigator.userAgent")
        w = await page.evaluate("window.innerWidth")
        h = await page.evaluate("window.innerHeight")
        print("Effective UA:", ua)
        print("Viewport:", w, "x", h)

        await browser.close()

    session.delete()  # finally, bow out and free the stage

if __name__ == "__main__":
    asyncio.run(main())
```

First we authenticate and create a session that knows how to host a browser. Then, instead of accepting the default identity, we dress the browser in a chosen user agent and set a viewport that mirrors a familiar laptop screen. After that, we breathe life into the browser with `initialize_async`, request the CDP endpoint, and cross the bridge with Playwright. Now the page loads under our chosen disguise and dimensions; a quick glance at `navigator.userAgent` and the window size confirms the transformation. And when the scene is over, we close the curtain by deleting the session, returning the resources so another performance can begin.

If you want to explore more configurable capabilities, see Core Features: [core-features.md](core-features.md).

## Utilizing PageUseAgent

PageUseAgent lets you speak to the browser in natural language and have it carry out intent-driven actions. Instead of meticulously crafting selectors and sequences, you describe the goal; the agent interprets it, maps it to DOM operations, and executes the steps reliably—with optional timeouts, iframe awareness, and variable injection for dynamic prompts.

Below we’ll search for a book on Google. First we bring a browser to life and open Google, then we ask the agent to perform the task: type the query and open the first result.

```python
import os
import asyncio
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ActOptions
from playwright.async_api import async_playwright

BOOK_QUERY = "The Pragmatic Programmer"

async def main():
    agent_bay = AgentBay(api_key=os.environ["AGENTBAY_API_KEY"])  # authenticate

    params = CreateSessionParams(image_id="browser_latest")       # provision session with browser image
    result = agent_bay.create(params)
    if not result.success:
        raise RuntimeError(result.error_message)
    session = result.session

    # initialize the remote browser
    if not await session.browser.initialize_async(BrowserOption()):
        raise RuntimeError("Browser initialization failed")

    endpoint_url = session.browser.get_endpoint_url()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint_url)
        page = await browser.new_page()

        # step onto the stage
        await page.goto("https://www.google.com")

        # ask the agent to act: type the book name into the search box
        act_result = await session.browser.agent.act_async(ActOptions(
            action=f"Type '{BOOK_QUERY}' into the search box and submit",
        ), page)
        print("act_result:", act_result.success, act_result.message)

        # let the agent open the first result
        open_first = await session.browser.agent.act_async(ActOptions(
            action="Click the first result in the search results",
        ), page)
        print("open_first:", open_first.success, open_first.message)

        # pause briefly to observe
        await page.wait_for_timeout(5000)
        await browser.close()

    session.delete()

if __name__ == "__main__":
    asyncio.run(main())
```

First we create and initialize a browser session as before; then, rather than hand-writing selectors, we simply tell the agent what to do—type a query and proceed to the first result. After that, the agent translates our intent into concrete interactions on the page. Now the browser flows from search box to results like a guided hand. Finally, we close the browser and release the session.

About `PageUseAgent.act`:
- Can interpolate dynamic values using `variables` for reusable prompts
- Operates on the active Playwright page by resolving its `context_id` and `page_id` under the hood
- Returns a structured `ActResult` with `success`, `message`, useful for logging and recovery flows

If you want to explore full capability of PageUseAgent, or other more advance features, see Advance Features: [advance-features.md](advance-features.md).

### Limitations

PageUseAgent does not include a long-horizon planner and won’t orchestrate multi-step schedules by itself. It relies on your invoker (or a higher-level agent) to break a project into steps and call `act` or other PageUseAgent method for each one. Its strength is in precise, atomic web operations—clicking, filling, scrolling, etc.—executed quickly and consistently. This narrow focus is deliberate: it prioritizes throughput and accuracy of each step while leaving complex task planning and branching logic to external controllers.






