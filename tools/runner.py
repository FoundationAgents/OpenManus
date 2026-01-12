import asyncio
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Mapping, Optional

from app.agent.base import TaskInterrupted
from core.task import Task
from app.tool.base import BaseTool, ToolResult


class ToolRunner:
    """Unified tool execution entry with timeout, output capture, and interruption checks."""

    def __init__(
        self,
        tools: Mapping[str, Any],
        default_timeout: Optional[float] = None,
        check_interval: float = 0.1,
    ) -> None:
        self.default_timeout = default_timeout
        self.check_interval = check_interval
        # Support ToolCollection or plain dict mapping
        if hasattr(tools, "tool_map"):
            self.tools = getattr(tools, "tool_map")
        else:
            self.tools = tools

    async def run(
        self, task: Task, tool_name: str, args: Optional[dict] = None
    ) -> ToolResult:
        if task.is_interrupted():
            raise TaskInterrupted()

        args = args or {}
        tool = self.tools.get(tool_name) if hasattr(self.tools, "get") else None
        if tool is None or not isinstance(tool, BaseTool):
            return ToolResult(error=f"Tool '{tool_name}' not found")

        async def _invoke():
            buf_out, buf_err = io.StringIO(), io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                result = await tool.execute(**args)
            return result, buf_out.getvalue(), buf_err.getvalue()

        tool_task = asyncio.create_task(_invoke())
        start = asyncio.get_event_loop().time()
        timeout = self.default_timeout

        while True:
            done, _ = await asyncio.wait(
                {tool_task}, timeout=self.check_interval, return_when=asyncio.FIRST_COMPLETED
            )
            if task.is_interrupted():
                tool_task.cancel()
                raise TaskInterrupted()
            if done:
                break
            if timeout is not None and (asyncio.get_event_loop().time() - start) > timeout:
                tool_task.cancel()
                return ToolResult(error=f"Tool '{tool_name}' execution timed out after {timeout} seconds")

        try:
            result, stdout_text, stderr_text = await tool_task
        except asyncio.CancelledError:
            return ToolResult(error=f"Tool '{tool_name}' execution cancelled")
        except Exception as exc:  # pragma: no cover - safety net
            return ToolResult(error=f"Tool '{tool_name}' failed: {exc}")

        system_info_parts = []
        if stdout_text:
            system_info_parts.append(f"stdout:\n{stdout_text}")
        if stderr_text:
            system_info_parts.append(f"stderr:\n{stderr_text}")
        system_info = "\n".join(system_info_parts) if system_info_parts else None

        if isinstance(result, ToolResult):
            if system_info:
                return result.replace(system=system_info if not result.system else f"{result.system}\n{system_info}")
            return result

        return ToolResult(output=result, system=system_info)


__all__ = ["ToolRunner"]
