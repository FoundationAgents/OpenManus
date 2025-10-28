from typing import Optional, List, Dict, Any, Callable
from agentbay.api.models import GetContextInfoRequest, SyncContextRequest
from agentbay.model.response import ApiResponse, extract_request_id
from .logger import get_logger, log_api_call, log_api_response
import json
import time
import threading
import asyncio

# Initialize logger for this module
logger = get_logger("context_manager")


class ContextStatusData:
    def __init__(
        self,
        context_id: str = "",
        path: str = "",
        error_message: str = "",
        status: str = "",
        start_time: int = 0,
        finish_time: int = 0,
        task_type: str = "",
    ):
        self.context_id = context_id
        self.path = path
        self.error_message = error_message
        self.status = status
        self.start_time = start_time
        self.finish_time = finish_time
        self.task_type = task_type

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextStatusData":
        return cls(
            context_id=data.get("contextId", ""),
            path=data.get("path", ""),
            error_message=data.get("errorMessage", ""),
            status=data.get("status", ""),
            start_time=data.get("startTime", 0),
            finish_time=data.get("finishTime", 0),
            task_type=data.get("taskType", ""),
        )


class ContextInfoResult(ApiResponse):
    def __init__(
        self,
        request_id: str = "",
        success: bool = True,
        context_status_data: Optional[List[ContextStatusData]] = None,
        error_message: str = "",
    ):
        super().__init__(request_id)
        self.success = success
        self.context_status_data = context_status_data or []
        self.error_message = error_message


class ContextSyncResult(ApiResponse):
    def __init__(
        self, request_id: str = "", success: bool = False, error_message: str = ""
    ):
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message


