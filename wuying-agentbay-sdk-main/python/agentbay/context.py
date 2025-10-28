from typing import TYPE_CHECKING, List, Optional

from agentbay.api.models import (
    DeleteContextRequest,
    GetContextRequest,
    ListContextsRequest,
    ModifyContextRequest,
    DescribeContextFilesRequest,
    GetContextFileDownloadUrlRequest,
    GetContextFileUploadUrlRequest,
    DeleteContextFileRequest,
)
from agentbay.exceptions import AgentBayError
from agentbay.model.response import ApiResponse, OperationResult, extract_request_id
from .logger import get_logger, log_api_call, log_api_response, log_operation_error
import json

# Initialize logger for this module
logger = get_logger("context")

if TYPE_CHECKING:
    from agentbay.agentbay import AgentBay


class Context:
    """
    Represents a persistent storage context in the AgentBay cloud environment.

    Attributes:
        id (str): The unique identifier of the context.
        name (str): The name of the context.
        state (str): **Deprecated.** This field is no longer used and will be removed in a future version.
        created_at (str): Date and time when the Context was created.
        last_used_at (str): Date and time when the Context was last used.
        os_type (str): **Deprecated.** This field is no longer used and will be removed in a future version.
    """

    def __init__(
        self,
        id: str,
        name: str,
        state: str = "available",
        created_at: Optional[str] = None,
        last_used_at: Optional[str] = None,
        os_type: Optional[str] = None,
    ):
        """
        Initialize a Context object.

        Args:
            id (str): The unique identifier of the context.
            name (str): The name of the context.
            state (str, optional): **Deprecated.** This parameter is no longer used.
            created_at (Optional[str], optional): Date and time when the Context was
                created. Defaults to None.
            last_used_at (Optional[str], optional): Date and time when the Context was
                last used. Defaults to None.
            os_type (Optional[str], optional): **Deprecated.** This parameter is no longer used.
        """
        self.id = id
        self.name = name
        self.state = state
        self.created_at = created_at
        self.last_used_at = last_used_at
        self.os_type = os_type


class ContextResult(ApiResponse):
    """Result of operations returning a Context."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        context_id: str = "",
        context: Optional[Context] = None,
        error_message: str = "",
    ):
        """
        Initialize a ContextResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            context_id (str, optional): The unique identifier of the context.
            context (Optional[Context], optional): The Context object.
            error_message (str, optional): Error message if operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.context_id = context_id
        self.context = context
        self.error_message = error_message


class ContextListResult(ApiResponse):
    """Result of operations returning a list of Contexts."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        contexts: Optional[List[Context]] = None,
        next_token: Optional[str] = None,
        max_results: Optional[int] = None,
        total_count: Optional[int] = None,
        error_message: str = "",
    ):
        """
        Initialize a ContextListResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            contexts (Optional[List[Context]], optional): The list of context objects.
            next_token (Optional[str], optional): Token for the next page of results.
            max_results (Optional[int], optional): Maximum number of results per page.
            total_count (Optional[int], optional): Total number of contexts available.
            error_message (str, optional): Error message if operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.contexts = contexts if contexts is not None else []
        self.next_token = next_token
        self.max_results = max_results
        self.total_count = total_count
        self.error_message = error_message


class ContextFileEntry:
    """Represents a file item in a context."""

    def __init__(
        self,
        file_id: str,
        file_name: str,
        file_path: str,
        file_type: Optional[str] = None,
        gmt_create: Optional[str] = None,
        gmt_modified: Optional[str] = None,
        size: Optional[int] = None,
        status: Optional[str] = None,
    ):
        self.file_id = file_id
        self.file_name = file_name
        self.file_path = file_path
        self.file_type = file_type
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified
        self.size = size
        self.status = status


class FileUrlResult(ApiResponse):
    """Result of a presigned URL request."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        url: str = "",
        expire_time: Optional[int] = None,
        error_message: str = "",
    ):
        super().__init__(request_id)
        self.success = success
        self.url = url
        self.expire_time = expire_time
        self.error_message = error_message


class ContextFileListResult(ApiResponse):
    """Result of file listing operation."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        entries: Optional[List[ContextFileEntry]] = None,
        count: Optional[int] = None,
    ):
        super().__init__(request_id)
        self.success = success
        self.entries = entries or []
        self.count = count


class ContextListParams:
    """Parameters for listing contexts with pagination support."""

    def __init__(
        self,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ):
        """
        Initialize ContextListParams.

        Args:
            max_results (Optional[int], optional): Maximum number of results per page.
                Defaults to 10 if not specified.
            next_token (Optional[str], optional): Token for the next page of results.
        """
        self.max_results = max_results
        self.next_token = next_token


