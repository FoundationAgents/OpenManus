import os
import asyncio
import json # Import json for structured output
from app.tool.base import BaseTool, ToolResult
import aiofiles # For async file operations
import logging # For logging potential issues during the tool's execution

logger = logging.getLogger(__name__)

# Developer Note:
# The rich diagnostic output from this tool (when a file/directory is not found)
# is returned as a JSON string in ToolResult.output.
# An agent could parse this JSON and use the information for more intelligent error handling.
# For example:
# - Compare `checked_path_absolute` with user-provided paths to identify discrepancies.
# - Use `parent_directory_listing` to suggest alternative files if `checked_path_original`
#   seems like a typo (e.g., "Did you mean 'prompt.txt.bkp' instead of 'prompt.txt'?").
# - Log `current_working_directory` to help diagnose issues if the agent is not running
#   in the expected directory.
class CheckFileExistenceTool(BaseTool):
    name: str = "check_file_existence"
    description: str = (
        "Verifica se um arquivo ou diretório existe no caminho especificado. "
        "Retorna SUCESSO se encontrado, ou FALHA com informações de diagnóstico detalhadas se não encontrado, "
        "incluindo o caminho absoluto verificado, o diretório de trabalho atual (CWD), "
        "e uma listagem do diretório pai."
    )

    async def _get_path_details(self, path: str) -> tuple[str, str, list[str] | str]:
        """Helper function to get absolute path, CWD, and parent directory listing."""
        try:
            # Get absolute path
            absolute_path = await asyncio.to_thread(os.path.abspath, path)
        except Exception as e:
            logger.warning(f"Error getting absolute path for {path}: {e}")
            absolute_path = f"Erro ao obter caminho absoluto: {e}"

        try:
            # Get current working directory
            current_working_directory = await asyncio.to_thread(os.getcwd)
        except Exception as e:
            logger.warning(f"Error getting CWD: {e}")
            current_working_directory = f"Erro ao obter CWD: {e}"

        parent_directory_listing: list[str] | str = []
        try:
            parent_dir = await asyncio.to_thread(os.path.dirname, absolute_path if isinstance(absolute_path, str) and not absolute_path.startswith("Erro") else path)
            if not parent_dir: # Handle cases like root or relative paths without a clear parent in the input
                 parent_dir = current_working_directory # Default to CWD if parent_dir is empty

            if await asyncio.to_thread(os.path.exists, parent_dir):
                if await asyncio.to_thread(os.path.isdir, parent_dir):
                    parent_directory_listing = await asyncio.to_thread(os.listdir, parent_dir)
                else:
                    parent_directory_listing = f"O caminho pai '{parent_dir}' não é um diretório."
            else:
                parent_directory_listing = f"O diretório pai '{parent_dir}' não foi encontrado."
        except Exception as e:
            logger.warning(f"Error listing parent directory for {path} (parent: {parent_dir if 'parent_dir' in locals() else 'N/A'}): {e}")
            parent_directory_listing = f"Erro ao listar o diretório pai: {e}"

        return absolute_path, current_working_directory, parent_directory_listing

    async def execute(self, path: str) -> ToolResult:
        path_exists = False
        error_message = None
        absolute_path_checked = ""

        try:
            # Ensure path is a string
            if not isinstance(path, str):
                return ToolResult(error=f"Erro de tipo: o caminho fornecido '{path}' não é uma string.")

            # Attempt to get absolute path early for diagnostics, even if it fails
            try:
                absolute_path_checked = await asyncio.to_thread(os.path.abspath, path)
            except Exception as e:
                absolute_path_checked = f"Não foi possível determinar o caminho absoluto para '{path}': {e}"
                logger.warning(f"Could not get abspath for {path} during execute: {e}")


            path_exists = await asyncio.to_thread(os.path.exists, path)

            if path_exists:
                output_data = {
                    "status": "SUCESSO",
                    "message": f"O arquivo ou diretório em '{path}' foi encontrado.",
                    "checked_path_original": path,
                    "checked_path_absolute": absolute_path_checked
                }
                # Attempt to convert to JSON string for output, fallback to repr
                try:
                    output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                except Exception:
                    output_str = repr(output_data)
                return ToolResult(output=output_str)
            else:
                # If not found, gather diagnostic information
                abs_path_diag, cwd_diag, parent_listing_diag = await self._get_path_details(path)

                output_data = {
                    "status": "FALHA",
                    "message": f"O arquivo ou diretório em '{path}' NÃO foi encontrado.",
                    "checked_path_original": path,
                    "checked_path_absolute": abs_path_diag, # Use the one from _get_path_details as it's more robustly attempted
                    "current_working_directory": cwd_diag,
                    "parent_directory_listing": parent_listing_diag
                }
                # Attempt to convert to JSON string for output, fallback to repr
                try:
                    output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                except Exception:
                    output_str = repr(output_data)
                return ToolResult(output=output_str)

        except Exception as e:
            logger.error(f"Erro inesperado na ferramenta CheckFileExistenceTool para o caminho '{path}': {e}", exc_info=True)
            # Gather diagnostic info even in case of an unexpected error during the check itself
            abs_path_diag, cwd_diag, parent_listing_diag = await self._get_path_details(path)

            error_output_data = {
                "status": "ERRO_INESPERADO",
                "message": f"Erro inesperado ao verificar a existência de '{path}': {str(e)}",
                "checked_path_original": path,
                "checked_path_absolute": abs_path_diag if abs_path_diag else absolute_path_checked,
                "current_working_directory": cwd_diag,
                "parent_directory_listing": parent_listing_diag
            }
            try:
                error_str = json.dumps(error_output_data, ensure_ascii=False, indent=2)
            except Exception:
                error_str = repr(error_output_data)
            return ToolResult(error=error_str)
