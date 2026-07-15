import asyncio
import os
import sys
import tempfile
from typing import Dict

from app.task_context import (
    emit_current_task,
    get_current_sandbox,
    get_current_task,
    get_current_tool_call,
)
from app.tool.base import BaseTool


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and visible output."""

    name: str = "python_execute"
    description: str = (
        "Executes Python code string. Note: Only printed stdout/stderr are visible, "
        "function return values are not captured. Use print statements to see results."
    )
    emits_progress: bool = True  # streams stdout/stderr lines while running
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    async def execute(
        self,
        code: str,
        timeout: int = 5,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'observation' with execution output and success status.
        """
        tool_call = get_current_tool_call() or {}
        sandbox = get_current_sandbox()
        if sandbox is not None:
            script_path = "/workspace/.openmanus/python_execute.py"
            await sandbox.write_file(script_path, code)
            emit_current_task(
                "tool:progress",
                {
                    "id": tool_call.get("id"),
                    "name": self.name,
                    "status": "running",
                    "message": "Executing Python script in sandbox...",
                },
            )
            return_code, stdout, stderr = await sandbox.run(
                f"python -u {script_path}",
                timeout=timeout,
                task=get_current_task(),
                tool_call=tool_call,
                tool_name=self.name,
            )
            emit_current_task(
                "tool:progress",
                {
                    "id": tool_call.get("id"),
                    "name": self.name,
                    "status": "done",
                    "exit_code": return_code,
                },
            )
            return {
                "observation": stdout + stderr,
                "success": return_code == 0,
            }

        fd, path = tempfile.mkstemp(prefix="openmanus_python_", suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(code)

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_parts: list[str] = []
            stderr_parts: list[str] = []

            async def read_stream(stream, stream_name: str, sink: list[str]) -> None:
                while True:
                    chunk = await stream.readline()
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    sink.append(text)
                    emit_current_task(
                        "terminal_output",
                        {
                            "id": tool_call.get("id"),
                            "name": tool_call.get("name", self.name),
                            "stream": stream_name,
                            "chunk": text,
                        },
                    )

            stdout_task = asyncio.create_task(
                read_stream(process.stdout, "stdout", stdout_parts)
            )
            stderr_task = asyncio.create_task(
                read_stream(process.stderr, "stderr", stderr_parts)
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                await asyncio.gather(stdout_task, stderr_task)
                message = f"Execution timeout after {timeout} seconds"
                emit_current_task(
                    "terminal_output",
                    {
                        "id": tool_call.get("id"),
                        "name": tool_call.get("name", self.name),
                        "stream": "stderr",
                        "chunk": message,
                    },
                )
                return {"observation": message, "success": False}

            await asyncio.gather(stdout_task, stderr_task)
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            observation = stdout + stderr
            return {
                "observation": observation,
                "success": process.returncode == 0,
            }
        except Exception as exc:
            return {"observation": str(exc), "success": False}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
