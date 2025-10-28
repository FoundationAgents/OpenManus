# PageUseAgent Guide 

An AI-powered, natural-language web agent that performs precise, reliable page operations via AgentBay’s managed browser. It exposes simple SDK methods to navigate, observe, act, extract.

- Works with natural language instructions
- Supports structured extraction via Pydantic schemas
- Uses MCP tools under the hood (no local browser needed)
- Optional Playwright CDP connection for advanced scenarios

## Table of Contents

- [PageUseAgent Guide](#pageuseagent-guide)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
    - [Prerequisites](#prerequisites)
    - [Minimal Example](#minimal-example)
  - [Architecture Overview](#architecture-overview)
  - [Core APIs](#core-apis)
    - [Navigation](#navigation)
    - [Screenshot](#screenshot)
    - [Observe](#observe)
    - [Act](#act)
    - [Extract](#extract)
    - [Close Session](#close-session)
  - [End-to-End Examples](#end-to-end-examples)
    - [1) Recipe Site (Search + Extract)](#1-recipe-site-search--extract)
    - [2) Apple Purchase Flow (Sequence of Acts)](#2-apple-purchase-flow-sequence-of-acts)
    - [3) Amazon Demo (Observe → Act → Assert)](#3-amazon-demo-observe--act--assert)
  - [Error Handling and Debug](#error-handling-and-debug)
  - [Best Practices](#best-practices)
  - [FAQ](#faq)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Install: `pip install wuying-agentbay-sdk`
- Set environment variable `AGENTBAY_API_KEY`

### Minimal Example

```python
import os
import asyncio
from pydantic import BaseModel, Field
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import BrowserAgent, ActOptions, ExtractOptions

class Product(BaseModel):
    name: str = Field(..., description="Product name")
    price: str | None = Field(None, description="Price text")
    link: str = Field(..., description="Relative product link like /products/abc")

class ProductList(BaseModel):
    products: list[Product]

async def main():
    agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))

    # Create a browser session
    params = CreateSessionParams(image_id="browser_latest")  # your image id
    session_result = agent_bay.create(params)
    if not session_result.success:
        print(f"Create session failed: {session_result.error_message}")
        return
    session = session_result.session

    # Initialize managed browser
    ok = await session.browser.initialize_async(BrowserOption())
    if not ok:
        print("Browser initialization failed")
        return

    agent: BrowserAgent = session.browser.agent

    # Navigate
    print(await agent.navigate_async("https://example.com"))

    # Act (natural language)
    await agent.act_async(action_input=ActOptions(action="go to products or shop page"))

    # Extract structured data
    ok, data = await agent.extract_async(
        options=ExtractOptions(
            instruction="Extract all products with name, optional price, and relative link",
            schema=ProductList,
            use_text_extract=True
        )
    )
    if ok:
        print(f"Extracted {len(data.products)} products")
    else:
        print("Extraction failed")

    # Clean up
    await agent.close_async()
    session.delete()

if __name__ == "__main__":
    asyncio.run(main())
```

Notes:
- `page` is optional; `None` uses the current managed page.
- `image_id` depends on your backend catalog (e.g., `browser_latest`).

---

## Architecture Overview

- Your code calls `BrowserAgent` (SDK).
- SDK invokes MCP tools within the managed browser image:
  - `page_use_navigate`
  - `page_use_observe`
  - `page_use_act`
  - `page_use_extract`
  - `page_use_screenshot`
  - `page_use_close_session`
- No local browser needed. Optionally, you can connect via Playwright CDP to the managed browser for custom checks.

---

## Core APIs

### Navigation

```python
# Sync
def navigate(self, url: str) -> str

# Async
async def navigate_async(self, url: str) -> str
```

- Description: Navigates the managed page to the given URL.
- Returns: Result message string.

Example:
```python
await agent.navigate_async("https://example.com")
```

---

### Screenshot

```python
# Sync
def screenshot(self, page=None, full_page=True, quality=80, clip=None, timeout=None) -> str

# Async
async def screenshot_async(self, page=None, full_page=True, quality=80, clip=None, timeout=None) -> str
```

- Returns: A base64-encoded PNG.
  - By default, the MCP tool wraps it as a data URL like `data:image/png;base64,<...>`.
  - If you call lower-level internals (e.g., CDP or event bus) you may receive raw base64 without the `data:image/...` prefix.
- `page` is optional; the managed page is used by default.

Parameters:
- full_page (bool): Capture the full scrollable page (default True).
- quality (int): 0–100, for JPEG format only (default 80).
- clip (dict | None): Clipping region with keys {x, y, width, height}. If provided, `full_page` is ignored.
- timeout (int | None): Operation timeout in ms.

Example (robust decode for both formats):
```python
data = await agent.screenshot_async()
if data.startswith("data:image/"):
    header, encoded = data.split(",", 1)
    png_bytes = base64.b64decode(encoded)
else:
    png_bytes = base64.b64decode(data)
```

---

### Observe

```python
# Options
class ObserveOptions:
    def __init__(self, instruction: str, iframes: bool | None = None, dom_settle_timeout_ms: int | None = None)

# Result
class ObserveResult:
    def __init__(self, selector: str, description: str, method: str, arguments: dict)

# APIs
def observe(self, page, options: ObserveOptions) -> tuple[bool, list[ObserveResult]]
async def observe_async(self, page, options: ObserveOptions) -> tuple[bool, list[ObserveResult]]
```

- Description: Finds elements or actionable targets based on natural language.
- Returns: `(success, [ObserveResult])`

Example:
```python
ok, items = await agent.observe_async(
    options=ObserveOptions(
        instruction="find the Add to Cart button",
    )
)
```

---

### Act

```python
# Options
class ActOptions:
    def __init__(self, action: str, timeoutMS: int | None = None, iframes: bool | None = None,
                 dom_settle_timeout_ms: int | None = None, variables: dict[str, str] | None = None)

# Result
class ActResult:
    def __init__(self, success: bool, message: str, action: str)

# APIs
def act(self, action_input: Union[ObserveResult, ActOptions], page) -> ActResult
async def act_async(self, action_input: Union[ObserveResult, ActOptions], page) -> ActResult
```

- Description: Performs an action with NL instruction or using an `ObserveResult`.
- Returns: `ActResult(success, message, action)`

Examples:
```python
# Natural language
await agent.act_async(action_input=ActOptions(action="type 'ipad' in the search bar and press enter"))

# Act on observed element
ok, items = await agent.observe_async(options=ObserveOptions(instruction="find the sign in button"))
if ok and items:
    await agent.act_async(action_input=items[0])
```

---

### Extract

```python
# Generic Options
class ExtractOptions(Generic[T]):
    def __init__(self, instruction: str, schema: Type[T], use_text_extract: bool | None = None,
                 selector: str | None = None, iframe: bool | None = None,
                 dom_settle_timeout_ms: int | None = None, use_vision: bool | None = None)

# APIs
def extract(self, options: ExtractOptions[T], page) -> tuple[bool, T]
async def extract_async(self, options: ExtractOptions[T], page) -> tuple[bool, T]
```

- Description: Extracts structured data as a Pydantic model instance.
- Returns: `(success, model_instance)`
- Options:
  - use_text_extract (bool): Prefer text-based parsing when true (useful for text-heavy pages).
  - use_vision (bool): Attach a viewport screenshot to help the model interpret visually-indicated states (optional).
  - selector, iframe, dom_settle_timeout_ms: Narrow scope or tune stability.

Example:
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: str | None
    link: str

class ItemList(BaseModel):
    products: list[Item]

ok, result = await agent.extract_async(
    options=ExtractOptions(
        instruction="extract all products with name, price and link",
        schema=ItemList,
        use_text_extract=True,
        use_vision=True
    )
)
```

---

### Close Session

```python
async def close_async(self) -> bool
```

- Gracefully closes the remote browser agent session.

---

## End-to-End Examples

### 1) Recipe Site (Search + Extract)

```python
from pydantic import BaseModel, Field
from agentbay.browser.browser_agent import ActOptions, ExtractOptions

class RecipeDetails(BaseModel):
    title: str = Field(..., description="Recipe title")
    total_ratings: int | None

await agent.navigate_async("https://www.allrecipes.com/")
await agent.act_async(action_input=ActOptions(action='type "chocolate chip cookies" in the search bar'))
await agent.act_async(action_input=ActOptions(action="press enter"))

ok, data = await agent.extract_async(
    options=ExtractOptions(
        instruction="extract the title and the total number of ratings from the first recipe",
        schema=RecipeDetails,
        use_text_extract=True,
    )
)
```

### 2) Apple Purchase Flow (Sequence of Acts)

```python
actions = [
    "click on the buy button",
    "select the Pro Max model",
    "select the natural titanium color",
    "select the 256GB storage option",
    "click on the 'select a smartphone' trade-in option",
    "select the iPhone 13 mini model from the dropdown",
    "select the iPhone 13 mini is in good condition",
]

for a in actions:
    await agent.act_async(action_input=ActOptions(action=a))
```

### 3) Amazon Demo (Observe → Act → Assert)

```python
from agentbay.browser.browser_agent import ObserveOptions

ok, obs1 = await agent.observe_async(
    options=ObserveOptions(instruction="Find and click the 'Add to Cart' button")
)
if ok and obs1:
    await agent.act_async(action_input=obs1[0])

ok, obs2 = await agent.observe_async(
    options=ObserveOptions(instruction="Find and click the 'Proceed to checkout' button")
)
if ok and obs2:
    await agent.act_async(action_input=obs2[0])
```

---

## Error Handling and Debug

- Exceptions surfaced by the SDK:
  - `BrowserError`: SDK-side or tool invocation failures.
  - `AgentBayError`: Service-related errors (wrapped to `BrowserError` by default).

- Result types:
  - `ActResult`: `{ success: bool, message: str, action: str }`
  - `observe` returns `(success: bool, results: list[ObserveResult])`
  - `extract` returns `(success: bool, data: T)`

- MCP validation hints:
  - If you see Pydantic validation errors (e.g., dropdown indices must be >= 1), ensure your generated action JSON conforms to the tool schema.
  - Avoid passing extra fields not defined in the schema.

---

## Best Practices

- Write concise, unambiguous natural-language actions.
- For structured data, always define strict Pydantic schemas.
- Use `use_text_extract=True` for text-heavy pages; use DOM-based for structured layouts.
- Consider `use_vision=True` for visually-driven pages to improve robustness.
- Chain `Observe -> Act` when direct acting is ambiguous.
- Consider small waits between dependent steps on dynamic pages.

---

## FAQ

- Do I need Playwright locally?
  - The agent runs in a managed browser session. Local Playwright is optional for your custom checks via CDP.

- How do I pass variables into actions?
  - Use `ActOptions.variables` (dict) and ensure your backend/tooling supports placeholders.

- How do screenshots return?
  - By default, as a data URL `data:image/png;base64,<...>`. If you use lower-level internals, you may get raw base64 without the header.

- Observe vs Extract?
  - `observe` finds actionable elements; `extract` returns structured data based on your schema.
## 📚 Related Guides

- [Browser Use Overview](../README.md) - Complete browser automation features
- [Session Management](../../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Code Examples](../code-example.md) - PageUseAgent example code

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
