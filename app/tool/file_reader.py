import os
from typing import Dict, Union

from app.tool.base import BaseTool
from app.tool.file_operators import LocalFileOperator # To use for reading
from app.config import config # For workspace path resolution
from app.logger import logger
from app.exceptions import ToolError # For error handling

class ReadFileContent(BaseTool):
    name: str = "read_file_content"
    description: str = (
        "Reads and returns the entire raw content of a specified file. "
        "This tool should be used when the full context of a file is needed for analysis or processing. "
        "Relative paths are resolved from the agent's workspace root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative (from workspace root) or absolute path to the file to be read.",
            }
        },
        "required": ["path"],
    }

    _local_operator: LocalFileOperator = LocalFileOperator()

    async def execute(self, path: str) -> Union[str, Dict[str, str]]:
        """
        Reads and returns the full, raw, untruncated content of a file.

        Args:
            path (str): The path to the file.

        Returns:
            Union[str, Dict[str, str]]: The full file content as a string if successful,
                                         or a dictionary with an 'error' message if reading fails.
        """
        # Resolve the path relative to the workspace root if it's not absolute
        if not os.path.isabs(path):
            file_path = os.path.join(config.workspace_root, path)
        else:
            file_path = path

        # Normalize the path to handle potential ".." or "." segments and ensure it's an absolute path
        file_path = os.path.normpath(os.path.abspath(file_path))

        # Security check: Ensure the path is still within the workspace_root
        # This is important even for read operations to prevent arbitrary file access.
        if not file_path.startswith(os.path.normpath(os.path.abspath(config.workspace_root))):
            logger.error(f"Path traversal attempt detected for read_file_content. Original path: '{path}', Resolved path: '{file_path}' is outside workspace '{os.path.normpath(os.path.abspath(config.workspace_root))}'.")
            return {"error": f"Path is outside the allowed workspace: {path}"}

        # Check using os.path.isfile first, as LocalFileOperator.read_file might raise specific ToolErrors for not found
        # that we want to catch more generically here for this tool's specific error reporting.
        if not os.path.isfile(file_path):
            logger.error(f"File not found at path for read_file_content: {file_path} (original input: '{path}')")
            return {"error": f"File not found: {path} (resolved to: {file_path})"}

        try:
            # Use the instantiated LocalFileOperator
            content = await self._local_operator.read_file(file_path)
            logger.info(f"Successfully read {len(content)} characters from {file_path}.")
            return content
        except ToolError as e: # Catch specific ToolError from LocalFileOperator (e.g., if it has its own not found)
            logger.error(f"ToolError reading file {file_path} (original input: '{path}'): {e}")
            # Return the specific error from LocalFileOperator if available and informative
            return {"error": f"Failed to read file '{path}': {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error reading file {file_path} (original input: '{path}'): {e}", exc_info=True)
            return {"error": f"An unexpected error occurred while reading file '{path}': {str(e)}"}
