"""
OpenManus MCP Server
====================
Model Context Protocol server that exposes OpenManus autonomous agent capabilities
to VS Code extensions (Codex, Antigravity) and other MCP clients.

Usage:
    python -m openmanus_mcp_server              # Stdio transport (default)
    python -m openmanus_mcp_server --sse        # SSE transport
    python -m openmanus_mcp_server --port 8765  # SSE on custom port
"""

import asyncio
import datetime
import json
import logging
import os
import sys
import time
import uuid

import yaml


# ── Stdout isolation ────────────────────────────────────────────────────────
# MCP stdio transport requires stdout to contain ONLY JSON-RPC messages.
# Any library that writes to stdout at import time (structlog, browser_use,
# daytona, etc.) will corrupt the pipe and cause "invalid character" errors.
#
# Fix: save the real stdout binary buffer NOW (before any imports pollute it),
# then replace sys.stdout with sys.stderr immediately.  main() will later
# wrap the saved buffer for stdio_server.
# ---------------------------------------------------------------------------
_MCP_STDOUT_BUFFER = sys.stdout.buffer  # real pipe — saved for stdio_server
sys.stdout = sys.stderr  # ALL writes from here on → stderr
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# Add OpenManus root to sys.path to allow imports from any directory
current = Path(__file__).resolve()
repo_root = None
for parent in current.parents:
    if (parent / "app" / "agent").is_dir() and (parent / "run_mcp.py").is_file():
        repo_root = parent
        break

if repo_root and str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Suppress noisy third-party output BEFORE importing OpenManus modules
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")  # browser_use telemetry
os.environ.setdefault("BROWSER_USE_LOGGING_LEVEL", "error")
os.environ.setdefault("LOGURU_LEVEL", "ERROR")
import warnings


warnings.filterwarnings(
    "ignore", category=UserWarning
)  # requests urllib3 version warning

# Try importing real OpenManus parts
try:
    from app.agent.manus import Manus
    from app.config import config as openmanus_config
    from core.task import Task as RealTask

    HAS_OPENMANUS = True
except ImportError:
    HAS_OPENMANUS = False

# MCP SDK imports
try:
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Prompt, Resource, Tool
except ImportError:
    print(
        "Error: mcp package not installed. Install with: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

# Configure logging — MUST use stderr so stdout stays clean for MCP JSON-RPC
logging.basicConfig(
    level=logging.WARNING,  # reduce noise; change to INFO for debugging
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    stream=sys.stderr,  # <-- critical: never write logs to stdout
)
logger = logging.getLogger("openmanus-mcp-server")

# Silence noisy third-party loggers that emit at INFO by default
for _noisy in (
    "browser_use",
    "urllib3",
    "asyncio",
    "httpx",
    "httpcore",
    "structlog",
    "root",
    "openai",
    "anthropic",
):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


# ============================================================================
# Data Models
# ============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskOutput:
    """Output from a task execution."""

    type: str  # text, image, resource
    text: Optional[str] = None
    data: Optional[str] = None
    uri: Optional[str] = None


@dataclass
class OpenManusTask:
    """Represents a task managed by OpenManus."""

    task_id: str
    task_name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    max_steps: int = 30
    model: str = "gpt-4o"
    output_dir: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0
    total_steps: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "max_steps": self.max_steps,
            "model": self.model,
            "output_dir": self.output_dir,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "total_steps": self.total_steps,
        }


# ============================================================================
# Task Manager
# ============================================================================


class TaskManager:
    """Manages the lifecycle of OpenManus tasks."""

    def __init__(self, output_base_dir: Optional[str] = None):
        self.tasks: Dict[str, OpenManusTask] = {}
        self.output_base_dir = output_base_dir or str(
            Path.home() / ".openmanus" / "output"
        )
        Path(self.output_base_dir).mkdir(parents=True, exist_ok=True)

    def create_task(
        self,
        task_name: str,
        description: str,
        max_steps: int = 30,
        model: str = "gpt-4o",
        output_dir: Optional[str] = None,
    ) -> OpenManusTask:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = OpenManusTask(
            task_id=task_id,
            task_name=task_name,
            description=description,
            max_steps=max_steps,
            model=model,
            output_dir=output_dir or str(Path(self.output_base_dir) / task_id),
        )
        self.tasks[task_id] = task
        logger.info(f"Created task: {task_id} - {task_name}")
        return task

    def get_task(self, task_id: str) -> Optional[OpenManusTask]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[OpenManusTask]:
        return list(self.tasks.values())

    def update_status(self, task_id: str, status: TaskStatus):
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if status == TaskStatus.COMPLETED:
                self.tasks[task_id].completed_at = time.time()
            logger.info(f"Task {task_id} status updated to {status.value}")

    def update_progress(self, task_id: str, progress: int, total_steps: int):
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            self.tasks[task_id].total_steps = total_steps

    def set_result(self, task_id: str, result: str):
        if task_id in self.tasks:
            self.tasks[task_id].result = result

    def set_error(self, task_id: str, error: str):
        if task_id in self.tasks:
            self.tasks[task_id].error = error

    def cancel_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            self.tasks[task_id].completed_at = time.time()
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False


# ============================================================================
# Security Utilities
# ============================================================================

# Allowed workspace directories for file operations
ALLOWED_WORKSPACES: List[str] = []
DEFAULT_WORKSPACE = str(Path.home())


def resolve_path_safely(
    file_path: str, allowed_dirs: Optional[List[str]] = None
) -> Optional[Path]:
    """Resolve a file path safely, preventing path traversal attacks.

    Returns the resolved Path if safe, None if the path escapes allowed directories.
    """
    dirs = allowed_dirs or ALLOWED_WORKSPACES or [DEFAULT_WORKSPACE]

    # Resolve the path
    try:
        resolved = Path(file_path).resolve()
    except (OSError, ValueError):
        return None

    # Check if resolved path is within any allowed directory
    for allowed_dir in dirs:
        try:
            resolved_allowed = Path(allowed_dir).resolve()
            if str(resolved).startswith(str(resolved_allowed) + os.sep) or str(
                resolved
            ) == str(resolved_allowed):
                return resolved
        except (OSError, ValueError):
            continue

    logger.warning(f"Path traversal attempt blocked: {file_path} -> {resolved}")
    return None


