from typing import Optional

from pydantic import Field

from app.sandbox.providers import FileService
from app.tool.base import BaseTool, ToolResult


_FILES_DESCRIPTION = """\
Perform basic file operations inside the sandbox environment.
Paths are interpreted relative to the provider's workspace unless absolute.
"""


class SandboxFilesTool(BaseTool):
    """Provider-agnostic file management tool."""

    name: str = "sandbox_files"
    description: str = _FILES_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_file",
                    "str_replace",
                    "full_file_rewrite",
                    "delete_file",
                ],
            },
            "file_path": {"type": "string"},
            "file_contents": {"type": "string"},
            "old_str": {"type": "string"},
            "new_str": {"type": "string"},
        },
        "required": ["action"],
    }

    file_service: FileService = Field(exclude=True)

    def __init__(self, file_service: FileService, **data):
        super().__init__(file_service=file_service, **data)

    async def execute(
        self,
        action: str,
        file_path: Optional[str] = None,
        file_contents: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "create_file":
                if not file_path or file_contents is None:
                    return self.fail_response(
                        "file_path and file_contents are required for create_file"
                    )
                if await self.file_service.exists(file_path):
                    return self.fail_response(
                        f"File '{file_path}' already exists. Use full_file_rewrite instead."
                    )
                await self.file_service.write(file_path, file_contents, overwrite=True)
                return self.success_response(
                    {"message": f"File '{file_path}' created successfully."}
                )

            if action == "str_replace":
                if not file_path or old_str is None or new_str is None:
                    return self.fail_response(
                        "file_path, old_str and new_str are required for str_replace"
                    )
                content = await self.file_service.read(file_path)
                occurrences = content.count(old_str)
                if occurrences == 0:
                    return self.fail_response(
                        f"String '{old_str}' not found in '{file_path}'"
                    )
                if occurrences > 1:
                    return self.fail_response(
                        f"String '{old_str}' occurs multiple times; please make it unique."
                    )
                updated = content.replace(old_str, new_str)
                await self.file_service.write(file_path, updated, overwrite=True)
                return self.success_response(
                    {"message": f"Updated '{file_path}' successfully."}
                )

            if action == "full_file_rewrite":
                if not file_path or file_contents is None:
                    return self.fail_response(
                        "file_path and file_contents are required for full_file_rewrite"
                    )
                if not await self.file_service.exists(file_path):
                    return self.fail_response(
                        f"File '{file_path}' does not exist. Use create_file instead."
                    )
                await self.file_service.write(file_path, file_contents, overwrite=True)
                return self.success_response(
                    {"message": f"File '{file_path}' rewritten successfully."}
                )

            if action == "delete_file":
                if not file_path:
                    return self.fail_response("file_path is required for delete_file")
                if not await self.file_service.exists(file_path):
                    return self.fail_response(f"File '{file_path}' does not exist")
                await self.file_service.delete(file_path)
                return self.success_response(
                    {"message": f"File '{file_path}' deleted successfully."}
                )

            return self.fail_response(f"Unknown action: {action}")

        except Exception as exc:
            return self.fail_response(f"File action failed: {exc}")
