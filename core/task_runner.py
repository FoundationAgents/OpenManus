from typing import Any, Awaitable, Optional

from app.agent.base import TaskInterrupted
from core.task import Task, TaskStatus


async def run_with_status(
    task: Task, work: Awaitable[Any], mark_running: bool = True
) -> Any:
    """Execute an awaitable and update task status with unified rules."""

    def _set_status(status: TaskStatus, reason: Optional[str] = None) -> None:
        task.status = status
        payload = {"status": status.value}
        if reason:
            payload["reason"] = reason
        task.emit("task.status", payload)

    if mark_running:
        _set_status(TaskStatus.RUNNING)

    try:
        result = await work
        _set_status(TaskStatus.DONE)
        return result
    except TaskInterrupted:
        _set_status(TaskStatus.INTERRUPTED)
        raise
    except Exception as exc:
        _set_status(TaskStatus.FAILED, reason=str(exc))
        raise


__all__ = ["run_with_status"]
