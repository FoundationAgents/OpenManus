"""
Asynchronous Docker Terminal

This module provides asynchronous terminal functionality for Docker containers,
allowing interactive command execution with timeout control.
"""

import asyncio
import socket # Keep socket for DockerSession if it's used elsewhere or for future
from typing import Dict, Optional, Tuple, Union, Any # Add Any for dict value

import docker
# from docker import APIClient # Not directly used by AsyncDockerizedTerminal after refactor
from docker.errors import APIError
from docker.models.containers import Container

from app.sandbox.core.exceptions import SandboxTimeoutError


# DockerSession might be simplified or removed if not essential for other functionalities
# For now, we are keeping it as it might be used for interactive scenarios.
# If run_command is the primary way of interacting, DockerSession's role diminishes.

class DockerSession:  # This class is for interactive sessions
    def __init__(self, container_id: str) -> None:
        """Initializes a Docker session.

        Args:
            container_id: ID of the Docker container.
        """
        # self.api = APIClient() # Potentially unused if only exec_run is used
        self.api = docker.APIClient() # Ensure APIClient is available
        self.container_id = container_id
        self.exec_id = None
        self.socket = None

    async def create(self, working_dir: str, env_vars: Dict[str, str]) -> None:
        """Creates an interactive session with the container.

        Args:
            working_dir: Working directory inside the container.
            env_vars: Environment variables to set.

        Raises:
            RuntimeError: If socket connection fails.
        """
        startup_command = [
            "bash",
            "-c",
            f"cd {working_dir} && "
            "PROMPT_COMMAND='' "
            "PS1='$ ' "
            "exec bash --norc --noprofile",
        ]

        exec_data = self.api.exec_create(
            self.container_id,
            startup_command,
            stdin=True,
            tty=True,
            stdout=True,
            stderr=True,
            privileged=True, # Consider if privileged is always needed
            user="root",
            environment={**env_vars, "TERM": "dumb", "PS1": "$ ", "PROMPT_COMMAND": ""},
        )
        self.exec_id = exec_data["Id"]

        # demux=True is important for exec_start if we need separate streams
        socket_data = self.api.exec_start(
            self.exec_id, socket=True, tty=True, stream=True, demux=True
        )

        if hasattr(socket_data, "_sock"):
            self.socket = socket_data._sock
            self.socket.setblocking(False)
        else:
            # This path might indicate an issue with Docker's response or setup
            raise RuntimeError("Failed to get socket connection for interactive session")

        await self._read_until_prompt() # Specific to interactive sessions

    async def close(self) -> None:
        """Cleans up session resources."""
        try:
            if self.socket:
                try:
                    self.socket.sendall(b"exit\n")
                    await asyncio.sleep(0.1)
                except Exception: # pylint: disable=broad-except
                    pass

                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except Exception: # pylint: disable=broad-except
                    pass
                self.socket.close()
                self.socket = None

            if self.exec_id:
                try:
                    exec_inspect = self.api.exec_inspect(self.exec_id)
                    if exec_inspect.get("Running", False):
                        await asyncio.sleep(0.5) # Give a bit of time for exec to finish
                        # Optionally, send a kill signal if it's stuck
                except Exception: # pylint: disable=broad-except
                    pass # Ignore inspection errors during cleanup
                self.exec_id = None
        except Exception as e: # pylint: disable=broad-except
            print(f"Warning: Error during DockerSession cleanup: {e}")


    async def _read_until_prompt(self) -> str:
        """Reads output until prompt is found. (Interactive session specific)"""
        buffer = b""
        prompt_marker = b"$ " # Standard prompt marker
        # A more robust prompt detection might be needed if PS1 is complex
        while prompt_marker not in buffer:
            try:
                # Non-blocking read with async sleep
                chunk = await asyncio.to_thread(self.socket.recv, 4096)
                if chunk:
                    buffer += chunk
                else:
                    # Socket closed or no data, might indicate end of stream or error
                    await asyncio.sleep(0.01) # Small delay before retrying or breaking
                    # Add a counter or timeout here to prevent infinite loop if prompt never appears
            except socket.error as e:
                if e.errno == socket.EWOULDBLOCK or e.errno == socket.EAGAIN:
                    await asyncio.sleep(0.05) # Wait for data
                    continue
                # Other socket errors could be critical
                raise RuntimeError(f"Socket error while reading for prompt: {e}")
            except Exception as e: # pylint: disable=broad-except
                # Catch other potential errors during recv
                raise RuntimeError(f"Unexpected error while reading for prompt: {e}")
        return buffer.decode("utf-8", errors="replace")


    async def execute(self, command: str, timeout: Optional[int] = None) -> str:
        """Executes a command in an interactive session and returns cleaned output."""
        if not self.socket or not self.exec_id:
            raise RuntimeError("Interactive session not properly initialized.")

        try:
            # Command sanitation should ideally happen before this point if it's generic
            # For interactive sessions, users might expect more raw execution
            full_command = f"{command}\necho EXEC_END_MARKER $?\n" # Use a unique marker
            self.socket.sendall(full_command.encode())

            async def read_interactive_output() -> str:
                buffer = b""
                output_lines = []
                # This logic needs to be robust to capture multi-line outputs
                # and correctly identify the end of the command execution.
                # The `echo EXEC_END_MARKER $?` helps in finding the command's end.
                # This is a simplified version. A full implementation would need
                # careful handling of stream data, potential partial lines, etc.
                while not (b"EXEC_END_MARKER" in buffer and b"$ " in buffer): # Wait for marker and next prompt
                    try:
                        chunk = await asyncio.to_thread(self.socket.recv, 4096)
                        if chunk:
                            buffer += chunk
                        else:
                            await asyncio.sleep(0.01)
                    except socket.error as e:
                        if e.errno == socket.EWOULDBLOCK or e.errno == socket.EAGAIN:
                            await asyncio.sleep(0.05)
                            continue
                        raise RuntimeError(f"Socket error during interactive command execution: {e}")
                
                # Process buffer to extract relevant output before EXEC_END_MARKER
                # This part is complex and error-prone with interactive sessions.
                # For structured output (stdout, stderr, exit_code), non-interactive exec_run is preferred.
                raw_output = buffer.decode("utf-8", errors="replace")
                # Simplified: extract content before the marker. Needs refinement.
                command_output = raw_output.split("EXEC_END_MARKER")[0]
                # Remove the sent command from the output if it's echoed back
                if command_output.startswith(command):
                    command_output = command_output[len(command):].lstrip()
                return command_output.strip()


            if timeout:
                return await asyncio.wait_for(read_interactive_output(), timeout=timeout)
            return await read_interactive_output()

        except asyncio.TimeoutError:
            # In a timeout, the session might be in an inconsistent state.
            # Consider trying to send a Ctrl+C or closing/recreating the session.
            raise SandboxTimeoutError(f"Interactive command timed out after {timeout} seconds.")
        except Exception as e:
            raise RuntimeError(f"Failed to execute interactive command: {e}")

    def _sanitize_command(self, command: str) -> str: # This might be less relevant for direct exec_run
        """Sanitizes the command string (basic version)."""
        # This is a very basic sanitizer. For robust security, more is needed.
        # Or, rely on sandbox permissions and container hardening.
        if ";" in command and "&&" not in command and "||" not in command:
             # Simple check for multiple commands not using && or ||
             pass # Allow for now, but this is a weak check.
        # Add more checks as necessary, e.g., for risky patterns.
        # However, over-sanitization can also break valid commands.
        return command


