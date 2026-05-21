"""Codebase navigation tools for fast, low-friction agent inspection."""

from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from app.task_context import get_current_workspace
from app.tool.base import BaseTool, ToolResult


MAX_OUTPUT_CHARS = 24000
DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    "coverage",
}


def _resolve_path(path: Optional[str] = None) -> Path:
    workspace = get_current_workspace()
    if path and workspace and (path == "/workspace" or path.startswith("/workspace/")):
        rel = path.removeprefix("/workspace").lstrip("/")
        return (Path(workspace) / rel).resolve()
    base = Path.cwd()
    if not path:
        return base
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else (base / candidate).resolve()


def _truncate(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return (
        text[:max_chars]
        + "\n\n<response clipped: narrow the path/pattern or increase specificity>"
    )


def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in DEFAULT_IGNORES and not name.startswith(".")
        ]
        for filename in filenames:
            if filename.startswith("."):
                continue
            yield Path(dirpath) / filename


class GlobSearch(BaseTool):
    """Find files by glob pattern."""

    name: str = "glob"
    parallel_safe: bool = True  # read-only, no shared state
    description: str = (
        "Fast file discovery by glob pattern. Use this before reading files when "
        "you need to locate likely implementation, config, test, or artifact files."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern, e.g. '**/*.py', 'frontend/src/**/*.tsx', '*.log'.",
            },
            "path": {
                "type": "string",
                "description": "Optional directory to search. Defaults to the current conversation workspace.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of paths to return. Defaults to 200.",
            },
        },
        "required": ["pattern"],
    }

    async def execute(
        self, pattern: str, path: Optional[str] = None, max_results: int = 200, **kwargs
    ) -> ToolResult:
        root = _resolve_path(path)
        if not root.exists():
            return ToolResult(error=f"Path does not exist: {root}")

        limit = max(1, min(max_results or 200, 1000))
        results: list[str] = []
        for file_path in _walk_files(root):
            rel = file_path.relative_to(root)
            if fnmatch.fnmatch(str(rel), pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                results.append(str(rel))
                if len(results) >= limit:
                    break

        if not results:
            return ToolResult(output=f"No files matched {pattern!r} under {root}")

        suffix = "\n<results clipped>" if len(results) >= limit else ""
        return ToolResult(output="\n".join(results) + suffix)


class GrepSearch(BaseTool):
    """Search file contents with ripgrep when available."""

    name: str = "grep"
    parallel_safe: bool = True  # read-only, no shared state
    description: str = (
        "Fast text search with line numbers. Use this to locate symbols, errors, TODOs, "
        "or relevant code before opening files."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text or regex to search for."},
            "path": {
                "type": "string",
                "description": "Optional file or directory. Defaults to the current conversation workspace.",
            },
            "glob": {
                "type": "string",
                "description": "Optional file glob filter, e.g. '*.py' or 'src/**/*.tsx'.",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether matching is case-sensitive. Defaults to false.",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines around each match. Defaults to 0.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum matching lines to return. Defaults to 200.",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        case_sensitive: bool = False,
        context_lines: int = 0,
        max_results: int = 200,
        **kwargs,
    ) -> ToolResult:
        target = _resolve_path(path)
        if not target.exists():
            return ToolResult(error=f"Path does not exist: {target}")

        limit = max(1, min(max_results or 200, 1000))
        rg = shutil.which("rg")
        if rg:
            cmd = [
                rg,
                "--line-number",
                "--no-heading",
                "--color=never",
                "--max-count",
                str(limit),
            ]
            if not case_sensitive:
                cmd.append("--ignore-case")
            if context_lines:
                cmd.extend(["--context", str(max(0, min(context_lines, 10)))])
            if glob:
                cmd.extend(["--glob", glob])
            cmd.extend([query, str(target)])
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 1:
                return ToolResult(output=f"No matches for {query!r} in {target}")
            if proc.returncode != 0:
                return ToolResult(error=proc.stderr.strip() or "ripgrep failed")
            return ToolResult(output=_truncate(proc.stdout))

        matches: list[str] = []
        needle = query if case_sensitive else query.lower()
        for file_path in _walk_files(target if target.is_dir() else target.parent):
            if target.is_file() and file_path != target:
                continue
            if glob and not fnmatch.fnmatch(str(file_path), glob):
                continue
            try:
                lines = file_path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for index, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    matches.append(f"{file_path}:{index}:{line}")
                    if len(matches) >= limit:
                        return ToolResult(output=_truncate("\n".join(matches)))

        if not matches:
            return ToolResult(output=f"No matches for {query!r} in {target}")
        return ToolResult(output=_truncate("\n".join(matches)))


class ReadFiles(BaseTool):
    """Read one or more files with line numbers."""

    name: str = "read_files"
    parallel_safe: bool = True  # read-only, no shared state
    description: str = (
        "Read one or more files with line numbers. Prefer this for small batches of "
        "related files after glob/grep has found them."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Single file path to read (convenience alias for paths=[path]).",
            },
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths to read. Relative paths resolve from the current conversation workspace.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-based start line.",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional inclusive end line.",
            },
            "max_chars_per_file": {
                "type": "integer",
                "description": "Maximum characters per file. Defaults to 12000.",
            },
        },
        "anyOf": [
            {"required": ["paths"]},
            {"required": ["path"]},
        ],
    }

    async def execute(
        self,
        paths: Optional[list[str]] = None,
        path: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_chars_per_file: int = 12000,
        **kwargs,
    ) -> ToolResult:
        if paths is None and path:
            paths = [path]
        elif path and paths is not None:
            paths = [path, *paths]

        if not paths:
            return ToolResult(
                error="At least one path is required via 'path' or 'paths'"
            )

        limit = max(1000, min(max_chars_per_file or 12000, 50000))
        sections: list[str] = []
        for raw_path in paths[:20]:
            file_path = _resolve_path(raw_path)
            if not file_path.exists():
                sections.append(f"== {raw_path} ==\nERROR: file does not exist")
                continue
            if not file_path.is_file():
                sections.append(f"== {raw_path} ==\nERROR: not a file")
                continue

            try:
                lines = file_path.read_text(errors="replace").splitlines()
            except OSError as exc:
                sections.append(f"== {raw_path} ==\nERROR: {exc}")
                continue

            start = max(1, start_line or 1)
            end = min(len(lines), end_line or len(lines))
            numbered = [
                f"{line_no:>5}\t{lines[line_no - 1]}"
                for line_no in range(start, end + 1)
            ]
            content = "\n".join(numbered)
            sections.append(f"== {file_path} ==\n{_truncate(content, limit)}")

        return ToolResult(output=_truncate("\n\n".join(sections)))


