import asyncio
import os
from typing import Optional

from app.config import config
from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult
from app.logger import logger # ADDED


_BASH_DESCRIPTION = '''Execute a bash command in the terminal.
* working_directory: Optional. The working directory from which to run the command. If not specified, uses the agent's current working directory. This directory is set when the session (re)starts.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.'''


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 86400.0  # seconds (24 hours)
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self, working_directory: Optional[str] = None): # Adicionar parâmetro
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            # preexec_fn=os.setsid, # Esta linha já deve estar removida/comentada
            shell=True,
            bufsize=0,
            cwd=working_directory, # Adicionar este parâmetro
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._started = True

    def stop(self): # Renomear para indicar que é síncrono e apenas tenta terminar
        """Attempts to terminate the bash shell process."""
        if not self._started or not hasattr(self, '_process') or self._process.returncode is not None: # Adicionado hasattr
            return
        try:
            self._process.terminate()
            logger.info("Bash process terminated.") 
        except ProcessLookupError: 
            logger.info("Bash process already terminated.")
        except Exception as e: 
            logger.error(f"Error terminating bash process: {e}")

    async def close_async(self): # Novo método assíncrono para limpeza completa
        """Closes stdin, terminates the process, and waits for it to exit."""
        logger.info("_BashSession.close_async: Starting...")
        if not self._started or not hasattr(self, '_process') or self._process.returncode is not None:
            logger.info("_BashSession.close_async: Session already closed or not started.")
            return

        logger.info("_BashSession.close_async: Closing bash session asynchronously...")
        try:
            if self._process.stdin and hasattr(self._process.stdin, 'is_closing') and not self._process.stdin.is_closing():
                try:
                    logger.info("_BashSession.close_async: Attempting to write EOF to stdin.")
                    self._process.stdin.write_eof()
                    await self._process.stdin.drain() 
                    logger.info("_BashSession.close_async: Bash stdin EOF sent and drained.")
                except (ConnectionResetError, BrokenPipeError, AttributeError) as e: 
                    logger.warning(f"_BashSession.close_async: Error sending EOF to bash stdin (may be already closed): {e}")
                except Exception as e:
                    logger.error(f"_BashSession.close_async: Unexpected error closing bash stdin: {e}")
                finally:
                    if self._process.stdin and hasattr(self._process.stdin, 'close') and hasattr(self._process.stdin, 'is_closing') and not self._process.stdin.is_closing(): # Checagens extras
                        self._process.stdin.close()

            if self._process.returncode is None: 
                logger.info("_BashSession.close_async: Attempting to terminate process.")
                self._process.terminate()
                logger.info("_BashSession.close_async: Sent SIGTERM to bash process.")
                try:
                    logger.info("_BashSession.close_async: Waiting for process to exit after terminate...")
                    await asyncio.wait_for(self._process.wait(), timeout=5.0) 
                    logger.info(f"_BashSession.close_async: Bash process exited with code {self._process.returncode}.")
                except asyncio.TimeoutError:
                    logger.warning("_BashSession.close_async: Bash process did not terminate gracefully after 5s, sending SIGKILL.")
                    if self._process.returncode is None: 
                        logger.info("_BashSession.close_async: Process did not terminate, attempting to kill.")
                        self._process.kill()
                        await self._process.wait() 
                        logger.info(f"_BashSession.close_async: Bash process killed. Exit code {self._process.returncode}.")
                except ProcessLookupError:
                    logger.info("_BashSession.close_async: Bash process already exited before wait.")
                except Exception as e: 
                    logger.error(f"_BashSession.close_async: Error during bash process wait: {e}")
        except ProcessLookupError: 
            logger.info("_BashSession.close_async: Bash process does not exist (already cleaned up).")
        except Exception as e:
            logger.error(f"_BashSession.close_async: Error during bash session close_async: {e}")
        finally:
            logger.info("_BashSession.close_async: Setting self._started to False.")
            self._started = False 
            if hasattr(self, '_process'): # Garantir que _process existe
                logger.info(f"Bash session close_async completed. Final process return code: {self._process.returncode}")
            else:
                logger.info("Bash session close_async completed (process attribute was missing).")

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
        async def _read_output_with_sentinel():
            while True:
                await asyncio.sleep(self._output_delay)
                # if we read directly from stdout/stderr, it will wait forever for
                # EOF. use the StreamReader buffer directly instead.
                output_val = ( # Renamed to output_val to avoid conflict with outer scope 'output'
                    self._process.stdout._buffer.decode()
                )  # pyright: ignore[reportAttributeAccessIssue]
                if self._sentinel in output_val:
                    # strip the sentinel and break
                    output_val = output_val[: output_val.index(self._sentinel)]
                    return output_val # Return the output when sentinel is found
                # Check if process has exited unexpectedly to prevent infinite loop.
                if self._process.returncode is not None:
                    logger.warning("_BashSession._read_output_with_sentinel: Process exited prematurely.")
                    # Try to get any remaining output, may not contain sentinel
                    return self._process.stdout._buffer.decode() # pyright: ignore[reportAttributeAccessIssue]
        
        output = "" # Initialize output to ensure it's defined
        try:
            output = await asyncio.wait_for(_read_output_with_sentinel(), timeout=self._timeout)
        except asyncio.TimeoutError:
            self._timed_out = True
            # logger.error(f"Command timed out after {self._timeout}s in _BashSession.run") # Logger available
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output and output.endswith("\n"): # Check if output is not None
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
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
            },
            "working_directory": { # Novo parâmetro
                "type": "string",
                "description": "Optional. The working directory from which to run the command. Defaults to the agent's current working directory if not specified. This directory is set when the session (re)starts.",
                "nullable": True 
            }
        },
        "required": ["command"],
    }

    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, working_directory: Optional[str] = None, **kwargs # Adicionar parâmetro
    ) -> CLIResult:
        if restart:
            if self._session:
                await self._session.close_async() # MUDAR AQUI
            self._session = _BashSession()
            # Use config.workspace_root as default for working_directory
            effective_working_directory = working_directory if working_directory is not None else str(config.workspace_root)
            await self._session.start(working_directory=effective_working_directory)
            return CLIResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession()
            # Use config.workspace_root as default for working_directory
            effective_working_directory = working_directory if working_directory is not None else str(config.workspace_root)
            await self._session.start(working_directory=effective_working_directory)

        if command is not None:
            # Nota: working_directory é definido no início da sessão. 
            # Se for necessário mudar por comando, o próprio comando 'cd' deve ser usado.
            return await self._session.run(command)

        raise ToolError("no command provided.")

    async def cleanup(self):
        """Cleans up the bash session if it exists."""
        logger.info("Bash.cleanup: Starting...")
        if self._session:
            logger.info("Bash.cleanup: About to call self._session.close_async()")
            await self._session.close_async()
            logger.info("Bash.cleanup: self._session.close_async() completed.")
            self._session = None
            logger.info("Bash.cleanup: self._session set to None.")
        else:
            logger.info("Bash.cleanup: No active Bash tool session to cleanup.")
        logger.info("Bash.cleanup: Finished.")


if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