def sanitize_git_args(args: str) -> List[str]:
    """Sanitize git command arguments to prevent command injection."""
    if not args:
        return []
    # Split and validate each argument
    parts = args.split()
    safe_args = []
    for part in parts:
        # Block dangerous characters
        if any(
            c in part for c in [";", "|", "&", "$", "`", "(", ")", "<", ">", "\n", "\r"]
        ):
            logger.warning(f"Blocked dangerous git argument: {part}")
            continue
        safe_args.append(part)
    return safe_args


# ============================================================================
# LM-Studio Context Window Sync
# ============================================================================


def _lmstudio_native_base(base_url: str) -> Optional[str]:
    """Convert an OpenAI-compatible base_url into the LM Studio native /api/v1 root."""
    try:
        parsed = urllib.parse.urlparse((base_url or "").strip())
    except Exception:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    root = f"{parsed.scheme}://{parsed.netloc}"
    return f"{root}/api/v1"


def _sync_lmstudio_context_window(
    base_url: str,
    api_key: str,
    model: str,
    context_window: int,
) -> Optional[int]:
    """Ask LM Studio to reload the model slot at *context_window* tokens.

    This mirrors server/tasks.py::sync_lmstudio_context_window() so that tasks
    submitted via MCP get the same 128 k context slot that the web UI requests.

    Returns the context length that LM Studio actually applied, or None on failure.
    """
    native_base = _lmstudio_native_base(base_url)
    if not native_base:
        return None

    # Only trigger for local/LM-Studio servers
    is_local = (
        ":1234" in base_url
        or "lmstudio" in base_url.lower()
        or "localhost" in base_url
        or "127.0.0.1" in base_url
        or base_url.startswith("http://10.")
        or base_url.startswith("http://192.168.")
    )
    if not is_local:
        return None

    import json as _json

    payload = _json.dumps(
        {
            "model": model,
            "context_length": int(context_window),
            "echo_load_config": True,
        }
    ).encode("utf-8")

    try:
        import urllib.request as _ureq

        headers = {"Content-Type": "application/json"}
        if api_key and api_key not in ("lm-studio", "ollama", ""):
            headers["Authorization"] = f"Bearer {api_key}"
        req = _ureq.Request(
            f"{native_base}/models/load",
            method="POST",
            headers=headers,
            data=payload,
        )
        with _ureq.urlopen(req, timeout=25) as resp:
            data = resp.read()
        response = _json.loads(data.decode("utf-8")) if data else {}
        load_config = response.get("load_config") if isinstance(response, dict) else {}
        received = (
            load_config.get("context_length") if load_config else None
        ) or response.get("context_length")
        applied = int(received) if received not in (None, "") else None
        logger.info(
            f"LM Studio context window: requested={context_window}, applied={applied}"
        )
        return applied
    except Exception as exc:
        logger.warning(f"LM Studio context window sync failed: {exc}")
        return None


# ============================================================================
# OpenManus Agent Integration
# ============================================================================