class ContextManager:
    def __init__(self, session):
        self.session = session

    def info(
        self,
        context_id: Optional[str] = None,
        path: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> ContextInfoResult:
        request = GetContextInfoRequest(
            authorization=f"Bearer {self.session.get_api_key()}",
            session_id=self.session.get_session_id(),
        )
        if context_id:
            request.context_id = context_id
        if path:
            request.path = path
        if task_type:
            request.task_type = task_type
        log_api_call(
            "GetContextInfo",
            f"SessionId={self.session.get_session_id()}, ContextId={context_id}, Path={path}, TaskType={task_type}",
        )
        response = self.session.get_client().get_context_info(request)
        try:
            response_body = json.dumps(
                response.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"📥 Response: {response}")
        request_id = extract_request_id(response)
        response_map = response.to_map()

        context_status_data = []
        if isinstance(response_map, dict):
            body = response_map.get("body", {})

            # Check for API-level errors
            if not body.get("Success", True) and body.get("Code"):
                code = body.get("Code", "Unknown")
                message = body.get("Message", "Unknown error")
                return ContextInfoResult(
                    request_id=request_id,
                    success=False,
                    context_status_data=[],
                    error_message=f"[{code}] {message}",
                )

            data = body.get("Data", {})
            context_status_str = data.get("ContextStatus", "")

            # Parse the context status data
            if context_status_str:
                try:
                    # First, parse the outer array
                    status_items = json.loads(context_status_str)
                    for item in status_items:
                        if item.get("type") == "data":
                            # Parse the inner data string
                            data_items = json.loads(item.get("data", "[]"))
                            for data_item in data_items:
                                context_status_data.append(
                                    ContextStatusData.from_dict(data_item)
                                )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error parsing context status: {e}")
                except Exception as e:
                    logger.error(f"❌ Unexpected error parsing context status: {e}")

        return ContextInfoResult(
            request_id=request_id,
            success=True,
            context_status_data=context_status_data,
            error_message="",
        )

    async def sync(
        self,
        context_id: Optional[str] = None,
        path: Optional[str] = None,
        mode: Optional[str] = None,
        callback: Optional[Callable[[bool], None]] = None,
        max_retries: int = 150,
        retry_interval: int = 1500,
    ) -> ContextSyncResult:
        """
        Synchronizes context with support for both async and sync calling patterns.

        Usage:
            # Async call - wait for completion
            result = await session.context.sync()

            # Sync call - immediate return with callback
            session.context.sync(callback=lambda success: print(f"Done: {success}"))

        Args:
            context_id: ID of the context to sync
            path: Path to sync
            mode: Sync mode
            callback: Optional callback function that receives success status
            max_retries: Maximum number of retries for polling (default: 150)
            retry_interval: Milliseconds to wait between retries (default: 1500)

        Returns:
            ContextSyncResult: Result of the sync operation
        """
        request = SyncContextRequest(
            authorization=f"Bearer {self.session.get_api_key()}",
            session_id=self.session.get_session_id(),
        )
        if context_id:
            request.context_id = context_id
        if path:
            request.path = path
        if mode:
            request.mode = mode
        log_api_call(
            "SyncContext",
            f"SessionId={self.session.get_session_id()}, ContextId={context_id}, Path={path}, Mode={mode}",
        )
        response = self.session.get_client().sync_context(request)
        try:
            response_body = json.dumps(
                response.to_map().get("body", {}), ensure_ascii=False, indent=2
            )
            log_api_response(response_body)
        except Exception:
            logger.debug(f"📥 Response: {response}")
        request_id = extract_request_id(response)
        response_map = response.to_map()
        success = False
        if isinstance(response_map, dict):
            body = response_map.get("body", {})

            # Check for API-level errors
            if not body.get("Success", True) and body.get("Code"):
                code = body.get("Code", "Unknown")
                message = body.get("Message", "Unknown error")
                return ContextSyncResult(
                    request_id=request_id,
                    success=False,
                    error_message=f"[{code}] {message}",
                )

            success = body.get("Success", False)

        # If callback is provided, start polling in background thread (sync mode)
        if callback is not None and success:
            # Check if we're in an event loop
            try:
                asyncio.get_running_loop()
                # We're in an event loop, start polling in background thread
                poll_thread = threading.Thread(
                    target=self._poll_for_completion,
                    args=(callback, context_id, path, max_retries, retry_interval),
                    daemon=True,
                )
                poll_thread.start()
                return ContextSyncResult(request_id=request_id, success=success)
            except RuntimeError:
                # No event loop running, start polling in background thread
                poll_thread = threading.Thread(
                    target=self._poll_for_completion,
                    args=(callback, context_id, path, max_retries, retry_interval),
                    daemon=True,
                )
                poll_thread.start()
                return ContextSyncResult(request_id=request_id, success=success)

        # If no callback, wait for completion (async mode)
        if success:
            final_success = await self._poll_for_completion_async(
                context_id, path, max_retries, retry_interval
            )
            return ContextSyncResult(request_id=request_id, success=final_success)

        return ContextSyncResult(request_id=request_id, success=success)

    def _poll_for_completion(
        self,
        callback: Callable[[bool], None],
        context_id: Optional[str] = None,
        path: Optional[str] = None,
        max_retries: int = 150,
        retry_interval: int = 1500,
    ) -> None:
        """
        Polls the info interface to check if sync is completed and calls callback.

        Args:
            callback: Callback function that receives success status
            context_id: ID of the context to check
            path: Path to check
            max_retries: Maximum number of retries
            retry_interval: Milliseconds to wait between retries
        """
        for retry in range(max_retries):
            try:
                # Get context status data
                info_result = self.info(context_id=context_id, path=path)

                # Check if all sync tasks are completed
                all_completed = True
                has_failure = False
                has_sync_tasks = False

                for item in info_result.context_status_data:
                    # We only care about sync tasks (upload/download)
                    if item.task_type not in ["upload", "download"]:
                        continue

                    has_sync_tasks = True
                    logger.info(
                        f"🔄 Sync task {item.context_id} status: {item.status}, path: {item.path}"
                    )

                    if item.status not in ["Success", "Failed"]:
                        all_completed = False
                        break

                    if item.status == "Failed":
                        has_failure = True
                        logger.error(
                            f"❌ Sync failed for context {item.context_id}: {item.error_message}"
                        )

                if all_completed or not has_sync_tasks:
                    # All tasks completed or no sync tasks found
                    if has_failure:
                        logger.warning("Context sync completed with failures")
                        callback(False)
                    elif has_sync_tasks:
                        logger.info("✅ Context sync completed successfully")
                        callback(True)
                    else:
                        logger.info("ℹ️  No sync tasks found")
                        callback(True)
                    break

                logger.info(
                    f"⏳ Waiting for context sync to complete, attempt {retry+1}/{max_retries}"
                )
                time.sleep(retry_interval / 1000.0)

            except Exception as e:
                logger.error(
                    f"❌ Error checking context status on attempt {retry+1}: {e}"
                )
                time.sleep(retry_interval / 1000.0)

        # If we've exhausted all retries, call callback with failure
        if retry == max_retries - 1:
            logger.error(
                f"❌ Context sync polling timed out after {max_retries} attempts"
            )
            callback(False)

    async def _poll_for_completion_async(
        self,
        context_id: Optional[str] = None,
        path: Optional[str] = None,
        max_retries: int = 150,
        retry_interval: int = 1500,
    ) -> bool:
        """
        Async version of polling for sync completion.

        Args:
            context_id: ID of the context to check
            path: Path to check
            max_retries: Maximum number of retries
            retry_interval: Milliseconds to wait between retries

        Returns:
            bool: True if sync completed successfully, False otherwise
        """
        for retry in range(max_retries):
            try:
                # Get context status data
                info_result = self.info(context_id=context_id, path=path)

                # Check if all sync tasks are completed
                all_completed = True
                has_failure = False
                has_sync_tasks = False

                for item in info_result.context_status_data:
                    # We only care about sync tasks (upload/download)
                    if item.task_type not in ["upload", "download"]:
                        continue

                    has_sync_tasks = True
                    logger.info(
                        f"🔄 Sync task {item.context_id} status: {item.status}, path: {item.path}"
                    )

                    if item.status not in ["Success", "Failed"]:
                        all_completed = False
                        break

                    if item.status == "Failed":
                        has_failure = True
                        logger.error(
                            f"❌ Sync failed for context {item.context_id}: {item.error_message}"
                        )

                if all_completed or not has_sync_tasks:
                    # All tasks completed or no sync tasks found
                    if has_failure:
                        logger.warning("Context sync completed with failures")
                        return False
                    elif has_sync_tasks:
                        logger.info("✅ Context sync completed successfully")
                        return True
                    else:
                        logger.info("ℹ️  No sync tasks found")
                        return True

                logger.info(
                    f"⏳ Waiting for context sync to complete, attempt {retry+1}/{max_retries}"
                )
                await asyncio.sleep(retry_interval / 1000.0)

            except Exception as e:
                logger.error(
                    f"❌ Error checking context status on attempt {retry+1}: {e}"
                )
                await asyncio.sleep(retry_interval / 1000.0)

        # If we've exhausted all retries, return failure
        logger.error(f"❌ Context sync polling timed out after {max_retries} attempts")
        return False
