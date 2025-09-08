import asyncio
import time
from typing import Any, Dict, Optional, TypeVar
from uuid import uuid4

from app.daytona.tool_base import Sandbox, SandboxToolsBase
from app.tool.base import ToolResult
from app.utils.logger import logger


Context = TypeVar("Context")
_SHELL_DESCRIPTION = """\
Execute a shell command in the workspace directory.
IMPORTANT: Commands are non-blocking by default and run in a tmux session.
This is ideal for long-running operations like starting servers or build processes.
Uses sessions to maintain state between commands.
This tool is essential for running CLI tools, installing packages, and managing system operations.
"""


class SandboxShellTool(SandboxToolsBase):
    """Tool for executing tasks in a Daytona sandbox with browser-use capabilities.
    Uses sessions for maintaining state between commands and provides comprehensive process management.
    """

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
                "description": "The shell action to perform",
            },
            "command": {
                "type": "string",
                "description": "The shell command to execute. Use this for running CLI tools, installing packages, "
                "or system operations. Commands can be chained using &&, ||, and | operators.",
            },
            "folder": {
                "type": "string",
                "description": "Optional relative path to a subdirectory of /workspace where the command should be "
                "executed. Example: 'data/pdfs'",
            },
            "session_name": {
                "type": "string",
                "description": "Optional name of the tmux session to use. Use named sessions for related commands "
                "that need to maintain state. Defaults to a random session name.",
            },
            "blocking": {
                "type": "boolean",
                "description": "Whether to wait for the command to complete. Defaults to false for non-blocking "
                "execution.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Optional timeout in seconds for blocking commands. Defaults to 60. Ignored for "
                "non-blocking commands.",
                "default": 60,
            },
            "kill_session": {
                "type": "boolean",
                "description": "Whether to terminate the tmux session after checking. Set to true when you're done "
                "with the command.",
                "default": False,
            },
        },
        "required": ["action"],
        "dependencies": {
            "execute_command": ["command"],
            "check_command_output": ["session_name"],
            "terminate_command": ["session_name"],
            "list_commands": [],
        },
    }

    def __init__(
        self, sandbox: Optional[Sandbox] = None, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional sandbox and thread_id."""
        super().__init__(**data)
        if sandbox is not None:
            self._sandbox = sandbox

    async def _ensure_session(self, session_name: str = "default") -> str:
        """Ensure a session exists and return its ID."""
        if session_name not in self._sessions:
            session_id = str(uuid4())
            try:
                await self._ensure_sandbox()  # Ensure sandbox is initialized
                self.sandbox.process.create_session(session_id)
                self._sessions[session_name] = session_id
            except Exception as e:
                raise RuntimeError(f"Failed to create session: {str(e)}")
        return self._sessions[session_name]

    async def _cleanup_session(self, session_name: str):
        """Clean up a session if it exists."""
        if session_name in self._sessions:
            try:
                await self._ensure_sandbox()  # Ensure sandbox is initialized
                self.sandbox.process.delete_session(self._sessions[session_name])
                del self._sessions[session_name]
            except Exception as e:
                print(f"Warning: Failed to cleanup session {session_name}: {str(e)}")

    async def _execute_raw_command(self, command: str) -> Dict[str, Any]:
        """Execute a raw command directly in the sandbox."""
        # Ensure session exists for raw commands
        session_id = await self._ensure_session("raw_commands")

        # Execute command in session
        from app.daytona.sandbox import SessionExecuteRequest

        req = SessionExecuteRequest(
            command=command, run_async=False, cwd=self.workspace_path
        )

        response = self.sandbox.process.execute_session_command(
            session_id=session_id,
            req=req,
            timeout=30,  # Short timeout for utility commands
        )

        logs = self.sandbox.process.get_session_command_logs(
            session_id=session_id, command_id=response.cmd_id
        )

        return {"output": logs, "exit_code": response.exit_code}

    async def _execute_command(
        self,
        command: str,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
    ) -> ToolResult:
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            # Set up working directory
            cwd = self.workspace_path
            if folder:
                folder = folder.strip("/")
                cwd = f"{self.workspace_path}/{folder}"

            # Generate a session name if not provided
            if not session_name:
                session_name = f"session_{str(uuid4())[:8]}"

            # Check if tmux session already exists
            check_session = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            session_exists = "not_exists" not in check_session.get("output", "")

            if not session_exists:
                # Create a new tmux session
                await self._execute_raw_command(
                    f"tmux new-session -d -s {session_name}"
                )

            # Ensure we're in the correct directory and send command to tmux
            full_command = f"cd {cwd} && {command}"
            wrapped_command = full_command.replace('"', '\\"')  # Escape double quotes

            # Send command to tmux session
            await self._execute_raw_command(
                f'tmux send-keys -t {session_name} "{wrapped_command}" Enter'
            )

            if blocking:
                # For blocking execution, wait and capture output
                start_time = time.time()
                while (time.time() - start_time) < timeout:
                    # Wait a bit before checking
                    time.sleep(2)

                    # Check if session still exists (command might have exited)
                    check_result = await self._execute_raw_command(
                        f"tmux has-session -t {session_name} 2>/dev/null || echo 'ended'"
                    )
                    if "ended" in check_result.get("output", ""):
                        break

                    # Get current output and check for common completion indicators
                    output_result = await self._execute_raw_command(
                        f"tmux capture-pane -t {session_name} -p -S - -E -"
                    )
                    current_output = output_result.get("output", "")

                    # Check for prompt indicators that suggest command completion
                    last_lines = current_output.split("\n")[-3:]
                    completion_indicators = [
                        "$",
                        "#",
                        ">",
                        "Done",
                        "Completed",
                        "Finished",
                        "✓",
                    ]
                    if any(
                        indicator in line
                        for indicator in completion_indicators
                        for line in last_lines
                    ):
                        break

                # Capture final output
                output_result = await self._execute_raw_command(
                    f"tmux capture-pane -t {session_name} -p -S - -E -"
                )
                final_output = output_result.get("output", "")

                # Kill the session after capture
                await self._execute_raw_command(f"tmux kill-session -t {session_name}")

                return self.success_response(
                    {
                        "output": final_output,
                        "session_name": session_name,
                        "cwd": cwd,
                        "completed": True,
                    }
                )
            else:
                # For non-blocking, just return immediately
                return self.success_response(
                    {
                        "session_name": session_name,
                        "cwd": cwd,
                        "message": f"Command sent to tmux session '{session_name}'. Use check_command_output to view results.",
                        "completed": False,
                    }
                )

        except Exception as e:
            # Attempt to clean up session in case of error
            if session_name:
                try:
                    await self._execute_raw_command(
                        f"tmux kill-session -t {session_name}"
                    )
                except:
                    pass
            return self.fail_response(f"Error executing command: {str(e)}")

    async def _check_command_output(
        self, session_name: str, kill_session: bool = False
    ) -> ToolResult:
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            # Check if session exists
            check_result = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in check_result.get("output", ""):
                return self.fail_response(
                    f"Tmux session '{session_name}' does not exist."
                )

            # Get output from tmux pane
            output_result = await self._execute_raw_command(
                f"tmux capture-pane -t {session_name} -p -S - -E -"
            )
            output = output_result.get("output", "")

            # Kill session if requested
            if kill_session:
                await self._execute_raw_command(f"tmux kill-session -t {session_name}")
                termination_status = "Session terminated."
            else:
                termination_status = "Session still running."

            return self.success_response(
                {
                    "output": output,
                    "session_name": session_name,
                    "status": termination_status,
                }
            )

        except Exception as e:
            return self.fail_response(f"Error checking command output: {str(e)}")

    async def _terminate_command(self, session_name: str) -> ToolResult:
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            # Check if session exists
            check_result = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in check_result.get("output", ""):
                return self.fail_response(
                    f"Tmux session '{session_name}' does not exist."
                )

            # Kill the session
            await self._execute_raw_command(f"tmux kill-session -t {session_name}")

            return self.success_response(
                {"message": f"Tmux session '{session_name}' terminated successfully."}
            )

        except Exception as e:
            return self.fail_response(f"Error terminating command: {str(e)}")

    async def _list_commands(self) -> ToolResult:
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            # List all tmux sessions
            result = await self._execute_raw_command(
                "tmux list-sessions 2>/dev/null || echo 'No sessions'"
            )
            output = result.get("output", "")

            if "No sessions" in output or not output.strip():
                return self.success_response(
                    {"message": "No active tmux sessions found.", "sessions": []}
                )

            # Parse session list
            sessions = []
            for line in output.split("\n"):
                if line.strip():
                    parts = line.split(":")
                    if parts:
                        session_name = parts[0].strip()
                        sessions.append(session_name)

            return self.success_response(
                {
                    "message": f"Found {len(sessions)} active sessions.",
                    "sessions": sessions,
                }
            )

        except Exception as e:
            return self.fail_response(f"Error listing commands: {str(e)}")

    async def execute(
        self,
        action: str,
        command: str,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
        kill_session: bool = False,
    ) -> ToolResult:
        """
        Execute a browser action in the sandbox environment.
        Args:
            timeout:
            blocking:
            session_name:
            folder:
            command:
            kill_session:
            action: The browser action to perform
        Returns:
            ToolResult with the action's output or error
        """
        async with asyncio.Lock():
            try:
                # Navigation actions
                if action == "execute_command":
                    if not command:
                        return self.fail_response("command is required for navigation")
                    return await self._execute_command(
                        command, folder, session_name, blocking, timeout
                    )
                elif action == "check_command_output":
                    if session_name is None:
                        return self.fail_response(
                            "session_name is required for navigation"
                        )
                    return await self._check_command_output(session_name, kill_session)
                elif action == "terminate_command":
                    if session_name is None:
                        return self.fail_response(
                            "session_name is required for click_element"
                        )
                    return await self._terminate_command(session_name)
                elif action == "list_commands":
                    return await self._list_commands()
                else:
                    return self.fail_response(f"Unknown action: {action}")
            except Exception as e:
                logger.error(f"Error executing shell action: {e}")
                return self.fail_response(f"Error executing shell action: {e}")

    async def cleanup(self):
        """Clean up all sessions."""
        for session_name in list(self._sessions.keys()):
            await self._cleanup_session(session_name)

        # Also clean up any tmux sessions
        try:
            await self._ensure_sandbox()
            await self._execute_raw_command("tmux kill-server 2>/dev/null || true")
        except Exception as e:
            logger.error(f"Error shell box cleanup action: {e}")
