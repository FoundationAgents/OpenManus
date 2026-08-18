"""
Invisible Firefox Tool for OpenManus (proposal stub).

Optional Firefox-based stealth fetcher tool, parallel to Crawl4aiTool and
BrowserUseTool. Wraps invisible_playwright which drives a patched Firefox
150 binary with fingerprint patches applied at the C++ source code level
(no JS shims to detect).

Tracking discussion: TBD
"""

from typing import Optional

from app.logger import logger
from app.tool.base import BaseTool, ToolResult

try:
    from invisible_playwright import InvisiblePlaywright
except ImportError:
    raise ImportError(
        "`invisible_playwright` not installed. "
        "Install with `pip install invisible_playwright` and run "
        "`python -m invisible_playwright fetch` to download the patched Firefox binary."
    )


class InvisibleFirefoxTool(BaseTool):
    """Firefox-based stealth fetcher tool.

    Wraps invisible_playwright (https://github.com/feder-cr/invisible_playwright),
    which drives a patched Firefox 150 binary (feder-cr/invisible_firefox,
    MPL-2.0, same license as Firefox upstream). Useful for sites where the
    Crawl4aiTool, BrowserUseTool, or web_search backends hit Cloudflare,
    Akamai, Datadome, or hCaptcha walls.
    """

    name: str = "invisible_firefox"
    description: str = """Fetch a URL using a patched stealth Firefox browser.

    Use this when other browser or scraper tools return 403, empty content,
    or get flagged as automation. The patched binary handles fingerprint
    spoofing at the native level so there are no detectable JS shims.

    Returns the rendered HTML of the page.
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "(required) The URL to fetch.",
            },
            "wait_for_selector": {
                "type": "string",
                "description": "(optional) CSS selector to wait for before returning. Useful for JS-rendered pages.",
            },
            "seed": {
                "type": "integer",
                "description": "(optional) Integer seed for deterministic fingerprint across runs.",
            },
        },
        "required": ["url"],
    }

    async def execute(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> ToolResult:
        try:
            from invisible_playwright.async_api import InvisiblePlaywright as AsyncIP

            async with AsyncIP(seed=seed, headless=True) as browser:
                page = await browser.new_page()
                await page.goto(url)
                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector)
                html = await page.content()
                return ToolResult(output=html)
        except Exception as e:
            logger.error(f"InvisibleFirefoxTool failed for {url}: {e}")
            return ToolResult(error=str(e))
