from typing import Optional

from pydantic import Field

from app.sandbox.providers import ShellCommandResult, ShellService
from app.tool.base import BaseTool, ToolResult


_SHELL_DESCRIPTION = """\
Execute shell commands inside the sandbox environment.
Supports blocking and non-blocking execution depending on provider capability.
"""


class SandboxShellTool(BaseTool):
    """Provider-agnostic shell execution tool."""

    name: str = "sandbox_shell"
    description: str = _SHELL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "execute_command",
                    "check_command_output",
                    "terminate_command",
                    "list_commands",
                ],
                "description": "Shell action to perform",
            },
            "command": {
                "type": "string",
                "description": "Command to execute when using execute_command",
            },
            "folder": {
                "type": "string",
                "description": "Optional working directory relative to sandbox root",
            },
            "session_name": {
                "type": "string",
                "description": "Existing session name for long-running commands",
            },
            "blocking": {
                "type": "boolean",
                "description": "Wait for command completion when true",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for blocking commands",
                "default": 60,
            },
        },
        "required": ["action"],
    }

    shell_service: ShellService = Field(exclude=True)

    def __init__(self, shell_service: ShellService, **data):
        super().__init__(shell_service=shell_service, **data)

    async def execute(
        self,
        action: str,
        command: Optional[str] = None,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
    ) -> ToolResult:
        try:
            if action == "execute_command":
                if not command:
                    return self.fail_response("command is required for execute_command")
                result = await self.shell_service.execute(
                    command,
                    cwd=folder,
                    timeout=timeout,
                    blocking=blocking,
                    session=session_name,
                )
                return self._convert_result(result)

            if action == "check_command_output":
                if not session_name:
                    return self.fail_response("session_name is required for check")
                result = await self.shell_service.check(session_name)
                return self._convert_result(result)

            if action == "terminate_command":
                if not session_name:
                    return self.fail_response("session_name is required for terminate")
                result = await self.shell_service.terminate(session_name)
                return self._convert_result(result)

            if action == "list_commands":
                sessions = list(await self.shell_service.list_sessions())
                return self.success_response({"sessions": sessions, "count": len(sessions)})

            return self.fail_response(f"Unknown action: {action}")

        except NotImplementedError as exc:
            return self.fail_response(str(exc))
        except Exception as exc:
            return self.fail_response(f"Shell action failed: {exc}")

    def _convert_result(self, result: ShellCommandResult) -> ToolResult:
        if not result.success:
            return self.fail_response(result.error or "Shell command failed")

        payload = {
            "output": result.output or "",
            "session_name": result.session_name,
            "completed": result.completed,
            "metadata": result.metadata,
        }
        # Remove None fields for cleaner JSON
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.success_response(payload)
