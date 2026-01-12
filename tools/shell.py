from typing import Any, Dict, Optional

from app.tool.base import ToolResult
from app.tool.bash import Bash
from core.task import Task
from tools.runner import ToolRunner


class ShellResult(ToolResult):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True


class Shell:
    """Shell command runner that delegates to ToolRunner and Bash tool."""

    def __init__(self, default_timeout: Optional[float] = None):
        self.runner = ToolRunner({"bash": Bash()}, default_timeout=default_timeout)

    async def run(
        self, task: Task, command: str, timeout: Optional[float] = None
    ) -> ShellResult:
        args: Dict[str, Any] = {"command": command}
        runner = self.runner
        if timeout is not None:
            runner = ToolRunner({"bash": runner.tools["bash"]}, default_timeout=timeout)

        result = await runner.run(task, "bash", args)

        return ShellResult(
            output=result.output,
            error=result.error,
            system=result.system,
            base64_image=result.base64_image,
            stdout=result.output,
            stderr=result.error,
            exit_code=None,
        )


__all__ = ["Shell", "ShellResult"]
