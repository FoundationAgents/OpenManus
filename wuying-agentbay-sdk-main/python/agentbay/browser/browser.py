from typing import TYPE_CHECKING, Optional, Literal
import asyncio
import time
import os
from agentbay.api.models import InitBrowserRequest
from agentbay.browser.browser_agent import BrowserAgent
from agentbay.api.base_service import BaseService
from agentbay.exceptions import BrowserError
from agentbay.config import BROWSER_DATA_PATH
from agentbay.logger import get_logger

# Initialize logger for this module
logger = get_logger("browser")

if TYPE_CHECKING:
    from agentbay.session import Session

class BrowserProxy:
    """
    Browser proxy configuration.
    Supports two types of proxy: custom proxy, wuying proxy.
    wuying proxy support two strategies: restricted and polling.
    """
    def __init__(
        self,
        proxy_type: Literal["custom", "wuying"],
        server: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        strategy: Optional[Literal["restricted", "polling"]] = None,
        pollsize: int = 10
    ):
        """
        Initialize a BrowserProxy.

        Args:
            proxy_type: Type of proxy - "custom" or "wuying"
            server: Proxy server address (required for custom type)
            username: Proxy username (optional for custom type)
            password: Proxy password (optional for custom type)
            strategy: Strategy for wuying support "restricted" and "polling"
            pollsize: Pool size (optional for proxy_type wuying and strategy polling)

            example:
            # custom proxy
            proxy_type: custom
            server: "127.0.0.1:9090"
            username: "username"
            password: "password"

            # wuying proxy with polling strategy
            proxy_type: wuying
            strategy: "polling"
            pollsize: 10

            # wuying proxy with restricted strategy
            proxy_type: wuying
            strategy: "restricted"
        """
        self.type = proxy_type
        self.server = server
        self.username = username
        self.password = password
        self.strategy = strategy
        self.pollsize = pollsize

        # Validation
        if proxy_type not in ["custom", "wuying"]:
            raise ValueError("proxy_type must be custom or wuying")

        if proxy_type == "custom" and not server:
            raise ValueError("server is required for custom proxy type")

        if proxy_type == "wuying" and not strategy:
            raise ValueError("strategy is required for wuying proxy type")

        if proxy_type == "wuying" and strategy not in ["restricted", "polling"]:
            raise ValueError("strategy must be restricted or polling for wuying proxy type")

        if proxy_type == "wuying" and strategy == "polling" and pollsize <= 0:
            raise ValueError("pollsize must be greater than 0 for polling strategy")
    def to_map(self):
        proxy_map = {
            "type": self.type
        }

        if self.type == "custom":
            proxy_map["server"] = self.server
            if self.username:
                proxy_map["username"] = self.username
            if self.password:
                proxy_map["password"] = self.password
        elif self.type == "wuying":
            proxy_map["strategy"] = self.strategy
            if self.strategy == "polling":
                proxy_map["pollsize"] = self.pollsize


        return proxy_map

    @classmethod
    def from_map(cls, m: dict = None):
        if not m:
            return None

        proxy_type = m.get("type")
        if not proxy_type:
            raise ValueError("type is required in proxy configuration")

        if proxy_type == "custom":
            return cls(
                proxy_type=proxy_type,
                server=m.get("server"),
                username=m.get("username"),
                password=m.get("password")
            )
        elif proxy_type == "wuying":
            return cls(
                proxy_type=proxy_type,
                strategy=m.get("strategy"),
                pollsize=m.get("pollsize", 10)
            )
        else:
            raise ValueError(f"Unsupported proxy type: {proxy_type}")

class BrowserViewport:
    """
    Browser viewport options.
    """
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def to_map(self):
        viewport_map = dict()
        if self.width is not None:
            viewport_map['width'] = self.width
        if self.height is not None:
            viewport_map['height'] = self.height
        return viewport_map

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('width') is not None:
            self.width = m.get('width')
        if m.get('height') is not None:
            self.height = m.get('height')
        return self

class BrowserScreen:
    """
    Browser screen options.
    """
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def to_map(self):
        screen_map = dict()
        if self.width is not None:
            screen_map['width'] = self.width
        if self.height is not None:
            screen_map['height'] = self.height
        return screen_map

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('width') is not None:
            self.width = m.get('width')
        if m.get('height') is not None:
            self.height = m.get('height')
        return self