class AsyncDockerizedTerminal:
    def __init__(
        self,
        container: Union[str, Container],
        working_dir: str = "/workspace", # Default working directory in the container
        env_vars: Optional[Dict[str, str]] = None,
        default_timeout: int = 60, # Default timeout for commands
    ) -> None:
        """Initializes an asynchronous terminal for Docker containers.

        Args:
            container: Docker container ID or Container object.
            working_dir: Working directory inside the container for commands.
            env_vars: Environment variables to set for commands.
            default_timeout: Default command execution timeout in seconds.
        """
        self.docker_client = docker.from_env() # Standard Docker client
        self.container = (
            container
            if isinstance(container, Container)
            else self.docker_client.containers.get(container)
        )
        self.working_dir = working_dir
        self.env_vars = env_vars if env_vars is not None else {}
        self.default_timeout = default_timeout
        # Interactive session is now optional, only created if specific methods are called
        self.session: Optional[DockerSession] = None


    async def init_interactive_session(self) -> None:
        """Initializes the interactive terminal session.
        This is separated so that not every terminal usage implies an interactive session.
        """
        if not self.session:
            await self._ensure_workdir() # Ensure working dir exists before session
            self.session = DockerSession(self.container.id)
            try:
                await self.session.create(self.working_dir, self.env_vars)
            except Exception as e:
                self.session = None # Reset session on failure
                raise RuntimeError(f"Failed to initialize interactive session: {e}")

    async def _ensure_workdir(self) -> None:
        """Ensures working directory exists in the container.
        Uses a non-interactive exec_run for this setup command.
        """
        # This command is simple and non-interactive, suitable for a direct exec_run.
        # It doesn't strictly need the full run_command treatment with timeout here,
        # but for consistency, it could use a simplified version of run_command.
        mkdir_cmd = f"mkdir -p {self.working_dir}"
        try:
            # Using exec_run directly for setup.
            # No need for demux=True here as output is not critical, only exit_code.
            exit_code, (stdout, stderr) = await asyncio.to_thread(
                self.container.exec_run,
                mkdir_cmd,
                workdir=self.working_dir, # Ensure command runs in the context of workdir
                environment=self.env_vars,
                demux=True # Get separate streams
            )
            if exit_code != 0:
                stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
                raise RuntimeError(
                    f"Failed to create working directory '{self.working_dir}': "
                    f"Exit code {exit_code}, Stdout: '{stdout_str}', Stderr: '{stderr_str}'"
                )
        except APIError as e:
            raise RuntimeError(f"APIError during _ensure_workdir: {e}")
        except Exception as e: # Catch other potential errors
            raise RuntimeError(f"Unexpected error during _ensure_workdir: {e}")


    async def run_command(
        self, cmd: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Runs a non-interactive command in the container with timeout and returns structured output.

        Args:
            cmd: Shell command to execute.
            timeout: Maximum execution time in seconds. Defaults to self.default_timeout.

        Returns:
            A dictionary with "exit_code", "stdout", and "stderr".

        Raises:
            SandboxTimeoutError: If command execution exceeds timeout.
            RuntimeError: If command execution fails for other reasons.
        """
        exec_timeout = timeout if timeout is not None else self.default_timeout

        try:
            # Ensure working directory exists. This is crucial for command execution context.
            # Call it here to make sure it's set up before any command.
            # If called multiple times, it's idempotent ("mkdir -p").
            await self._ensure_workdir()

            # `exec_run` is suitable for non-interactive commands where we need exit code & output.
            # `tty=False` is generally better for non-interactive execs capturing stdout/stderr.
            # `demux=True` gives separate stdout and stderr streams.
            exec_coro = asyncio.to_thread(
                self.container.exec_run,
                cmd,
                workdir=self.working_dir,
                environment=self.env_vars,
                demux=True, # Crucial for separate stdout/stderr
                tty=False, # Non-interactive, so no TTY needed
            )
            
            # Execute with timeout
            exit_code, (stdout_bytes, stderr_bytes) = await asyncio.wait_for(
                exec_coro, timeout=exec_timeout
            )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            return {
                "exit_code": exit_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
            }

        except asyncio.TimeoutError:
            # Construct a meaningful timeout message
            timeout_message = (
                f"Command '{cmd[:100]}{'...' if len(cmd) > 100 else ''}' "
                f"timed out after {exec_timeout} seconds."
            )
            # It's good practice to include stderr in timeout if available,
            # but exec_run result is not available if timeout occurs during await.
            # So, we typically won't have stdout/stderr here.
            raise SandboxTimeoutError(timeout_message)
        
        except APIError as e:
            # Docker API errors
            raise RuntimeError(f"Docker APIError executing command '{cmd}': {e}")
        except Exception as e:
            # Other unexpected errors
            raise RuntimeError(f"Unexpected error executing command '{cmd}': {e}")


    async def run_interactive_command(self, cmd: str, timeout: Optional[int] = None) -> str:
        """Runs a command in an interactive session.
        Requires init_interactive_session to be called first.
        """
        if not self.session:
            # Automatically initialize if not already done.
            # Or raise error: raise RuntimeError("Interactive session not initialized. Call init_interactive_session() first.")
            await self.init_interactive_session()
        
        # Ensure session is now available after potential initialization
        if not self.session:
             raise RuntimeError("Failed to create interactive session for command.")

        return await self.session.execute(cmd, timeout=timeout or self.default_timeout)


    async def close(self) -> None:
        """Closes the terminal session, primarily the interactive one if it exists."""
        if self.session:
            await self.session.close()
            self.session = None # Clear the session
        # self.docker_client.close() # Typically, the client is managed externally or at app level


    async def __aenter__(self) -> "AsyncDockerizedTerminal":
        # The __aenter__ could optionally initialize the interactive session
        # if that's the primary use case for contexts.
        # For now, it just returns self. `_ensure_workdir` is called by `run_command`.
        # If interactive session is commonly used with `async with`, then:
        # await self.init_interactive_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager entry."""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close() # Ensure interactive session resources are cleaned up
