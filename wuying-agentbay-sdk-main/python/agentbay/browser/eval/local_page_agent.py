import asyncio
import os
import concurrent.futures
from typing import Dict, Any
from playwright.async_api import async_playwright
from mcp import ClientSession, StdioServerParameters, stdio_client
import json
from agentbay.browser import Browser, BrowserOption
from agentbay.session import Session
from agentbay.api.base_service import OperationResult
from agentbay.browser.browser_agent import BrowserAgent
from agentbay.logger import get_logger

# Use the AgentBay logger instead of the standard logger
logger = get_logger("local_page_agent")

class LocalMCPClient:
    def __init__(self, server: str, command: str, args: list[str])-> None:
        self.server = server
        self.command = command
        self.args = args
        self.session: ClientSession | None = None
        self.worker_thread: concurrent.futures.Future | None = None
        self._tool_call_queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def connect(self) -> None:
        if (self.worker_thread is None):
            promise: concurrent.futures.Future[bool] = concurrent.futures.Future()
            def thread_target() -> None:
                async def _connect_and_list_tools() -> None:
                    success = False
                    logger.info("Start connect to mcp server")
                    try:
                        logger.debug(f"command = {self.command}, args = {self.args}")
                        server_params = StdioServerParameters(command=self.command, args=self.args)
                        async with stdio_client(server_params) as (read_stream, write_stream):
                            async with ClientSession(read_stream, write_stream) as session:
                                # Setup queue and event loop reference
                                self._tool_call_queue = asyncio.Queue()
                                self._loop = asyncio.get_running_loop()

                                self.session = session
                                logger.info("Initialize MCP client session")
                                await self.session.initialize()
                                logger.info("Client initialized. Listing available tools...")
                                tools = await self.session.list_tools()
                                logger.info(f"Tools: {tools}")
                                success = True
                                promise.set_result(success)
                                await self._interactive_loop()
                    except Exception as e:
                        logger.error(f"Failed to connect to MCP server: {e}")
                        success = False
                        promise.set_result(success)
                asyncio.run(_connect_and_list_tools())
            self.worker_thread = concurrent.futures.ThreadPoolExecutor().submit(thread_target)
            promise.result()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        if not self.session or not self._tool_call_queue or not self._loop:
            raise RuntimeError("MCP client is not connected. Call connect() and ensure it returns True before calling callTool.")
        caller_loop = asyncio.get_running_loop()
        fut = caller_loop.create_future()
        await self._tool_call_queue.put((tool_name, arguments, fut))
        return await fut

    async def _interactive_loop(self):
        """Run interactive loop."""
        while True:
            if self._tool_call_queue is not None:
                try:
                    tool_name, arguments, future = await asyncio.wait_for(self._tool_call_queue.get(), timeout=1.0)
                    try:
                        logger.info(f"Call tool {tool_name} with arguments {arguments}")
                        if self.session is not None:
                            response = await self.session.call_tool(tool_name, arguments)
                            is_successful = not response.isError

                            mcp_response = OperationResult(
                                request_id="local_request_dummy_id",
                                success=is_successful,
                            )

                            # Extract text content from response
                            text_content = ""
                            if hasattr(response, 'content') and response.content:
                                for content_item in response.content:
                                    if hasattr(content_item, 'text') and content_item.text:
                                        text_content = content_item.text
                                        break
                                if is_successful:
                                    mcp_response.data = text_content
                                    logger.info(f"MCP tool text response (data): {str(text_content)[:2000]}")
                                else:
                                    mcp_response.error_message = text_content
                                    logger.info(f"MCP tool text response (error): {str(text_content)[:2000]}")

                            if asyncio.isfuture(future):
                                fut_loop = future.get_loop()
                                fut_loop.call_soon_threadsafe(future.set_result, mcp_response)
                            elif isinstance(future, concurrent.futures.Future):
                                future.set_result(mcp_response)
                            else:
                                raise TypeError(f"Unexpected future type: {type(future)}")
                        else:
                            future.set_exception(RuntimeError("MCP client session is not initialized."))
                    except Exception as e:
                        future.set_exception(e)
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(1)

class LocalPageAgent(BrowserAgent):
    def __init__(self, session, browser):
        super().__init__(session, browser)

        mcp_script = os.environ.get("PAGE_TASK_MCP_SERVER_SCRIPT", "")

        self.mcp_client: LocalMCPClient | None = LocalMCPClient(
            server="PageUseAgent",
            command="python",
            args=[mcp_script]
        )

    def initialize(self):
        self.mcp_client.connect()

    def _call_mcp_tool(self, name: str, args: dict, read_timeout: int = None, connect_timeout: int = None) -> OperationResult:
        if not self.mcp_client:
            return super()._call_mcp_tool(name, args, read_timeout, connect_timeout)

        target_loop = self.mcp_client._loop
        coro = self._call_mcp_tool_async(name, args)
        fut = asyncio.run_coroutine_threadsafe(coro, target_loop)
        return fut.result()
    
    async def _call_mcp_tool_async(self, name: str, args: dict) -> OperationResult:
        if not self.mcp_client:
            raise RuntimeError("mcp_client is not set on LocalBrowserAgent.")
        return await self.mcp_client.call_tool(name, args)


class LocalBrowser(Browser):
    def __init__(self, session=None):
        # Optionally skip calling super().__init__ if not needed for tests
        self.contexts = []
        self._cdp_port = 9222
        self.agent: LocalPageAgent = LocalPageAgent(session, self)
        self._worker_thread = None

    async def initialize_async(self, options: BrowserOption) -> bool:
        if (self._worker_thread is None):
            promise: concurrent.futures.Future[bool] = concurrent.futures.Future()
            def thread_target() -> None:
                async def _launch_local_browser() -> None:
                    success = False
                    logger.info("Start launching local browser")
                    try:
                        async with async_playwright() as p:
                            # Define CDP port
                            # Recreate /tmp/chrome_cdp_ports.json with the required content
                            chrome_cdp_ports_path = "/tmp/chrome_cdp_ports.json"
                            with open(chrome_cdp_ports_path, "w") as f:
                                json.dump({"chrome": str(self._cdp_port), "router": str(self._cdp_port)}, f)

                            # Launch headless browser and create a page for all tests
                            self._browser = await p.chromium.launch_persistent_context(
                                headless=False,
                                viewport={"width": 1280, "height": 1200},
                                args=[
                                    f'--remote-debugging-port={self._cdp_port}',
                                ],
                                user_data_dir="/tmp/browser_user_data")

                            logger.info("Local browser launched successfully:")
                            success = True
                            promise.set_result(success)
                            await self._playwright_interactive_loop()
                    except Exception as e:
                        logger.error(f"Failed to connect to browser: {e}")
                        success = False
                        promise.set_result(success)
                asyncio.run(_launch_local_browser())
            self._worker_thread = concurrent.futures.ThreadPoolExecutor().submit(thread_target)
            promise.result()

        self.agent.initialize()
        return True

    def is_initialized(self) -> bool:
        return True

    def get_endpoint_url(self) -> str:
        return f"http://localhost:{self._cdp_port}"

    async def _playwright_interactive_loop(self):
        """Run interactive loop."""
        while True:
            await asyncio.sleep(3)

class LocalSession(Session):
    def __init__(self):
        super().__init__(None, "local_session")
        self.browser = LocalBrowser(self)

    def delete(self, sync_context: bool = False):
        pass