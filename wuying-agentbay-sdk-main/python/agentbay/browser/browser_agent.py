import json, asyncio
from typing import List, Dict, Union, Any, Optional, Tuple, TypeVar, Generic, Type
from pydantic import BaseModel
from agentbay.api.base_service import BaseService, OperationResult
from agentbay.exceptions import BrowserError, AgentBayError
from agentbay.logger import get_logger

logger = get_logger("browser_agent")

T = TypeVar("T", bound=BaseModel)


class ActOptions:
    """
    Options for configuring the behavior of the act method.
    """

    def __init__(
        self,
        action: str,
        timeoutMS: Optional[int] = None,
        iframes: Optional[bool] = None,
        dom_settle_timeout_ms: Optional[int] = None,
        variables: Optional[Dict[str, str]] = None,
        use_vision: Optional[bool] = None,
    ):
        self.action = action
        self.timeoutMS = timeoutMS
        self.iframes = iframes
        self.dom_settle_timeout_ms = dom_settle_timeout_ms
        self.variables = variables
        self.use_vision = use_vision


class ActResult:
    """
    Result of the act method.
    """

    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message


class ObserveOptions:
    """
    Options for configuring the behavior of the observe method.
    """

    def __init__(
        self,
        instruction: str,
        iframes: Optional[bool] = None,
        dom_settle_timeout_ms: Optional[int] = None,
        use_vision: Optional[bool] = None,
    ):
        self.instruction = instruction
        self.iframes = iframes
        self.dom_settle_timeout_ms = dom_settle_timeout_ms
        self.use_vision = use_vision


class ObserveResult:
    """
    Result of the observe method.
    """

    def __init__(self, selector: str, description: str, method: str, arguments: dict):
        self.selector = selector
        self.description = description
        self.method = method
        self.arguments = arguments


class ExtractOptions(Generic[T]):
    """
    Options for configuring the behavior of the extract method.
    """

    def __init__(
        self,
        instruction: str,
        schema: Type[T],
        use_text_extract: Optional[bool] = None,
        selector: Optional[str] = None,
        iframe: Optional[bool] = None,
        dom_settle_timeout_ms: Optional[int] = None,
        use_vision: Optional[bool] = None,
    ):
        self.instruction = instruction
        self.schema = schema
        self.use_text_extract = use_text_extract
        self.selector = selector
        self.iframe = iframe
        self.dom_settle_timeout_ms = dom_settle_timeout_ms
        self.use_vision = use_vision


