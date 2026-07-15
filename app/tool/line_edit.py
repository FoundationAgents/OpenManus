"""
LineEdit — unambiguous line-number-based file editor.

Why this exists:
    str_replace_editor fails when the target string has any whitespace difference,
    duplicate occurrence, or the model hallucinates context lines.
    apply_patch_editor requires clean hunk headers and can reject drifted patches.

    This tool avoids string matching entirely. The model reads the file with
    line numbers, identifies the exact range it wants to change, and passes
    start_line / end_line directly. The replacement is applied by list slicing —
    it CANNOT mis-match.

Workflow the model should follow:
    1. Call str_replace_editor view OR bash "cat -n <file>" to see line numbers.
    2. Identify start_line and end_line of the region to replace (inclusive, 1-indexed).
    3. Call line_edit with path, start_line, end_line, new_content.
    4. Verify the result snippet shown in the response.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import config
from app.exceptions import ToolError
from app.task_context import emit_current_task, get_current_tool_call
from app.tool.base import BaseTool
from app.tool.file_operators import LocalFileOperator, SandboxFileOperator


SNIPPET_CONTEXT = 4  # lines of context shown above/below the edit in the response


class LineEdit(BaseTool):
    """Replace a range of lines in a file by line number — no string matching."""

    name: str = "line_edit"
    description: str = (
        "Edit a file by replacing a specific range of lines (start_line to end_line, "
        "inclusive, 1-indexed) with new_content. "
        "ALWAYS read the file with line numbers first (use str_replace_editor view or "
        "'cat -n'), identify the exact line range, then call this tool. "
        "This never fails due to string matching issues. "
        "Use this as the primary method for all code edits — "
        "only fall back to apply_patch_editor for multi-file atomic changes."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file to edit.",
            },
            "start_line": {
                "type": "integer",
                "description": (
                    "First line of the region to replace (1-indexed, inclusive). "
                    "To insert BEFORE line N use start_line=N, end_line=N-1 (empty range). "
                    "To insert at end of file use start_line=<last_line+1>, end_line=<last_line>."
                ),
            },
            "end_line": {
                "type": "integer",
                "description": (
                    "Last line of the region to replace (1-indexed, inclusive). "
                    "Use -1 to mean 'end of file'. "
                    "Set end_line < start_line to insert without deleting any lines."
                ),
            },
            "new_content": {
                "type": "string",
                "description": (
                    "Replacement text for the selected line range. "
                    "Must include correct indentation. "
                    "Pass an empty string to delete the selected lines."
                ),
            },
        },
        "required": ["path", "start_line", "end_line", "new_content"],
    }

    _local_operator: LocalFileOperator = LocalFileOperator()
    _sandbox_operator: SandboxFileOperator = SandboxFileOperator()

    def _operator(self):
        return (
            self._sandbox_operator
            if config.sandbox.use_sandbox
            else self._local_operator
        )

    async def execute(
        self,
        *,
        path: str,
        start_line: int,
        end_line: int,
        new_content: str,
        **kwargs: Any,
    ) -> str:
        p = Path(path)
        if not p.is_absolute():
            raise ToolError(f"path must be absolute, got: {path!r}")

        op = self._operator()

        if not await op.exists(path):
            raise ToolError(f"File not found: {path}")
        if await op.is_directory(path):
            raise ToolError(f"path is a directory, not a file: {path}")

        original = await op.read_file(path)
        lines = original.splitlines(keepends=True)
        total = len(lines)

        # Normalise end_line=-1 → last line
        if end_line == -1:
            end_line = total

        # Convert to 0-based slice indices
        # start_line=1, end_line=3 → lines[0:3]
        slice_start = max(0, start_line - 1)
        slice_end = end_line  # end_line=3 means up to and including line 3 → index 3

        if slice_start > total:
            raise ToolError(
                f"start_line {start_line} is beyond end of file ({total} lines)."
            )
        if slice_end < slice_start:
            # Pure insert: no lines deleted
            slice_end = slice_start

        # Build replacement lines (ensure trailing newline on each line)
        if new_content:
            replacement_lines = []
            for ln in new_content.splitlines():
                replacement_lines.append(ln + "\n")
            # Remove the trailing newline from the very last replacement line
            # only if the original file didn't end with a blank line there —
            # just keep it simple and always include it.
        else:
            replacement_lines = []

        new_lines = lines[:slice_start] + replacement_lines + lines[slice_end:]
        new_text = "".join(new_lines)

        await op.write_file(path, new_text)

        # Build a context snippet for the response
        edit_start_0 = slice_start
        edit_end_0 = slice_start + len(replacement_lines)
        snip_start = max(0, edit_start_0 - SNIPPET_CONTEXT)
        snip_end = min(len(new_lines), edit_end_0 + SNIPPET_CONTEXT)

        snippet_lines = new_lines[snip_start:snip_end]
        snippet = "".join(
            f"{snip_start + i + 1:6}\t{ln}" for i, ln in enumerate(snippet_lines)
        )

        lines_deleted = max(0, slice_end - slice_start)
        lines_added = len(replacement_lines)

        summary = (
            f"Edited {path}: replaced lines {start_line}–{end_line} "
            f"(-{lines_deleted} +{lines_added} lines).\n"
            f"File now has {len(new_lines)} lines.\n\n"
            f"Context around edit (lines {snip_start + 1}–{snip_end}):\n"
            f"{snippet}"
        )

        # Emit workspace_file_updated event for the UI diff panel
        tool_call = get_current_tool_call() or {}
        emit_current_task(
            "workspace_file_updated",
            {
                "tool_call_id": str(tool_call.get("id") or ""),
                "tool": self.name,
                "path": path,
                "added_lines": lines_added,
                "deleted_lines": lines_deleted,
                "diff_preview": {
                    "command": "line_edit",
                    "start_line": start_line,
                    "end_line": end_line,
                    "lines": snippet_lines[:120],
                },
            },
        )

        return summary
