"""
API response models for AgentBay SDK.
"""

from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from agentbay.session import Session
    from agentbay.models.mcp_tool import McpTool


class ApiResponse:
    """Base class for all API responses, containing RequestID"""

    def __init__(self, request_id: str = ""):
        """
        Initialize an ApiResponse with a request_id.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
        """
        self.request_id = request_id

    def get_request_id(self) -> str:
        """Returns the unique identifier for the API request."""
        return self.request_id


class SessionResult(ApiResponse):
    """Result of operations returning a single Session."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        error_message: str = "",
        session: Optional["Session"] = None,
    ):
        """
        Initialize a SessionResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            session (Optional[Session], optional): The session object. Defaults to None.
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message
        self.session = session


class SessionListResult(ApiResponse):
    """Result of operations returning a list of Sessions."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        error_message: str = "",
        session_ids: List[str] = None,
        next_token: str = "",
        max_results: int = 0,
        total_count: int = 0,
    ):
        """
        Initialize a SessionListResult.

        Args:
            request_id (str): The request ID.
            success (bool): Whether the operation was successful.
            error_message (str): Error message if the operation failed.
            session_ids (List[str]): List of session IDs.
            next_token (str): Token for the next page of results.
            max_results (int): Number of results per page.
            total_count (int): Total number of results available.
        """
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message
        self.session_ids = session_ids if session_ids is not None else []
        self.next_token = next_token
        self.max_results = max_results
        self.total_count = total_count


class DeleteResult(ApiResponse):
    """Result of delete operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        error_message: str = "",
        code: str = "",
        message: str = "",
        http_status_code: int = 0,
    ):
        """
        Initialize a DeleteResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the delete operation was successful.
                Defaults to False.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
            code (str, optional): API error code. Defaults to "".
            message (str, optional): Detailed error message from API. Defaults to "".
            http_status_code (int, optional): HTTP status code. Defaults to 0.
        """
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message
        self.code = code
        self.message = message
        self.http_status_code = http_status_code


class GetSessionData:
    """Data returned by GetSession API."""

    def __init__(
        self,
        app_instance_id: str = "",
        resource_id: str = "",
        session_id: str = "",
        success: bool = False,
        http_port: str = "",
        network_interface_ip: str = "",
        token: str = "",
        vpc_resource: bool = False,
        resource_url: str = "",
    ):
        """
        Initialize GetSessionData.

        Args:
            app_instance_id (str): Application instance ID.
            resource_id (str): Resource ID.
            session_id (str): Session ID.
            success (bool): Success status.
            http_port (str): HTTP port for VPC sessions.
            network_interface_ip (str): Network interface IP for VPC sessions.
            token (str): Token for VPC sessions.
            vpc_resource (bool): Whether this session uses VPC resources.
            resource_url (str): Resource URL for accessing the session.
        """
        self.app_instance_id = app_instance_id
        self.resource_id = resource_id
        self.session_id = session_id
        self.success = success
        self.http_port = http_port
        self.network_interface_ip = network_interface_ip
        self.token = token
        self.vpc_resource = vpc_resource
        self.resource_url = resource_url


class GetSessionResult(ApiResponse):
    """Result of GetSession operations."""

    def __init__(
        self,
        request_id: str = "",
        http_status_code: int = 0,
        code: str = "",
        success: bool = False,
        data: Optional[GetSessionData] = None,
        error_message: str = "",
    ):
        """
        Initialize a GetSessionResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            http_status_code (int, optional): HTTP status code. Defaults to 0.
            code (str, optional): Response code. Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            data (Optional[GetSessionData], optional): Session data. Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.http_status_code = http_status_code
        self.code = code
        self.success = success
        self.data = data
        self.error_message = error_message


class OperationResult(ApiResponse):
    """Result of general operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        data: Any = None,
        error_message: str = "",
        code: str = "",
        message: str = "",
        http_status_code: int = 0,
    ):
        """
        Initialize an OperationResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            data (Any, optional): Data returned by the operation. Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
            code (str, optional): API error code. Defaults to "".
            message (str, optional): Detailed error message from API. Defaults to "".
            http_status_code (int, optional): HTTP status code. Defaults to 0.
        """
        super().__init__(request_id)
        self.success = success
        self.data = data
        self.error_message = error_message
        self.code = code
        self.message = message
        self.http_status_code = http_status_code


class BoolResult(ApiResponse):
    """Result of operations returning a boolean value."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        data: Optional[bool] = None,
        error_message: str = "",
    ):
        """
        Initialize a BoolResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            data (Optional[bool], optional): The boolean result. Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.success = success
        self.data = data
        self.error_message = error_message


def extract_request_id(response) -> str:
    """
    Extracts RequestID from API response.
    This is a helper function used to extract RequestID in all API methods.

    Args:
        response: The response object from the API call.

    Returns:
        str: The request ID extracted from the response, or an empty string if not
            found.
    """
    if response is None:
        return ""

    try:
        # Convert response to a dictionary
        response_dict = response.to_map()

        # Extract RequestId from the body field
        if isinstance(response_dict, dict) and "body" in response_dict:
            body = response_dict.get("body", {})
            if isinstance(body, dict) and "RequestId" in body:
                return body["RequestId"]
    except (AttributeError, KeyError, TypeError):
        pass

    return ""


class McpToolsResult(ApiResponse):
    """Result containing MCP tools list and request ID."""

    def __init__(self, request_id: str = "", tools: Optional[List["McpTool"]] = None):
        """
        Initialize a McpToolsResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            tools (Optional[List[McpTool]], optional): List of MCP tools.
                Defaults to None.
        """
        super().__init__(request_id)
        self.tools = tools or []