class BrowserAgent(BaseService):
    """
    BrowserAgent handles browser automation and agent logic.
    """

    def __init__(self, session, browser):
        self.session = session
        self.browser = browser

    async def navigate_async(self, url: str) -> str:
        """
        Navigates a specific page to the given URL.

        Args:
            url: The URL to navigate to.

        Returns:
            A string indicating the result of the navigation.
        """
        if not self.browser.is_initialized():
            raise BrowserError(
                "Browser must be initialized before calling navigate_async."
            )
        try:
            args = {"url": url}
            response = self._call_mcp_tool_timeout("page_use_navigate", args)
            if response.success:
                return response.data
            else:
                return f"Navigation failed: {response.error_message}"
        except Exception as e:
            raise BrowserError(f"Failed to navigate: {e}")

    def screenshot(
        self,
        page=None,
        full_page: bool = True,
        quality: int = 80,
        clip: Optional[Dict[str, float]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Takes a screenshot of the specified page.

        Args:
            page (Optional[Page]): The Playwright Page object to take a screenshot of. If None,
                                   the agent's currently focused page will be used.
            full_page (bool): Whether to capture the full scrollable page.
            quality (int): The quality of the image (0-100), for JPEG format.
            clip (Optional[Dict[str, float]]): An object specifying the clipping region {x, y, width, height}.
            timeout (Optional[int]): Custom timeout for the operation in milliseconds.

        Returns:
            str: A base64 encoded data URL of the screenshot, or an error message.
        """
        if not self.browser.is_initialized():
            raise BrowserError("Browser must be initialized before calling screenshot.")
        try:
            page_id, context_id = self._get_page_and_context_index(page)
            return asyncio.get_event_loop().run_until_complete(
                self._execute_screenshot(
                    context_id, page_id, full_page, quality, clip, timeout
                )
            )
        except Exception as e:
            raise BrowserError(f"Failed to call screenshot: {e}") from e

    async def screenshot_async(
        self,
        page=None,
        full_page: bool = True,
        quality: int = 80,
        clip: Optional[Dict[str, float]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Asynchronously takes a screenshot of the specified page.

        Args:
            page (Optional[Page]): The Playwright Page object to take a screenshot of. If None,
                                   the agent's currently focused page will be used.
            full_page (bool): Whether to capture the full scrollable page.
            quality (int): The quality of the image (0-100), for JPEG format.
            clip (Optional[Dict[str, float]]): An object specifying the clipping region {x, y, width, height}.
            timeout (Optional[int]): Custom timeout for the operation in milliseconds.

        Returns:
            str: A base64 encoded data URL of the screenshot, or an error message.
        """
        if not self.browser.is_initialized():
            raise BrowserError(
                "Browser must be initialized before calling screenshot_async."
            )
        try:
            page_id, context_id = await self._get_page_and_context_index_async(page)
            return await self._execute_screenshot(
                context_id, page_id, full_page, quality, clip, timeout
            )
        except Exception as e:
            raise BrowserError(f"Failed to call screenshot_async: {e}") from e

    async def _execute_screenshot(
        self,
        context_id: int,
        page_id: Optional[str] = None,
        full_page: bool = True,
        quality: int = 80,
        clip: Optional[Dict[str, float]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        logger.debug(f"Screenshot page_id: {page_id}, context_id: {context_id}")
        args = {
            "context_id": context_id,
            "page_id": page_id,
            "full_page": full_page,
            "quality": quality,
            "clip": clip,
            "timeout": timeout,
        }
        args = {k: v for k, v in args.items() if v is not None}

        response = self._call_mcp_tool_timeout("page_use_screenshot", args)
        if response.success:
            return response.data
        else:
            return f"Screenshot failed: {response.error_message}"

    async def close_async(self) -> bool:
        """
        Asynchronously closes the remote browser agent session.
        This will terminate the browser process managed by the agent.
        """
        try:
            response = self._call_mcp_tool_timeout("page_use_close_session", args={})
            if response.success:
                logger.info(f"Session close status: {response.data}")
                return True
            else:
                logger.warning(f"Failed to close session: {response.error_message}")
                return False
        except Exception as e:
            raise BrowserError(f"Failed to call close_async: {e}") from e

    def act(
        self,
        action_input: Union[ObserveResult, ActOptions],
        page=None,
    ) -> "ActResult":
        """
        Perform an action on a web page, using ActOptions to configure behavior.

        Args:
            page (Optional[Page]): The Playwright Page object to act on. If None, the agent's
                                   currently focused page will be used automatically.
            action_input (Union[ObserveResult, ActOptions]): The action to perform, either as a
                                                             pre-defined ObserveResult or custom ActOptions.
        Returns:
            ActResult: The result of the action.
        """
        if not self.browser.is_initialized():
            raise BrowserError("Browser must be initialized before calling act.")
        try:
            page_id, context_id = self._get_page_and_context_index(page)
            return asyncio.get_event_loop().run_until_complete(
                self._execute_act_async(action_input, context_id, page_id)
            )
        except Exception as e:
            raise BrowserError(f"Failed to act: {e}")

    async def act_async(
        self,
        action_input: Union[ObserveResult, ActOptions],
        page=None,
    ) -> "ActResult":
        """
        Asynchronously perform an action on a web page.

        Args:
            page (Optional[Page]): The Playwright Page object to act on. If None, the agent's
                                   currently focused page will be used automatically.
            action_input (Union[ObserveResult, ActOptions]): The action to perform.

        Returns:
            ActResult: The result of the action.
        """
        if not self.browser.is_initialized():
            raise BrowserError("Browser must be initialized before calling act_async.")
        try:
            page_id, context_id = await self._get_page_and_context_index_async(page)
            return await self._execute_act_async(action_input, context_id, page_id)
        except Exception as e:
            raise BrowserError(f"Failed to act: {e}")

    async def _execute_act(
        self,
        action_input: Union[ObserveResult, ActOptions],
        context_id: int,
        page_id: Optional[str],
    ) -> "ActResult":
        logger.debug(f"Acting page_id: {page_id}, context_id: {context_id}")
        args = {
            "context_id": context_id,
            "page_id": page_id,
        }
        if isinstance(action_input, ActOptions):
            args.update(
                {
                    "action": action_input.action,
                    "variables": action_input.variables,
                    "timeout_ms": action_input.timeoutMS,
                    "iframes": action_input.iframes,
                    "dom_settle_timeout_ms": action_input.dom_settle_timeout_ms,
                    "use_vision": action_input.use_vision,
                }
            )
            task_name = action_input.action
        elif isinstance(action_input, ObserveResult):
            action_dict = {
                "method": action_input.method,
                "arguments": (
                    json.loads(action_input.arguments)
                    if isinstance(action_input.arguments, str)
                    else action_input.arguments
                ),
            }
            args["action"] = json.dumps(action_dict)
            task_name = action_input.method
        args = {k: v for k, v in args.items() if v is not None}
        logger.info(f"{task_name}")

        response = self._call_mcp_tool_timeout("page_use_act", args)
        if response.success and response.data:
            data = (
                response.data
                if isinstance(response.data, str)
                else json.dumps(response.data, ensure_ascii=False)
            )
            logger.info(f"{task_name} response data: {data}")
            return ActResult(success=True, message=data)
        else:
            return ActResult(success=False, message=response.error_message)

    async def _execute_act_async(
        self,
        action_input: Union[ObserveResult, ActOptions],
        context_id: int,
        page_id: Optional[str],
    ) -> "ActResult":
        logger.debug(f"Acting page_id: {page_id}, context_id: {context_id}")
        args = {
            "context_id": context_id,
            "page_id": page_id,
        }
        if isinstance(action_input, ActOptions):
            args.update(
                {
                    "action": action_input.action,
                    "variables": action_input.variables,
                    "timeout_ms": action_input.timeoutMS,
                    "iframes": action_input.iframes,
                    "dom_settle_timeout_ms": action_input.dom_settle_timeout_ms,
                    "use_vision": action_input.use_vision,
                }
            )
            task_name = action_input.action
        elif isinstance(action_input, ObserveResult):
            action_dict = {
                "method": action_input.method,
                "arguments": (
                    json.loads(action_input.arguments)
                    if isinstance(action_input.arguments, str)
                    else action_input.arguments
                ),
            }
            args["action"] = json.dumps(action_dict)
            task_name = action_input.method
        args = {k: v for k, v in args.items() if v is not None}
        logger.info(f"{task_name}")

        response = self._call_mcp_tool_timeout("page_use_act_async", args)
        if not response.success:
            raise BrowserError("Failed to start act task")

        task_id = json.loads(response.data)["task_id"]
        max_retries = 30

        while max_retries > 0:
            await asyncio.sleep(5)
            if hasattr(self, "mcp_client") and self.mcp_client:
                result = await self._call_mcp_tool_async(
                    "page_use_get_act_result", {"task_id": task_id}
                )
            else:
                result = self._call_mcp_tool_timeout(
                    "page_use_get_act_result", {"task_id": task_id}
                )
            if result.success and result.data:
                data = (
                    json.loads(result.data)
                    if isinstance(result.data, str)
                    else result.data
                )
                steps = data.get("steps", [])
                is_done = data.get("is_done", False)
                success = bool(data.get("success", False))
                no_action_msg = "No actions have been executed."
                if is_done:
                    if steps:
                        task_status = (
                            steps
                            if isinstance(steps, str)
                            else json.dumps(steps, ensure_ascii=False)
                        )
                    else:
                        task_status = no_action_msg
                    logger.info(
                        f"Task {task_id}:{task_name} is done. Success: {success}. {task_status}"
                    )
                    return ActResult(success=success, message=task_status)
                task_status = (
                    f"{len(steps)} steps done. Details: {steps}"
                    if steps
                    else no_action_msg
                )
                logger.info(f"Task {task_id}:{task_name} in progress. {task_status}")
            max_retries -= 1
        raise BrowserError(f"Task {task_id}:{task_name} Act timed out")

    def observe(
        self,
        options: ObserveOptions,
        page=None,
    ) -> Tuple[bool, List[ObserveResult]]:
        """
        Observe elements or state on a web page.

        Args:
            page (Optional[Page]): The Playwright Page object to observe. If None, the agent's
                                   currently focused page will be used.
            options (ObserveOptions): Options to configure the observation behavior.

        Returns:
            Tuple[bool, List[ObserveResult]]: A tuple containing a success boolean and a list
                                              of observation results.
        """
        if not self.browser.is_initialized():
            raise BrowserError("Browser must be initialized before calling observe.")
        try:
            page_id, context_id = self._get_page_and_context_index(page)
            return asyncio.get_event_loop().run_until_complete(
                self._execute_observe(options, context_id, page_id)
            )
        except Exception as e:
            raise BrowserError(f"Failed to observe: {e}")

    async def observe_async(
        self,
        options: ObserveOptions,
        page=None,
    ) -> Tuple[bool, List[ObserveResult]]:
        """
        Asynchronously observe elements or state on a web page.

        Args:
            page (Optional[Page]): The Playwright Page object to observe. If None, the agent's
                                   currently focused page will be used.
            options (ObserveOptions): Options to configure the observation behavior.

        Returns:
            Tuple[bool, List[ObserveResult]]: A tuple containing a success boolean and a list
                                              of observation results.
        """
        if not self.browser.is_initialized():
            raise BrowserError(
                "Browser must be initialized before calling observe_async."
            )
        try:
            page_id, context_id = await self._get_page_and_context_index_async(page)
            return await self._execute_observe(options, context_id, page_id)
        except Exception as e:
            raise BrowserError(f"Failed to observe_async: {e}")

    async def _execute_observe(
        self,
        options: ObserveOptions,
        context_id: int,
        page_id: Optional[str],
    ) -> Tuple[bool, List[ObserveResult]]:
        logger.debug(f"Observing page_id: {page_id}, context_id: {context_id}")
        args = {
            "context_id": context_id,
            "page_id": page_id,
            "instruction": options.instruction,
            "iframes": options.iframes,
            "dom_settle_timeout_ms": options.dom_settle_timeout_ms,
            "use_vision": options.use_vision,
        }
        args = {k: v for k, v in args.items() if v is not None}

        response = self._call_mcp_tool_timeout("page_use_observe", args)

        if not response.success or not response.data:
            logger.warning(f"Failed to execute observe: {response.error_message}")
            return False, []

        data = (
            json.loads(response.data)
            if isinstance(response.data, str)
            else response.data
        )
        logger.info(f"observe results: {data}")
        results = []
        for item in data:
            selector = item.get("selector", "")
            description = item.get("description", "")
            method = item.get("method", "")
            arguments_str = item.get("arguments", "{}")
            try:
                arguments_dict = json.loads(arguments_str)
            except json.JSONDecodeError:
                logger.warning(
                    f"Warning: Could not parse arguments as JSON: {arguments_str}"
                )
                arguments_dict = arguments_str
            results.append(ObserveResult(selector, description, method, arguments_dict))

        return True, results

    def extract(self, options: ExtractOptions, page=None) -> Tuple[bool, T]:
        """
        Extract information from a web page.

        Args:
            page (Optional[Page]): The Playwright Page object to extract from. If None, the agent's
                                   currently focused page will be used.
            options (ExtractOptions): Options to configure the extraction, including schema.

        Returns:
            Tuple[bool, T]: A tuple containing a success boolean and the extracted data as a
                            Pydantic model instance, or None on failure.
        """
        if not self.browser.is_initialized():
            raise BrowserError("Browser must be initialized before calling extract.")
        try:
            page_id, context_id = self._get_page_and_context_index(page)
            return asyncio.get_event_loop().run_until_complete(
                self._execute_extract_async(options, context_id, page_id)
            )
        except Exception as e:
            raise BrowserError(f"Failed to extract: {e}")

    async def extract_async(
        self,
        options: ExtractOptions,
        page=None,
    ) -> Tuple[bool, T]:
        """
        Asynchronously extract information from a web page.

        Args:
            page (Optional[Page]): The Playwright Page object to extract from. If None, the agent's
                                   currently focused page will be used.
            options (ExtractOptions): Options to configure the extraction, including schema.

        Returns:
            Tuple[bool, T]: A tuple containing a success boolean and the extracted data as a
                            Pydantic model instance, or None on failure.
        """
        if not self.browser.is_initialized():
            raise BrowserError(
                "Browser must be initialized before calling extract  _async."
            )
        try:
            page_id, context_id = await self._get_page_and_context_index_async(page)
            return await self._execute_extract_async(options, context_id, page_id)
        except Exception as e:
            raise BrowserError(f"Failed to extract_async: {e}")

    async def _execute_extract(
        self,
        options: ExtractOptions,
        context_id: int,
        page_id: Optional[str],
    ) -> Tuple[bool, T]:
        args = {
            "context_id": context_id,
            "page_id": page_id,
            "instruction": options.instruction,
            "field_schema": "schema: " + json.dumps(options.schema.model_json_schema()),
            "use_text_extract": options.use_text_extract,
            "use_vision": options.use_vision,
            "selector": options.selector,
            "iframe": options.iframe,
            "dom_settle_timeout_ms": options.dom_settle_timeout_ms,
        }
        args = {k: v for k, v in args.items() if v is not None}
        logger.debug(
            f"Extracting page_id: {page_id}, context_id: {context_id}, args: {args}"
        )

        response = self._call_mcp_tool_timeout("page_use_extract", args)

        if response.success and response.data:
            extract_result = (
                json.loads(response.data)
                if isinstance(response.data, str)
                else response.data
            )
            logger.info(f"extract result: {extract_result}")
            return True, options.schema.model_validate(extract_result)
        else:
            logger.warning(f"Faild to execute extract: {response.error_message}")
            return False, None

    async def _execute_extract_async(
        self,
        options: ExtractOptions,
        context_id: int,
        page_id: Optional[str],
    ) -> Tuple[bool, T]:
        args = {
            "context_id": context_id,
            "page_id": page_id,
            "instruction": options.instruction,
            "field_schema": "schema: " + json.dumps(options.schema.model_json_schema()),
            "use_text_extract": options.use_text_extract,
            "use_vision": options.use_vision,
            "selector": options.selector,
            "iframe": options.iframe,
            "dom_settle_timeout_ms": options.dom_settle_timeout_ms,
        }
        args = {k: v for k, v in args.items() if v is not None}

        response = self._call_mcp_tool_timeout("page_use_extract_async", args)
        if not response.success:
            raise BrowserError("Failed to start extraction task")

        task_id = json.loads(response.data)["task_id"]
        max_retries = 20

        while max_retries > 0:
            await asyncio.sleep(8)

            if hasattr(self, "mcp_client") and self.mcp_client:
                result = await self._call_mcp_tool_async(
                    "page_use_get_extract_result", {"task_id": task_id}
                )
            else:
                result = self._call_mcp_tool_timeout(
                    "page_use_get_extract_result", {"task_id": task_id}
                )
            if result.success and result.data:
                extract_result = (
                    json.loads(result.data)
                    if isinstance(result.data, str)
                    else result.data
                )
                return True, options.schema.model_validate(extract_result)
            max_retries -= 1
            logger.debug(
                f"Task {task_id}: No extract result yet (attempt {20 - max_retries}/20)"
            )

        raise BrowserError(f"Task {task_id}: Extract timed out")

    def _get_page_and_context_index(self, page):
        """
        Given a Playwright Page object, return its page index within the context and the context index within the browser.
        Args:
            page: Playwright Page object
        Returns:
            (str, int): (page_index, context_index)
        Raises:
            BrowserError: If indices cannot be determined.
        """
        if page is None:
            return None, 0

        try:
            cdp_session = page.context.new_cdp_session(page)
            target_info = cdp_session.send("Target.getTargetInfo")
            page_index = target_info["targetInfo"]["targetId"]
            cdp_session.detach()
            if hasattr(page.context.browser, "contexts"):
                context_index = page.context.browser.contexts.index(page.context)
            else:
                context_index = 0
            return page_index, 0
        except Exception as e:
            raise BrowserError(f"Failed to get page/context index: {e}")

    async def _get_page_and_context_index_async(self, page):
        """
        Async version of _get_page_and_context_index for getting page and context indices asynchronously.
        Args:
            page: Playwright Page object
        Returns:
            (str, int): (page_index, context_index)
        Raises:
            BrowserError: If indices cannot be determined.
        """
        if page is None:
            return None, 0
        try:
            cdp_session = await page.context.new_cdp_session(page)
            target_info = await cdp_session.send("Target.getTargetInfo")
            page_index = target_info["targetInfo"]["targetId"]
            await cdp_session.detach()
            if hasattr(page.context.browser, "contexts"):
                context_index = page.context.browser.contexts.index(page.context)
            else:
                context_index = 0
            return page_index, 0
        except Exception as e:
            raise BrowserError(f"Failed to get page/context index: {e}")

    def _handle_error(self, e):
        """
        Handle and convert exceptions. This method should be overridden by subclasses
        to provide specific error handling.

        Args:
            e (Exception): The exception to handle.

        Returns:
            Exception: The handled exception.
        """
        if isinstance(e, BrowserError):
            return e
        if isinstance(e, AgentBayError):
            return BrowserError(str(e))
        return e

    def _call_mcp_tool_timeout(
        self, name: str, args: Dict[str, Any]
    ) -> OperationResult:
        """
        Call MCP tool with timeout.
        """
        return self._call_mcp_tool(
            name, args, read_timeout=60000, connect_timeout=60000
        )