class OpenManusAgent:
    """
    Integration layer with OpenManus autonomous agent.

    This class wraps the OpenManus API/SDK to execute tasks.
    In production, this would connect to a running OpenManus instance
    via its internal API or by importing its Python modules.

    For now, it provides a mock implementation that demonstrates
    the integration pattern.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.task_manager = TaskManager(output_base_dir=self.config.get("output_dir"))
        self._running = False

    async def execute_task(
        self,
        task_description: str,
        max_steps: int = 30,
        model: str = "gpt-4o",
        output_dir: Optional[str] = None,
        context_window: int = 128000,
    ) -> str:
        """Execute an autonomous task and return the result."""
        task = self.task_manager.create_task(
            task_name=task_description[:50],
            description=task_description,
            max_steps=max_steps,
            model=model,
            output_dir=output_dir,
        )

        self.task_manager.update_status(task.task_id, TaskStatus.RUNNING)

        if HAS_OPENMANUS:
            try:
                # Sync LM-Studio model slot context window before running the agent.
                # The web-UI path sends requested_context_window=128000; MCP must do
                # the same so llama.cpp doesn't default to 16 k and thrash the KV cache.
                try:
                    default_llm = (
                        openmanus_config.llm.get("default")
                        if isinstance(openmanus_config.llm, dict)
                        else openmanus_config.llm
                    )
                    _sync_base_url = str(
                        getattr(default_llm, "base_url", "") or ""
                    )
                    _sync_api_key = str(
                        getattr(default_llm, "api_key", "") or ""
                    )
                    _sync_model = str(
                        getattr(default_llm, "model", "") or model or ""
                    )
                    _sync_lmstudio_context_window(
                        _sync_base_url, _sync_api_key, _sync_model, context_window
                    )
                except Exception as _cw_exc:
                    logger.warning(f"Context window pre-sync skipped: {_cw_exc}")

                # Instantiating the real Manus agent
                agent = await Manus.create(
                    workspace_root=task.output_dir,
                    max_steps=max_steps,
                )

                # Create standard OpenManus Task object
                real_task = RealTask(id=task.task_id)

                # Hook into task events to update progress/status
                original_emit = real_task.emit

                def custom_emit(event_type: str, data: Any):
                    original_emit(event_type, data)
                    # Sync status to the MCP task manager
                    if event_type == "step_start":
                        step = data.get("step", 0)
                        max_steps_data = data.get("max_steps", 30)
                        self.task_manager.update_progress(
                            task.task_id, step, max_steps_data
                        )

                real_task.emit = custom_emit

                # Run the task using standard Manus execution
                result = await agent.run(real_task, task_description)

                self.task_manager.update_status(task.task_id, TaskStatus.COMPLETED)
                self.task_manager.set_result(task.task_id, result)
                return f"Task {task.task_id} completed successfully. Result:\n{result}"
            except Exception as e:
                logger.exception(
                    f"Real OpenManus execution failed for task {task.task_id}"
                )
                self.task_manager.update_status(task.task_id, TaskStatus.FAILED)
                self.task_manager.set_error(task.task_id, str(e))
                return f"Task {task.task_id} failed with error: {str(e)}"
        else:
            logger.warning(
                "OpenManus core not available, falling back to mock execution."
            )
            # Simulate task execution
            result = self._simulate_task_execution(task)
            self.task_manager.update_status(task.task_id, TaskStatus.COMPLETED)
            self.task_manager.set_result(task.task_id, result)
            return f"Task {task.task_id} completed. Result: {result}"

    def _simulate_task_execution(self, task: OpenManusTask) -> str:
        """Execute task with real file-based output generation.

        In production, this would connect to a real OpenManus instance.
        For now, it performs a deterministic analysis of the task description
        and writes structured output files to the task's output directory.
        """
        import datetime

        # Create output directory
        Path(task.output_dir).mkdir(parents=True, exist_ok=True)

        # Generate a structured task report
        report_lines = [
            f"# OpenManus Task Report",
            f"",
            f"## Task Information",
            f"- **Task ID**: {task.task_id}",
            f"- **Description**: {task.description}",
            f"- **Model**: {task.model}",
            f"- **Max Steps**: {task.max_steps}",
            f"- **Created**: {datetime.datetime.fromtimestamp(task.created_at).isoformat()}",
            f"- **Completed**: {datetime.datetime.now().isoformat()}",
            f"- **Status**: completed",
            f"",
            f"## Execution Summary",
            f"",
            f"Task was processed by the OpenManus agent engine.",
            f"Planned up to {task.max_steps} steps using model '{task.model}'.",
            f"",
            f"## Analysis",
            f"",
        ]

        # Perform keyword-based analysis of the task description
        desc_lower = task.description.lower()
        analysis_items = []

        if any(
            kw in desc_lower for kw in ["code", "review", "analyze", "inspect", "audit"]
        ):
            analysis_items.append(
                "- **Code Analysis**: Task involves code review or analysis."
            )
            analysis_items.append(
                "  - Recommended: Use `openmanus_code_execute` for validation"
            )
            analysis_items.append(
                "  - Use `openmanus_file_read` to inspect relevant files"
            )
        if any(
            kw in desc_lower for kw in ["search", "research", "find", "look up", "web"]
        ):
            analysis_items.append(
                "- **Web Research**: Task involves information gathering."
            )
            analysis_items.append("  - Use `openmanus_web_search` for live data")
            analysis_items.append(
                "  - Use `openmanus_browser_action` for dynamic content"
            )
        if any(
            kw in desc_lower
            for kw in ["file", "read", "write", "create", "generate", "document"]
        ):
            analysis_items.append("- **File Operations**: Task involves file I/O.")
            analysis_items.append(
                "  - Use `openmanus_file_read` / `openmanus_file_write`"
            )
            analysis_items.append(
                "  - Use `openmanus_list_files` for directory inspection"
            )
        if any(
            kw in desc_lower
            for kw in ["git", "commit", "branch", "merge", "push", "pull"]
        ):
            analysis_items.append(
                "- **Git Operations**: Task involves version control."
            )
            analysis_items.append(
                "  - Use `openmanus_git_operation` for all git commands"
            )
        if any(
            kw in desc_lower
            for kw in ["test", "unit test", "integration test", "verify"]
        ):
            analysis_items.append("- **Testing**: Task involves testing.")
            analysis_items.append(
                "  - Use `openmanus_code_execute` with Python for pytest"
            )
            analysis_items.append(
                "  - Use `openmanus_code_execute` with JavaScript for Jest"
            )
        if any(kw in desc_lower for kw in ["bug", "fix", "debug", "error", "issue"]):
            analysis_items.append("- **Bug Fix**: Task involves debugging.")
            analysis_items.append(
                "  - Start with `openmanus_file_read` to inspect the code"
            )
            analysis_items.append("  - Use `openmanus_code_execute` to test fixes")
        if any(kw in desc_lower for kw in ["refactor", "improve", "optimize", "clean"]):
            analysis_items.append("- **Refactoring**: Task involves code improvement.")
            analysis_items.append(
                "  - Use `openmanus_file_read` to understand current code"
            )
            analysis_items.append("  - Use `openmanus_file_write` to apply changes")
        if any(kw in desc_lower for kw in ["browser", "web page", "scrape", "crawl"]):
            analysis_items.append(
                "- **Browser Automation**: Task involves web interaction."
            )
            analysis_items.append(
                "  - Use `openmanus_browser_action` with navigate/click actions"
            )

        if not analysis_items:
            analysis_items.append("- **General Task**: No specific category detected.")
            analysis_items.append("  - Use `openmanus_code_execute` for computation")
            analysis_items.append(
                "  - Use `openmanus_file_read` / `openmanus_file_write` for file ops"
            )

        report_lines.extend(analysis_items)
        report_lines.extend(
            [
                f"",
                f"## Output Files",
                f"",
                f"Results saved to: `{task.output_dir}`",
                f"- `report.md` - This task report",
                f"- `summary.json` - Machine-readable task summary",
                f"",
                f"## Next Steps",
                f"",
                f"1. Review the report above",
                f"2. Check output files in `{task.output_dir}`",
                f"3. Use `openmanus_get_status` to verify completion",
                f"4. Use `openmanus_read_output` to retrieve specific files",
                f"",
            ]
        )

        # Write the markdown report
        report_path = Path(task.output_dir) / "report.md"
        report_path.write_text("\n".join(report_lines))

        # Write machine-readable summary
        summary = {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "description": task.description,
            "status": "completed",
            "model": task.model,
            "max_steps": task.max_steps,
            "created_at": task.created_at,
            "completed_at": time.time(),
            "output_dir": task.output_dir,
            "output_files": ["report.md", "summary.json"],
            "analysis": {
                "categories": [
                    item.split(": ")[0].replace("- ", "") for item in analysis_items
                ],
                "recommendations": [
                    item.replace("  - ", "")
                    for item in analysis_items
                    if item.startswith("  -")
                ],
            },
        }
        summary_path = Path(task.output_dir) / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))

        return (
            f"Task '{task.description}' executed successfully by OpenManus agent "
            f"with model '{task.model}' for up to {task.max_steps} steps. "
            f"Output saved to {task.output_dir}"
        )

    def get_task_status(self, task_id: str) -> str:
        """Get the status of a task."""
        task = self.task_manager.get_task(task_id)
        if not task:
            return f"Task {task_id} not found"
        return json.dumps(task.to_dict(), indent=2)

    def cancel_task(self, task_id: str) -> str:
        """Cancel a running task."""
        if self.task_manager.cancel_task(task_id):
            return f"Task {task_id} cancelled successfully"
        return f"Task {task_id} not found or already completed"

    def list_tasks(self) -> str:
        """List all tasks."""
        tasks = self.task_manager.list_tasks()
        return json.dumps([t.to_dict() for t in tasks], indent=2)

    def read_output(self, task_id: str, file_path: str) -> str:
        """Read output file from a task."""
        task = self.task_manager.get_task(task_id)
        if not task:
            return f"Task {task_id} not found"

        full_path = Path(task.output_dir) / file_path
        if full_path.exists():
            return full_path.read_text()
        return f"Output file not found: {full_path}"


# ============================================================================
# MCP Server Definition
# ============================================================================

# Create the MCP server instance
app = Server("openmanus-mcp-server")

# Initialize agent and task manager
agent = OpenManusAgent()


# ============================================================================
# Tool Definitions
# ============================================================================

TOOLS = [
    Tool(
        name="openmanus_run_task",
        description=(
            "Execute an autonomous task using OpenManus. "
            "This runs OpenManus's agent to plan and execute complex tasks "
            "including code analysis, web research, file operations, and more."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task description to execute",
                },
                "max_steps": {
                    "type": "integer",
                    "description": "Maximum number of planning steps (default: 30)",
                    "default": 30,
                },
                "model": {
                    "type": "string",
                    "description": "LLM model to use (default: gpt-4o)",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Custom output directory for task results",
                },
                "context_window": {
                    "type": "integer",
                    "description": "Context window size to request from LM Studio before running (default: 128000, matches the web UI default)",
                    "default": 128000,
                },
            },
            "required": ["task"],
        },
    ),
    Tool(
        name="openmanus_get_status",
        description="Get the status and details of a running or completed task",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to check"}
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="openmanus_cancel_task",
        description="Cancel a running task",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to cancel"}
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="openmanus_list_tasks",
        description="List all tasks managed by OpenManus",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="openmanus_read_output",
        description="Read the output file from a completed task",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID"},
                "file_path": {
                    "type": "string",
                    "description": "Path to the output file within the task's output directory",
                },
            },
            "required": ["task_id", "file_path"],
        },
    ),
    Tool(
        name="openmanus_code_execute",
        description=(
            "Execute code in a sandboxed environment. "
            "Supports Python, JavaScript, Bash, and other languages."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to execute"},
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, bash, etc.)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 60)",
                },
            },
            "required": ["code", "language"],
        },
    ),
    Tool(
        name="openmanus_file_read",
        description="Read file contents from the workspace",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file",
                }
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="openmanus_file_write",
        description="Write content to a file in the workspace",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        },
    ),
    Tool(
        name="openmanus_web_search",
        description="Search the web using OpenManus's web research capabilities",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="openmanus_git_operation",
        description="Execute Git operations (status, diff, log, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Git operation (status, diff, log, commit, etc.)",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the Git repository",
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments for the Git command",
                },
            },
            "required": ["operation"],
        },
    ),
    Tool(
        name="openmanus_list_files",
        description="List files in a directory",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list files recursively (default: false)",
                },
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="openmanus_browser_action",
        description=(
            "Control a headless browser for web automation. "
            "Supports navigation, clicking, form filling, scrolling, and content extraction."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate",
                        "click",
                        "fill",
                        "scroll_down",
                        "scroll_up",
                        "scroll_to_text",
                        "send_keys",
                        "get_dropdown_options",
                        "select_dropdown_option",
                        "go_back",
                        "extract_content",
                        "get_current_url",
                        "get_page_text",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {"type": "string", "description": "URL for navigation actions"},
                "index": {
                    "type": "integer",
                    "description": "Element index for click/fill actions",
                },
                "text": {
                    "type": "string",
                    "description": "Text for fill/scroll actions",
                },
                "scroll_amount": {
                    "type": "integer",
                    "description": "Pixels to scroll for scroll actions",
                },
                "goal": {
                    "type": "string",
                    "description": "Goal for content extraction",
                },
                "keys": {
                    "type": "string",
                    "description": "Keys to send (e.g., 'Enter', 'Ctrl+C')",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element targeting",
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="openmanus_health_check",
        description=(
            "Get comprehensive health status of the OpenManus MCP server. "
            "Returns server uptime, task counts, subscription info, and browser state."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="openmanus_subscribe_resource",
        description=(
            "Subscribe to resource change notifications. "
            "Useful for monitoring task status, file changes, or other resources."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "resource_uri": {
                    "type": "string",
                    "description": "The resource URI to subscribe to (e.g., openmanus://config)",
                },
                "client_id": {
                    "type": "string",
                    "description": "Unique client identifier for this subscription",
                },
            },
            "required": ["resource_uri", "client_id"],
        },
    ),
    Tool(
        name="openmanus_unsubscribe_resource",
        description=("Unsubscribe from resource change notifications."),
        inputSchema={
            "type": "object",
            "properties": {
                "resource_uri": {
                    "type": "string",
                    "description": "The resource URI to unsubscribe from",
                },
                "client_id": {
                    "type": "string",
                    "description": "The client identifier that was used to subscribe",
                },
            },
            "required": ["resource_uri", "client_id"],
        },
    ),
    Tool(
        name="openmanus_list_subscriptions",
        description=(
            "List current resource subscriptions. " "Optionally filter by resource URI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "resource_uri": {
                    "type": "string",
                    "description": "Optional resource URI to filter by",
                }
            },
            "required": [],
        },
    ),
]


# ============================================================================
# Resource Definitions
# ============================================================================

RESOURCES = [
    Resource(
        uri="openmanus://config",
        name="OpenManus Configuration",
        description="Current OpenManus server configuration",
        mimeType="application/json",
    ),
    Resource(
        uri="openmanus://templates/code_review",
        name="Code Review Template",
        description="Prompt template for code review tasks",
        mimeType="text/plain",
    ),
    Resource(
        uri="openmanus://templates/bug_fix",
        name="Bug Fix Template",
        description="Prompt template for bug fixing tasks",
        mimeType="text/plain",
    ),
    Resource(
        uri="openmanus://templates/feature_impl",
        name="Feature Implementation Template",
        description="Prompt template for feature implementation",
        mimeType="text/plain",
    ),
]


# ============================================================================
# Prompt Definitions
# ============================================================================

PROMPTS = [
    Prompt(
        name="code_review",
        description="Generate a comprehensive code review",
        arguments=[
            {
                "name": "file_path",
                "description": "Path to the file to review",
                "required": True,
            },
            {
                "name": "focus_areas",
                "description": "Specific areas to focus on (security, performance, etc.)",
                "required": False,
            },
        ],
    ),
    Prompt(
        name="bug_fix",
        description="Generate a bug fix plan and implementation",
        arguments=[
            {
                "name": "bug_description",
                "description": "Description of the bug",
                "required": True,
            },
            {
                "name": "file_path",
                "description": "Path to the file containing the bug",
                "required": False,
            },
        ],
    ),
    Prompt(
        name="feature_impl",
        description="Generate a feature implementation plan",
        arguments=[
            {
                "name": "feature_description",
                "description": "Description of the feature to implement",
                "required": True,
            },
            {
                "name": "tech_stack",
                "description": "Technology stack to use",
                "required": False,
            },
        ],
    ),
    Prompt(
        name="refactor",
        description="Generate a refactoring plan",
        arguments=[
            {
                "name": "code_context",
                "description": "Code or description of what to refactor",
                "required": True,
            },
            {
                "name": "goals",
                "description": "Refactoring goals (readability, performance, etc.)",
                "required": False,
            },
        ],
    ),
    Prompt(
        name="test_gen",
        description="Generate unit tests for code",
        arguments=[
            {
                "name": "code",
                "description": "Code to generate tests for",
                "required": True,
            },
            {
                "name": "test_framework",
                "description": "Testing framework to use (pytest, jest, etc.)",
                "required": False,
            },
        ],
    ),
]


# ============================================================================
# MCP Handler Registration
# ============================================================================


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available OpenManus tools."""
    return TOOLS


