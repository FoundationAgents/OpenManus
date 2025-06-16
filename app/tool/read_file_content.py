import os
from pathlib import Path

from app.config import config
from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.file_operators import LocalFileOperator
from app.tool.file_system_tools import ListFilesTool # Nova importação


class ReadFileContentTool(BaseTool):
    """
    Reads the entire content of a specified file and returns it as a string.
    Use this to get the full context of a file for analysis or understanding.
    """

    name: str = "read_file_content"
    description: str = (
        "Reads the entire content of a specified file and returns it as a string. "
        "Use this to get the full context of a file for analysis or understanding."
    )
    args_schema: dict = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the file."},
        },
        "required": ["path"],
    }

    async def execute(self, path: str) -> ToolResult:
        """
        Reads the entire content of a specified file and returns it as a string.

        Args:
            path: Absolute path to the file.

        Returns:
            The content of the file as a string.
        """
        absolute_path = Path(path)
        if not absolute_path.is_absolute():
            absolute_path = Path(config.workspace_root) / path

        logger.info(f"ReadFileContentTool: Attempting to read file: {absolute_path}")
        local_file_op = LocalFileOperator()

        try:
            # LocalFileOperator.read_file is async, so it needs to be awaited
            content = await local_file_op.read_file(str(absolute_path))
            logger.info(f"ReadFileContentTool: Successfully read file: {absolute_path}, content length: {len(content)}")
            return ToolResult(output=content)
        except FileNotFoundError as e:
            logger.error(f"ReadFileContentTool: FileNotFoundError reading file {absolute_path}: {e}")

            parent_dir_listing_str = "Could not list parent directory."
            try:
                parent_dir = absolute_path.parent
                # Ensure parent_dir is within workspace_root for security before listing
                if not str(parent_dir.resolve()).startswith(str(config.workspace_root.resolve())):
                    parent_dir_listing_str = f"Parent directory '{parent_dir}' is outside the allowed workspace. Cannot list."
                    logger.warning(f"Attempt to list parent directory '{parent_dir}' outside workspace denied.")
                else:
                    list_files_tool = ListFilesTool()
                    # Chamar execute com path e depth.
                    list_result = await list_files_tool.execute(path=str(parent_dir), depth=1)
                    if list_result.error:
                        parent_dir_listing_str = f"Error listing parent directory '{parent_dir}': {list_result.error}"
                    elif list_result.output:
                        # A saída de ListFilesTool é uma string JSON.
                        # Para melhor legibilidade, podemos tentar parsear e formatar um pouco,
                        # mas usar diretamente também é uma opção.
                        try:
                            parsed_listing = json.loads(list_result.output)
                            items_str = "\n".join([f"  - {item.get('path')} ({item.get('type')})" for item in parsed_listing.get('items', [])])
                            if not items_str:
                                items_str = "  (empty or no items found)"
                            parent_dir_listing_str = f"Listing of parent directory '{parent_dir}':\n{items_str}"
                        except json.JSONDecodeError:
                             parent_dir_listing_str = f"Listing of parent directory '{parent_dir}' (raw JSON):\n{list_result.output}"
                        except Exception as parse_fmt_e:
                            logger.error(f"ReadFileContentTool: Error parsing/formatting ListFilesTool output: {parse_fmt_e}")
                            parent_dir_listing_str = f"Listing of parent directory '{parent_dir}' (raw output, format error):\n{list_result.output}"

                    else:
                        parent_dir_listing_str = f"Parent directory '{parent_dir}' is empty or no output from list_files."

            except Exception as list_e:
                logger.error(f"ReadFileContentTool: Error when trying to list parent directory for {absolute_path}: {list_e}", exc_info=True)
                parent_dir_listing_str = f"Exception while trying to list parent directory: {list_e}"

            # Modificar a mensagem de erro para incluir a listagem
            error_message = (
                f"File not found: {absolute_path}.\n"
                f"{parent_dir_listing_str}"
            )
            raise ToolError(error_message)
        except IOError as e:
            logger.error(f"ReadFileContentTool: IOError reading file {absolute_path}: {e}")
            raise ToolError(f"Error reading file {absolute_path}: {e}")
        except Exception as e: # Catch-all for other unexpected errors during the read attempt itself
            logger.error(f"ReadFileContentTool: Unexpected error reading file {absolute_path}: {e}", exc_info=True)
            # Attempt to list parent directory even for other errors if absolute_path is defined
            parent_dir_listing_str = "Could not list parent directory due to earlier error."
            if 'absolute_path' in locals() and absolute_path:
                try:
                    parent_dir = absolute_path.parent
                    if not str(parent_dir.resolve()).startswith(str(config.workspace_root.resolve())):
                        parent_dir_listing_str = f"Parent directory '{parent_dir}' is outside the allowed workspace. Cannot list."
                    else:
                        list_files_tool = ListFilesTool()
                        list_result = await list_files_tool.execute(path=str(parent_dir), depth=1)
                        if list_result.error:
                            parent_dir_listing_str = f"Error listing parent directory '{parent_dir}' (during general error handling): {list_result.error}"
                        elif list_result.output:
                             parent_dir_listing_str = f"Parent directory '{parent_dir}' listing (during general error handling):\n{list_result.output}"
                        else:
                            parent_dir_listing_str = f"Parent directory '{parent_dir}' is empty or no output (during general error handling)."
                except Exception as list_e_general:
                    parent_dir_listing_str = f"Exception listing parent directory (during general error handling): {list_e_general}"

            raise ToolError(f"Unexpected error reading file {absolute_path}: {e}. {parent_dir_listing_str}")
