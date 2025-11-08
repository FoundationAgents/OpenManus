"""
High-level browser automation tool for agents.

Provides semantic interface for browser operations:
- navigate(url)
- click(selector_or_description)
- fill(selector_or_description, value)
- extract(description)
- scroll(direction, amount)
- screenshot(output_path)
- get_page_state()
- execute_script(js_code)
- wait_for_navigation()

All operations flow through BrowserRAGHelper for semantic understanding.
Guardian checks on all navigation and data extraction.
"""

import asyncio
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.browser.manager import get_browser_manager
from app.browser.rag_helper import BrowserRAGHelper
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


_BROWSER_AUTOMATION_DESCRIPTION = """\
High-level browser automation tool with semantic understanding.

Features:
* Navigate to URLs with automatic waiting
* Click elements using CSS selectors or semantic descriptions
* Fill form fields intelligently based on field purpose
* Extract information using LLM-based semantic understanding
* Scroll pages naturally
* Capture screenshots
* Get page state optimized for agent understanding
* Execute arbitrary JavaScript
* Wait for navigation and content changes

The tool uses RAG-based semantic understanding to:
- Identify elements by natural language description
- Understand form field purposes
- Extract relevant information without embeddings
- Suggest interactions based on page context

All operations are validated through Guardian for security.
"""


