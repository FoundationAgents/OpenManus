import os

from app.config import PROJECT_ROOT
from app.logger import logger
from app.tool.base import BaseTool


class WriteFileTool(BaseTool):
    """A tool for writing content to a file within the designated output directory."""

    name: str = "write_file"
    description: str = (
        "Writes or appends the given content to a specified file. "
        "If the file exists, the content is appended to the end. If it doesn't exist, it is created. "
        "The filename must be relative to the 'output/' directory and can include subdirectories (e.g., 'subdir/report.txt'). "
        "This tool ensures files are saved safely within the project's output folder."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "The relative path (including filename) within the 'output/' directory where the content should be saved. Subdirectories are allowed.",
            },
            "content": {
                "type": "string",
                "description": "The text content to write to the file.",
            },
        },
        "required": ["filename", "content"],
    }

    async def execute(self, filename: str, content: str) -> str:
        """
        Executes the file writing operation.

        Args:
            filename (str): The relative path for the file within the output directory.
            content (str): The content to write.

        Returns:
            str: A message indicating success or failure.
        """
        output_base_dir = PROJECT_ROOT / "output"

        # Basic sanitization and path validation
        if not filename or ".." in filename or filename.startswith(("/", "\\")):
            error_msg = f"Invalid filename provided: '{filename}'. Filename must be relative and cannot contain '..' or start with a slash."
            logger.error(error_msg)
            return f"Error: {error_msg}"

        try:
            # Construct the full path
            # Use os.path.normpath to handle mixed slashes and normalize
            normalized_filename = os.path.normpath(filename)
            if normalized_filename.startswith(
                (".", "/", "\\")
            ):  # Check again after normalization
                raise ValueError(
                    "Invalid path components detected after normalization."
                )

            full_path = output_base_dir.joinpath(normalized_filename).resolve()

            # Security check: Ensure the resolved path is still within the output directory
            if not str(full_path).startswith(str(output_base_dir.resolve())):
                raise ValueError(
                    f"Attempted path traversal detected. Final path '{full_path}' is outside of '{output_base_dir.resolve()}'."
                )

            # Create necessary directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Append to the file
            file_exists = full_path.exists()
            with open(full_path, "a", encoding="utf-8") as f:
                # Optionally add a newline if appending to an existing file that's not empty
                # if file_exists and full_path.stat().st_size > 0:
                #     f.write("\n")
                f.write(content)

            relative_path = full_path.relative_to(PROJECT_ROOT)
            action = "appended to" if file_exists else "created"
            success_msg = f"Successfully {action} file '{relative_path}'"
            logger.info(success_msg)
            return success_msg

        except ValueError as ve:
            error_msg = f"Error writing file '{filename}': {ve}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except OSError as e:
            error_msg = f"Error writing file '{filename}': {e}"
            logger.error(error_msg, exc_info=True)
            return f"Error: Could not write file. {e}"
        except Exception as e:
            error_msg = (
                f"An unexpected error occurred while writing file '{filename}': {e}"
            )
            logger.error(error_msg, exc_info=True)
            return f"Error: An unexpected error occurred. {e}"