class BrowserFingerprint:
    """
    Browser fingerprint options.
    """
    def __init__(
        self,
        devices: list[Literal["desktop", "mobile"]] = None,
        operating_systems: list[Literal["windows", "macos", "linux", "android", "ios"]] = None,
        locales: list[str] = None
    ):
        self.devices = devices
        self.operating_systems = operating_systems
        self.locales = locales


        # Validation


        if devices is not None:
            if not isinstance(devices, list):
                raise ValueError("devices must be a list")
            for device in devices:
                if device not in ["desktop", "mobile"]:
                    raise ValueError("device must be desktop or mobile")

        if operating_systems is not None:
            if not isinstance(operating_systems, list):
                raise ValueError("operating_systems must be a list")
            for operating_system in operating_systems:
                if operating_system not in ["windows", "macos", "linux", "android", "ios"]:
                    raise ValueError("operating_system must be windows, macos, linux, android or ios")

    def to_map(self):
        fingerprint_map = dict()
        if self.devices is not None:
            fingerprint_map['devices'] = self.devices
        if self.operating_systems is not None:
            fingerprint_map['operatingSystems'] = self.operating_systems
        if self.locales is not None:
            fingerprint_map['locales'] = self.locales
        return fingerprint_map

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('devices') is not None:
            self.devices = m.get('devices')
        if m.get('operatingSystems') is not None:
            self.operating_systems = m.get('operatingSystems')
        if m.get('locales') is not None:
            self.locales = m.get('locales')
        return self

class BrowserOption:
    """
    browser initialization options.
    """
    def __init__(
        self,
        use_stealth: bool = False,
        user_agent: str = None,
        viewport: BrowserViewport = None,
        screen: BrowserScreen = None,
        fingerprint: BrowserFingerprint = None,
        solve_captchas: bool = False,
        proxies: Optional[list[BrowserProxy]] = None,
        extension_path: Optional[str] = "/tmp/extensions/",
    ):
        self.use_stealth = use_stealth
        self.user_agent = user_agent
        self.viewport = viewport
        self.screen = screen
        self.fingerprint = fingerprint
        self.solve_captchas = solve_captchas
        self.proxies = proxies
        self.extension_path = extension_path

        # Validate proxies list items
        if proxies is not None:
            if not isinstance(proxies, list):
                raise ValueError("proxies must be a list")
            if len(proxies) > 1:
                raise ValueError("proxies list length must be limited to 1")

        # Validate extension_path if provided
        if extension_path is not None:
            if not isinstance(extension_path, str):
                raise ValueError("extension_path must be a string")
            if not extension_path.strip():
                raise ValueError("extension_path cannot be empty")

    def to_map(self):
        option_map = dict()
        if behavior_simulate_env := os.getenv("AGENTBAY_BROWSER_BEHAVIOR_SIMULATE"):
            option_map['behaviorSimulate'] = behavior_simulate_env != "0"
        if self.use_stealth is not None:
            option_map['useStealth'] = self.use_stealth
        if self.user_agent is not None:
            option_map['userAgent'] = self.user_agent
        if self.viewport is not None:
            option_map['viewport'] = self.viewport.to_map()
        if self.screen is not None:
            option_map['screen'] = self.screen.to_map()
        if self.fingerprint is not None:
            option_map['fingerprint'] = self.fingerprint.to_map()
        if self.solve_captchas is not None:
            option_map['solveCaptchas'] = self.solve_captchas
        if self.proxies is not None:
            option_map['proxies'] = [proxy.to_map() for proxy in self.proxies]
        if self.extension_path is not None:
            option_map['extensionPath'] = self.extension_path
        return option_map

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('useStealth') is not None:
            self.use_stealth = m.get('useStealth')
        else:
            self.use_stealth = False
        if m.get('userAgent') is not None:
            self.user_agent = m.get('userAgent')
        if m.get('viewport') is not None:
            self.viewport = BrowserViewport.from_map(m.get('viewport'))
        if m.get('screen') is not None:
            self.screen = BrowserScreen.from_map(m.get('screen'))
        if m.get('fingerprint') is not None:
            self.fingerprint = BrowserFingerprint.from_map(m.get('fingerprint'))
        if m.get('solveCaptchas') is not None:
            self.solve_captchas = m.get('solveCaptchas')
        else:
            self.solve_captchas = False
        if m.get('proxies') is not None:
            proxy_list = m.get('proxies')
            if len(proxy_list) > 1:
                raise ValueError("proxies list length must be limited to 1")
            self.proxies = [BrowserProxy.from_map(proxy_data) for proxy_data in proxy_list]
        return self

