import asyncio
import base64
import json
from typing import Generic, Optional, TypeVar

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

import markdownify # Adicionado import
from app.config import config
from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch


_BROWSER_DESCRIPTION = """\
Your **PRIMARY tool for ALL web-related tasks** including: browsing, navigation, scraping, data extraction from websites, clicking elements, filling forms, and executing JavaScript.
* Use this to go to URLs, interact with page content, and extract information.
* Indispensable for modern, JavaScript-heavy websites.
* If the task is to 'scrape a website', 'get data from a URL', 'navigate a webpage', or 'view website content', **this tool should be your first choice.**
* It maintains state across calls (active browser session).
* Actions: go_to_url, click_element, input_text, scroll, extract_content, web_search (which then navigates to the first result), etc. See 'parameters' for full action list.
"""

Context = TypeVar("Context")


class BrowserUseTool(BaseTool, Generic[Context]):
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "go_to_url",
                    "click_element",
                    "input_text",
                    "scroll_down",
                    "scroll_up",
                    "scroll_to_text",
                    "send_keys",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "go_back",
                    "web_search",
                    "wait",
                    "extract_content",
                    "switch_tab",
                    "open_tab",
                    "close_tab",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'go_to_url' or 'open_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click_element', 'input_text', 'get_dropdown_options', or 'select_dropdown_option' actions",
            },
            "text": {
                "type": "string",
                "description": "Text for 'input_text', 'scroll_to_text', or 'select_dropdown_option' actions",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll_down' or 'scroll_up' actions",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
            "query": {
                "type": "string",
                "description": "Search query for 'web_search' action",
            },
            "goal": {
                "type": "string",
                "description": "Extraction goal for 'extract_content' action",
            },
            "keys": {
                "type": "string",
                "description": "Keys to send for 'send_keys' action",
            },
            "seconds": {
                "type": "integer",
                "description": "Seconds to wait for 'wait' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "go_to_url": ["url"],
            "click_element": ["index"],
            "input_text": ["index", "text"],
            "switch_tab": ["tab_id"],
            "open_tab": ["url"],
            "scroll_down": ["scroll_amount"],
            "scroll_up": ["scroll_amount"],
            "scroll_to_text": ["text"],
            "send_keys": ["keys"],
            "get_dropdown_options": ["index"],
            "select_dropdown_option": ["index", "text"],
            "go_back": [],
            "web_search": ["query"],
            "wait": ["seconds"],
            "extract_content": ["goal"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)
    web_search_tool: WebSearch = Field(default_factory=WebSearch, exclude=True)

    # Context for generic functionality
    tool_context: Optional[Context] = Field(default=None, exclude=True)

    llm: Optional[LLM] = Field(default_factory=LLM)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        logger.info(f"BrowserUseTool._ensure_browser_initialized: Current state - self.browser is {'None' if self.browser is None else 'Exists'}, self.context is {'None' if self.context is None else 'Exists'}")

        if self.browser is None:
            logger.info("BrowserUseTool._ensure_browser_initialized: self.browser is None, initializing BrowserUseBrowser.")
            browser_config_kwargs = {"headless": False, "disable_security": True}

            if config.browser_config:
                from browser_use.browser.browser import ProxySettings

                # handle proxy settings.
                if config.browser_config.proxy and config.browser_config.proxy.server:
                    browser_config_kwargs["proxy"] = ProxySettings(
                        server=config.browser_config.proxy.server,
                        username=config.browser_config.proxy.username,
                        password=config.browser_config.proxy.password,
                    )

                browser_attrs = [
                    "headless",
                    "disable_security",
                    "extra_chromium_args",
                    "chrome_instance_path",
                    "wss_url",
                    "cdp_url",
                ]

                for attr in browser_attrs:
                    value = getattr(config.browser_config, attr, None)
                    if value is not None:
                        # Ensure that list arguments are not empty if provided
                        if isinstance(value, list) and not value:
                            logger.info(f"BrowserUseTool._ensure_browser_initialized: Skipping empty list for {attr}")
                            continue
                        browser_config_kwargs[attr] = value
                logger.info(f"BrowserUseTool._ensure_browser_initialized: BrowserConfig kwargs: {browser_config_kwargs}")

            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))
            logger.info("BrowserUseTool._ensure_browser_initialized: BrowserUseBrowser initialized.")

        if self.context is None:
            logger.info("BrowserUseTool._ensure_browser_initialized: self.context is None, creating new context.")
            context_config = BrowserContextConfig()

            # if there is context config in the config, use it.
            if (
                config.browser_config
                and hasattr(config.browser_config, "new_context_config")
                and config.browser_config.new_context_config
            ):
                context_config = config.browser_config.new_context_config
                logger.info("BrowserUseTool._ensure_browser_initialized: Using custom new_context_config.")
            else:
                logger.info("BrowserUseTool._ensure_browser_initialized: Using default BrowserContextConfig.")

            self.context = await self.browser.new_context(context_config)
            logger.info("BrowserUseTool._ensure_browser_initialized: New context created.")
            # Ensure DomService is initialized only after a page is available
            try:
                current_page = await self.context.get_current_page()
                if current_page:
                    self.dom_service = DomService(current_page)
                    logger.info("BrowserUseTool._ensure_browser_initialized: DomService initialized with current page.")
                else:
                    logger.warning("BrowserUseTool._ensure_browser_initialized: Could not get current page to initialize DomService.")
                    self.dom_service = None # Explicitly set to None
            except Exception as e:
                logger.error(f"BrowserUseTool._ensure_browser_initialized: Error getting current page or initializing DomService: {e}")
                self.dom_service = None # Explicitly set to None


        # Ensure logger is imported if not already: from app.logger import logger
        # Ensure BrowserUseBrowser, BrowserConfig, BrowserContext, BrowserContextConfig, DomService are imported from browser_use
        # Ensure config is imported: from app.config import config
        # These imports should already be there, this is just a reminder.
        return self.context

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        tab_id: Optional[int] = None,
        query: Optional[str] = None,
        goal: Optional[str] = None,
        keys: Optional[str] = None,
        seconds: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action.

        Args:
            action: The browser action to perform
            url: URL for navigation or new tab
            index: Element index for click or input actions
            text: Text for input action or search query
            scroll_amount: Pixels to scroll for scroll action
            tab_id: Tab ID for switch_tab action
            query: Search query for Google search
            goal: Extraction goal for content extraction
            keys: Keys to send for keyboard actions
            seconds: Seconds to wait
            **kwargs: Additional arguments

        Returns:
            ToolResult with the action's output or error
        """
        async with self.lock:
            try:
                context = await self._ensure_browser_initialized()

                # Get max content length from config
                max_content_length = getattr(
                    config.browser_config, "max_content_length", 2000
                )

                # Navigation actions
                if action == "go_to_url":
                    if not url:
                        return ToolResult(
                            error="URL is required for 'go_to_url' action"
                        )
                    if not url:
                        return ToolResult(
                            error="URL is required for 'go_to_url' action"
                        )
                    try:
                        page = await context.get_current_page()
                        await page.goto(url)
                        await page.wait_for_load_state()
                        return ToolResult(output=f"Navigated to {url}")
                    except asyncio.TimeoutError as e:
                        return ToolResult(error=f"Timeout durante navegação para {url}: {str(e)}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao navegar para {url}: {str(e)}")

                elif action == "go_back":
                    try:
                        await context.go_back()
                        return ToolResult(output="Navigated back")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao navegar para trás: {str(e)}")

                elif action == "refresh":
                    try:
                        await context.refresh_page()
                        return ToolResult(output="Refreshed current page")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao atualizar a página: {str(e)}")

                elif action == "web_search":
                    if not query:
                        return ToolResult(
                            error="Query is required for 'web_search' action"
                        )
                    try:
                        # Execute the web search and return results directly without browser navigation
                        search_response = await self.web_search_tool.execute(
                            query=query, fetch_content=True, num_results=1
                        )
                        if not search_response.results:
                             return ToolResult(error=f"Nenhum resultado encontrado para a busca: {query}")
                        # Navigate to the first search result
                        first_search_result = search_response.results[0]
                        url_to_navigate = first_search_result.url

                        page = await context.get_current_page()
                        await page.goto(url_to_navigate)
                        await page.wait_for_load_state()
                        return search_response # Retorna o SearchResponse completo
                    except asyncio.TimeoutError as e:
                        return ToolResult(error=f"Timeout durante web_search e navegação para resultado: {str(e)}")
                    except Exception as e:
                        return ToolResult(error=f"Erro durante web_search e navegação: {str(e)}")

                # Element interaction actions
                elif action == "click_element":
                    if index is None:
                        return ToolResult(
                            error="Index is required for 'click_element' action"
                        )
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                        download_path = await context._click_element_node(element)
                        output = f"Clicked element at index {index}"
                        if download_path:
                            output += f" - Downloaded file to {download_path}"
                        return ToolResult(output=output)
                    except Exception as e:
                        return ToolResult(error=f"Erro ao clicar no elemento no índice {index}: {str(e)}")

                elif action == "input_text":
                    if index is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'input_text' action"
                        )
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                        await context._input_text_element_node(element, text)
                        return ToolResult(
                            output=f"Input '{text}' into element at index {index}"
                        )
                    except Exception as e:
                        return ToolResult(error=f"Erro ao inserir texto no elemento no índice {index}: {str(e)}")

                elif action == "scroll_down" or action == "scroll_up":
                    try:
                        direction = 1 if action == "scroll_down" else -1
                        amount = (
                            scroll_amount
                            if scroll_amount is not None
                            else context.config.browser_window_size["height"]
                        )
                        await context.execute_javascript(
                            f"window.scrollBy(0, {direction * amount});"
                        )
                        return ToolResult(
                            output=f"Scrolled {'down' if direction > 0 else 'up'} by {amount} pixels"
                        )
                    except Exception as e:
                        return ToolResult(error=f"Erro ao rolar a página: {str(e)}")

                elif action == "scroll_to_text":
                    if not text:
                        return ToolResult(
                            error="Text is required for 'scroll_to_text' action"
                        )
                    try:
                        page = await context.get_current_page()
                        locator = page.get_by_text(text, exact=False)
                        await locator.scroll_into_view_if_needed()
                        return ToolResult(output=f"Scrolled to text: '{text}'")
                    except asyncio.TimeoutError as e:
                        return ToolResult(error=f"Timeout ao rolar para o texto '{text}': {str(e)}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao rolar para o texto '{text}': {str(e)}")

                elif action == "send_keys":
                    if not keys:
                        return ToolResult(
                            error="Keys are required for 'send_keys' action"
                        )
                    try:
                        page = await context.get_current_page()
                        await page.keyboard.press(keys)
                        return ToolResult(output=f"Sent keys: {keys}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao enviar teclas '{keys}': {str(e)}")

                elif action == "get_dropdown_options":
                    if index is None:
                        return ToolResult(
                            error="Index is required for 'get_dropdown_options' action"
                        )
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                        page = await context.get_current_page()
                        options = await page.evaluate(
                            """
                            (xpath) => {
                                const select = document.evaluate(xpath, document, null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (!select) return null;
                            return Array.from(select.options).map(opt => ({
                                text: opt.text,
                                value: opt.value,
                                index: opt.index
                            }));
                        }
                        """,
                            element.xpath,
                        )
                        return ToolResult(output=f"Dropdown options: {options}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao obter opções do dropdown no índice {index}: {str(e)}")

                elif action == "select_dropdown_option":
                    if index is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'select_dropdown_option' action"
                        )
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                        page = await context.get_current_page()
                        await page.select_option(element.xpath, label=text)
                        return ToolResult(
                            output=f"Selected option '{text}' from dropdown at index {index}"
                        )
                    except Exception as e:
                        return ToolResult(error=f"Erro ao selecionar opção '{text}' do dropdown no índice {index}: {str(e)}")

                # Content extraction actions
                elif action == "extract_content":
                    if not goal:
                        return ToolResult(
                            error="Goal is required for 'extract_content' action"
                        )
                    try: # Try principal da ação
                        page = await context.get_current_page()
                        # import markdownify # Movido para o topo do arquivo

                        # Bloco interno para obter conteúdo da página, com seu próprio try-except
                        try:
                            page_content_html = await page.content()
                            content = markdownify.markdownify(page_content_html) # Assumindo que markdownify está importado no topo
                        except Exception as page_err:
                            logger.error(f"Erro ao obter/converter conteúdo da página: {page_err}")
                            return ToolResult(error=f"Erro ao processar conteúdo da página: {str(page_err)}")

                        prompt = f"""\
Your task is to extract the content of the page. You will be given a page and a goal, and you should extract all relevant information around this goal from the page. If the goal is vague, summarize the page. Respond in json format.
Extraction goal: {goal}

Page content:
{content[:max_content_length]}
"""
                        messages = [{"role": "system", "content": prompt}]

                        extraction_function = {
                            "type": "function",
                            "function": {
                                "name": "extract_content",
                                "description": "Extract specific information from a webpage based on a goal",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "extracted_content": {
                                            "type": "object",
                                            "description": "The content extracted from the page according to the goal",
                                            "properties": {
                                                "text": {
                                                    "type": "string",
                                                    "description": "Text content extracted from the page",
                                                },
                                                "metadata": {
                                                    "type": "object",
                                                    "description": "Additional metadata about the extracted content",
                                                    "properties": {
                                                        "source": {
                                                            "type": "string",
                                                            "description": "Source of the extracted content",
                                                        }
                                                    },
                                                },
                                            },
                                        }
                                    },
                                    "required": ["extracted_content"],
                                },
                            },
                        }

                        response = await self.llm.ask_tool(
                            messages,
                            tools=[extraction_function],
                            tool_choice="required",
                        )

                        if response and response.tool_calls:
                            args = json.loads(response.tool_calls[0].function.arguments)
                            extracted_content = args.get("extracted_content", {})
                            return ToolResult(
                                output=f"Extracted from page:\n{extracted_content}\n"
                            )

                        return ToolResult(output="No content was extracted from the page.")

                    except asyncio.TimeoutError as e:
                        logger.error(f"Timeout durante a extração de conteúdo para o objetivo '{goal}': {str(e)}")
                        return ToolResult(error=f"Timeout durante a extração de conteúdo para o objetivo '{goal}': {str(e)}")
                    except Exception as e:
                        logger.error(f"Erro ao extrair conteúdo para o objetivo '{goal}': {str(e)}")
                        return ToolResult(error=f"Erro ao extrair conteúdo para o objetivo '{goal}': {str(e)}")

                # Tab management actions
                elif action == "switch_tab":
                    if tab_id is None:
                        return ToolResult(
                            error="Tab ID is required for 'switch_tab' action"
                        )
                    try:
                        await context.switch_to_tab(tab_id)
                        page = await context.get_current_page()
                        await page.wait_for_load_state()
                        return ToolResult(output=f"Switched to tab {tab_id}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao trocar para a aba {tab_id}: {str(e)}")

                elif action == "open_tab":
                    if not url:
                        return ToolResult(error="URL is required for 'open_tab' action")
                    try:
                        await context.create_new_tab(url)
                        return ToolResult(output=f"Opened new tab with {url}")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao abrir nova aba com URL {url}: {str(e)}")

                elif action == "close_tab":
                    try:
                        await context.close_current_tab()
                        return ToolResult(output="Closed current tab")
                    except Exception as e:
                        return ToolResult(error=f"Erro ao fechar a aba atual: {str(e)}")

                # Utility actions
                elif action == "wait":
                    try:
                        seconds_to_wait = seconds if seconds is not None else 3
                        await asyncio.sleep(seconds_to_wait)
                        return ToolResult(output=f"Waited for {seconds_to_wait} seconds")
                    except Exception as e: # Embora improvável para asyncio.sleep, por consistência
                        return ToolResult(error=f"Erro durante a ação 'wait': {str(e)}")
                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except asyncio.TimeoutError as e_timeout:
                logger.error(f"Playwright/Asyncio TimeoutError em BrowserUseTool action '{action}': {e_timeout}")
                return ToolResult(error=f"Timeout na ação do navegador '{action}': {str(e_timeout)}")
            except Exception as e_general:
                # Este é um catch-all para erros inesperados não capturados nos blocos internos
                # ou erros na inicialização/validação antes dos blocos de ação.
                logger.error(f"Exceção geral em BrowserUseTool action '{action}': {e_general}")
                return ToolResult(error=f"Falha geral na ação do navegador '{action}': {str(e_general)}")

    async def get_current_state(
        self, context: Optional[BrowserContext] = None
    ) -> ToolResult:
        """
        Get the current browser state as a ToolResult.
        If context is not provided, uses self.context.
        """
        try:
            # Use provided context or fall back to self.context
            ctx = context or self.context
            if not ctx:
                return ToolResult(error="Browser context not initialized")

            state = await ctx.get_state()

            # Create a viewport_info dictionary if it doesn't exist
            viewport_height = 0
            if hasattr(state, "viewport_info") and state.viewport_info:
                viewport_height = state.viewport_info.height
            elif hasattr(ctx, "config") and hasattr(ctx.config, "browser_window_size"):
                viewport_height = ctx.config.browser_window_size.get("height", 0)

            # Take a screenshot for the state
            page = await ctx.get_current_page()

            await page.bring_to_front()
            await page.wait_for_load_state()

            screenshot = await page.screenshot(
                full_page=True, animations="disabled", type="jpeg", quality=100
            )

            screenshot = base64.b64encode(screenshot).decode("utf-8")

            # Build the state info with all required fields
            state_info = {
                "url": state.url,
                "title": state.title,
                "tabs": [tab.model_dump() for tab in state.tabs],
                "help": "[0], [1], [2], etc., represent clickable indices corresponding to the elements listed. Clicking on these indices will navigate to or interact with the respective content behind them.",
                "interactive_elements": (
                    state.element_tree.clickable_elements_to_string()
                    if state.element_tree
                    else ""
                ),
                "scroll_info": {
                    "pixels_above": getattr(state, "pixels_above", 0),
                    "pixels_below": getattr(state, "pixels_below", 0),
                    "total_height": getattr(state, "pixels_above", 0)
                    + getattr(state, "pixels_below", 0)
                    + viewport_height,
                },
                "viewport_height": viewport_height,
            }

            return ToolResult(
                output=json.dumps(state_info, indent=4, ensure_ascii=False),
                base64_image=screenshot,
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self):
        """Clean up browser resources."""
        async with self.lock:
            if self.context is not None:
                try:
                    await self.context.close()
                    logger.info("BrowserUseTool: Context closed successfully.")
                except Exception as e:
                    logger.warning(f"BrowserUseTool: Error closing context: {e}. It might have been already closed.")
                finally:
                    self.context = None
                    self.dom_service = None # Ensure dom_service is also cleared
            else:
                logger.info("BrowserUseTool: Context was already None, no action taken.")

            if self.browser is not None:
                try:
                    await self.browser.close()
                    logger.info("BrowserUseTool: Browser closed successfully.")
                except Exception as e:
                    logger.warning(f"BrowserUseTool: Error closing browser: {e}. It might have been already closed.")
                finally:
                    self.browser = None
            else:
                logger.info("BrowserUseTool: Browser was already None, no action taken.")

    def __del__(self):
        """Ensure cleanup when object is destroyed.
        Note: Running asyncio code within __del__ can be problematic due to
        uncertainty about the state of the event loop, especially during
        interpreter shutdown or if called from different threads.
        The robustness of the `cleanup` method itself is key here.
        """
        # Check if cleanup is even necessary
        if self.browser is not None or self.context is not None:
            try:
                # Attempt to run cleanup using asyncio.run()
                # This will create a new event loop if one isn't running.
                asyncio.run(self.cleanup())
            except RuntimeError as e:
                # This typically means an event loop is already running in the current thread.
                # It's complex to reliably get and use the existing loop here,
                # or to know if it's the 'right' one for this cleanup.
                # Creating a new loop is a common fallback but has its own issues.
                # The warning below uses print as logger might also be in an uncertain state.
                print(f"WARNING: BrowserUseTool.__del__: RuntimeError during cleanup (possibly due to existing event loop): {e}")
                print("WARNING: BrowserUseTool.__del__: Attempting cleanup in a new event loop as a fallback.")
                new_loop = None
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(self.cleanup())
                except Exception as e_new_loop:
                    print(f"ERROR: BrowserUseTool.__del__: Error during cleanup in new event loop: {e_new_loop}")
                finally:
                    if new_loop:
                        new_loop.close()
                    # It's important to restore the original event loop policy if changed.
                    # However, set_event_loop(None) after closing the current loop is standard.
                    # If another loop was previously set for this thread, this might disrupt it.
                    # This is part of why __del__ with asyncio is tricky.
                    asyncio.set_event_loop(None) # Resets the current event loop for the OS thread to None
            except Exception as e:
                # Catch any other unexpected errors during the cleanup attempt.
                print(f"ERROR: BrowserUseTool.__del__: Unexpected error during cleanup: {e}")
        # else:
            # print("DEBUG: BrowserUseTool.__del__: Cleanup not necessary, browser and context are None.")

    @classmethod
    def create_with_context(cls, context: Context) -> "BrowserUseTool[Context]":
        """Factory method to create a BrowserUseTool with a specific context."""
        tool = cls()
        tool.tool_context = context
        return tool
