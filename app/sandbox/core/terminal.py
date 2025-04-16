"""
Asynchronous Docker Terminal

This module provides asynchronous terminal functionality for Docker containers,
allowing interactive command execution with timeout control.
"""

import asyncio
import re
import socket
from typing import Dict, Optional, Tuple, Union

import docker
from docker import APIClient
from docker.errors import APIError
from docker.models.containers import Container


class DockerSession:
    def __init__(self, container_id: str) -> None:
        """Initializes a Docker session.

        Args:
            container_id: ID of the Docker container.
        """
        self.api = APIClient()
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
            privileged=True,
            user="root",
            environment={**env_vars, "TERM": "dumb", "PS1": "$ ", "PROMPT_COMMAND": ""},
        )
        self.exec_id = exec_data["Id"]

        socket_data = self.api.exec_start(
            self.exec_id, socket=True, tty=True, stream=True, demux=True
        )

        if hasattr(socket_data, "_sock"):
            self.socket = socket_data._sock
            self.socket.setblocking(False)
        else:
            raise RuntimeError("Failed to get socket connection")

        await self._read_until_prompt()

    async def close(self) -> None:
        """Cleans up session resources.

        1. Sends exit command
        2. Closes socket connection
        3. Checks and cleans up exec instance
        """
        try:
            if self.socket:
                # Send exit command to close bash session
                try:
                    self.socket.sendall(b"exit\n")
                    # Allow time for command execution
                    await asyncio.sleep(0.1)
                except:
                    pass  # Ignore sending errors, continue cleanup

                # Close socket connection
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass  # Some platforms may not support shutdown

                self.socket.close()
                self.socket = None

            if self.exec_id:
                try:
                    # Check exec instance status
                    exec_inspect = self.api.exec_inspect(self.exec_id)
                    if exec_inspect.get("Running", False):
                        # If still running, wait for it to complete
                        await asyncio.sleep(0.5)
                except:
                    pass  # Ignore inspection errors, continue cleanup

                self.exec_id = None

        except Exception as e:
            # Log error but don't raise, ensure cleanup continues
            print(f"Warning: Error during session cleanup: {e}")

    async def _read_until_prompt(self) -> str:
        """Reads output until prompt is found.

        Returns:
            String containing output up to the prompt.

        Raises:
            socket.error: If socket communication fails.
        """
        buffer = b""
        while b"$ " not in buffer:
            try:
                chunk = self.socket.recv(4096)
                if chunk:
                    buffer += chunk
            except socket.error as e:
                if e.errno == socket.EWOULDBLOCK:
                    await asyncio.sleep(0.1)
                    continue
                raise
        return buffer.decode("utf-8")

    async def execute(self, command: str, timeout: Optional[int] = None) -> str:
        """Executes a command and returns cleaned output.

        Args:
            command: Shell command to execute.
            timeout: Maximum execution time in seconds.

        Returns:
            Command output as string with prompt markers removed.

        Raises:
            RuntimeError: If session not initialized or execution fails.
            TimeoutError: If command execution exceeds timeout.
        """
        if not self.socket:
            raise RuntimeError("Session not initialized")

        try:
            # Sanitize command to prevent shell injection
            sanitized_command = self._sanitize_command(command)
            full_command = f"{sanitized_command}\necho $?\n"
            self.socket.sendall(full_command.encode())

            async def read_output() -> str:
                buffer = b""
                result_lines = []
                command_sent = False

                while True:
                    try:
                        chunk = self.socket.recv(4096)
                        if not chunk:
                            break

                        buffer += chunk
                        lines = buffer.split(b"\n")

                        buffer = lines[-1]
                        lines = lines[:-1]

                        for line in lines:
                            line = line.rstrip(b"\r")

                            if not command_sent:
                                command_sent = True
                                continue

                            if line.strip() == b"echo $?" or line.strip().isdigit():
                                continue

                            if line.strip():
                                result_lines.append(line)

                        if buffer.endswith(b"$ "):
                            break

                    except socket.error as e:
                        if e.errno == socket.EWOULDBLOCK:
                            await asyncio.sleep(0.1)
                            continue
                        raise

                output = b"\n".join(result_lines).decode("utf-8")
                output = re.sub(r"\n\$ echo \$\$?.*$", "", output)

                return output

            if timeout:
                result = await asyncio.wait_for(read_output(), timeout)
            else:
                result = await read_output()

            return result.strip()

        except asyncio.TimeoutError:
            raise TimeoutError(f"Command execution timed out after {timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e}")

    def _sanitize_command(self, command: str) -> str:
        """Sanitizes the command string to prevent shell injection.

        Args:
            command: Raw command string.

        Returns:
            Sanitized command string.

        Raises:
            ValueError: If command contains potentially dangerous patterns.
        """

        # Additional checks for specific risky commands
        risky_commands = [
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=/dev/zero",
            ":(){:|:&};:",
            "chmod -R 777 /",
            "chown -R",
        ]

        for risky in risky_commands:
            if risky in command.lower():
                raise ValueError(
                    f"Command contains potentially dangerous operation: {risky}"
                )

        return command


class ProcessWrapper:
    """Wraps process input/output to provide an interface similar to asyncio.subprocess"""

    def __init__(self, stdin_queue, stdout_queue):
        self.stdin_queue = stdin_queue
        self.stdout_queue = stdout_queue
        self._closed = False

    @property
    def stdin(self):
        """Provides an interface for writing to the process"""
        return self

    @property
    def stdout(self):
        """Provides an interface for reading from the process"""
        return self

    async def write(self, data):
        """Writes data to the process's standard input"""
        if self._closed:
            raise ValueError("Process connection is closed")
        await self.stdin_queue.put(data)

    async def read(self, n=-1):
        """Reads data from the process's standard output"""
        if self._closed:
            return b""
        try:
            return await self.stdout_queue.get()
        except asyncio.CancelledError:
            self._closed = True
            return b""

    def close(self):
        """Closes the process connection"""
        self._closed = True

    async def __aenter__(self):
        """Async context manager entry point"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit point"""
        self.close()


