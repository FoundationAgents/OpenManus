import asyncio
import os
from typing import Optional

import redis as redis_lib

from app.task_context import get_current_task
from app.tool.base import BaseTool, ToolResult


REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")


class WaitForUserInput(BaseTool):
    """Optionally wait for a mid-task user message from the web UI."""

    name: str = "wait_for_user_input"
    description: str = (
        "Optionally waits for a user message that may arrive while this task is running. "
        "Do not use this for clarification before starting work; make reasonable assumptions "
        "and continue autonomously if no message arrives before the timeout."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Optional short note explaining what information would help.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Maximum seconds to wait before continuing autonomously.",
            },
        },
    }

    async def execute(
        self, message: Optional[str] = None, timeout_seconds: Optional[int] = None
    ) -> ToolResult:
        task = get_current_task()
        if task is None or not getattr(task, "id", None):
            return ToolResult(
                output="No active task inbox is available; continue autonomously."
            )

        timeout = max(1, min(timeout_seconds or 30, 300))
        inbox_key = f"task:{task.id}:inbox"

        if message:
            task.emit(
                "user_input_wait", {"message": message, "timeout_seconds": timeout}
            )

        def _wait_for_message():
            client = redis_lib.from_url(REDIS_URL, decode_responses=True)
            try:
                return client.blpop(inbox_key, timeout=timeout)
            finally:
                client.close()

        result = await asyncio.to_thread(_wait_for_message)
        if not result:
            return ToolResult(
                output=(
                    f"No user message arrived within {timeout} seconds. "
                    "Continue with the most reasonable assumption."
                )
            )

        _key, user_message = result
        task.emit("user_message", {"message": user_message})
        return ToolResult(output=f"User message received: {user_message}")