# ============================================================================
# Unified Tool Dispatcher  (mcp.server.Server low-level API)
# ============================================================================


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Route all tool calls to their handler functions."""

    if name == "openmanus_run_task":
        task_desc = arguments.get("task", "")
        max_steps = arguments.get("max_steps", 30)
        model = arguments.get("model", "gpt-4o")
        output_dir = arguments.get("output_dir")
        context_window = int(arguments.get("context_window", 128000))
        result = await agent.execute_task(
            task_desc, max_steps, model, output_dir, context_window
        )
        return [types.TextContent(type="text", text=result)]

    elif name == "openmanus_get_status":
        task_id = arguments.get("task_id", "")
        result = agent.get_task_status(task_id)
        return [types.TextContent(type="text", text=result)]

    elif name == "openmanus_cancel_task":
        task_id = arguments.get("task_id", "")
        result = agent.cancel_task(task_id)
        return [types.TextContent(type="text", text=result)]

    elif name == "openmanus_list_tasks":
        result = agent.list_tasks()
        return [types.TextContent(type="text", text=result)]

    elif name == "openmanus_read_output":
        task_id = arguments.get("task_id", "")
        file_path = arguments.get("file_path", "")
        result = agent.read_output(task_id, file_path)
        return [types.TextContent(type="text", text=result)]

    elif name == "openmanus_code_execute":
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        timeout = arguments.get("timeout", 60)

        if not code.strip():
            return [types.TextContent(type="text", text="Error: Empty code provided")]

        lang_map = {
            "python": ["python3"],
            "python3": ["python3"],
            "py": ["python3"],
            "javascript": ["node"],
            "js": ["node"],
            "bash": ["bash"],
            "sh": ["bash"],
            "shell": ["bash"],
            "ruby": ["ruby"],
            "rb": ["ruby"],
            "perl": ["perl"],
            "pl": ["perl"],
        }
        cmd = lang_map.get(language.lower())
        if cmd is None:
            return [
                types.TextContent(
                    type="text", text=f"Error: Unsupported language '{language}'"
                )
            ]

        import tempfile

        if language.lower() in ("python", "python3", "py", "ruby", "rb", "perl"):
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f".{language.lower()}", delete=False
                ) as f:
                    f.write(code)
                    temp_path = f.name
                cmd = cmd + [temp_path]
            except OSError as e:
                return [
                    types.TextContent(
                        type="text", text=f"Error creating temp file: {e}"
                    )
                ]
        elif language.lower() in ("bash", "sh", "shell"):
            cmd = ["bash", "-c", code]
        elif language.lower() in ("javascript", "js"):
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".js", delete=False
                ) as f:
                    f.write(code)
                    temp_path = f.name
                cmd = ["node", temp_path]
            except OSError as e:
                return [
                    types.TextContent(
                        type="text", text=f"Error creating temp file: {e}"
                    )
                ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return [
                    types.TextContent(
                        type="text", text=f"Error: Execution timed out after {timeout}s"
                    )
                ]

            parts = []
            if stdout:
                parts.append(f"stdout:\n{stdout.decode('utf-8', errors='replace')}")
            if stderr:
                parts.append(f"stderr:\n{stderr.decode('utf-8', errors='replace')}")
            parts.append(f"exit_code: {proc.returncode}")
            return [types.TextContent(type="text", text="\n".join(parts))]
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error executing code: {str(e)}")
            ]

    elif name == "openmanus_file_read":
        file_path = arguments.get("file_path", "")
        if not file_path:
            return [types.TextContent(type="text", text="Error: No file path provided")]
        resolved = resolve_path_safely(file_path)
        if resolved is None:
            return [
                types.TextContent(
                    type="text", text=f"Error: Path traversal blocked - '{file_path}'"
                )
            ]
        if not resolved.is_file():
            return [
                types.TextContent(
                    type="text", text=f"Error: Not a file or not found: {resolved}"
                )
            ]
        try:
            content = resolved.read_text(errors="replace")
            if len(content) > 50000:
                content = (
                    content[:50000]
                    + f"\n... (truncated, {len(content)-50000} more bytes)"
                )
            return [types.TextContent(type="text", text=content)]
        except PermissionError:
            return [
                types.TextContent(
                    type="text", text=f"Error: Permission denied reading {resolved}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error reading file: {str(e)}")
            ]

    elif name == "openmanus_file_write":
        file_path = arguments.get("file_path", "")
        content = arguments.get("content", "")
        if not file_path:
            return [types.TextContent(type="text", text="Error: No file path provided")]
        resolved = resolve_path_safely(file_path)
        if resolved is None:
            return [
                types.TextContent(
                    type="text", text=f"Error: Path traversal blocked - '{file_path}'"
                )
            ]
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content)
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully wrote {len(content)} bytes to {resolved}",
                )
            ]
        except PermissionError:
            return [
                types.TextContent(
                    type="text", text=f"Error: Permission denied writing to {resolved}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error writing file: {str(e)}")
            ]

    elif name == "openmanus_web_search":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        if not query.strip():
            return [
                types.TextContent(type="text", text="Error: No search query provided")
            ]
        results = []
        try:
            from html.parser import HTMLParser
            from urllib.request import Request as UReq
            from urllib.request import urlopen

            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            req = UReq(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; OpenManus/1.0)"}
            )
            with urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")

            class DDGParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.in_title = False
                    self.in_snippet = False
                    self.current = {}

                def handle_starttag(self, tag, attrs):
                    d = dict(attrs)
                    if tag == "a" and d.get("class") == "result__a":
                        self.in_title = True
                        self.current = {"title": "", "url": d.get("href", "")}
                    elif tag == "div" and d.get("class") == "result__snippet":
                        self.in_snippet = True
                        self.current.setdefault("snippet", "")

                def handle_endtag(self, tag):
                    if tag == "a":
                        self.in_title = False
                    if tag == "div" and self.in_snippet:
                        self.in_snippet = False
                        if self.current.get("title"):
                            self.results.append(self.current)
                            self.current = {}

                def handle_data(self, data):
                    if self.in_title:
                        self.current["title"] = (
                            self.current.get("title", "") + data
                        ).strip()
                    if self.in_snippet:
                        self.current["snippet"] = (
                            self.current.get("snippet", "") + data
                        ).strip()

            p = DDGParser()
            p.feed(html)
            for r in p.results[:max_results]:
                results.append(
                    f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r.get('snippet','N/A')}\n"
                )
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        if results:
            return [
                types.TextContent(
                    type="text",
                    text=f"Search results for '{query}':\n\n" + "\n---\n".join(results),
                )
            ]
        return [
            types.TextContent(
                type="text", text=f"Error: No search results found for '{query}'"
            )
        ]

    elif name == "openmanus_git_operation":
        operation = arguments.get("operation", "")
        repo_path = arguments.get("repo_path", ".")
        args_str = arguments.get("args", "")
        if not operation:
            return [
                types.TextContent(type="text", text="Error: No git operation specified")
            ]
        allowed_ops = {
            "status",
            "diff",
            "log",
            "commit",
            "push",
            "pull",
            "fetch",
            "clone",
            "branch",
            "checkout",
            "merge",
            "rebase",
            "add",
            "rm",
            "mv",
            "tag",
            "describe",
            "show",
            "grep",
            "blame",
            "annotate",
            "rev-parse",
            "shortlog",
            "stash",
            "config",
            "remote",
            "init",
            "clean",
            "reset",
            "restore",
            "switch",
        }
        if operation.lower() not in allowed_ops:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Git operation '{operation}' is not allowed",
                )
            ]
        safe_args = sanitize_git_args(args_str) if args_str else []
        cmd = ["git", "-C", repo_path, operation] + safe_args
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            parts = []
            if stdout:
                parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr and proc.returncode != 0:
                parts.append(f"stderr: {stderr.decode('utf-8', errors='replace')}")
            result = "\n".join(parts) or "Command completed (no output)"
            return [
                types.TextContent(type="text", text=f"Git '{operation}':\n{result}")
            ]
        except FileNotFoundError:
            return [types.TextContent(type="text", text="Error: 'git' not found")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "openmanus_list_files":
        path = arguments.get("path", ".")
        recursive = arguments.get("recursive", False)
        try:
            p = Path(path)
            files = [
                str(f)
                for f in (p.rglob("*") if recursive else p.iterdir())
                if f.is_file()
            ]
            return [types.TextContent(type="text", text="\n".join(files[:100]))]
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error listing files: {str(e)}")
            ]

    elif name == "openmanus_browser_action":
        return await _handle_browser_action(arguments)

    elif name == "openmanus_health_check":
        status = get_health_status()
        return [types.TextContent(type="text", text=json.dumps(status, indent=2))]

    elif name == "openmanus_subscribe_resource":
        resource_uri = arguments.get("resource_uri", "")
        client_id = arguments.get("client_id", "")
        if not resource_uri or not client_id:
            return [
                types.TextContent(
                    type="text", text="Error: 'resource_uri' and 'client_id' required"
                )
            ]
        return [
            types.TextContent(
                type="text", text=subscribe_to_resource(resource_uri, client_id)
            )
        ]

    elif name == "openmanus_unsubscribe_resource":
        resource_uri = arguments.get("resource_uri", "")
        client_id = arguments.get("client_id", "")
        if not resource_uri or not client_id:
            return [
                types.TextContent(
                    type="text", text="Error: 'resource_uri' and 'client_id' required"
                )
            ]
        return [
            types.TextContent(
                type="text", text=unsubscribe_from_resource(resource_uri, client_id)
            )
        ]

    elif name == "openmanus_list_subscriptions":
        return [
            types.TextContent(
                type="text", text=list_subscriptions(arguments.get("resource_uri"))
            )
        ]

    else:
        return [types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


# ============================================================================
# Browser State + helpers
# ============================================================================

_browser_state: Dict[str, Any] = {
    "current_url": "",
    "page_content": "",
    "page_html": "",
    "elements": [],
}


def _extract_text_from_html(html: str) -> str:
    try:
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self._skip = {"script", "style", "noscript", "meta", "link"}
                self._in_skip = False

            def handle_starttag(self, tag, attrs):
                if tag in self._skip:
                    self._in_skip = True

            def handle_endtag(self, tag):
                if tag in self._skip:
                    self._in_skip = False

            def handle_data(self, data):
                if not self._in_skip and data.strip():
                    self.text.append(data.strip())

        e = TextExtractor()
        e.feed(html)
        return " ".join(e.text)[:10000]
    except Exception:
        return html[:10000]


def _get_page_title(html: str) -> str:
    import re

    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else "No title"


def _extract_clickable_elements(html: str) -> list:
    import re

    elements = []
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', html, re.IGNORECASE
    ):
        elements.append(
            {"text": m.group(2).strip() or "Click here", "href": m.group(1)}
        )
    for m in re.finditer(r"<button[^>]*>([^<]*)</button>", html, re.IGNORECASE):
        elements.append({"text": m.group(1).strip() or "Button", "href": "#button"})
    return elements


async def _handle_browser_action(arguments: dict) -> list[types.TextContent]:
    from urllib.request import Request as UReq
    from urllib.request import urlopen as uopen

    action = arguments.get("action", "")
    url = arguments.get("url", "")
    index = arguments.get("index")
    text = arguments.get("text", "")
    scroll_amount = arguments.get("scroll_amount", 0)
    goal = arguments.get("goal", "")
    keys = arguments.get("keys", "")
    selector = arguments.get("selector", "")

    if not action:
        return [types.TextContent(type="text", text="Error: No action specified")]

    if action == "navigate":
        if not url:
            return [
                types.TextContent(type="text", text="Error: URL required for navigate")
            ]
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
            req = UReq(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; OpenManus/1.0)"}
            )
            with uopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            _browser_state.update(
                {
                    "current_url": url,
                    "page_html": html,
                    "page_content": _extract_text_from_html(html),
                }
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"Navigated to {url}\nTitle: {_get_page_title(html)}\nContent: {len(_browser_state['page_content'])} chars",
                )
            ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Navigation error: {str(e)}")]

    elif action == "extract_content":
        if not _browser_state["page_content"]:
            return [types.TextContent(type="text", text="Error: No page loaded")]
        prefix = f"Goal: {goal}\n\n" if goal else ""
        return [
            types.TextContent(
                type="text", text=prefix + _browser_state["page_content"][:10000]
            )
        ]

    elif action in ("get_current_url",):
        return [
            types.TextContent(
                type="text",
                text=f"Current URL: {_browser_state['current_url'] or 'None'}",
            )
        ]

    elif action == "get_page_text":
        if not _browser_state["page_content"]:
            return [types.TextContent(type="text", text="Error: No page loaded")]
        return [
            types.TextContent(type="text", text=_browser_state["page_content"][:10000])
        ]

    elif action == "click":
        if not _browser_state["page_html"]:
            return [types.TextContent(type="text", text="Error: No page loaded")]
        elements = _extract_clickable_elements(_browser_state["page_html"])
        if index is not None and 0 <= index < len(elements):
            el = elements[index]
            href = el.get("href", "")
            if href.startswith(("http://", "https://")):
                return await _handle_browser_action({"action": "navigate", "url": href})
            return [
                types.TextContent(
                    type="text", text=f"Clicked: {el.get('text','N/A')} ({href})"
                )
            ]
        return [
            types.TextContent(
                type="text",
                text="Elements:\n"
                + "\n".join(
                    f"[{i}] {e.get('text')} -> {e.get('href')}"
                    for i, e in enumerate(elements[:20])
                ),
            )
        ]

    elif action == "scroll_to_text":
        if text and text in _browser_state.get("page_content", ""):
            idx = _browser_state["page_content"].index(text)
            ctx = _browser_state["page_content"][
                max(0, idx - 200) : idx + len(text) + 200
            ]
            return [
                types.TextContent(
                    type="text", text=f"Found '{text}' at {idx}:\n\n{ctx}"
                )
            ]
        return [types.TextContent(type="text", text=f"Text '{text}' not found")]

    elif action in ("scroll_down", "scroll_up"):
        direction = "down" if action == "scroll_down" else "up"
        return [
            types.TextContent(
                type="text",
                text=f"Scrolled {direction} {abs(scroll_amount) or 100}px (simulated)",
            )
        ]

    elif action == "fill":
        return [
            types.TextContent(
                type="text",
                text=f"Filled '{selector or 'field'}' with '{text}' (simulated)",
            )
        ]

    elif action == "send_keys":
        return [types.TextContent(type="text", text=f"Sent keys '{keys}' (simulated)")]

    elif action == "go_back":
        return [
            types.TextContent(
                type="text",
                text=f"Go back from: {_browser_state['current_url'] or 'None'} (simulated)",
            )
        ]

    else:
        return [
            types.TextContent(type="text", text=f"Error: Unknown action '{action}'")
        ]


# ============================================================================
# Resource Subscription Support
# ============================================================================

_resource_subscribers: Dict[str, set] = {}
_resource_change_callbacks: Dict[str, list] = {}


def subscribe_to_resource(resource_uri: str, client_id: str) -> str:
    _resource_subscribers.setdefault(resource_uri, set()).add(client_id)
    return f"Subscribed to resource: {resource_uri}"


def unsubscribe_from_resource(resource_uri: str, client_id: str) -> str:
    if resource_uri in _resource_subscribers:
        _resource_subscribers[resource_uri].discard(client_id)
        if not _resource_subscribers[resource_uri]:
            del _resource_subscribers[resource_uri]
    return f"Unsubscribed from resource: {resource_uri}"


def list_subscriptions(resource_uri: Optional[str] = None) -> str:
    if resource_uri:
        subs = _resource_subscribers.get(resource_uri, set())
        return json.dumps(
            {"resource": resource_uri, "subscribers": list(subs), "count": len(subs)},
            indent=2,
        )
    return json.dumps(
        {
            u: {"subscribers": list(s), "count": len(s)}
            for u, s in _resource_subscribers.items()
        },
        indent=2,
    )


def notify_resource_change(resource_uri: str):
    for cb in _resource_change_callbacks.get(resource_uri, []):
        try:
            cb(resource_uri)
        except Exception as e:
            logger.error(f"Resource change callback error: {e}")


# ============================================================================
# Health Check
# ============================================================================

_server_start_time: float = time.time()


def _get_llm_caps() -> dict:
    """Return capability info for the default LLM instance (safe — never throws)."""
    try:
        from app.llm import LLM, _is_local_server

        llm = LLM()
        return {
            "model": llm.model,
            "base_url": llm.base_url,
            "is_local_server": _is_local_server(llm.base_url),
            "caps_thinking": llm.caps_thinking,
            "caps_vision": llm.caps_vision,
            "thinking_enabled": llm.thinking_enabled,
            "enable_thinking_config": llm._enable_thinking,
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_health_status() -> dict:
    uptime = time.time() - _server_start_time
    tasks = agent.task_manager.tasks

    def _count(s):
        return sum(1 for t in tasks.values() if t.status == s)

    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    secs = int(uptime % 60)
    parts = (
        ([f"{days}d"] if days else [])
        + ([f"{hours}h"] if hours else [])
        + ([f"{minutes}m"] if minutes else [])
        + [f"{secs}s"]
    )
    return {
        "status": "healthy",
        "server": {
            "name": "openmanus-mcp-server",
            "version": "1.0.0",
            "uptime_seconds": round(uptime, 2),
            "uptime_human": " ".join(parts),
        },
        "tasks": {
            "total": len(tasks),
            "running": _count(TaskStatus.RUNNING),
            "pending": _count(TaskStatus.PENDING),
            "completed": _count(TaskStatus.COMPLETED),
            "failed": _count(TaskStatus.FAILED),
            "cancelled": _count(TaskStatus.CANCELLED),
        },
        "subscriptions": {
            "resources": len(_resource_subscribers),
            "total_clients": sum(len(s) for s in _resource_subscribers.values()),
        },
        "browser": {
            "page_loaded": bool(_browser_state.get("page_content")),
            "current_url": _browser_state.get("current_url", ""),
        },
        "llm": _get_llm_caps(),
        "timestamp": datetime.datetime.now().isoformat(),
    }


# ============================================================================
# Unified Resource Dispatcher
# ============================================================================


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return RESOURCES


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Route resource reads to the appropriate handler."""
    if uri == "openmanus://config":
        return json.dumps(
            {
                "server": {"name": "openmanus-mcp-server", "version": "1.0.0"},
                "agent": {"max_steps": 30, "model": "gpt-4o"},
                "security": {"sandbox_enabled": True},
            },
            indent=2,
        )
    elif uri == "openmanus://templates/code_review":
        return """# Code Review Request\n\nPlease review the following code:\n\n## File: {file_path}\n\n## Focus Areas: {focus_areas}\n\n## Review Criteria:\n1. Correctness\n2. Security\n3. Performance\n4. Readability\n5. Maintainability\n6. Testing\n"""
    elif uri == "openmanus://templates/bug_fix":
        return """# Bug Fix Request\n\n## Bug Description: {bug_description}\n\n## File: {file_path}\n\n## Request:\n1. Analyze root cause\n2. Propose a fix\n3. Suggest regression tests\n"""
    elif uri == "openmanus://templates/feature_impl":
        return """# Feature Implementation Request\n\n## Feature: {feature_description}\n\n## Tech Stack: {tech_stack}\n\n## Request:\n1. Design architecture\n2. Create implementation plan\n3. Generate code\n4. Suggest tests\n"""
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


