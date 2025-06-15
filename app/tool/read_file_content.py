import os
from pathlib import Path

from app.config import config
from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.file_operators import LocalFileOperator


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
            raise ToolError(f"File not found: {absolute_path}")
        except IOError as e:
            logger.error(f"ReadFileContentTool: IOError reading file {absolute_path}: {e}")
            raise ToolError(f"Error reading file {absolute_path}: {e}")
        except Exception as e:
            logger.error(f"ReadFileContentTool: Unexpected error reading file {absolute_path}: {e}")
            raise ToolError(f"Unexpected error reading file {absolute_path}: {e}")
