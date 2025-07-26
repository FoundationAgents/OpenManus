import asyncio # Should be there
import os
import uuid
from typing import Any, Dict, Optional

from app.sandbox.client import SANDBOX_CLIENT
from app.config import config
from app.sandbox.core.exceptions import SandboxTimeoutError
from app.tool.base import BaseTool, ToolResult # Import ToolResult
from app.exceptions import ToolError
from app.logger import logger


class SandboxPythonExecutor(BaseTool):
    """
    Executes Python code or a Python script file within a secure sandbox environment.
    If 'file_path' is provided, it must be an absolute path to a Python script on the
    host machine, located within the agent's configured workspace root. This file will
    be copied into the sandbox for execution.
    If 'code' is provided, the raw Python code string will be executed.
    Only one of 'file_path' or 'code' can be provided.
    The tool captures and returns stdout, stderr, and the exit code from the execution.
    """

    name: str = "sandbox_python_executor"
    description: str = (
        "Executes Python code (from string or host file_path) in a sandbox. "
        "If file_path is used, it must be an absolute path on the host within the workspace root. "
        "The file is copied to '/workspace/scripts_from_host/' in the sandbox. "
        "Captures stdout, stderr, and exit code."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string", 
                "description": "Optional. The Python code string to execute. If provided, 'file_path' must be None."
            },
            "file_path": {
                "type": "string", 
                "description": "Optional. The absolute path to a Python script file on the host machine (must be within the configured workspace) to be executed in the sandbox. If provided, 'code' must be None."
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds.",
                "default": 60, # Default timeout increased as per new signature
            },
        },
        "required": [] # Validation of code OR file_path is done in execute
    }

    async def execute(self, code: Optional[str] = None, timeout: int = 60, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes Python code from a string or a file path (copied from host) within the sandbox.
        """
        logger.info(f"SandboxPythonExecutor.execute called. Code provided: {bool(code)}, file_path: '{file_path}', timeout: {timeout}")

        if not config.sandbox.use_sandbox:
            error_msg = "SandboxPythonExecutor cannot be used because config.sandbox.use_sandbox is set to False. Use PythonExecute for host execution or enable the sandbox in the configuration."
            logger.error(error_msg)
            # Retornar um dicionário que se assemelha a uma falha de ferramenta para consistência
            return {
                "stdout": "",
                "stderr": f"ToolError: {error_msg}",
                "exit_code": -5, # Código de erro específico para sandbox desabilitado
            }

        # Validação inicial de parâmetros
        
        # Args:
        #     code: An optional string containing the Python code.
        #     timeout: Max execution time in seconds. Defaults to 60.
        #     file_path: An optional string specifying the absolute path to a Python script
        #                on the host machine (within workspace_root) to be copied and executed.
        #
        # Returns:
        #     A dictionary containing the execution results:
        #     - "stdout" (str): The standard output from the executed code.
        #     - "stderr" (str): The standard error output. This will include
        #                       tracebacks if the Python script raises an unhandled exception.
        #     - "exit_code" (int): The exit code of the Python script.
        #                          Typically, 0 indicates success, and non-zero
        #                          indicates an error. A special exit code 124
        #                          is used if the execution times out. Other negative
        #                          values (-1, -2, -3) might indicate internal tool
        #                          or sandbox errors.
        #
        # Raises:
        #     No explicit exceptions are raised by this method directly to the caller.
        #     Instead, errors are captured and returned within the result dictionary
        #     (e.g., in "stderr" and "exit_code").
        #     - SandboxTimeoutError: If execution exceeds `timeout`, `stderr` will
        # END DOCSTRING

        logger.info(f"SandboxPythonExecutor.execute called. Code provided: {bool(code)}, file_path: '{file_path}', timeout: {timeout}")
        # Validação inicial de parâmetros
        if not code and not file_path:
            logger.warning("Neither 'code' nor 'file_path' provided to SandboxPythonExecutor. Aborting.")
            return {"stdout": "", "stderr": "ToolError: Either 'code' or 'file_path' must be provided.", "exit_code": -1}
        if code and file_path:
            logger.warning("Both 'code' and 'file_path' provided to SandboxPythonExecutor. Aborting.")
            return {"stdout": "", "stderr": "ToolError: Cannot provide both 'code' and 'file_path'.", "exit_code": -1}

        script_to_execute_in_sandbox = ""
        original_script_filename_on_host = None # Para saber se precisa limpar no sandbox depois
        # cleanup_temp_script_in_sandbox = False # Flag para limpar script temporário de 'code' # Não mais necessária com original_script_filename_on_host

        # Garantir que o sandbox está criado e rodando
        if not SANDBOX_CLIENT.sandbox or not SANDBOX_CLIENT.sandbox.container:
            try:
                await SANDBOX_CLIENT.create()
            except Exception as e:
                return {
                    "stdout": "",
                    "stderr": "ToolError: {'success': false, 'error_type': 'environment', 'message': 'Falha ao conectar com o sandbox. Verifique se o Docker está instalado e em execução ou se a imagem configurada está disponível.'}",
                    "exit_code": -2,
                }
        
        if file_path:
            host_abs_path = os.path.abspath(file_path)
            # Validar se o file_path está dentro do workspace_root configurado
            if not host_abs_path.startswith(str(config.workspace_root)):
                logger.warning(f"Attempt to execute file_path '{file_path}' (abs: '{host_abs_path}') outside workspace '{config.workspace_root}'. Denied.")
                return {"stdout": "", "stderr": f"ToolError: file_path '{file_path}' is outside the allowed workspace directory '{config.workspace_root}'.", "exit_code": -4}
            if not os.path.exists(host_abs_path):
                logger.warning(f"File_path '{file_path}' (abs: '{host_abs_path}') not found on host. Denied.")
                return {"stdout": "", "stderr": f"ToolError: file_path '{file_path}' does not exist on the host.", "exit_code": -4}
            if not os.path.isfile(host_abs_path):
                # This case might be redundant if os.path.exists already fails for non-files, but good for clarity
                logger.warning(f"File_path '{file_path}' (abs: '{host_abs_path}') is not a file. Denied.")
                return {"stdout": "", "stderr": f"ToolError: file_path '{file_path}' is not a file on the host.", "exit_code": -4}

            script_filename_in_sandbox = os.path.basename(host_abs_path)
            sandbox_internal_dir = "/workspace/scripts_from_host" 
            
            try:
                # This mkdir might not be strictly necessary if copy_to handles dir creation,
                # but it's good for explicit control and logging.
                mkdir_cmd = f"mkdir -p {sandbox_internal_dir}"
                logger.info(f"Ensuring directory '{sandbox_internal_dir}' exists in sandbox.")
                mkdir_result = await SANDBOX_CLIENT.run_command(mkdir_cmd, timeout=10)
                if mkdir_result.get("exit_code") != 0:
                    logger.error(f"Failed to create directory '{sandbox_internal_dir}' in sandbox. Stderr: {mkdir_result.get('stderr','')}")
                    return {"stdout": "", "stderr": f"SandboxError: Failed to create directory '{sandbox_internal_dir}' in sandbox. Stderr: {mkdir_result.get('stderr','')}", "exit_code": -2}
            except Exception as e_mkdir:
                 logger.error(f"Exception creating directory '{sandbox_internal_dir}' in sandbox: {e_mkdir}")
                 return {"stdout": "", "stderr": f"SandboxError: Exception creating directory '{sandbox_internal_dir}' in sandbox: {e_mkdir}", "exit_code": -2}

            sandbox_internal_path = f"{sandbox_internal_dir}/{script_filename_in_sandbox}"
            logger.info(f"Preparing to copy from host path '{host_abs_path}' to sandbox path '{sandbox_internal_path}'")
            try:
                await SANDBOX_CLIENT.copy_to(local_path=host_abs_path, container_path=sandbox_internal_path)
                logger.info(f"Successfully copied '{host_abs_path}' to '{sandbox_internal_path}' in sandbox.")
                script_to_execute_in_sandbox = sandbox_internal_path
                original_script_filename_on_host = sandbox_internal_path # Guardar para limpeza no sandbox
            except Exception as e_copy:
                logger.error(f"Failed to copy file_path '{file_path}' to sandbox: {str(e_copy)}")
                return {"stdout": "", "stderr": f"ToolError: Failed to copy file_path '{file_path}' to sandbox: {str(e_copy)}", "exit_code": -4}
        
        elif code: # Se não for file_path, mas code
            temp_script_filename = f"/tmp/{uuid.uuid4().hex}.py"
            logger.info(f"Writing provided code to temporary sandbox file: {temp_script_filename}")
            await SANDBOX_CLIENT.write_file(temp_script_filename, code)
            script_to_execute_in_sandbox = temp_script_filename
            original_script_filename_on_host = temp_script_filename # Guardar para limpeza no sandbox
            # cleanup_temp_script_in_sandbox = True # Marcar para limpar este script específico de /tmp

        pid_file_sandbox_path = f"/tmp/script_pid_{uuid.uuid4().hex}.pid"
        command = f"sh -c 'echo $$ > {pid_file_sandbox_path}; exec python3 {script_to_execute_in_sandbox}'"
        logger.info(f"Executing command in sandbox: '{command}' (PID file: {pid_file_sandbox_path})")

        stdout_val = ""
        stderr_val = ""
        exit_code_val = -1
        # generated_files = [] # Mantido comentado

        try:
            result = await SANDBOX_CLIENT.run_command(command, timeout=timeout)
            stdout_val = result.get("stdout", "")
            stderr_val = result.get("stderr", "") 
            exit_code_val = result.get("exit_code", -1)

            # Lógica de copiar arquivos de /tmp para ./workspace (COMENTADA POR ENQUANTO)
            # A subtask não pede para manter ou remover explicitamente, mas com a nova lógica de scripts
            # sendo executados de /workspace/scripts_from_host, esta parte pode precisar ser reavaliada.
            # if not (file_path and file_path.startswith("/tmp/")) and exit_code_val != 2 :
            #     os.makedirs("./workspace", exist_ok=True)
            #     list_files_cmd = "ls /tmp/ 2>/dev/null"
            #     # ... (resto da lógica como estava antes, mas precisa cuidado com script_filename vs original_script_filename_on_host)

        except SandboxTimeoutError as e_timeout:
            stderr_val = f"SandboxTimeoutError: A execução do comando '{command}' excedeu o tempo limite de {timeout} segundos.\nDetalhes: {str(e_timeout)}"
            exit_code_val = 124
        except FileNotFoundError as e_fnf: 
            stderr_val = f"FileNotFoundError during sandbox execution: {str(e_fnf)}"
            exit_code_val = 2 
        except Exception as e_runtime:
            stderr_val = f"An unexpected error occurred during sandbox execution: {str(e_runtime)}"
            exit_code_val = -3
        
        if original_script_filename_on_host: 
            try:
                cleanup_command = f"rm -f {original_script_filename_on_host}"
                logger.info(f"Attempting to cleanup sandbox script: {cleanup_command}")
                await SANDBOX_CLIENT.run_command(cleanup_command, timeout=5)
                logger.info(f"Successfully cleaned up sandbox script: {original_script_filename_on_host}")
            except Exception as e_cleanup:
                additional_stderr = f"Warning: Failed to cleanup script '{original_script_filename_on_host}' in sandbox: {str(e_cleanup)}"
                logger.warning(additional_stderr)
                stderr_val = f"{stderr_val}\n{additional_stderr}".strip()
        
        logger.info(f"Returning execution result: stdout='{stdout_val.strip()}', stderr='{stderr_val.strip()}', exit_code={exit_code_val}")
        return {
            "stdout": stdout_val.strip(),
            "stderr": stderr_val.strip(),
            "exit_code": exit_code_val,
            "pid_file_path": pid_file_sandbox_path
        }

# Example of how to register the tool (if a registration mechanism exists)
# This part is usually handled by the tool management system.
# from app.tool_registry import register_tool
# register_tool(SandboxPythonExecutor)