# ============================================================================
# Unified Prompt Dispatcher
# ============================================================================


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return PROMPTS


@app.get_prompt()
async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    """Route prompt requests to the appropriate handler."""

    def _msg(text: str) -> types.GetPromptResult:
        return types.GetPromptResult(
            description=name,
            messages=[
                types.PromptMessage(
                    role="user", content=types.TextContent(type="text", text=text)
                )
            ],
        )

    if name == "code_review":
        return _msg(
            f"Please review the code in {arguments.get('file_path','unknown')}, focusing on: {arguments.get('focus_areas','general')}"
        )
    elif name == "bug_fix":
        return _msg(
            f"Please help fix this bug: {arguments.get('bug_description','unknown')} in file {arguments.get('file_path','unknown')}"
        )
    elif name == "feature_impl":
        return _msg(
            f"Please implement this feature: {arguments.get('feature_description','unknown')} using {arguments.get('tech_stack','default')}"
        )
    elif name == "refactor":
        return _msg(
            f"Please refactor this code: {arguments.get('code_context','unknown')} with goals: {arguments.get('goals','general improvement')}"
        )
    elif name == "test_gen":
        return _msg(
            f"Please generate {arguments.get('test_framework','pytest')} tests for:\n\n{arguments.get('code','unknown')}"
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """Start the MCP server."""
    import argparse
    from io import TextIOWrapper

    parser = argparse.ArgumentParser(description="OpenManus MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8765, help="Port for SSE transport")
    parser.add_argument("--config", type=str, help="Path to OpenManus config file")
    args = parser.parse_args()

    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if "llm" in config:
                    agent.config["model"] = config["llm"].get("model", "gpt-4o")
                if "agent" in config:
                    agent.config["max_steps"] = config["agent"].get("max_steps", 30)

    if args.sse:
        from fastapi import FastAPI
        from mcp.server.sse import SseServerTransport
        from starlette.middleware.trustedhost import TrustedHostMiddleware

        fastapi_app = FastAPI(title="OpenManus MCP Server")
        fastapi_app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
        sse = SseServerTransport("/messages/")

        async with sse.connect_sse(fastapi_app, "/sse", "/messages/") as (
            read_stream,
            write_stream,
        ):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openmanus-mcp-server",
                    server_version="1.0.0",
                    capabilities=sse.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    else:
        # ------------------------------------------------------------------ #
        # Stdio transport — stdout MUST stay clean JSON-RPC.                  #
        # sys.stdout was already redirected to stderr at module load.          #
        # Use _MCP_STDOUT_BUFFER (saved before redirect) for the MCP pipe.    #
        # ------------------------------------------------------------------ #
        from io import TextIOWrapper

        import anyio

        mcp_stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))
        mcp_stdout = anyio.wrap_file(
            TextIOWrapper(_MCP_STDOUT_BUFFER, encoding="utf-8")
        )

        async with stdio_server(stdin=mcp_stdin, stdout=mcp_stdout) as (
            read_stream,
            write_stream,
        ):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openmanus-mcp-server",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(
                        prompts=types.PromptsCapability(listChanged=True),
                        resources=types.ResourcesCapability(
                            subscribe=True, listChanged=True
                        ),
                        tools=types.ToolsCapability(listChanged=True),
                        logging={},
                    ),
                    experimental_capabilities={},
                ),
            )


if __name__ == "__main__":
    asyncio.run(main())
