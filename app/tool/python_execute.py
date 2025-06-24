import multiprocessing
import multiprocessing
import sys
import os
from io import StringIO
from typing import Dict, Optional
import traceback # Added import traceback
import ast # Added import ast
from app.logger import logger

from app.tool.base import BaseTool, ToolResult # Import ToolResult


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = ("Executes Python code directly on the host machine (not in the sandbox). "
                        "Accepts either a 'code' string or a 'file_path_to_execute'. "
                        "Captures and returns stdout, stderr, and an exit_code. "
                        "Use 'working_directory' to specify the execution path, especially if the code/script interacts with local files. "
                        "If 'file_path_to_execute' is used and 'working_directory' is not set, the script's directory will be used as the working directory. "
                        "For sandboxed execution, use 'sandbox_python_executor'.")
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code string to execute. Use this OR 'file_path_to_execute'.",
                "nullable": True
            },
            "file_path_to_execute": {
                "type": "string",
                "description": "Path to a Python script file to execute. Use this OR 'code'. If provided, 'code' parameter is ignored.",
                "nullable": True
            },
            "working_directory": {
                "type": "string",
                "description": "Optional. The working directory for execution. If 'file_path_to_execute' is used and this is not set, the script's directory is used. Otherwise, defaults to agent's main process CWD.",
                "nullable": True
            },
            "timeout": {
                       "type": "integer",
                       "description": "Optional. The maximum execution time in seconds. Defaults to 120 seconds.",
                       "default": 120
            }
        },
        "required": [], # No longer strictly 'code' due to file_path option
    }

    def _run_code(self, code_to_run: str, result_dict: dict, safe_globals: dict, working_directory: Optional[str] = None) -> None:
        original_stdout = sys.stdout
        original_stderr = sys.stderr # Capture original stderr
        original_cwd = os.getcwd()
        cwd_changed_successfully = False
        output_buffer = StringIO()
        error_buffer = StringIO() # Buffer for stderr
        sys.stdout = output_buffer
        sys.stderr = error_buffer # Redirect stderr

        try:
            if working_directory:
                if os.path.isdir(working_directory):
                    os.chdir(working_directory)
                    cwd_changed_successfully = True
                else:
                    # This error will be caught by the except block
                    raise FileNotFoundError(f"Specified working_directory '{working_directory}' does not exist or is not a directory.")

            exec(code, safe_globals, safe_globals)
            result_dict["stdout"] = output_buffer.getvalue()
            result_dict["stderr"] = error_buffer.getvalue()
            result_dict["exit_code"] = 0
            result_dict["success"] = True
            result_dict["observation"] = result_dict["stdout"] # Keep observation as stdout for compatibility
        except Exception as e:
            stderr_capture = error_buffer.getvalue()
            exception_traceback = traceback.format_exc()
            result_dict["stdout"] = output_buffer.getvalue() # Capture any stdout before the error
            result_dict["stderr"] = (stderr_capture + "\n" + str(e) + "\n" + exception_traceback).strip()
            result_dict["exit_code"] = 1
            result_dict["success"] = False
            result_dict["observation"] = result_dict["stderr"] # Keep observation as stderr on error
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr # Restore original stderr
            if cwd_changed_successfully:
                os.chdir(original_cwd)

    async def execute(
        self,
        code: Optional[str] = None,
        file_path_to_execute: Optional[str] = None,
        timeout: int = 120,
        working_directory: Optional[str] = None,
    ) -> ToolResult: # Changed return type to ToolResult
        """
        Executes Python code from a string or a file directly on the host.

        Args:
            code (Optional[str]): The Python code string to execute.
            file_path_to_execute (Optional[str]): Path to a Python script file to execute.
                                                 If provided, 'code' parameter is ignored.
            timeout (int): Optional. Max execution time in seconds. Defaults to 120.
            working_directory (Optional[str]): Optional. Working directory for execution.
                                               If file_path_to_execute is used and this is not set,
                                               the script's directory is used.

        Returns:
            ToolResult: Contains 'stdout', 'stderr', 'exit_code', 'success' in its 'output' dict,
                        and an 'error' message if applicable.
        """
        code_to_run: Optional[str] = None
        effective_working_directory: Optional[str] = working_directory

        if file_path_to_execute:
            if not os.path.isabs(file_path_to_execute):
                 # Assume it's relative to workspace_root if not absolute
                 # This requires config to be accessible or passed. For now, let's assume it's best if agent passes absolute path.
                 # Or, we could make it an error if not absolute, to be safer.
                 # For now, let's log a warning and proceed, assuming it might be relative to CWD.
                 logger.warning(f"file_path_to_execute '{file_path_to_execute}' is not an absolute path. Attempting to use as is.")

            try:
                if not os.path.exists(file_path_to_execute):
                    return ToolResult(error=f"File not found: {file_path_to_execute}", output={
                        "stdout": "", "stderr": f"File not found: {file_path_to_execute}", "exit_code": 1, "success": False
                    })
                with open(file_path_to_execute, 'r', encoding='utf-8') as f:
                    code_to_run = f.read()
                if not effective_working_directory: # If WD not set by user, use script's dir
                    effective_working_directory = os.path.dirname(file_path_to_execute)
                logger.info(f"Executing code from file: {file_path_to_execute}. Effective WD: {effective_working_directory}")
            except Exception as e:
                logger.error(f"Error reading file {file_path_to_execute}: {e}\n{traceback.format_exc()}")
                return ToolResult(error=f"Error reading file {file_path_to_execute}: {e}", output={
                    "stdout": "", "stderr": f"Error reading file {file_path_to_execute}: {e}", "exit_code": 1, "success": False
                })
        elif code:
            code_to_run = code
            logger.info(f"Executing code string. Effective WD: {effective_working_directory if effective_working_directory else 'agent CWD'}")
        else:
            return ToolResult(error="No code or file_path_to_execute provided.", output={
                "stdout": "", "stderr": "No code or file_path_to_execute provided.", "exit_code": 1, "success": False
            })

        if code_to_run is None: # Should be caught by above, but as a safeguard
             return ToolResult(error="Internal error: code_to_run is None after processing inputs.", output={
                "stdout": "", "stderr": "Internal error: code_to_run is None.", "exit_code": 1, "success": False
            })

        try:
            ast.parse(code_to_run)
        except SyntaxError as e:
            logger.error(f"SyntaxError in code: {e}\n{traceback.format_exc()}")
            error_details = f"SyntaxError: {str(e)}\n{traceback.format_exc()}"
            return ToolResult(error=f"SyntaxError: {str(e)}", output={ # Pass the error to ToolResult
                "stdout": "", "stderr": error_details, "exit_code": 1, "success": False
            })

        with multiprocessing.Manager() as manager:
            result = manager.dict({"stdout": "", "stderr": "", "exit_code": -1, "success": False, "observation": ""})
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}
            
            proc = multiprocessing.Process(
                target=self._run_code, args=(code_to_run, result, safe_globals, effective_working_directory)
            )
            proc.start()
            proc.join(timeout)

            # timeout process
            if proc.is_alive():
                proc.terminate()
                proc.join(1) # Dar um segundo para o terminate
                # Adicionar working_directory à mensagem de timeout se ele foi especificado
                timeout_message = f"Execution timeout after {timeout} seconds"
                if working_directory:
                    timeout_message += f" (in working_directory: '{working_directory}')"

                timeout_output = {"stdout": "", "stderr": timeout_message, "exit_code": 1, "success": False, "observation": timeout_message}
                return ToolResult(error="Execution timed out.", output=timeout_output)

            final_result_dict = dict(result)
            # Determinar se houve erro para o campo error do ToolResult
            tool_error_msg = None
            if not final_result_dict.get("success", False):
                tool_error_msg = final_result_dict.get("stderr", "Python execution failed without specific stderr.")
                if not tool_error_msg: # Caso stderr seja vazio mas success é False
                    tool_error_msg = "Python execution failed with an unspecified error."
            return ToolResult(output=final_result_dict, error=tool_error_msg)