class CodebaseOverview(BaseTool):
    """Summarize workspace structure and likely verification commands."""

    name: str = "codebase_overview"
    parallel_safe: bool = True  # read-only, no shared state
    description: str = (
        "Inspect the current workspace quickly: important files, detected languages, "
        "package managers, and likely build/test commands."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional directory. Defaults to the current conversation workspace.",
            },
            "max_files": {
                "type": "integer",
                "description": "Maximum files to include in the tree. Defaults to 120.",
            },
        },
    }

    async def execute(
        self, path: Optional[str] = None, max_files: int = 120, **kwargs
    ) -> ToolResult:
        root = _resolve_path(path)
        if not root.exists():
            return ToolResult(error=f"Path does not exist: {root}")

        limit = max(20, min(max_files or 120, 500))
        files = sorted(_walk_files(root), key=lambda p: str(p.relative_to(root)))[
            :limit
        ]
        rel_files = [str(file_path.relative_to(root)) for file_path in files]
        names = {Path(p).name for p in rel_files}
        suffixes = {Path(p).suffix for p in rel_files}

        commands: list[str] = []
        if "package.json" in names:
            commands.extend(["npm run build", "npm test"])
        if (
            "pyproject.toml" in names
            or "pytest.ini" in names
            or "requirements.txt" in names
        ):
            commands.append("pytest -q")
        if "Cargo.toml" in names:
            commands.extend(["cargo test", "cargo clippy"])
        if "go.mod" in names:
            commands.append("go test ./...")
        if "pom.xml" in names:
            commands.append("mvn test")
        if "build.gradle" in names or "build.gradle.kts" in names:
            commands.append("./gradlew test")

        language_hints = []
        if ".py" in suffixes:
            language_hints.append("Python")
        if suffixes & {".ts", ".tsx", ".js", ".jsx"}:
            language_hints.append("JavaScript/TypeScript")
        if ".rs" in suffixes:
            language_hints.append("Rust")
        if ".go" in suffixes:
            language_hints.append("Go")
        if ".java" in suffixes:
            language_hints.append("Java")
        if ".tex" in suffixes:
            language_hints.append("LaTeX")

        output = [
            f"Workspace: {root}",
            f"Detected languages: {', '.join(language_hints) or 'unknown'}",
            "Likely verification commands:",
            *(f"- {cmd}" for cmd in commands),
            "Files:",
            *(f"- {file}" for file in rel_files),
        ]
        if len(files) >= limit:
            output.append("<file list clipped>")
        return ToolResult(output="\n".join(output))
