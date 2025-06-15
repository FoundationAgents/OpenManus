import os
from typing import Dict, Union

from app.tool.base import BaseTool
from app.tool.file_operators import LocalFileOperator # To use for writing
from app.config import config # For workspace path resolution
from app.logger import logger
from app.exceptions import ToolError # For error handling

class ReplaceEntireFileContent(BaseTool):
    name: str = "replace_entire_file_content"
    description: str = (
        "Overwrites the entire content of a specified file with new_content. "
        "This is useful for tasks like updating a checklist file where providing the "
        "full new content is more robust than partial string replacement. "
        "If the file does not exist, it will be created. "
        "Relative paths are resolved from the agent's workspace root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative (from workspace root) or absolute path to the file to be overwritten or created.",
            },
            "new_content": {
                "type": "string",
                "description": "The entire new content to be written to the file.",
            }
        },
        "required": ["path", "new_content"],
    }

    _local_operator: LocalFileOperator = LocalFileOperator()

    async def execute(self, path: str, new_content: str) -> Dict[str, str]:
        """
        Overwrites a file with new content. Creates the file if it doesn't exist.

        Args:
            path (str): The path to the file.
            new_content (str): The new content for the file.

        Returns:
            Dict[str, str]: A dictionary with a 'status' or 'error' message.
        """
        original_path_for_logging = path # Keep original path for user-facing messages

        if not os.path.isabs(path):
            file_path = os.path.join(config.workspace_root, path)
        else:
            file_path = path

        # Normalize the path to handle potential ".." or "." segments and ensure it's an absolute path
        file_path = os.path.normpath(os.path.abspath(file_path))

        # Security check: Ensure the path is still within the workspace_root
        if not file_path.startswith(os.path.normpath(os.path.abspath(config.workspace_root))):
            logger.error(f"Path traversal attempt detected for replace_entire_file_content. Original path: '{original_path_for_logging}', Resolved path: '{file_path}' is outside workspace '{os.path.normpath(os.path.abspath(config.workspace_root))}'.")
            return {"error": f"Path is outside the allowed workspace: {original_path_for_logging}"}

        try:
            # Ensure new_content is a string
            if not isinstance(new_content, str):
                logger.warning(f"new_content was not a string (type: {type(new_content)}), converting to string.")
                new_content = str(new_content)

            # Basic null byte sanitization
            processed_content = new_content.replace('\u0000', '')
            if processed_content != new_content:
                logger.warning("Null bytes were removed from new_content before writing to file.")

            # Check if file exists before writing to determine action for logging
            file_existed_before_write = os.path.exists(file_path)

            await self._local_operator.write_file(file_path, processed_content)

            action = "overwritten" if file_existed_before_write else "created"
            # To be absolutely sure for "overwritten", we could check if it existed *and* if the write_file actually modified it
            # (e.g. if it was already there and write_file is smart to not touch it if content is same).
            # However, LocalFileOperator.write_file implies an overwrite.

            logger.info(f"Successfully {action} file {file_path} (original input: '{original_path_for_logging}') with new content.")
            return {"status": f"File {original_path_for_logging} successfully {action}."}
        except ToolError as e:
            logger.error(f"ToolError writing file {file_path} (original input: '{original_path_for_logging}'): {e}")
            return {"error": f"Failed to write file '{original_path_for_logging}': {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error writing file {file_path} (original input: '{original_path_for_logging}'): {e}", exc_info=True)
            return {"error": f"An unexpected error occurred while writing file '{original_path_for_logging}': {str(e)}"}