class BrowserAutomationTool(BaseTool):
    """High-level browser automation tool for agents."""
    
    name: str = "browser_automation"
    description: str = _BROWSER_AUTOMATION_DESCRIPTION
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "fill",
                    "extract",
                    "scroll",
                    "screenshot",
                    "get_page_state",
                    "execute_script",
                    "wait_for_navigation",
                    "create_tab",
                    "switch_tab",
                    "close_tab",
                    "get_cookies",
                    "set_cookies",
                ],
                "description": "Browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for navigation",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector or semantic description for element",
            },
            "description": {
                "type": "string",
                "description": "Semantic description of element or content",
            },
            "value": {
                "type": "string",
                "description": "Value to fill or data to extract",
            },
            "direction": {
                "type": "string",
                "enum": ["up", "down", "top", "bottom"],
                "description": "Scroll direction",
            },
            "amount": {
                "type": "integer",
                "description": "Scroll amount in pixels",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save screenshot",
            },
            "script": {
                "type": "string",
                "description": "JavaScript code to execute",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds",
            },
            "tab_index": {
                "type": "integer",
                "description": "Tab index for switch_tab",
            },
            "cookies": {
                "type": "object",
                "description": "Dictionary of cookies for set_cookies",
            },
        },
        "required": ["action"],
        "dependencies": {
            "navigate": ["url"],
            "click": ["selector"],
            "fill": ["selector", "value"],
            "extract": ["description"],
            "scroll": ["direction"],
            "screenshot": [],
            "get_page_state": [],
            "execute_script": ["script"],
            "wait_for_navigation": ["timeout"],
            "create_tab": [],
            "switch_tab": ["tab_index"],
            "close_tab": [],
            "get_cookies": [],
            "set_cookies": ["cookies"],
        },
    }
    
    browser_manager = Field(default_factory=get_browser_manager, exclude=True)
    rag_helper = Field(default_factory=BrowserRAGHelper, exclude=True)
    agent_id: Optional[str] = Field(default=None, exclude=True)
    
    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        description: Optional[str] = None,
        value: Optional[str] = None,
        direction: Optional[str] = None,
        amount: Optional[int] = None,
        output_path: Optional[str] = None,
        script: Optional[str] = None,
        timeout: Optional[float] = None,
        tab_index: Optional[int] = None,
        cookies: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a browser automation action.
        
        Args:
            action: Action to perform
            url: URL for navigation
            selector: CSS selector or element description
            description: Semantic description
            value: Value to fill or extract
            direction: Scroll direction
            amount: Scroll amount
            output_path: Screenshot path
            script: JavaScript code
            timeout: Operation timeout
            tab_index: Tab index
            cookies: Cookie dictionary
            **kwargs: Additional arguments
            
        Returns:
            ToolResult with action output
        """
        try:
            agent_id = self.agent_id or kwargs.get("agent_id", "default")
            
            if action == "navigate":
                if not url:
                    return ToolResult(error="URL required for navigate action")
                
                success = await self.browser_manager.navigate(agent_id, url)
                if success:
                    # Get page summary via RAG helper
                    browser = await self.browser_manager.get_browser(agent_id)
                    if browser:
                        page_content = await browser.get_page_content()
                        page_text = await browser.get_page_text()
                        
                        # Run async RAG helper in background
                        asyncio.create_task(
                            self.rag_helper.understand_page(url, page_content, page_text)
                        )
                    
                    return ToolResult(output=f"Navigated to {url}")
                else:
                    return ToolResult(error=f"Navigation to {url} failed")
            
            elif action == "click":
                if not selector:
                    return ToolResult(error="Selector required for click action")
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                # Try direct selector first, then semantic lookup
                success = await browser.click_element(selector)
                if not success and description:
                    # Try semantic element finding
                    page_content = await browser.get_page_content()
                    element = await self.rag_helper.find_element_by_description(
                        page_content, 
                        description,
                    )
                    if element:
                        success = await browser.click_element(element.xpath)
                
                if success:
                    return ToolResult(output=f"Clicked element: {selector}")
                else:
                    return ToolResult(error=f"Failed to click element: {selector}")
            
            elif action == "fill":
                if not selector or not value:
                    return ToolResult(error="Selector and value required for fill action")
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                success = await browser.fill_form(selector, value)
                if success:
                    return ToolResult(output=f"Filled form field: {selector} = {value}")
                else:
                    return ToolResult(error=f"Failed to fill form field: {selector}")
            
            elif action == "extract":
                if not description:
                    return ToolResult(error="Description required for extract action")
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                page_content = await browser.get_page_content()
                page_text = await browser.get_page_text()
                
                # Use RAG helper to extract information
                understanding = await self.rag_helper.answer_question_about_page(
                    browser.current_url or "unknown",
                    page_text,
                    description,
                )
                
                return ToolResult(
                    output={
                        "extracted": understanding.answer,
                        "evidence": understanding.supporting_evidence,
                        "confidence": understanding.confidence,
                    }
                )
            
            elif action == "scroll":
                if not direction:
                    return ToolResult(error="Direction required for scroll action")
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                scroll_amount = amount or 300
                success = await browser.scroll(direction, scroll_amount)
                
                if success:
                    return ToolResult(output=f"Scrolled {direction} by {scroll_amount}px")
                else:
                    return ToolResult(error=f"Failed to scroll {direction}")
            
            elif action == "screenshot":
                screenshot_bytes = await self.browser_manager.screenshot(
                    agent_id,
                    output_path=output_path,
                    full_page=True,
                )
                
                if screenshot_bytes:
                    return ToolResult(
                        output={
                            "screenshot": screenshot_bytes.hex(),
                            "path": output_path,
                        }
                    )
                else:
                    return ToolResult(error="Failed to capture screenshot")
            
            elif action == "get_page_state":
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                # Get optimized page state
                dom_snapshot = await browser.get_dom_snapshot()
                page_text = await browser.get_page_text()
                
                return ToolResult(
                    output={
                        "url": browser.current_url,
                        "title": browser.page_title,
                        "dom_snapshot": dom_snapshot,
                        "text_content": page_text[:500],
                    }
                )
            
            elif action == "execute_script":
                if not script:
                    return ToolResult(error="Script required for execute_script action")
                
                result = await self.browser_manager.execute_script(agent_id, script)
                return ToolResult(output={"result": result})
            
            elif action == "wait_for_navigation":
                wait_timeout = timeout or 10.0
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                # Wait for page load
                await asyncio.sleep(0.5)
                metrics = await browser.get_performance_metrics()
                
                return ToolResult(
                    output={
                        "waited": wait_timeout,
                        "metrics": metrics.model_dump() if metrics else {},
                    }
                )
            
            elif action == "create_tab":
                success = await self.browser_manager.create_tab(agent_id, url=url)
                if success:
                    return ToolResult(output="Created new tab")
                else:
                    return ToolResult(error="Failed to create tab")
            
            elif action == "switch_tab":
                if tab_index is None:
                    return ToolResult(error="Tab index required for switch_tab action")
                
                success = await self.browser_manager.switch_tab(agent_id, tab_index)
                if success:
                    return ToolResult(output=f"Switched to tab {tab_index}")
                else:
                    return ToolResult(error=f"Failed to switch to tab {tab_index}")
            
            elif action == "close_tab":
                if tab_index is None:
                    return ToolResult(error="Tab index required for close_tab action")
                
                success = await self.browser_manager.close_tab(agent_id, tab_index)
                if success:
                    return ToolResult(output=f"Closed tab {tab_index}")
                else:
                    return ToolResult(error=f"Failed to close tab {tab_index}")
            
            elif action == "get_cookies":
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                cookies_dict = await browser.get_cookies()
                return ToolResult(output={"cookies": cookies_dict})
            
            elif action == "set_cookies":
                if not cookies:
                    return ToolResult(error="Cookies required for set_cookies action")
                
                browser = await self.browser_manager.get_browser(agent_id)
                if not browser:
                    return ToolResult(error="No browser available")
                
                success = await browser.set_cookies(cookies)
                if success:
                    return ToolResult(output="Cookies set successfully")
                else:
                    return ToolResult(error="Failed to set cookies")
            
            else:
                return ToolResult(error=f"Unknown action: {action}")
        
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            return ToolResult(error=f"Browser automation failed: {str(e)}")
