from pathlib import Path
from typing import Any, Union

import fitz  # PyMuPDF

from app.config import config
from app.exceptions import ToolError
from app.tool import BaseTool
from app.tool.base import ToolResult
from app.tool.file_operators import FileOperator, LocalFileOperator, SandboxFileOperator


class ReadPDFTool(BaseTool):
    name: str = "read_pdf"
    description: str = "Reads and extracts text from a PDF file."
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the PDF file."}
        },
        "required": ["path"],
    }

    _local_operator: LocalFileOperator = LocalFileOperator()
    _sandbox_operator: SandboxFileOperator = SandboxFileOperator()

    def _get_operator(self) -> FileOperator:
        return (
            self._sandbox_operator
            if config.sandbox.use_sandbox
            else self._local_operator
        )

    async def execute(self, *, path: str, **kwargs: Any) -> str:
        operator = self._get_operator()

        if not path.lower().endswith(".pdf"):
            raise ToolError(f"The file '{path}' is not a PDF.")

        if not await operator.exists(path):
            raise ToolError(f"The file '{path}' does not exist.")

        is_dir = await operator.is_directory(path)
        if is_dir:
            raise ToolError(f"'{path}' is a directory, not a PDF file.")

        try:
            if isinstance(operator, LocalFileOperator):
                return self._read_pdf_local(Path(path))
            elif isinstance(operator, SandboxFileOperator):
                return await self._read_pdf_sandbox(path)
            else:
                raise ToolError("Unsupported file operator.")
        except Exception as e:
            raise ToolError(f"Failed to extract text from PDF: {str(e)}") from e

    def _read_pdf_local(self, path: Path) -> str:
        """Reads a PDF file locally using PyMuPDF."""
        try:
            doc = fitz.open(path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip() if text.strip() else "No text found in the PDF."
        except Exception as e:
            raise ToolError(f"Error reading PDF locally: {str(e)}") from e

    async def _read_pdf_sandbox(self, path: str) -> str:
        """Reads a PDF file from the sandbox using raw bytes."""
        pdf_bytes = await self._sandbox_operator.sandbox_client.read_file_binary(path)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip() if text.strip() else "No text found in the PDF."
        except Exception as e:
            raise ToolError(f"Error reading PDF from sandbox: {str(e)}") from e