class AsyncDockerizedTerminal:
    def __init__(
        self,
        container: Union[str, Container],
        working_dir: str = "/workspace",
        env_vars: Optional[Dict[str, str]] = None,
        default_timeout: int = 60,
    ) -> None:
        """Initializes an asynchronous terminal for Docker containers.

        Args:
            container: Docker container ID or Container object.
            working_dir: Working directory inside the container.
            env_vars: Environment variables to set.
            default_timeout: Default command execution timeout in seconds.
        """
        self.client = docker.from_env()
        self.container = (
            container
            if isinstance(container, Container)
            else self.client.containers.get(container)
        )
        self.working_dir = working_dir
        self.env_vars = env_vars or {}
        self.default_timeout = default_timeout
        self.session = None

    async def init(self) -> None:
        """Initializes the terminal environment.

        Ensures working directory exists and creates an interactive session.

        Raises:
            RuntimeError: If initialization fails.
        """
        await self._ensure_workdir()

        self.session = DockerSession(self.container.id)
        await self.session.create(self.working_dir, self.env_vars)

    async def _ensure_workdir(self) -> None:
        """Ensures working directory exists in container.

        Raises:
            RuntimeError: If directory creation fails.
        """
        try:
            await self._exec_simple(f"mkdir -p {self.working_dir}")
        except APIError as e:
            raise RuntimeError(f"Failed to create working directory: {e}")

    async def _exec_simple(self, cmd: str) -> Tuple[int, str]:
        """Executes a simple command using Docker's exec_run.

        Args:
            cmd: Command to execute.

        Returns:
            Tuple of (exit_code, output).
        """
        result = await asyncio.to_thread(
            self.container.exec_run, cmd, environment=self.env_vars
        )
        return result.exit_code, result.output.decode("utf-8")

    async def run_command(self, cmd: str, timeout: Optional[int] = None) -> str:
        """Runs a command in the container with timeout.

        Args:
            cmd: Shell command to execute.
            timeout: Maximum execution time in seconds.

        Returns:
            Command output as string.

        Raises:
            RuntimeError: If terminal not initialized.
        """
        if not self.session:
            raise RuntimeError("Terminal not initialized")

        return await self.session.execute(cmd, timeout=timeout or self.default_timeout)

    async def start_process(self, cmd: str) -> ProcessWrapper:
        """Starts a long-running process and returns a wrapper for interaction.

        Args:
            cmd: Command to execute

        Returns:
            ProcessWrapper: Wrapper for interacting with the process

        Raises:
            RuntimeError: If terminal is not initialized
        """
        if not self.session:
            raise RuntimeError("Terminal not initialized")

        # Create input and output queues
        stdin_queue = asyncio.Queue()
        stdout_queue = asyncio.Queue()

        # Create the wrapper
        wrapper = ProcessWrapper(stdin_queue, stdout_queue)

        # Start background task to handle process interaction
        asyncio.create_task(self._process_handler(cmd, stdin_queue, stdout_queue))

        return wrapper

    async def _process_handler(
        self, cmd: str, stdin_queue: asyncio.Queue, stdout_queue: asyncio.Queue
    ):
        """Handles interaction with the process

        This is a background task that:
        1. Starts the command
        2. Forwards data from stdin_queue to the process
        3. Puts process output into stdout_queue
        """
        if not self.session or not self.session.socket:
            return

        try:
            # Send command but don't wait for it to finish
            sanitized_cmd = self.session._sanitize_command(cmd)
            self.session.socket.sendall(f"{sanitized_cmd}\n".encode())

            # Start two tasks: one for reading process output, one for writing process input
            read_task = asyncio.create_task(self._read_process_output(stdout_queue))
            write_task = asyncio.create_task(self._write_process_input(stdin_queue))

            # Wait for both tasks to complete
            await asyncio.gather(read_task, write_task)

        except Exception as e:
            # When an error occurs, make sure to send the error message to the queue
            error_msg = f"Process error: {str(e)}".encode()
            await stdout_queue.put(error_msg)

    async def _read_process_output(self, output_queue: asyncio.Queue):
        """Reads output from the process and puts it into the queue"""
        if not self.session or not self.session.socket:
            return

        try:
            while True:
                try:
                    # Non-blocking read from socket
                    chunk = self.session.socket.recv(4096)
                    if not chunk:
                        # Connection closed
                        break

                    await output_queue.put(chunk)
                except socket.error as e:
                    if e.errno == socket.EWOULDBLOCK:
                        # No data to read, wait a bit and try again
                        await asyncio.sleep(0.1)
                        continue
                    raise
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            # Other errors
            error_msg = f"Read error: {str(e)}".encode()
            await output_queue.put(error_msg)

    async def _write_process_input(self, input_queue: asyncio.Queue):
        """Gets data from the queue and writes it to the process"""
        if not self.session or not self.session.socket:
            return

        try:
            while True:
                # Wait for input data
                data = await input_queue.get()

                # Write to socket
                self.session.socket.sendall(data)

                # Mark task as done
                input_queue.task_done()
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            # Other errors, log but don't raise
            print(f"Write error: {str(e)}")

    async def close(self) -> None:
        """Closes the terminal session."""
        if self.session:
            await self.session.close()

    async def __aenter__(self) -> "AsyncDockerizedTerminal":
        """Async context manager entry."""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