class Browser(BaseService):
    """
    Browser provides browser-related operations for the session.
    """
    def __init__(self, session: "Session"):
        self.session = session
        self._endpoint_url = None
        self._initialized = False
        self._option = None
        self.agent = BrowserAgent(self.session, self)
        self.endpoint_router_port = None

    def initialize(self, option: "BrowserOption") -> bool:
        """
        Initialize the browser instance with the given options.
        Returns True if successful, False otherwise.
        """
        if self.is_initialized():
            return True
        try:
            browser_option_dict = option.to_map()

            # Enable record if session.enableBrowserReplay is True
            if hasattr(self.session, 'enableBrowserReplay') and self.session.enableBrowserReplay:
                browser_option_dict['enableRecord'] = True

            request = InitBrowserRequest(
                authorization=f"Bearer {self.session.get_api_key()}",
                session_id=self.session.get_session_id(),
                persistent_path=BROWSER_DATA_PATH,
                browser_option=browser_option_dict,
            )
            response = self.session.get_client().init_browser(request)

            logger.info(f"Response from init_browser: {response}")
            response_map = response.to_map()
            body = response_map.get("body", {})
            data = body.get("Data", {})
            success = data.get("Port") is not None
            if success:
                self._initialized = True
                self._option = option
                logger.info("Browser instance was successfully initialized.")

            return success
        except Exception as e:
            logger.error(f"Failed to initialize browser instance: {e}")
            self._initialized = False
            self._endpoint_url = None
            self._option = None
            return False

    async def initialize_async(self, option: "BrowserOption") -> bool:
        """
        Initialize the browser instance with the given options asynchronously.
        Returns True if successful, False otherwise.
        """
        if self.is_initialized():
            return True
        try:
            browser_option_dict = option.to_map()

            # Enable record if session.enableBrowserReplay is True
            if hasattr(self.session, 'enableBrowserReplay') and self.session.enableBrowserReplay:
                browser_option_dict['enableRecord'] = True

            request = InitBrowserRequest(
                authorization=f"Bearer {self.session.get_api_key()}",
                session_id=self.session.get_session_id(),
                persistent_path=BROWSER_DATA_PATH,
                browser_option=browser_option_dict,
            )
            response = await self.session.get_client().init_browser_async(request)
            logger.debug(f"Response from init_browser: {response}")
            response_map = response.to_map()
            body = response_map.get("body", {})
            data = body.get("Data", {})
            success = data.get("Port") is not None
            if success:
                self.endpoint_router_port = data.get("Port")
                self._initialized = True
                self._option = option
                logger.info("Browser instance successfully initialized")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize browser instance: {e}")
            self._initialized = False
            self._endpoint_url = None
            self._option = None
            return False

    def _stop_browser(self):
        """
        Stop the browser instance, internal use only.
        """
        if self.is_initialized():
            self._call_mcp_tool("stopChrome", {})
        else:
            raise BrowserError("Browser is not initialized. Cannot stop browser.")

    def get_endpoint_url(self) -> str:
        """
        Returns the endpoint URL if the browser is initialized, otherwise raises an exception.
        When initialized, always fetches the latest CDP url from session.get_link().
        """
        if not self.is_initialized():
            raise BrowserError("Browser is not initialized. Cannot access endpoint URL.")
        try:
            if self.session.is_vpc:
                logger.debug(f"VPC mode, endpoint_router_port: {self.endpoint_router_port}")
                self._endpoint_url = f"ws://{self.session.network_interface_ip}:{self.endpoint_router_port}"
            else:
                cdp_url = self.session.get_link()
                self._endpoint_url = cdp_url.data
            return self._endpoint_url
        except Exception as e:
            raise BrowserError(f"Failed to get endpoint URL from session: {e}")

    def get_option(self) -> Optional["BrowserOption"]:
        """
        Returns the current BrowserOption used to initialize the browser, or None if not set.
        """
        return self._option

    def is_initialized(self) -> bool:
        """
        Returns True if the browser was initialized, False otherwise.
        """
        return self._initialized
