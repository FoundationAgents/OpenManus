import json
import requests
import time
import random
import string
from typing import Any, Dict

from agentbay.api.models import CallMcpToolRequest
from agentbay.exceptions import AgentBayError
from agentbay.model import OperationResult, extract_request_id
from agentbay.logger import (
    get_logger,
    log_api_call,
    log_api_response,
    log_operation_error,
)

# Initialize logger for this module
logger = get_logger("base_service")


class BaseService:
    """
    Base service class that provides common functionality for all service classes.
    This class implements the common methods for calling MCP tools and parsing
    responses.
    """

    def __init__(self, session):
        """
        Initialize a BaseService object.

        Args:
            session: The Session instance that this service belongs to.
        """
        self.session = session

    def _handle_error(self, e):
        """
        Handle and convert exceptions. This method should be overridden by subclasses
        to provide specific error handling.

        Args:
            e (Exception): The exception to handle.

        Returns:
            Exception: The handled exception.
        """
        return e

    def _call_mcp_tool_vpc(
        self, tool_name: str, args_json: str, default_error_msg: str
    ) -> OperationResult:
        """
        Handle VPC-based MCP tool calls using HTTP requests.

        Args:
            tool_name: Name of the tool to call
            args_json: JSON string of arguments
            default_error_msg: Default error message

        Returns:
            OperationResult: The response from the tool
        """
        log_api_call(f"CallMcpTool (VPC) - {tool_name}", f"Args={args_json}")

        # Find server for this tool
        server = self.session.find_server_for_tool(tool_name)
        if not server:
            return OperationResult(
                request_id="",
                success=False,
                error_message=f"server not found for tool: {tool_name}",
            )

        # Construct VPC URL with query parameters
        base_url = f"http://{self.session.get_network_interface_ip()}:{self.session.get_http_port()}/callTool"

        # Prepare query parameters
        # Add requestId for debugging purposes
        request_id = f"vpc-{int(time.time() * 1000)}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=9))}"
        params = {
            "server": server,
            "tool": tool_name,
            "args": args_json,
            "token": self.session.get_token(),
            "requestId": request_id,
        }

        # Set headers
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            # Send HTTP request
            response = requests.get(
                base_url, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            log_api_response(json.dumps(response_data, ensure_ascii=False))

            # Extract the actual result from the nested VPC response structure
            actual_result = None
            if isinstance(response_data.get("data"), str):
                try:
                    data_map = json.loads(response_data["data"])
                    if "result" in data_map:
                        actual_result = data_map["result"]
                except json.JSONDecodeError:
                    pass
            elif isinstance(response_data.get("data"), dict):
                actual_result = response_data["data"]

            if actual_result is None:
                actual_result = response_data

            # For VPC responses, we need to parse the content similar to non-VPC mode
            # The actual_result contains the parsed response structure
            if isinstance(actual_result, dict) and "content" in actual_result:
                # Extract text from content array
                content = actual_result.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    content_item = content[0]
                    if isinstance(content_item, dict) and "text" in content_item:
                        actual_result = content_item["text"]

            return OperationResult(
                request_id="",  # VPC requests don't have traditional request IDs
                success=True,
                data=actual_result,
            )

        except requests.RequestException as e:
            sanitized_error = self._sanitize_error(str(e))
            log_operation_error(f"CallMcpTool (VPC) - {tool_name}", sanitized_error)
            return OperationResult(
                request_id="",
                success=False,
                error_message=f"failed to call VPC {tool_name}: {e}",
            )

    def _call_mcp_tool(
        self,
        name: str,
        args: Dict[str, Any],
        read_timeout: int = None,
        connect_timeout: int = None,
    ) -> OperationResult:
        """
        Internal helper to call MCP tool and handle errors.

        Args:
            name (str): The name of the tool to call.
            args (Dict[str, Any]): The arguments to pass to the tool.

        Returns:
            OperationResult: The response from the tool with request ID.
        """
        try:
            args_json = json.dumps(args, ensure_ascii=False)

            # Check if this is a VPC session
            if self.session.is_vpc_enabled():
                return self._call_mcp_tool_vpc(
                    name, args_json, f"Failed to call {name}"
                )

            # Non-VPC mode: use traditional API call
            request = CallMcpToolRequest(
                authorization=f"Bearer {self.session.get_api_key()}",
                session_id=self.session.get_session_id(),
                name=name,
                args=args_json,
            )
            response = self.session.get_client().call_mcp_tool(
                request, read_timeout=read_timeout, connect_timeout=connect_timeout
            )

            # Extract request ID
            request_id = extract_request_id(response)

            response_map = response.to_map()
            if not response_map:
                return OperationResult(
                    request_id=request_id,
                    success=False,
                    error_message="Invalid response format",
                )

            body = response_map.get("body", {})
            try:
                response_body = json.dumps(body, ensure_ascii=False, indent=2)
                log_api_response(response_body)
            except Exception:
                logger.debug(f"Response: {body}")
            if not body:
                return OperationResult(
                    request_id=request_id,
                    success=False,
                    error_message="Invalid response body",
                )

            # Check for API-level errors before parsing Data
            if not body.get("Success", True) and body.get("Code"):
                code = body.get("Code", "Unknown")
                message = body.get("Message", "Unknown error")
                return OperationResult(
                    request_id=request_id,
                    success=False,
                    error_message=f"[{code}] {message}",
                )

            result = self._parse_response_body(body)
            return OperationResult(request_id=request_id, success=True, data=result)

        except AgentBayError as e:
            handled_error = self._handle_error(e)
            request_id = "" if "request_id" not in locals() else request_id
            return OperationResult(
                request_id=request_id,
                success=False,
                error_message=str(handled_error),
            )
        except Exception as e:
            handled_error = self._handle_error(e)
            request_id = "" if "request_id" not in locals() else request_id
            return OperationResult(
                request_id=request_id,
                success=False,
                error_message=f"Failed to call MCP tool {name}: {handled_error}",
            )

    def _sanitize_error(self, error_str: str) -> str:
        """
        Sanitizes error messages to remove sensitive information like API keys.

        Args:
            error_str (str): The error string to sanitize.

        Returns:
            str: The sanitized error string.
        """
        import re

        if not error_str:
            return error_str

        # Remove API key from URLs
        # Pattern: apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        api_key_pattern = re.compile(r"apiKey=akm-[a-f0-9-]+")
        error_str = api_key_pattern.sub("apiKey=***REDACTED***", error_str)

        # Remove API key from Bearer tokens
        # Pattern: Bearer akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        bearer_pattern = re.compile(r"Bearer akm-[a-f0-9-]+")
        error_str = bearer_pattern.sub("Bearer ***REDACTED***", error_str)

        # Remove API key from query parameters
        # Pattern: &apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        query_pattern = re.compile(r"&apiKey=akm-[a-f0-9-]+")
        error_str = query_pattern.sub("&apiKey=***REDACTED***", error_str)

        # Remove API key from URL paths
        # Pattern: /callTool?apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        url_pattern = re.compile(r"/callTool\?apiKey=akm-[a-f0-9-]+")
        error_str = url_pattern.sub("/callTool?apiKey=***REDACTED***", error_str)

        return error_str

    def _parse_response_body(
        self, body: Dict[str, Any], parse_json: bool = False
    ) -> Any:
        """
        Parses the response body from the MCP tool.

        Args:
            body (Dict[str, Any]): The response body.
            parse_json (bool, optional): Whether to parse the text as JSON.
            Defaults to False.

        Returns:
            Any: The parsed content. If parse_json is True, returns the parsed
                 JSON object; otherwise returns the raw text.


        Raises:
            AgentBayError: If the response contains errors or is invalid.
        """
        try:
            if body.get("Data", {}).get("isError", False):
                error_content = body.get("Data", {}).get("content", [])
                try:
                    error_content_json = json.dumps(
                        error_content, ensure_ascii=False, indent=2
                    )
                    logger.debug(f"error_content = {error_content_json}")
                except Exception:
                    logger.debug(f"error_content: {error_content}")
                error_message = "; ".join(
                    item.get("text", "Unknown error")
                    for item in error_content
                    if isinstance(item, dict)
                )
                raise AgentBayError(f"Error in response: {error_message}")

            response_data = body.get("Data", {})
            if not response_data:
                raise AgentBayError("No data field in response")

            # Handle 'content' field for other methods
            content = response_data.get("content", [])
            if not content or not isinstance(content, list):
                raise AgentBayError("No content found in response")

            content_item = content[0]
            text_string = content_item.get("text")

            # Allow text field to be empty string
            if text_string is None:
                raise AgentBayError("Text field not found in response")

            return text_string

        except AgentBayError as e:
            # Transform AgentBayError to the expected type
            handled_error = self._handle_error(e)
            raise handled_error
        except Exception as e:
            # Transform AgentBayError to the expected type
            handled_error = self._handle_error(
                AgentBayError(f"Error parsing response body: {e}")
            )
            raise handled_error
