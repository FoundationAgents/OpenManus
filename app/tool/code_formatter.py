import asyncio
import subprocess
import traceback
from typing import Dict, Union

from app.tool.base import BaseTool
from app.logger import logger

class FormatPythonCode(BaseTool):
    name: str = "format_python_code"
    description: str = (
        "Formats a given Python code string using an external formatter (Ruff, with Black as fallback). "
        "This helps ensure consistent code style and can fix minor syntax/indentation issues."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code string to format.",
            }
        },
        "required": ["code"],
    }

    async def execute(self, code: str) -> Union[str, Dict[str, str]]:
        """
        Formats the Python code using Ruff, with Black as a fallback.

        Args:
            code (str): The Python code string to format.

        Returns:
            Union[str, Dict[str, str]]: The formatted code string if successful,
                                         or a dictionary with an error message if formatting fails.
        """
        try:
            # Try Ruff first
            # Using --stdin-filename temp.py helps ruff apply project-specific rules if pyproject.toml is found
            process_ruff = await asyncio.create_subprocess_shell(
                "ruff format --stdin-filename temp.py -",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout_ruff, stderr_ruff = await process_ruff.communicate(input=code.encode())

            if process_ruff.returncode == 0:
                formatted_code = stdout_ruff.decode()
                logger.info("Code successfully formatted using Ruff.")
                return formatted_code
            else:
                ruff_error_output = stderr_ruff.decode()
                logger.warning(f"Ruff formatting failed. Return code: {process_ruff.returncode}. Error: {ruff_error_output}")
                logger.info("Attempting to format with Black as a fallback.")

                process_black = await asyncio.create_subprocess_shell(
                    "black -q -", # -q for quiet, suppresses non-error messages from Black
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout_black, stderr_black = await process_black.communicate(input=code.encode())

                if process_black.returncode == 0:
                    formatted_code_black = stdout_black.decode()
                    logger.info("Code successfully formatted using Black.")
                    return formatted_code_black
                else:
                    black_error_output = stderr_black.decode()
                    logger.error(f"Black formatting also failed. Return code: {process_black.returncode}. Error: {black_error_output}")
                    return {
                        "error": "Formatting failed with both Ruff and Black.",
                        "ruff_error": ruff_error_output,
                        "black_error": black_error_output,
                    }

        except FileNotFoundError as e:
            # This catches if 'ruff' or 'black' command itself is not found
            logger.error(f"Formatter command not found (Ruff or Black): {e}. Ensure they are installed and in PATH.")
            return {"error": f"Formatter command not found: {e}. Please ensure Ruff (or Black as fallback) is installed and in the system PATH."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during code formatting: {e}\n{traceback.format_exc()}")
            return {"error": f"An unexpected error occurred during formatting: {str(e)}"}
