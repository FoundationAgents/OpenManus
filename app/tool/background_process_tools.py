import subprocess
import os
import psutil # Certifique-se de que psutil será adicionado aos requirements
from typing import Dict, Any, Optional
import json # Added import
from app.config import config # Already here, used for config.workspace_root

from app.tool.base import BaseTool
from app.logger import logger
# from app.config import config # No need to re-import if already at module level

class ExecuteBackgroundProcessTool(BaseTool):
    """
    Executes a shell command as a background process, detached from the agent's main execution lifecycle.
    It logs stdout and stderr to specified files and persists task information.
    """
    name: str = "execute_background_process"
    description: str = (
        "Executes a command as a background process, detached from the agent's main execution. "
        "Outputs stdout and stderr to specified log files and records the task."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command to execute (e.g., 'python3 my_script.py arg1')."},
            "working_directory": {
                "type": "string",
                "description": "The working directory for the command. Defaults to agent's workspace root if not specified or if relative.",
                "nullable": True,
            },
            "log_file_stdout": {"type": "string", "description": "Path to the file where stdout will be logged. Must be within workspace."},
            "log_file_stderr": {"type": "string", "description": "Path to the file where stderr will be logged. Must be within workspace."},
            "task_description": {
                "type": "string",
                "description": "Optional. A brief description of the task being executed.",
                "nullable": True
            }
        },
        "required": ["command", "log_file_stdout", "log_file_stderr"],
    }

    async def execute(self, command: str, log_file_stdout: str, log_file_stderr: str, working_directory: Optional[str] = None, task_description: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the given command in the background.

        Args:
            command (str): The command string to execute (e.g., 'python3 my_script.py arg1').
            working_directory (Optional[str]): The working directory for the command.
                                               Defaults to the agent's workspace root if not specified or if relative.
            log_file_stdout (str): Path to the file where stdout will be logged. Must be within the workspace.
            log_file_stderr (str): Path to the file where stderr will be logged. Must be within the workspace.
            task_description (Optional[str]): An optional brief description of the task.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "pid" (Optional[int]): The PID of the started process, or None if an error occurred.
                - "log_stdout" (str): The absolute path to the stdout log file (if successful).
                - "log_stderr" (str): The absolute path to the stderr log file (if successful).
                - "status" (str): "started" if successful, or "error" if failed.
                - "message" (Optional[str]): An error message if the status is "error".
        """
        logger.info(f"Executing background command: {command} in dir: {working_directory}, description: {task_description}")

        processed_working_directory = working_directory # Renomeado para clareza
        if processed_working_directory:
            if not os.path.isabs(processed_working_directory):
                processed_working_directory = str(config.workspace_root / processed_working_directory)
            if not os.path.isdir(processed_working_directory):
                return {"pid": None, "status": "error", "message": f"Working directory '{processed_working_directory}' does not exist or is not a directory."}
        else:
            processed_working_directory = str(config.workspace_root)

        # Validar e normalizar caminhos de log
        processed_log_stdout = log_file_stdout
        processed_log_stderr = log_file_stderr
        for i, log_path_str in enumerate([log_file_stdout, log_file_stderr]):
            log_abs_path = os.path.abspath(str(config.workspace_root / log_path_str) if not os.path.isabs(log_path_str) else log_path_str)

            if not log_abs_path.startswith(str(config.workspace_root)):
                return {"pid": None, "status": "error", "message": f"Log file path '{log_path_str}' (resolved to '{log_abs_path}') is outside the allowed workspace directory."}

            if i == 0: processed_log_stdout = log_abs_path
            else: processed_log_stderr = log_abs_path

        # Garante que os diretórios para os arquivos de log existam
        for log_path in [processed_log_stdout, processed_log_stderr]:
            log_dir = os.path.dirname(log_path)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception as e_mkdir:
                    return {"pid": None, "status": "error", "message": f"Failed to create directory for log file '{log_path}': {str(e_mkdir)}"}

        try:
            stdout_log = open(processed_log_stdout, 'wb')
            stderr_log = open(processed_log_stderr, 'wb')

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=stdout_log,
                stderr=stderr_log,
                    cwd=processed_working_directory, # Usar o diretório de trabalho processado
                start_new_session=True,
                close_fds=True
            )
            logger.info(f"Background process started. PID: {process.pid}, Command: {command}, stdout_log: {processed_log_stdout}, stderr_log: {processed_log_stderr}")

            # Persistência do estado da tarefa
            running_tasks_file = config.workspace_root / "running_tasks.json"
            tasks = []
            if os.path.exists(running_tasks_file):
                try:
                    with open(running_tasks_file, 'r') as f:
                        tasks = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e_read:
                    logger.error(f"Error reading running_tasks.json: {e_read}. Starting with an empty list.")
                    tasks = []

            # Remove existing task with the same PID if any
            tasks = [task for task in tasks if task.get('pid') != process.pid]

            new_task_info = {
                "pid": process.pid,
                "command": command,
                "working_directory": processed_working_directory,
                "log_stdout": processed_log_stdout,
                "log_stderr": processed_log_stderr,
                "status": "started",
                "task_description": task_description if task_description else "N/A"
            }
            tasks.append(new_task_info)

            try:
                with open(running_tasks_file, 'w') as f:
                    json.dump(tasks, f, indent=4)
                logger.info(f"Task PID {process.pid} persisted to {running_tasks_file}")
            except Exception as e_write:
                logger.error(f"Error writing to running_tasks.json: {e_write}")
                # Optionally, could add this error to the return dict if critical

            return {"pid": process.pid, "log_stdout": processed_log_stdout, "log_stderr": processed_log_stderr, "status": "started"}
        except Exception as e:
            logger.error(f"Failed to start background process: {e}", exc_info=True)
            if 'stdout_log' in locals() and stdout_log: stdout_log.close()
            if 'stderr_log' in locals() and stderr_log: stderr_log.close()
            return {"pid": None, "status": "error", "message": f"Failed to start background process: {str(e)}"}

class CheckProcessStatusTool(BaseTool):
    """
    Checks the status of a process given its Process ID (PID) using psutil.
    """
    name: str = "check_process_status"
    description: str = "Checks the status of a process given its PID."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {"pid": {"type": "integer", "description": "The Process ID (PID) to check."}},
        "required": ["pid"],
    }

    async def execute(self, pid: int) -> Dict[str, Any]:
        """
        Checks the status of the process with the given PID.

        Args:
            pid (int): The Process ID (PID) to check.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "pid" (int): The PID checked.
                - "status" (str): The status of the process. Possible values include:
                    - "running": Process is actively running or sleeping.
                    - "finished": Process has terminated.
                    - "not_found": Process with the given PID does not exist.
                    - "error": An error occurred during the check (e.g., access denied, invalid PID).
                    - psutil status strings (e.g., 'sleeping', 'zombie') might also be returned directly
                      as 'psutil_status' if not mapped to a consolidated status.
                - "psutil_status" (Optional[str]): The raw status string from psutil (e.g., 'running', 'sleeping', 'zombie').
                - "return_code" (Optional[int]): The exit code of the process if it has finished and the code is available.
                                                 None otherwise.
                - "message" (Optional[str]): An error or informational message if applicable.
        """
        logger.info(f"Checking status for PID: {pid}")
        if pid is None or pid <= 0: # PID 0 or negative is invalid
            return {"pid": pid, "status": "error", "message": "Invalid PID (null, zero, or negative) provided.", "return_code": None}
        try:
            if not psutil.pid_exists(pid):
                logger.info(f"PID {pid} does not exist.")
                return {"pid": pid, "status": "not_found", "message": "Process not found (pid_exists is false).", "return_code": None}

            process = psutil.Process(pid)
            status = process.status() # E.g., 'running', 'sleeping', 'zombie', 'stopped'
            return_code = None

            if status == psutil.STATUS_ZOMBIE: # Process is a zombie, effectively finished
                try:
                    # For zombies, wait() should return immediately.
                    # This is to reap the process and get its exit code.
                    return_code = process.wait(timeout=0.01)
                    status = "finished" # Update status more definitively
                except psutil.TimeoutExpired: # Should not happen for true zombies if parent is us
                    logger.warning(f"PID {pid} is zombie, but wait() timed out. Return code might be unavailable.")
                except psutil.NoSuchProcess: # Zombie reaped by someone else
                    return {"pid": pid, "status": "finished_or_not_found", "message": "Zombie process reaped by another process during check.", "return_code": None}

            elif status not in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING, psutil.STATUS_DISK_SLEEP, psutil.STATUS_WAKING, psutil.STATUS_PARKED, psutil.STATUS_IDLE]:
                # If status is something like 'stopped', 'dead', it has effectively finished or is not runnable
                # Try to get return code, but it might not be available if already waited on.
                try:
                    return_code = process.returncode
                    if return_code is None and status == psutil.STATUS_DEAD: # If dead and no returncode, might have been killed
                         pass # Keep return_code as None
                    status = "finished" # Consolidate terminal states
                except psutil.Error: # process.returncode could raise if not terminated
                    pass # keep original status if returncode access fails

            logger.info(f"PID {pid} status: {status}, psutil_status: {process.status()}, return_code: {return_code}")
            return {"pid": pid, "status": status, "psutil_status": process.status(), "return_code": return_code}
        except psutil.NoSuchProcess:
            logger.info(f"PID {pid} not found by psutil (NoSuchProcess exception).")
            return {"pid": pid, "status": "not_found", "message": "Process not found (NoSuchProcess exception).", "return_code": None}
        except psutil.AccessDenied:
            logger.warning(f"Access denied when checking PID {pid}.")
            return {"pid": pid, "status": "error", "message": "Access denied to process information.", "return_code": None}
        except Exception as e:
            logger.error(f"Error checking PID {pid}: {e}", exc_info=True)
            return {"pid": pid, "status": "error", "message": f"Error checking process status: {str(e)}", "return_code": None}

class GetProcessOutputTool(BaseTool):
    """
    Reads the content of a specified log file, typically used for checking the output
    of background processes. Allows to tail the last N lines of the file.
    """
    name: str = "get_process_output"
    description: str = "Reads the content of a log file, typically associated with a background process. Can tail the last N lines."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "log_file": {"type": "string", "description": "The path to the log file to read. Must be within workspace."},
            "tail_lines": {
                "type": "integer",
                "description": "Optional. If provided, returns only the last N lines of the file.",
                "nullable": True
            },
        },
        "required": ["log_file"],
    }

    async def execute(self, log_file: str, tail_lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Reads content from the specified log file.

        Args:
            log_file (str): The path to the log file. If relative, it's considered
                            relative to the agent's workspace root.
            tail_lines (Optional[int]): If provided and positive, returns only the
                                        last N lines from the file. Otherwise, returns
                                        the full content.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - "log_file" (str): The absolute path of the log file read.
                - "content" (Optional[str]): The content of the file, or None if an error occurred.
                - "error" (Optional[str]): An error message if reading failed or the file
                                           was invalid/not found.
        """
        logger.info(f"Getting output for log file: {log_file}, tail: {tail_lines}")

        log_abs_path = os.path.abspath(str(config.workspace_root / log_file) if not os.path.isabs(log_file) else log_file)

        if not log_abs_path.startswith(str(config.workspace_root)):
            return {"log_file": log_file, "content": None, "error": f"Log file path '{log_file}' (resolved to '{log_abs_path}') is outside the allowed workspace directory."}

        if not os.path.exists(log_abs_path):
            return {"log_file": log_abs_path, "content": None, "error": "Log file not found."}
        if not os.path.isfile(log_abs_path):
            return {"log_file": log_abs_path, "content": None, "error": "Specified path is not a file."}

        try:
            with open(log_abs_path, 'r', encoding='utf-8', errors='replace') as f:
                if tail_lines is not None and tail_lines > 0:
                    lines = f.readlines() # Reads all lines, could be memory intensive for huge files
                    content = "".join(lines[-tail_lines:])
                else:
                    content = f.read()
            return {"log_file": log_abs_path, "content": content, "error": None}
        except Exception as e:
            logger.error(f"Error reading log file {log_abs_path}: {e}", exc_info=True)
            return {"log_file": log_abs_path, "content": None, "error": f"Error reading log file: {str(e)}"}
