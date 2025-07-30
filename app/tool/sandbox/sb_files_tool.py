import asyncio
from typing import Optional, TypeVar

from pydantic import Field

from app.daytona.tool_base import Sandbox, SandboxToolsBase
from app.tool.base import ToolResult
from app.utils.files_utils import clean_path, should_exclude_file
from app.utils.logger import logger


Context = TypeVar("Context")

_FILES_DESCRIPTION = """\
A sandbox-based file system tool that allows file operations in a secure sandboxed environment.
* This tool provides commands for creating, reading, updating, and deleting files in the workspace
* All operations are performed relative to the /workspace directory for security
* Use this when you need to manage files, edit code, or manipulate file contents in a sandbox
* Each action requires specific parameters as defined in the tool's dependencies
Key capabilities include:
* File creation: Create new files with specified content and permissions
* File modification: Replace specific strings or completely rewrite files
* File deletion: Remove files from the workspace
* File reading: Read file contents with optional line range specification
"""


class SandboxFilesTool(SandboxToolsBase):
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
                "description": "The file operation to perform",
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file, relative to /workspace (e.g., 'src/main.py')",
            },
            "file_contents": {
                "type": "string",
                "description": "Content to write to the file",
            },
            "old_str": {
                "type": "string",
                "description": "Text to be replaced (must appear exactly once)",
            },
            "new_str": {
                "type": "string",
                "description": "Replacement text",
            },
            "permissions": {
                "type": "string",
                "description": "File permissions in octal format (e.g., '644')",
                "default": "644",
            },
        },
        "required": ["action"],
        "dependencies": {
            "create_file": ["file_path", "file_contents"],
            "str_replace": ["file_path", "old_str", "new_str"],
            "full_file_rewrite": ["file_path", "file_contents"],
            "delete_file": ["file_path"],
        },
    }
    SNIPPET_LINES: int = Field(default=4, exclude=True)
    # workspace_path: str = Field(default="/workspace", exclude=True)
    # sandbox: Optional[Sandbox] = Field(default=None, exclude=True)

    def __init__(
        self, sandbox: Optional[Sandbox] = None, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional sandbox and thread_id."""
        super().__init__(**data)
        if sandbox is not None:
            self._sandbox = sandbox

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to /workspace"""
        return clean_path(path, self.workspace_path)

    def _should_exclude_file(self, rel_path: str) -> bool:
        """Check if a file should be excluded based on path, name, or extension"""
        return should_exclude_file(rel_path)

    def _file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox"""
        try:
            self.sandbox.fs.get_file_info(path)
            return True
        except Exception:
            return False

    async def get_workspace_state(self) -> dict:
        """Get the current workspace state by reading all files"""
        files_state = {}
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            files = self.sandbox.fs.list_files(self.workspace_path)
            for file_info in files:
                rel_path = file_info.name

                # Skip excluded files and directories
                if self._should_exclude_file(rel_path) or file_info.is_dir:
                    continue

                try:
                    full_path = f"{self.workspace_path}/{rel_path}"
                    content = self.sandbox.fs.download_file(full_path).decode()
                    files_state[rel_path] = {
                        "content": content,
                        "is_dir": file_info.is_dir,
                        "size": file_info.size,
                        "modified": file_info.mod_time,
                    }
                except Exception as e:
                    print(f"Error reading file {rel_path}: {e}")
                except UnicodeDecodeError:
                    print(f"Skipping binary file: {rel_path}")

            return files_state

        except Exception as e:
            print(f"Error getting workspace state: {str(e)}")
            return {}

    async def execute(
        self,
        action: str,
        file_path: Optional[str] = None,
        file_contents: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        permissions: Optional[str] = "644",
        **kwargs,
    ) -> ToolResult:
        """
        Execute a file operation in the sandbox environment.
        Args:
            action: The file operation to perform
            file_path: Path to the file relative to /workspace
            file_contents: Content to write to the file
            old_str: Text to be replaced (for str_replace)
            new_str: Replacement text (for str_replace)
            permissions: File permissions in octal format
        Returns:
            ToolResult with the operation's output or error
        """
        async with asyncio.Lock():
            try:
                # File creation
                if action == "create_file":
                    if not file_path or not file_contents:
                        return self.fail_response(
                            "file_path and file_contents are required for create_file"
                        )
                    return await self._create_file(
                        file_path, file_contents, permissions
                    )

                # String replacement
                elif action == "str_replace":
                    if not file_path or not old_str or not new_str:
                        return self.fail_response(
                            "file_path, old_str, and new_str are required for str_replace"
                        )
                    return await self._str_replace(file_path, old_str, new_str)

                # Full file rewrite
                elif action == "full_file_rewrite":
                    if not file_path or not file_contents:
                        return self.fail_response(
                            "file_path and file_contents are required for full_file_rewrite"
                        )
                    return await self._full_file_rewrite(
                        file_path, file_contents, permissions
                    )

                # File deletion
                elif action == "delete_file":
                    if not file_path:
                        return self.fail_response(
                            "file_path is required for delete_file"
                        )
                    return await self._delete_file(file_path)

                else:
                    return self.fail_response(f"Unknown action: {action}")

            except Exception as e:
                logger.error(f"Error executing file action: {e}")
                return self.fail_response(f"Error executing file action: {e}")

    async def _create_file(
        self, file_path: str, file_contents: str, permissions: str = "644"
    ) -> ToolResult:
        """Create a new file with the provided contents"""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if self._file_exists(full_path):
                return self.fail_response(
                    f"File '{file_path}' already exists. Use full_file_rewrite to modify existing files."
                )

            # Create parent directories if needed
            parent_dir = "/".join(full_path.split("/")[:-1])
            if parent_dir:
                self.sandbox.fs.create_folder(parent_dir, "755")

            # Write the file content
            self.sandbox.fs.upload_file(file_contents.encode(), full_path)
            self.sandbox.fs.set_file_permissions(full_path, permissions)

            message = f"File '{file_path}' created successfully."

            # Check if index.html was created and add 8080 server info (only in root workspace)
            if file_path.lower() == "index.html":
                try:
                    website_link = self.sandbox.get_preview_link(8080)
                    website_url = (
                        website_link.url
                        if hasattr(website_link, "url")
                        else str(website_link).split("url='")[1].split("'")[0]
                    )
                    message += f"\n\n[Auto-detected index.html - HTTP server available at: {website_url}]"
                    message += "\n[Note: Use the provided HTTP server URL above instead of starting a new server]"
                except Exception as e:
                    logger.warning(
                        f"Failed to get website URL for index.html: {str(e)}"
                    )

            return self.success_response(message)
        except Exception as e:
            return self.fail_response(f"Error creating file: {str(e)}")

    async def _str_replace(
        self, file_path: str, old_str: str, new_str: str
    ) -> ToolResult:
        """Replace specific text in a file"""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' does not exist")

            content = self.sandbox.fs.download_file(full_path).decode()
            old_str = old_str.expandtabs()
            new_str = new_str.expandtabs()

            occurrences = content.count(old_str)
            if occurrences == 0:
                return self.fail_response(f"String '{old_str}' not found in file")
            if occurrences > 1:
                lines = [
                    i + 1
                    for i, line in enumerate(content.split("\n"))
                    if old_str in line
                ]
                return self.fail_response(
                    f"Multiple occurrences found in lines {lines}. Please ensure string is unique"
                )

            # Perform replacement
            new_content = content.replace(old_str, new_str)
            self.sandbox.fs.upload_file(new_content.encode(), full_path)

            # Show snippet around the edit
            replacement_line = content.split(old_str)[0].count("\n")
            start_line = max(0, replacement_line - self.SNIPPET_LINES)
            end_line = replacement_line + self.SNIPPET_LINES + new_str.count("\n")
            snippet = "\n".join(new_content.split("\n")[start_line : end_line + 1])

            message = f"Replacement successful."

            return self.success_response(message)

        except Exception as e:
            return self.fail_response(f"Error replacing string: {str(e)}")

    async def _full_file_rewrite(
        self, file_path: str, file_contents: str, permissions: str = "644"
    ) -> ToolResult:
        """Completely rewrite an existing file with new content"""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not self._file_exists(full_path):
                return self.fail_response(
                    f"File '{file_path}' does not exist. Use create_file to create a new file."
                )

            self.sandbox.fs.upload_file(file_contents.encode(), full_path)
            self.sandbox.fs.set_file_permissions(full_path, permissions)

            message = f"File '{file_path}' completely rewritten successfully."

            # Check if index.html was rewritten and add 8080 server info (only in root workspace)
            if file_path.lower() == "index.html":
                try:
                    website_link = self.sandbox.get_preview_link(8080)
                    website_url = (
                        website_link.url
                        if hasattr(website_link, "url")
                        else str(website_link).split("url='")[1].split("'")[0]
                    )
                    message += f"\n\n[Auto-detected index.html - HTTP server available at: {website_url}]"
                    message += "\n[Note: Use the provided HTTP server URL above instead of starting a new server]"
                except Exception as e:
                    logger.warning(
                        f"Failed to get website URL for index.html: {str(e)}"
                    )

            return self.success_response(message)
        except Exception as e:
            return self.fail_response(f"Error rewriting file: {str(e)}")

    async def _delete_file(self, file_path: str) -> ToolResult:
        """Delete a file at the given path"""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()

            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' does not exist")

            self.sandbox.fs.delete_file(full_path)
            return self.success_response(f"File '{file_path}' deleted successfully.")
        except Exception as e:
            return self.fail_response(f"Error deleting file: {str(e)}")

    async def cleanup(self):
        """Clean up sandbox resources."""

    @classmethod
    def create_with_context(cls, context: Context) -> "SandboxFilesTool[Context]":
        """Factory method to create a SandboxFilesTool with a specific context."""
        raise NotImplementedError(
            "create_with_context not implemented for SandboxFilesTool"
        )
