import asyncio
import os
from typing import Optional

from app.exceptions import ToolError
from app.task_context import (
    emit_current_task,
    get_current_sandbox,
    get_current_task,
    get_current_tool_call,
)
from app.tool.base import BaseTool, CLIResult


_BASH_DESCRIPTION = """Execute a bash command in the terminal.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.
"""


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return CLIResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            last_output_len = 0
            last_error_len = 0
            tool_call = get_current_tool_call() or {}
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # if we read directly from stdout/stderr, it will wait forever for
                    # EOF. use the StreamReader buffer directly instead.
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    visible_output = (
                        output[: output.index(self._sentinel)]
                        if self._sentinel in output
                        else output
                    )
                    if len(visible_output) > last_output_len:
                        emit_current_task(
                            "terminal_output",
                            {
                                "id": tool_call.get("id"),
                                "name": tool_call.get("name", "bash"),
                                "stream": "stdout",
                                "chunk": visible_output[last_output_len:],
                            },
                        )
                        last_output_len = len(visible_output)

                    error = (
                        self._process.stderr._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if len(error) > last_error_len:
                        emit_current_task(
                            "terminal_output",
                            {
                                "id": tool_call.get("id"),
                                "name": tool_call.get("name", "bash"),
                                "stream": "stderr",
                                "chunk": error[last_error_len:],
                            },
                        )
                        last_error_len = len(error)

                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers so that the next output can be read correctly
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class Bash(BaseTool):
    """A tool for executing bash commands"""

    name: str = "bash"
    description: str = _BASH_DESCRIPTION
    emits_progress: bool = True  # streams stdout/stderr chunks while running
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
            },
        },
        "required": ["command"],
    }

    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, **kwargs
    ) -> CLIResult:
        sandbox = get_current_sandbox()
        if sandbox is not None:
            if not command:
                raise ToolError("no command provided.")
            tool_call = get_current_tool_call() or {}
            task = get_current_task()

            # Emit start heartbeat
            emit_current_task(
                "tool:progress",
                {
                    "id": tool_call.get("id"),
                    "name": self.name,
                    "status": "running",
                    "message": f"Executing: {command[:120]}",
                },
            )
            code, stdout, stderr = await sandbox.run(
                command,
                timeout=kwargs.get("timeout") or 120,
                task=task,
                tool_call=tool_call,
                tool_name=self.name,
            )
            emit_current_task(
                "tool:progress",
                {
                    "id": tool_call.get("id"),
                    "name": self.name,
                    "status": "done",
                    "exit_code": code,
                },
            )
            return CLIResult(output=stdout, error=stderr if code else None)

        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return CLIResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")


if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
