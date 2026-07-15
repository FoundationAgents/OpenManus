"""Unified-diff patch editor tool for reliable file updates."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import config
from app.exceptions import ToolError
from app.task_context import (
    emit_current_task,
    get_current_tool_call,
    get_current_workspace,
)
from app.tool.base import BaseTool


class ApplyPatchEditor(BaseTool):
    name: str = "apply_patch_editor"
    description: str = (
        "Apply a unified diff patch atomically across one or more files. "
        "Preferred for robust code edits over string replacement."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "patch": {
                "type": "string",
                "description": (
                    "Unified diff patch text. Example headers: "
                    "--- a/file.py and +++ b/file.py, followed by @@ hunks."
                ),
            },
            "check_only": {
                "type": "boolean",
                "description": "If true, validate patch applicability without applying it.",
            },
        },
        "required": ["patch"],
    }

    def _workspace_root(self) -> Path:
        active = get_current_workspace()
        if active:
            return Path(active)
        return Path(str(config.workspace_root))

    def _run_git_apply(self, patch_path: Path, *, check_only: bool, cwd: Path) -> str:
        base_cmd = [
            "git",
            "apply",
            "--recount",
            "--whitespace=nowarn",
            "--unsafe-paths",
            "--no-index",
        ]
        check_cmd = [*base_cmd, "--check", str(patch_path)]
        proc_check = subprocess.run(
            check_cmd,
            cwd=str(cwd),
            text=True,
            capture_output=True,
        )
        if proc_check.returncode != 0:
            detail = (proc_check.stderr or proc_check.stdout or "").strip()
            raise ToolError(f"Patch check failed: {detail}")
        if check_only:
            return "Patch check passed (no changes applied)."

        apply_cmd = [*base_cmd, str(patch_path)]
        proc_apply = subprocess.run(
            apply_cmd,
            cwd=str(cwd),
            text=True,
            capture_output=True,
        )
        if proc_apply.returncode != 0:
            detail = (proc_apply.stderr or proc_apply.stdout or "").strip()
            raise ToolError(f"Patch apply failed: {detail}")
        return "Patch applied successfully."

    @staticmethod
    def _parse_patch_files(patch_text: str) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        for raw in patch_text.splitlines():
            line = raw.rstrip("\n")
            if line.startswith("diff --git "):
                if current:
                    files.append(current)
                current = {"path": "", "added": 0, "deleted": 0, "lines": []}
                continue

            if line.startswith("+++ "):
                if current is None:
                    current = {"path": "", "added": 0, "deleted": 0, "lines": []}
                path = line[4:].strip()
                if path.startswith("b/"):
                    path = path[2:]
                current["path"] = path
                current["lines"].append(line)
                continue

            if current is None:
                continue

            if line.startswith("@@") or line.startswith("--- "):
                current["lines"].append(line)
                continue

            if line.startswith("+") and not line.startswith("+++"):
                current["added"] += 1
                current["lines"].append(line)
                continue

            if line.startswith("-") and not line.startswith("---"):
                current["deleted"] += 1
                current["lines"].append(line)
                continue

        if current:
            files.append(current)

        normalized: list[dict[str, Any]] = []
        for f in files:
            lines = f.get("lines", [])
            clipped = lines[:120]
            if len(lines) > 120:
                clipped.append("... (diff truncated)")
            normalized.append(
                {
                    "path": f.get("path") or "(unknown)",
                    "added": int(f.get("added", 0)),
                    "deleted": int(f.get("deleted", 0)),
                    "diff_preview": {"command": "apply_patch", "lines": clipped},
                }
            )
        return normalized

    async def execute(
        self, *, patch: str, check_only: bool = False, **kwargs: Any
    ) -> str:
        patch_text = str(patch or "").strip()
        if not patch_text:
            raise ToolError("Parameter `patch` is required and must be non-empty.")

        workspace_root = self._workspace_root()
        workspace_root.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".patch", delete=False
        ) as tmp:
            tmp.write(patch_text)
            tmp_path = Path(tmp.name)

        try:
            result = self._run_git_apply(
                tmp_path, check_only=bool(check_only), cwd=workspace_root
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        if not check_only:
            tool_call = get_current_tool_call() or {}
            tool_call_id = str(tool_call.get("id") or "")
            for item in self._parse_patch_files(patch_text):
                emit_current_task(
                    "workspace_file_updated",
                    {
                        "tool_call_id": tool_call_id,
                        "tool": self.name,
                        "path": item["path"],
                        "added_lines": item["added"],
                        "deleted_lines": item["deleted"],
                        "diff_preview": item["diff_preview"],
                    },
                )

        return result
