import json
from typing import TYPE_CHECKING, Dict, Optional
from .logger import (
    get_logger,
    log_api_call,
    log_api_response,
    log_operation_start,
    log_operation_success,
    log_operation_error,
    log_warning,
)

from agentbay.api.models import (
    GetLabelRequest,
    GetLinkRequest,
    GetLinkResponse,
    GetMcpResourceRequest,
    ReleaseMcpSessionRequest,
    SetLabelRequest,
)
from agentbay.application import ApplicationManager
from agentbay.code import Code
from agentbay.command import Command
from agentbay.computer import Computer
from agentbay.exceptions import SessionError
from agentbay.filesystem import FileSystem
from agentbay.mobile import Mobile
from agentbay.model import DeleteResult, OperationResult, extract_request_id
from agentbay.oss import Oss
from agentbay.ui import UI
from agentbay.agent import Agent
from agentbay.window import WindowManager
from agentbay.context_manager import ContextManager

if TYPE_CHECKING:
    from agentbay.agentbay import AgentBay

from agentbay.browser import Browser

# Initialize logger for this module
logger = get_logger("session")


class SessionInfo:
    """
    SessionInfo contains information about a session.
    """

    def __init__(
        self,
        session_id: str = "",
        resource_url: str = "",
        app_id: str = "",
        auth_code: str = "",
        connection_properties: str = "",
        resource_id: str = "",
        resource_type: str = "",
        ticket: str = "",
    ):
        self.session_id = session_id
        self.resource_url = resource_url
        self.app_id = app_id
        self.auth_code = auth_code
        self.connection_properties = connection_properties
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.ticket = ticket


