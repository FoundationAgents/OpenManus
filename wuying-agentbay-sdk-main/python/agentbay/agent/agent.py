from agentbay.exceptions import AgentError, AgentBayError
from agentbay.api.base_service import BaseService
from agentbay.model import ApiResponse
from agentbay.logger import get_logger
import time, json

# Initialize logger for this module
logger = get_logger("agent")


class QueryResult(ApiResponse):
    """Result of query operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        output: str = "",
        error_message: str = "",
    ):
        """
        Initialize a QueryResult..

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            output (str, optional): The query output.
            error_message (str, optional): Error message if the operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.output = output
        self.error_message = error_message


class ExecutionResult(ApiResponse):
    """Result of task execution."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        error_message: str = "",
        task_id: str = "",
        task_status: str = "",
        task_result: str = "",
    ):
        """
        Initialize a ExecutionResult object.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the execution was successful.
            error_message (str, optional): Error message if the execution failed.
        """
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message
        self.task_id = task_id
        self.task_status = task_status
        self.task_result = task_result


class Agent(BaseService):
    """
    An Agent to manipulate applications to complete specific tasks.
    """

    def __init__(self, session):
        self.session = session

    def _handle_error(self, e):
        """
        Convert AgentBayError to AgentError for compatibility.

        Args:
            e (Exception): The exception to convert.

        Returns:
            AgentError: The converted exception.
        """
        if isinstance(e, AgentError):
            return e
        if isinstance(e, AgentBayError):
            return AgentError(str(e))
        return e

    def execute_task(self, task: str, max_try_times: int) -> ExecutionResult:
        """
        To execute a specific task described in the humman language.

        Args:
            task: Task description in human language.

        Returns:
            ExecutionResult: Result object containing success status, task output,
            and error message if any.
        """
        try:
            args = {"task": task}
            result = self._call_mcp_tool("flux_execute_task", args)
            if result.success:
                content = json.loads(result.data)
                task_id = content["task_id"]
                tried_time: int = 0
                while tried_time < max_try_times:
                    query = self.get_task_status(task_id)
                    content = json.loads(query.output)
                    task_status = content["status"]
                    task_result = content["product"]
                    if task_status == "finished":
                        return ExecutionResult(
                            request_id=result.request_id,
                            success=True,
                            error_message="",
                            task_id=task_id,
                            task_status=task_status,
                            task_result=task_result,
                        )
                    elif task_status == "failed":
                        return ExecutionResult(
                            request_id=result.request_id,
                            success=False,
                            error_message="Failed to execute task.",
                            task_id=task_id,
                            task_status=task_status,
                            task_result=task_result,
                        )
                    elif task_status == "unsupported":
                        return ExecutionResult(
                            request_id=result.request_id,
                            success=False,
                            error_message="Unsuppported task.",
                            task_id=task_id,
                            task_status=task_status,
                            task_result=task_result,
                        )
                    logger.info(f"Task {task_id} is still running, please wait for a while.")
                    # keep waiting unit timeout if the status is running
                    # task_status {running, finished, failed, unsupported}
                    time.sleep(3)
                    tried_time += 1
            else:
                logger.error("task execute failed")
                return ExecutionResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message or "Failed to execute task",
                    task_status="failed",
                    task_id="",
                )
        except AgentError as e:
            return ExecutionResult(request_id="", success=False, error_message=str(e))
        except Exception as e:
            return ExecutionResult(
                request_id="",
                success=False,
                error_message=f"Failed to execute: {e}",
                task_status="failed",
                task_id="",
            )

    def get_task_status(self, task_id: str) -> QueryResult:
        """
        Get the status of the task with the given task_id.
        Args:
            task_id (str): task_id

        Returns:
            QueryResult: _description_
        """
        try:
            args = {"task_id": task_id}
            result = self._call_mcp_tool("flux_get_task_status", args)
            if result.success:
                return QueryResult(
                    request_id=result.request_id,
                    success=True,
                    output=result.data,
                )
            else:
                return QueryResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message or "Failed to terminate task",
                )
        except AgentError as e:
            return QueryResult(request_id="", success=False, error_message=str(e))
        except Exception as e:
            return QueryResult(
                request_id="",
                success=False,
                error_message=f"Failed to get task status: {e}",
            )

    def terminate_task(self, task_id: str) -> ExecutionResult:
        """
        Terminate a task  with a specified task_id.

        Args:
            task_id: The id of the runnning task.

        Returns:
            ExecutionResult: Result object containing success status, task output,
            and error message if any.
        """
        logger.info("Terminating task")
        try:
            args = {"task_id": task_id}

            result = self._call_mcp_tool("flux_terminate_task", args)
            if result.success:
                content = json.loads(result.data)
                task_id = content["task_id"]
                return ExecutionResult(
                    request_id=result.request_id,
                    success=True,
                    error_message="",
                    task_id=content["task_id"],
                    task_status=content["status"],
                )
            else:
                content = json.loads(result.data)
                return ExecutionResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message or "Failed to terminate task",
                    task_id=content["task_id"],
                    task_status=content["status"],
                )
        except AgentError as e:
            return ExecutionResult(
                request_id=result.request_id,
                success=False,
                error_message=str(e),
                task_id=task_id,
                task_status="failed",
            )
        except Exception as e:
            return ExecutionResult(
                request_id="",
                success=False,
                error_message=f"Failed to terminate: {e}",
                task_id=task_id,
                task_status="failed",
            )
