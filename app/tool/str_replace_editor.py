"""File and directory manipulation tool with sandbox support."""
import os # Ensure os is imported
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, List, Literal, Optional, get_args

from app.config import config
from app.exceptions import ToolError
from app.tool import BaseTool
from app.tool.base import CLIResult, ToolResult
from app.tool.file_operators import (
    FileOperator,
    LocalFileOperator,
    PathLike,
    SandboxFileOperator,
)
from app.logger import logger # Moved import here


Command = Literal[
    "view",
    "create",
    "str_replace",
    "insert",
    "undo_edit",
    "copy_to_sandbox", # Nova opção
]

# Constants
SNIPPET_LINES: int = 4
MAX_RESPONSE_LEN: int = 16000
TRUNCATED_MESSAGE: str = (
    "<response clipped><NOTE>To save on context only part of this file has been shown to you. "
    "You should retry this tool after you have searched inside the file with `grep -n` "
    "in order to find the line numbers of what you are looking for.</NOTE>"
)

# Tool description
_STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`
* O comando `copy_to_sandbox` copia um arquivo do sistema de arquivos local (host) para dentro do diretório `/workspace` do sandbox. Requer o parâmetro `path` (caminho do arquivo no host) e opcionalmente `container_filename` (nome do arquivo no sandbox, se diferente do original).

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""


def maybe_truncate(
    content: str, truncate_after: Optional[int] = MAX_RESPONSE_LEN
) -> str:
    """Truncate content and append a notice if content exceeds the specified length."""
    if not truncate_after or len(content) <= truncate_after:
        return content
    return content[:truncate_after] + TRUNCATED_MESSAGE


class StrReplaceEditor(BaseTool):
    """A tool for viewing, creating, and editing files with sandbox support."""

    name: str = "str_replace_editor"
    description: str = _STR_REPLACE_EDITOR_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`, `copy_to_sandbox`.",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit", "copy_to_sandbox"],
                "type": "string",
            },
            "path": {
                "description": "Absolute path to file or directory. For `copy_to_sandbox`, this is the source path on the host.",
                "type": "string",
            },
            "file_text": {
                "description": "Required parameter of `create` command, with the content of the file to be created.",
                "type": "string",
            },
            "old_str": {
                "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
                "type": "string",
            },
            "new_str": {
                "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
                "type": "string",
            },
            "insert_line": {
                "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
                "type": "integer",
            },
            "view_range": {
                "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                "items": {"type": "integer"},
                "type": "array",
            },
            "container_filename": { # Novo parâmetro
                "description": "Optional. For `copy_to_sandbox` command. The desired filename for the file inside the sandbox's /workspace directory. If not provided, the original filename from the host path is used.",
                "type": "string",
                "nullable": True
            },
            "overwrite": { # Added for create command
                "description": "Optional parameter of `create` command. If true, overwrite the file if it already exists. Defaults to false.",
                "type": "boolean",
            }
        },
        "required": ["command", "path"],
    }
    _file_history: DefaultDict[PathLike, List[str]] = defaultdict(list)
    _local_operator: LocalFileOperator = LocalFileOperator()
    _sandbox_operator: SandboxFileOperator = SandboxFileOperator()

    @staticmethod
    def _sanitize_text_for_file(text_content: Any) -> Any:
        if not isinstance(text_content, str):
            # Warning removed: print(f"Warning: StrReplaceEditor._sanitize_text_for_file expected string but got {type(text_content)}. Returning as is.", file=sys.stderr)
            return text_content
        sanitized_content = text_content.replace('\u0000', '')
        return sanitized_content

    def _get_operator(self) -> FileOperator:
        """Get the appropriate file operator based on execution mode."""
        return (
            self._sandbox_operator
            if config.sandbox.use_sandbox
            else self._local_operator
        )

    async def execute(
        self,
        *,
        command: Command,
        path: str, 
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        container_filename: Optional[str] = None,
        overwrite: bool = False, # Added overwrite parameter
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a file operation command."""
        
        if command == "copy_to_sandbox":
            # Ensure path is absolute for host operations before any operator selection
            # or workspace path prepending, as copy_to_sandbox host path is always absolute from user.
            host_path_for_copy = Path(path)
            if not host_path_for_copy.is_absolute():
                 raise ToolError(f"For 'copy_to_sandbox', the source 'path' on the host ('{path}') must be absolute.")

            await self.validate_path(command, host_path_for_copy, self._local_operator)
            try:
                target_container_filename = container_filename or os.path.basename(path)
                if not target_container_filename: 
                     raise ToolError("Could not determine a valid target filename for the container from the provided path.")
                container_path = f"/workspace/{target_container_filename}"
                # copy_to_sandbox always uses sandbox_operator's client for the destination.
                await self._sandbox_operator.sandbox_client.copy_to_sandbox(host_path=str(host_path_for_copy), container_path=container_path)
                result = ToolResult(output=f"Arquivo {str(host_path_for_copy)} copiado para {container_path} no sandbox com sucesso.")
                return result
            except Exception as e:
                raise ToolError(f"Erro ao copiar arquivo para o sandbox: {e}")

        # For commands other than copy_to_sandbox, determine operator and potentially make path relative to workspace
        operator = self._get_operator()

        path_obj = Path(path)
        if not path_obj.is_absolute():
            path = str(config.workspace_root / path_obj)
            path_obj = Path(path) # Update path_obj to the new absolute path

        # Validate path for non-copy_to_sandbox commands using the chosen operator
        # Pass the 'overwrite' flag to validate_path for the 'create' command
        await self.validate_path(command, path_obj, operator, overwrite_flag_for_create=overwrite if command == "create" else None)

        if command == "view":
            result = await self.view(path_obj, view_range, operator)
        elif command == "create":
            if file_text is None:
                raise ToolError("Parameter `file_text` is required for command: create")
            file_text = StrReplaceEditor._sanitize_text_for_file(file_text)

            # Existence check is now handled by validate_path for create (if overwrite is false)
            # If validate_path passed (either file doesn't exist, or it does and overwrite=True), we can write.
            log_message_action = "Overwriting file" if await operator.exists(path_obj) else "Creating file"
            await operator.write_file(path_obj, file_text)

            # Manage file history only for successful writes of new content (not overwrites of identical content, though current logic doesn't check that)
            # For simplicity, we'll record history on any write here.
            self._file_history[str(path_obj)].append(file_text) # Use string path for dict key
            action_past_tense = "overwritten" if log_message_action == "Overwriting file" else "created"
            result = ToolResult(output=f"File {action_past_tense} successfully at: {str(path_obj)}")
            return result # Ensure ToolResult is returned directly
        elif command == "str_replace":
            if old_str is None:
                raise ToolError(
                    "Parameter `old_str` is required for command: str_replace"
                )
            result = await self.str_replace(path, old_str, new_str, operator)
        elif command == "insert":
            if insert_line is None:
                raise ToolError(
                    "Parameter `insert_line` is required for command: insert"
                )
            if new_str is None:
                raise ToolError("Parameter `new_str` is required for command: insert")
            result = await self.insert(path, insert_line, new_str, operator)
        elif command == "undo_edit":
            result = await self.undo_edit(path, operator)
        else: # Should only be copy_to_sandbox if not caught above, but that is handled.
             # This case should ideally not be reached if command is valid and handled.
            raise ToolError(
                 f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
            )
        return result # result is already a ToolResult from the branches above

    async def validate_path(
        self, command: str, path: Path, operator: FileOperator, overwrite_flag_for_create: Optional[bool] = None
    ) -> None:
        """Validate path and command combination based on execution environment."""

        if command == "copy_to_sandbox": # Validation for copy_to_sandbox (host path)
            host_path_obj = path # In this context, path is the host_path
            if not host_path_obj.is_absolute(): # This check might be redundant if called after host_path_for_copy is made absolute
                raise ToolError(f"Para 'copy_to_sandbox', o 'path' (origem no host) '{host_path_obj}' deve ser absoluto.")
            # Use os.path for host checks, not operator (which could be sandbox)
            if not os.path.exists(str(host_path_obj)): 
                raise ToolError(f"Para 'copy_to_sandbox', o arquivo de origem no host '{host_path_obj}' não existe.")
            if not os.path.isfile(str(host_path_obj)): 
                raise ToolError(f"Para 'copy_to_sandbox', o 'path' de origem no host '{host_path_obj}' não é um arquivo.")
            return # Validation for copy_to_sandbox is complete

        # Validations for other commands (view, create, str_replace, insert, undo_edit)
        if not path.is_absolute(): # This should have been handled by the caller for non-copy_to_sandbox
            raise ToolError(f"The path {path} must be an absolute path for this operation.")

        path_exists_result = await operator.exists(path)

        if command == "create":
            if path_exists_result and overwrite_flag_for_create is False: # Explicitly check for False
                raise ToolError(
                    f"File '{str(path)}' already exists. Set 'overwrite=True' to replace it."
                )
            # If path_exists_result is True and overwrite_flag_for_create is True, it's okay.
            # If path_exists_result is False, it's also okay.
        else: # For commands other than 'create'
            if not path_exists_result:
                raise ToolError(
                    f"The path {path} does not exist. Please provide a valid path."
                )
            is_dir_result = await operator.is_directory(path)
            if is_dir_result and command != "view": 
                raise ToolError(
                    f"The path {path} is a directory and only the `view` command can be used on directories."
                )

    async def view(
        self,
        path: PathLike, # path is now Path object
        view_range: Optional[List[int]] = None,
        operator: FileOperator = None,
    ) -> CLIResult:
        """Display file or directory content."""
        is_dir = await operator.is_directory(path)
        if is_dir:
            if view_range:
                raise ToolError(
                    "The `view_range` parameter is not allowed when `path` points to a directory."
                )
            return await self._view_directory(path, operator)
        else:
            return await self._view_file(path, operator, view_range)

    @staticmethod
    async def _view_directory(path: PathLike, operator: FileOperator) -> CLIResult:
        """Display directory contents."""
        effective_path = str(path)
        if isinstance(operator, SandboxFileOperator):
            effective_path = await operator.get_sandbox_path(path)
        find_cmd = f"find {effective_path} -maxdepth 2 -not -path '*/\\.*'"
        returncode, stdout, stderr = await operator.run_command(find_cmd)
        if not stderr:
            stdout = (
                f"Here's the files and directories up to 2 levels deep in {path}, "
                f"excluding hidden items:\n{stdout}\n"
            )
        return CLIResult(output=stdout, error=stderr)

    async def _view_file(
        self,
        path: PathLike,
        operator: FileOperator,
        view_range: Optional[List[int]] = None,
    ) -> CLIResult:
        """Display file content, optionally within a specified line range."""
        file_content = await operator.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its first element `{init_line}` should be "
                    f"within the range of lines of the file: {[1, n_lines_file]}"
                )
            if final_line > n_lines_file: # Should be fine even if final_line == -1
                if final_line != -1 : # only raise if not -1
                    raise ToolError(
                        f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be "
                        f"smaller than or equal to the number of lines in the file: `{n_lines_file}`"
                    )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be "
                    f"larger or equal than its first `{init_line}`"
                )
            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])
        
        output_str = self._make_output(
            file_content, 
            str(path), 
            init_line=init_line,
            full_content_for_size_info=None if view_range else await operator.read_file(path) # Pass full content if not ranged
        )
        return CLIResult(output=output_str)

    async def str_replace(
        self,
        path: PathLike,
        old_str: str,
        new_str: Optional[str] = None,
        operator: FileOperator = None,
    ) -> CLIResult:
        """Replace a unique string in a file with a new string."""
        file_content_raw = await operator.read_file(path)
        file_content = file_content_raw.expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}."
            )
        elif occurrences > 1:
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` "
                f"in lines {lines}. Please ensure it is unique"
            )
        new_file_content = file_content.replace(old_str, new_str)
        new_file_content = StrReplaceEditor._sanitize_text_for_file(new_file_content)
        await operator.write_file(path, new_file_content)
        self._file_history[path].append(file_content)
        replacement_line = file_content.split(old_str)[0].count("\n")
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
        snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        success_msg += "Review the changes and make sure they are as expected. Edit the file again if necessary."
        return CLIResult(output=success_msg)

    async def insert(
        self,
        path: PathLike,
        insert_line: int,
        new_str: str,
        operator: FileOperator = None,
    ) -> CLIResult:
        """Insert text at a specific line in a file."""
        file_text_raw = await operator.read_file(path)
        file_text = file_text_raw.expandtabs()
        new_str = new_str.expandtabs()
        file_text_lines = file_text.split("\n")
        n_lines_file = len(file_text_lines)
        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f"Invalid `insert_line` parameter: {insert_line}. It should be within "
                f"the range of lines of the file: {[0, n_lines_file]}"
            )
        new_str_lines = new_str.split("\n")
        new_file_text_lines = (
            file_text_lines[:insert_line]
            + new_str_lines
            + file_text_lines[insert_line:]
        )
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + new_str_lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]
        )
        new_file_text = "\n".join(new_file_text_lines)
        snippet = "\n".join(snippet_lines)
        new_file_text = StrReplaceEditor._sanitize_text_for_file(new_file_text)
        await operator.write_file(path, new_file_text)
        self._file_history[path].append(file_text)
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet,
            "a snippet of the edited file",
            max(1, insert_line - SNIPPET_LINES + 1),
        )
        success_msg += "Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."
        return CLIResult(output=success_msg)

    async def undo_edit(
        self, path: PathLike, operator: FileOperator = None
    ) -> CLIResult:
        """Revert the last edit made to a file."""
        if not self._file_history[path]:
            raise ToolError(f"No edit history found for {path}.")
        old_text = self._file_history[path].pop()
        await operator.write_file(path, old_text)
        return CLIResult(
            output=f"Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}"
        )

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
        full_content_for_size_info: Optional[str] = None,
    ) -> str:
        """Format file content for display with line numbers."""
        truncated_content = maybe_truncate(file_content)
        if full_content_for_size_info and truncated_content.endswith(TRUNCATED_MESSAGE):
            actual_total_lines = len(full_content_for_size_info.split('\n'))
            actual_total_chars = len(full_content_for_size_info)
            detailed_truncation_msg = TRUNCATED_MESSAGE + f" Full file: {actual_total_lines} lines, {actual_total_chars} chars."
            truncated_content = truncated_content.replace(TRUNCATED_MESSAGE, detailed_truncation_msg)
        file_content = truncated_content 
        if expand_tabs:
            file_content = file_content.expandtabs()
        file_content = "\n".join(
            [
                f"{i + init_line:6}\t{line}"
                for i, line in enumerate(file_content.split("\n"))
            ]
        )
        return (
            f"Here's the result of running `cat -n` on {file_descriptor}:\n"
            + file_content
            + "\n"
        )