class ContextService:
    """
    Provides methods to manage persistent contexts in the AgentBay cloud environment.
    """

    def __init__(self, agent_bay: "AgentBay"):
        """
        Initialize the ContextService.

        Args:
            agent_bay (AgentBay): The AgentBay instance.
        """
        self.agent_bay = agent_bay

    def list(self, params: Optional[ContextListParams] = None) -> ContextListResult:
        """
        Lists all available contexts with pagination support.

        Args:
            params (Optional[ContextListParams], optional): Parameters for listing contexts.
                If None, defaults will be used.

        Returns:
            ContextListResult: A result object containing the list of Context objects,
                pagination information, and request ID.
        """
        try:
            if params is None:
                params = ContextListParams()
            max_results = params.max_results if params.max_results is not None else 10
            request_details = f"MaxResults={max_results}"
            if params.next_token:
                request_details += f", NextToken={params.next_token}"
            log_api_call("ListContexts", request_details)
            request = ListContextsRequest(
                authorization=f"Bearer {self.agent_bay.api_key}",
                max_results=max_results,
                next_token=params.next_token,
            )
            response = self.agent_bay.client.list_contexts(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")
            request_id = extract_request_id(response)
            try:
                response_map = response.to_map()
                if not isinstance(response_map, dict):
                    return ContextListResult(
                        request_id=request_id,
                        success=False,
                        contexts=[],
                        error_message="Invalid response format",
                    )
                body = response_map.get("body", {})
                if not isinstance(body, dict):
                    return ContextListResult(
                        request_id=request_id,
                        success=False,
                        contexts=[],
                        error_message="Invalid response body",
                    )

                # Check for API-level errors
                if not body.get("Success", True) and body.get("Code"):
                    code = body.get("Code", "Unknown")
                    message = body.get("Message", "Unknown error")
                    return ContextListResult(
                        request_id=request_id,
                        success=False,
                        contexts=[],
                        error_message=f"[{code}] {message}",
                    )

                contexts = []
                response_data = body.get("Data", [])
                if response_data and isinstance(response_data, list):
                    for context_data in response_data:
                        if isinstance(context_data, dict):
                            context = Context(
                                id=context_data.get("Id", ""),
                                name=context_data.get("Name", ""),
                                state=context_data.get("State", ""),
                                created_at=context_data.get("CreateTime"),
                                last_used_at=context_data.get("LastUsedTime"),
                                os_type=context_data.get("OsType"),
                            )
                            contexts.append(context)
                next_token = body.get("NextToken")
                max_results = body.get("MaxResults", max_results)
                total_count = body.get("TotalCount")
                return ContextListResult(
                    request_id=request_id,
                    success=True,
                    contexts=contexts,
                    next_token=next_token,
                    max_results=max_results,
                    total_count=total_count,
                    error_message="",
                )
            except Exception as e:
                log_operation_error("parse ListContexts response", str(e))
                return ContextListResult(
                    request_id=request_id,
                    success=False,
                    contexts=[],
                    error_message=f"Failed to parse response: {e}",
                )
        except Exception as e:
            log_operation_error("ListContexts", str(e))
            return ContextListResult(
                request_id="",
                success=False,
                contexts=[],
                next_token=None,
                max_results=None,
                total_count=None,
                error_message=f"Failed to list contexts: {e}",
            )

    def get(self, name: str, create: bool = False) -> ContextResult:
        """
        Gets a context by name. Optionally creates it if it doesn't exist.

        Args:
            name (str): The name of the context to get.
            create (bool, optional): Whether to create the context if it doesn't exist.

        Returns:
            ContextResult: The ContextResult object containing the Context and request
                ID.
        """
        try:
            log_api_call("GetContext", f"Name={name}, AllowCreate={create}")
            request = GetContextRequest(
                name=name,
                allow_create=create,
                authorization=f"Bearer {self.agent_bay.api_key}",
            )
            response = self.agent_bay.client.get_context(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")
            request_id = extract_request_id(response)
            try:
                response_map = response.to_map()
                if not isinstance(response_map, dict):
                    return ContextResult(
                        request_id=request_id,
                        success=False,
                        context_id="",
                        context=None,
                        error_message="Invalid response format",
                    )

                body = response_map.get("body", {})
                if not isinstance(body, dict):
                    return ContextResult(
                        request_id=request_id,
                        success=False,
                        context_id="",
                        context=None,
                        error_message="Invalid response body",
                    )

                # Check for API-level errors
                if not body.get("Success", True) and body.get("Code"):
                    code = body.get("Code", "Unknown")
                    message = body.get("Message", "Unknown error")
                    return ContextResult(
                        request_id=request_id,
                        success=False,
                        context_id="",
                        context=None,
                        error_message=f"[{code}] {message}",
                    )

                data = body.get("Data", {})
                if not isinstance(data, dict):
                    return ContextResult(
                        request_id=request_id,
                        success=False,
                        context_id="",
                        context=None,
                        error_message="Invalid data format",
                    )
                context_id = data.get("Id", "")
                context = Context(
                    id=context_id,
                    name=data.get("Name", "") or name,
                    state=data.get("State", "") or "available",
                    created_at=data.get("CreateTime"),
                    last_used_at=data.get("LastUsedTime"),
                    os_type=data.get("OsType"),
                )
                return ContextResult(
                    request_id=request_id,
                    success=True,
                    context_id=context_id,
                    context=context,
                    error_message="",
                )
            except Exception as e:
                log_operation_error("parse GetContext response", str(e))
                return ContextResult(
                    request_id=request_id,
                    success=False,
                    context_id="",
                    context=None,
                    error_message=f"Failed to parse response: {e}",
                )
        except Exception as e:
            log_operation_error("GetContext", str(e))
            return ContextResult(
                request_id="",
                success=False,
                context_id="",
                context=None,
                error_message=f"Failed to get context {name}: {e}",
            )

    def create(self, name: str) -> ContextResult:
        """
        Creates a new context with the given name.

        Args:
            name (str): The name for the new context.

        Returns:
            ContextResult: The created ContextResult object with request ID.
        """
        return self.get(name, create=True)

    def update(self, context: Context) -> OperationResult:
        """
        Updates the specified context.

        Args:
            context (Context): The Context object to update.

        Returns:
            OperationResult: Result object containing success status and request ID.
        """
        try:
            log_api_call("ModifyContext", f"Id={context.id}, Name={context.name}")
            request = ModifyContextRequest(
                id=context.id,
                name=context.name,
                authorization=f"Bearer {self.agent_bay.api_key}",
            )
            response = self.agent_bay.client.modify_context(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")
            request_id = extract_request_id(response)
            try:
                response_map = response.to_map() if hasattr(response, "to_map") else {}
                if not isinstance(response_map, dict) or not isinstance(
                    response_map.get("body", {}), dict
                ):
                    return OperationResult(
                        request_id=request_id,
                        success=False,
                        error_message="Invalid response format",
                    )
                body = response_map.get("body", {})
                success = body.get("Success", False)
                error_message = (
                    ""
                    if success
                    else f"[{body.get('Code', 'Unknown')}] {body.get('Message', 'Unknown error')}"
                )
                return OperationResult(
                    request_id=request_id,
                    success=success,
                    data=True if success else False,
                    error_message=error_message,
                )
            except Exception as e:
                logger.error(f"Error parsing ModifyContext response: {e}")
                return OperationResult(
                    request_id=request_id,
                    success=False,
                    error_message=f"Failed to parse response: {str(e)}",
                )
        except Exception as e:
            logger.error(f"Error calling ModifyContext: {e}")
            raise AgentBayError(f"Failed to update context {context.id}: {e}")

    def delete(self, context: Context) -> OperationResult:
        """
        Deletes the specified context.

        Args:
            context (Context): The Context object to delete.

        Returns:
            OperationResult: Result object containing success status and request ID.
        """
        try:
            log_api_call("DeleteContext", f"Id={context.id}")
            request = DeleteContextRequest(
                id=context.id, authorization=f"Bearer {self.agent_bay.api_key}"
            )
            response = self.agent_bay.client.delete_context(request)
            try:
                response_body = json.dumps(
                    response.to_map().get("body", {}), ensure_ascii=False, indent=2
                )
                log_api_response(response_body)
            except Exception:
                logger.debug(f"📥 Response: {response}")
            request_id = extract_request_id(response)
            try:
                response_map = response.to_map() if hasattr(response, "to_map") else {}
                if not isinstance(response_map, dict) or not isinstance(
                    response_map.get("body", {}), dict
                ):
                    return OperationResult(
                        request_id=request_id,
                        success=False,
                        error_message="Invalid response format",
                    )
                body = response_map.get("body", {})
                success = body.get("Success", False)
                error_message = (
                    ""
                    if success
                    else f"[{body.get('Code', 'Unknown')}] {body.get('Message', 'Unknown error')}"
                )
                return OperationResult(
                    request_id=request_id,
                    success=success,
                    data=True if success else False,
                    error_message=error_message,
                )
            except Exception as e:
                logger.error(f"Error parsing DeleteContext response: {e}")
                return OperationResult(
                    request_id=request_id,
                    success=False,
                    error_message=f"Failed to parse response: {str(e)}",
                )
        except Exception as e:
            logger.error(f"Error calling DeleteContext: {e}")
            raise AgentBayError(f"Failed to delete context {context.id}: {e}")

    def get_file_download_url(self, context_id: str, file_path: str) -> FileUrlResult:
        """Get a presigned download URL for a file in a context."""
        log_api_call(
            "GetContextFileDownloadUrl", f"ContextId={context_id}, FilePath={file_path}"
        )
        req = GetContextFileDownloadUrlRequest(
            authorization=f"Bearer {self.agent_bay.api_key}",
            context_id=context_id,
            file_path=file_path,
        )
        resp = self.agent_bay.client.get_context_file_download_url(req)
        try:
            response_body = json.dumps(
                resp.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"Response: {resp}")
        request_id = extract_request_id(resp)
        body = getattr(resp, "body", None)

        # Check for API-level errors
        if body:
            success = getattr(body, "success", False)
            if not success:
                code = getattr(body, "code", "Unknown")
                message = getattr(body, "message", "Unknown error")
                return FileUrlResult(
                    request_id=request_id,
                    success=False,
                    url="",
                    expire_time=None,
                    error_message=f"[{code}] {message}",
                )

        data = getattr(body, "data", None)
        return FileUrlResult(
            request_id=request_id,
            success=bool(body and getattr(body, "success", False)),
            url=(data.url if data else ""),
            expire_time=(data.expire_time if data else None),
            error_message="",
        )

    def get_file_upload_url(self, context_id: str, file_path: str) -> FileUrlResult:
        """Get a presigned upload URL for a file in a context."""
        log_api_call(
            "GetContextFileUploadUrl", f"ContextId={context_id}, FilePath={file_path}"
        )
        req = GetContextFileUploadUrlRequest(
            authorization=f"Bearer {self.agent_bay.api_key}",
            context_id=context_id,
            file_path=file_path,
        )
        resp = self.agent_bay.client.get_context_file_upload_url(req)
        try:
            response_body = json.dumps(
                resp.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"Response: {resp}")
        request_id = extract_request_id(resp)
        body = getattr(resp, "body", None)

        # Check for API-level errors
        if body:
            success = getattr(body, "success", False)
            if not success:
                code = getattr(body, "code", "Unknown")
                message = getattr(body, "message", "Unknown error")
                return FileUrlResult(
                    request_id=request_id,
                    success=False,
                    url="",
                    expire_time=None,
                    error_message=f"[{code}] {message}",
                )

        data = getattr(body, "data", None)
        return FileUrlResult(
            request_id=request_id,
            success=bool(body and getattr(body, "success", False)),
            url=(data.url if data else ""),
            expire_time=(data.expire_time if data else None),
            error_message="",
        )

    def delete_file(self, context_id: str, file_path: str) -> OperationResult:
        """Delete a file in a context."""
        log_api_call(
            "DeleteContextFile", f"ContextId={context_id}, FilePath={file_path}"
        )
        req = DeleteContextFileRequest(
            authorization=f"Bearer {self.agent_bay.api_key}",
            context_id=context_id,
            file_path=file_path,
        )
        resp = self.agent_bay.client.delete_context_file(req)
        try:
            response_body = json.dumps(
                resp.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"Response: {resp}")
        request_id = extract_request_id(resp)
        body = getattr(resp, "body", None)
        success = bool(body and getattr(body, "success", False))

        # Check for API-level errors
        error_message = ""
        if not success and body:
            code = getattr(body, "code", "Unknown")
            message = getattr(body, "message", "Failed to delete file")
            error_message = f"[{code}] {message}"

        return OperationResult(
            request_id=request_id,
            success=success,
            data=True if success else False,
            error_message=error_message,
        )

    def list_files(
        self,
        context_id: str,
        parent_folder_path: str,
        page_number: int = 1,
        page_size: int = 50,
    ) -> ContextFileListResult:
        """List files under a specific folder path in a context."""
        log_api_call(
            "DescribeContextFiles",
            f"ContextId={context_id}, ParentFolderPath={parent_folder_path}, "
            f"PageNumber={page_number}, PageSize={page_size}",
        )
        req = DescribeContextFilesRequest(
            authorization=f"Bearer {self.agent_bay.api_key}",
            page_number=page_number,
            page_size=page_size,
            parent_folder_path=parent_folder_path,
            context_id=context_id,
        )
        resp = self.agent_bay.client.describe_context_files(req)
        try:
            response_body = json.dumps(
                resp.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"Response: {resp}")
        request_id = extract_request_id(resp)
        body = getattr(resp, "body", None)
        raw_list = getattr(body, "data", None) or []
        entries = [
            ContextFileEntry(
                file_id=getattr(it, "file_id", ""),
                file_name=getattr(it, "file_name", ""),
                file_path=getattr(it, "file_path", ""),
                file_type=getattr(it, "file_type", None),
                gmt_create=getattr(it, "gmt_create", None),
                gmt_modified=getattr(it, "gmt_modified", None),
                size=getattr(it, "size", None),
                status=getattr(it, "status", None),
            )
            for it in raw_list
        ]
        return ContextFileListResult(
            request_id=request_id,
            success=bool(body and getattr(body, "success", False)),
            entries=entries,
            count=(getattr(body, "count", None) if body else None),
        )