class Session:
    """
    Session represents a session in the AgentBay cloud environment.
    """

    def __init__(self, agent_bay: "AgentBay", session_id: str):
        self.agent_bay = agent_bay
        self.session_id = session_id

        # VPC-related information
        self.is_vpc = False  # Whether this session uses VPC resources
        self.network_interface_ip = ""  # Network interface IP for VPC sessions
        self.http_port = ""  # HTTP port for VPC sessions
        self.token = ""

        # Resource URL for accessing the session
        self.resource_url = ""

        # Recording functionality
        self.enableBrowserReplay = (
            False  # Whether browser recording is enabled for this session
        )

        # MCP tools available for this session
        self.mcp_tools = []  # List[McpTool]

        # File transfer context ID
        self.file_transfer_context_id: Optional[str] = None

        # Initialize file system, command and code handlers
        self.file_system = FileSystem(self)
        self.command = Command(self)
        self.code = Code(self)
        self.oss = Oss(self)

        # Initialize application and window managers
        self.application = ApplicationManager(self)
        self.window = WindowManager(self)

        # Initialize Computer and Mobile modules
        self.computer = Computer(self)
        self.mobile = Mobile(self)

        self.ui = UI(self)
        self.context = ContextManager(self)
        self.browser = Browser(self)

        self.agent = Agent(self)

    def get_api_key(self) -> str:
        """Return the API key for this session."""
        return self.agent_bay.api_key

    def get_client(self):
        """Return the HTTP client for this session."""
        return self.agent_bay.client

    def get_session_id(self) -> str:
        """Return the session_id for this session."""
        return self.session_id

    def is_vpc_enabled(self) -> bool:
        """Return whether this session uses VPC resources."""
        return self.is_vpc

    def get_network_interface_ip(self) -> str:
        """Return the network interface IP for VPC sessions."""
        return self.network_interface_ip

    def get_http_port(self) -> str:
        """Return the HTTP port for VPC sessions."""
        return self.http_port

    def get_token(self) -> str:
        """Return the token for VPC sessions."""
        return self.token

    def find_server_for_tool(self, tool_name: str) -> str:
        """Find the server that provides the given tool."""
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                return tool.server
        return ""

    def delete(self, sync_context: bool = False) -> DeleteResult:
        """
        Delete this session.

        Args:
            sync_context (bool): Whether to sync context data (trigger file uploads)
                before deleting the session. Defaults to False.

        Returns:
            DeleteResult: Result indicating success or failure and request ID.
        """
        try:
            # If sync_context is True, trigger file uploads first
            if sync_context:
                log_operation_start(
                    "Context synchronization", "Before session deletion"
                )
                import time

                sync_start_time = time.time()

                try:
                    # Use asyncio.run to call the async context.sync synchronously (no callback)
                    import asyncio

                    sync_result = asyncio.run(self.context.sync())

                    sync_duration = time.time() - sync_start_time

                    if sync_result.success:
                        log_operation_success("Context sync")
                        logger.info(
                            f"⏱️  Context sync completed in {sync_duration:.2f} seconds"
                        )
                    else:
                        log_warning("Context sync completed with failures")
                        logger.warning(
                            f"⏱️  Context sync failed after {sync_duration:.2f} seconds"
                        )

                except Exception as e:
                    sync_duration = time.time() - sync_start_time
                    log_warning(f"Failed to trigger context sync: {e}")
                    logger.warning(
                        f"⏱️  Context sync failed after {sync_duration:.2f} seconds"
                    )
                    # Continue with deletion even if sync fails

            # Proceed with session deletion
            request = ReleaseMcpSessionRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.session_id,
            )
            response = self.get_client().release_mcp_session(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")

            # Extract request ID
            request_id = extract_request_id(response)

            # Check if the response is success
            response_map = response.to_map()
            body = response_map.get("body", {})
            success = body.get("Success", True)

            if not success:
                error_message = f"[{body.get('Code', 'Unknown')}] {body.get('Message', 'Failed to delete session')}"
                return DeleteResult(
                    request_id=request_id,
                    success=False,
                    error_message=error_message,
                )

            # Return success result with request ID
            return DeleteResult(request_id=request_id, success=True)

        except Exception as e:
            log_operation_error("release_mcp_session", str(e))
            # In case of error, return failure result with error message
            return DeleteResult(
                success=False,
                error_message=f"Failed to delete session {self.session_id}: {e}",
            )

    def _validate_labels(self, labels: Dict[str, str]) -> Optional[OperationResult]:
        """
        Validates labels parameter for label operations.

        Args:
            labels: The labels to validate

        Returns:
            None if validation passes, or OperationResult with error if validation fails
        """
        # Check if labels is None
        if labels is None:
            return OperationResult(
                request_id="",
                success=False,
                error_message="Labels cannot be null, undefined, or invalid type. Please provide a valid labels object.",
            )

        # Check if labels is a list (array equivalent) - check this before dict check
        if isinstance(labels, list):
            return OperationResult(
                request_id="",
                success=False,
                error_message="Labels cannot be an array. Please provide a valid labels object.",
            )

        # Check if labels is not a dict (after checking for list)
        if not isinstance(labels, dict):
            return OperationResult(
                request_id="",
                success=False,
                error_message="Labels cannot be null, undefined, or invalid type. Please provide a valid labels object.",
            )

        # Check if labels object is empty
        if len(labels) == 0:
            return OperationResult(
                request_id="",
                success=False,
                error_message="Labels cannot be empty. Please provide at least one label.",
            )

        for key, value in labels.items():
            # Check key validity
            if not key or (isinstance(key, str) and key.strip() == ""):
                return OperationResult(
                    request_id="",
                    success=False,
                    error_message="Label keys cannot be empty Please provide valid keys.",
                )

            # Check value is not None or empty
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return OperationResult(
                    request_id="",
                    success=False,
                    error_message="Label values cannot be empty Please provide valid values.",
                )

        # Validation passed
        return None

    def set_labels(self, labels: Dict[str, str]) -> OperationResult:
        """
        Sets the labels for this session.

        Args:
            labels (Dict[str, str]): The labels to set for the session.

        Returns:
            OperationResult: Result indicating success or failure with request ID.

        Raises:
            SessionError: If the operation fails.
        """
        try:
            # Validate labels using the extracted validation function
            validation_result = self._validate_labels(labels)
            if validation_result is not None:
                return validation_result

            # Convert labels to JSON string
            labels_json = json.dumps(labels)

            request = SetLabelRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.session_id,
                labels=labels_json,
            )

            response = self.get_client().set_label(request)

            # Extract request ID
            request_id = extract_request_id(response)

            return OperationResult(request_id=request_id, success=True)

        except Exception as e:
            log_operation_error("set_label", str(e))
            raise SessionError(
                f"Failed to set labels for session {self.session_id}: {e}"
            )

    def get_labels(self) -> OperationResult:
        """
        Gets the labels for this session.

        Returns:
            OperationResult: Result containing the labels as data and request ID.

        Raises:
            SessionError: If the operation fails.
        """
        try:
            request = GetLabelRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.session_id,
            )

            response = self.get_client().get_label(request)

            # Extract request ID
            request_id = extract_request_id(response)

            # Extract labels from response
            labels_json = (
                response.to_map().get("body", {}).get("Data", {}).get("Labels")
            )

            labels = {}
            if labels_json:
                labels = json.loads(labels_json)

            return OperationResult(request_id=request_id, success=True, data=labels)

        except Exception as e:
            log_operation_error("get_label", str(e))
            raise SessionError(
                f"Failed to get labels for session {self.session_id}: {e}"
            )

    def info(self) -> OperationResult:
        """
        Gets information about this session.

        Returns:
            OperationResult: Result containing the session information as data and
                request ID.

        Raises:
            SessionError: If the operation fails.
        """
        try:
            request = GetMcpResourceRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.session_id,
            )

            log_api_call("GetMcpResource", f"SessionId={self.session_id}")

            response = self.get_client().get_mcp_resource(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")

            # Extract request ID
            request_id = extract_request_id(response)

            # Extract session info from response
            response_map = response.to_map()
            data = response_map.get("body", {}).get("Data", {})

            session_info = SessionInfo()

            if "SessionId" in data:
                session_info.session_id = data["SessionId"]

            if "ResourceUrl" in data:
                session_info.resource_url = data["ResourceUrl"]
            # Transfer DesktopInfo fields to SessionInfo
            if "DesktopInfo" in data:
                desktop_info = data["DesktopInfo"]
                if "AppId" in desktop_info:
                    session_info.app_id = desktop_info["AppId"]
                if "AuthCode" in desktop_info:
                    session_info.auth_code = desktop_info["AuthCode"]
                if "ConnectionProperties" in desktop_info:
                    session_info.connection_properties = desktop_info[
                        "ConnectionProperties"
                    ]
                if "ResourceId" in desktop_info:
                    session_info.resource_id = desktop_info["ResourceId"]
                if "ResourceType" in desktop_info:
                    session_info.resource_type = desktop_info["ResourceType"]
                if "Ticket" in desktop_info:
                    session_info.ticket = desktop_info["Ticket"]

            return OperationResult(
                request_id=request_id, success=True, data=session_info
            )

        except Exception as e:
            log_operation_error("GetMcpResource", str(e))
            raise SessionError(
                f"Failed to get session info for session {self.session_id}: {e}"
            )

    def get_link(
        self, protocol_type: Optional[str] = None, port: Optional[int] = None
    ) -> OperationResult:
        """
        Get a link associated with the current session.

        Args:
            protocol_type (Optional[str], optional): The protocol type to use for the
                link. Defaults to None.
            port (Optional[int], optional): The port to use for the link. Must be an integer in the range [30100, 30199].
                Defaults to None.

        Returns:
            OperationResult: Result containing the link as data and request ID.

        Raises:
            SessionError: If the request fails or the response is invalid.
        """
        try:
            # Validate port range if port is provided
            if port is not None:
                if not isinstance(port, int) or port < 30100 or port > 30199:
                    raise SessionError(
                        f"Invalid port value: {port}. Port must be an integer in the range [30100, 30199]."
                    )

            request = GetLinkRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.get_session_id(),
                protocol_type=protocol_type,
                port=port,
            )
            response: GetLinkResponse = self.agent_bay.client.get_link(request)

            # Extract request ID
            request_id = extract_request_id(response)

            response_map = response.to_map()

            if not isinstance(response_map, dict):
                raise SessionError(
                    "Invalid response format: expected a dictionary from "
                    "response.to_map()"
                )

            body = response_map.get("body", {})
            if not isinstance(body, dict):
                raise SessionError(
                    "Invalid response format: 'body' field is not a dictionary"
                )

            data = body.get("Data", {})
            logger.debug(f"📊 Data: {data}")

            if not isinstance(data, dict):
                try:
                    data = json.loads(data) if isinstance(data, str) else {}
                except json.JSONDecodeError:
                    data = {}

            url = data.get("Url", "")

            return OperationResult(request_id=request_id, success=True, data=url)

        except SessionError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to get link: {e}")

    async def get_link_async(
        self, protocol_type: Optional[str] = None, port: Optional[int] = None
    ) -> OperationResult:
        """
        Asynchronously get a link associated with the current session.

        Args:
            protocol_type (Optional[str], optional): The protocol type to use for the
                link. Defaults to None.
            port (Optional[int], optional): The port to use for the link. Must be an integer in the range [30100, 30199].
                Defaults to None.

        Returns:
            OperationResult: Result containing the link as data and request ID.

        Raises:
            SessionError: If the request fails or the response is invalid.
        """
        try:
            # Validate port range if port is provided
            if port is not None:
                if not isinstance(port, int) or port < 30100 or port > 30199:
                    raise SessionError(
                        f"Invalid port value: {port}. Port must be an integer in the range [30100, 30199]."
                    )

            request = GetLinkRequest(
                authorization=f"Bearer {self.get_api_key()}",
                session_id=self.get_session_id(),
                protocol_type=protocol_type,
                port=port,
            )
            response: GetLinkResponse = await self.agent_bay.client.get_link_async(
                request
            )

            # Extract request ID
            request_id = extract_request_id(response)

            response_map = response.to_map()

            if not isinstance(response_map, dict):
                raise SessionError(
                    "Invalid response format: expected a dictionary from "
                    "response.to_map()"
                )

            body = response_map.get("body", {})
            if not isinstance(body, dict):
                raise SessionError(
                    "Invalid response format: 'body' field is not a dictionary"
                )

            data = body.get("Data", {})
            logger.debug(f"📊 Data: {data}")

            if not isinstance(data, dict):
                try:
                    data = json.loads(data) if isinstance(data, str) else {}
                except json.JSONDecodeError:
                    data = {}

            url = data.get("Url", "")

            return OperationResult(request_id=request_id, success=True, data=url)

        except SessionError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to get link asynchronously: {e}")

    def list_mcp_tools(self, image_id: Optional[str] = None):
        """
        List MCP tools available for this session.

        Args:
            image_id: Optional image ID, defaults to session's image_id or "linux_latest"

        Returns:
            Result containing tools list and request ID
        """
        from agentbay.api.models import ListMcpToolsRequest
        from agentbay.model.response import McpToolsResult
        from agentbay.models.mcp_tool import McpTool
        import json

        # Use provided image_id, session's image_id, or default
        if image_id is None:
            image_id = getattr(self, "image_id", "") or "linux_latest"

        request = ListMcpToolsRequest(
            authorization=f"Bearer {self.get_api_key()}", image_id=image_id
        )

        log_api_call("ListMcpTools", f"ImageId={image_id}")

        response = self.get_client().list_mcp_tools(request)

        # Extract request ID
        request_id = extract_request_id(response)

        if response and response.body:
            logger.debug(f"📥 Response from ListMcpTools: {response.body}")

        # Parse the response data
        tools = []
        if response and response.body and response.body.data:
            # The Data field is a JSON string, so we need to unmarshal it
            try:
                tools_data = json.loads(response.body.data)
                for tool_data in tools_data:
                    tool = McpTool(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server=tool_data.get("server", ""),
                        tool=tool_data.get("tool", ""),
                    )
                    tools.append(tool)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error unmarshaling tools data: {e}")

        self.mcp_tools = tools  # Update the session's mcp_tools field

        return McpToolsResult(request_id=request_id, tools=tools)
