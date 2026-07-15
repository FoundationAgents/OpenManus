import asyncio
import json
import os
import re
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

import redis as redis_lib
from sqlalchemy.exc import SQLAlchemyError

from app.agent.manus import Manus
from app.config import config
from app.memory.agentmemory import agentmemory
from app.runtime_settings import get_disabled_tools, get_llm_connection
from app.sandbox.conversation import ConversationSandbox
from app.skills import format_skill_context, load_skills, select_skills
from app.task_context import (
    current_auto_context_compress,
    current_llm_connection,
    current_model,
    current_requested_context_window,
    current_sandbox,
    current_task,
    current_workspace,
)
from core.task import TaskStatus
from core.task_registry import TaskRegistry
from server.celery_app import celery_app
from server.models import (
    ConversationEventORM,
    ConversationORM,
    ObsidianEdgeORM,
    ObsidianNoteORM,
    TaskORM,
)


registry = TaskRegistry()

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
DEFAULT_CONVERSATION_ID = os.getenv("OPENMANUS_DEFAULT_CONVERSATION_ID", "main")
TASK_HARD_TIMEOUT_SECONDS = int(
    os.getenv("OPENMANUS_TASK_HARD_TIMEOUT_SECONDS", "1800")
)
_redis_client: Optional[redis_lib.Redis] = None
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")
TAG_RE = re.compile(r"(^|\s)#([A-Za-z0-9_\-\/]+)")


def _lmstudio_native_base(base_url: str) -> Optional[str]:
    try:
        parsed = urllib.parse.urlparse((base_url or "").strip())
    except Exception:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    root = f"{parsed.scheme}://{parsed.netloc}"
    return f"{root}/api/v1"


def _http_json(
    method: str,
    url: str,
    payload: Optional[dict] = None,
    token: Optional[str] = None,
    timeout: int = 10,
) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        return json.loads(data.decode("utf-8")) if data else {}


def _connection_candidates(primary: dict) -> list[dict]:
    base = dict(primary or {})
    chain = base.get("fallback_chain", [])
    if isinstance(chain, str):
        try:
            chain = json.loads(chain)
        except Exception:
            chain = []
    candidates = [base]
    if isinstance(chain, list):
        for item in chain:
            if isinstance(item, dict):
                merged = dict(base)
                merged.update(item)
                candidates.append(merged)
    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        key = (
            str(candidate.get("api_type") or "").strip().lower(),
            str(candidate.get("base_url") or "").strip(),
            str(candidate.get("model") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _is_connection_healthy(connection: dict, timeout: int = 5) -> tuple[bool, str]:
    base_url = str(connection.get("base_url") or "").strip()
    api_key = str(connection.get("api_key") or "").strip() or None
    api_type = str(connection.get("api_type") or "").strip().lower()
    if not base_url:
        return False, "missing base_url"
    try:
        if api_type in {"lmstudio", "local"}:
            native = _lmstudio_native_base(base_url)
            if not native:
                return False, "invalid lmstudio base_url"
            _http_json("GET", f"{native}/models", token=api_key, timeout=timeout)
            return True, "lmstudio /models ok"
        # OpenAI-compatible default
        _http_json(
            "GET",
            base_url.rstrip("/") + "/models"
            if base_url.rstrip("/").endswith("/v1")
            else base_url.rstrip("/") + "/v1/models",
            token=api_key,
            timeout=timeout,
        )
        return True, "v1/models ok"
    except Exception as exc:
        return False, str(exc)


def resolve_llm_connection(connection: dict, task) -> dict:
    candidates = _connection_candidates(connection or {})
    for index, candidate in enumerate(candidates):
        ok, detail = _is_connection_healthy(candidate)
        task.emit(
            "agent_state",
            {
                "state": "llm_preflight",
                "candidate_index": index,
                "api_type": str(candidate.get("api_type") or ""),
                "base_url": str(candidate.get("base_url") or ""),
                "ok": ok,
                "detail": detail,
            },
        )
        if ok:
            selected = dict(candidate)
            selected.pop("fallback_chain", None)
            task.emit(
                "agent_state",
                {
                    "state": "llm_selected",
                    "candidate_index": index,
                    "api_type": str(selected.get("api_type") or ""),
                    "base_url": str(selected.get("base_url") or ""),
                    "model": str(selected.get("model") or ""),
                },
            )
            return selected
    # No healthy candidate; fall back to original so existing behavior remains.
    fallback = dict(connection or {})
    fallback.pop("fallback_chain", None)
    task.emit(
        "agent_state",
        {
            "state": "llm_selected",
            "candidate_index": -1,
            "api_type": str(fallback.get("api_type") or ""),
            "base_url": str(fallback.get("base_url") or ""),
            "model": str(fallback.get("model") or ""),
            "detail": "No healthy fallback candidate; using primary settings.",
        },
    )
    return fallback


def _persist_received_context_window(conversation_id: str, value: int) -> None:
    try:
        cid = uuid.UUID(str(conversation_id))
    except Exception:
        return
    try:
        with registry.SessionLocal() as session:
            conversation = session.get(ConversationORM, cid)
            if conversation is None:
                return
            settings = dict(conversation.settings or {})
            settings["received_context_window"] = int(value)
            settings["received_context_window_source"] = "lmstudio_load"
            conversation.settings = settings
            session.commit()
    except Exception:
        return


def sync_lmstudio_context_window(
    *,
    conversation_id: str,
    requested_context_window: Optional[int],
    llm_connection: dict,
    model: Optional[str],
    task,
) -> Optional[int]:
    """For LM Studio connections, load model with requested context_length and return applied value."""
    if not requested_context_window or requested_context_window <= 0:
        return None

    connection = llm_connection or {}
    default_llm = config.llm.get("default") if isinstance(config.llm, dict) else None

    base_url = str(
        connection.get("base_url") or getattr(default_llm, "base_url", "") or ""
    )
    api_type = str(
        connection.get("api_type") or getattr(default_llm, "api_type", "") or ""
    ).lower()
    api_key = str(
        connection.get("api_key") or getattr(default_llm, "api_key", "") or ""
    )
    selected_model = str(
        model or connection.get("model") or getattr(default_llm, "model", "") or ""
    ).strip()

    native_base = _lmstudio_native_base(base_url)
    is_lmstudio = api_type in {"lmstudio", "local", "openai"} and (
        ":1234" in base_url
        or "lmstudio" in base_url
        or "localhost" in base_url
        or "127.0.0.1" in base_url
    )
    if not native_base or not is_lmstudio or not selected_model:
        return None

    try:
        response = _http_json(
            "POST",
            f"{native_base}/models/load",
            payload={
                "model": selected_model,
                "context_length": int(requested_context_window),
                "echo_load_config": True,
            },
            token=api_key or None,
            timeout=20,
        )
        load_config = response.get("load_config") if isinstance(response, dict) else {}
        received = load_config.get("context_length") or response.get("context_length")
        if received in (None, ""):
            return None
        received_value = int(received)
        _persist_received_context_window(conversation_id, received_value)
        task.emit(
            "context_window_received",
            {
                "requested_window": int(requested_context_window),
                "received_window": received_value,
                "model": selected_model,
                "source": "lmstudio_load",
            },
        )
        return received_value
    except Exception as exc:
        task.emit(
            "context_window_received",
            {
                "requested_window": int(requested_context_window),
                "received_window": None,
                "model": selected_model,
                "source": "lmstudio_load",
                "error": str(exc),
            },
        )
        return None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def publish_event(task_id: str, event_type: str, data: dict) -> None:
    """Append an agent event to a Redis Stream so SSE can replay from the start."""
    stream_key = f"task:{task_id}:stream"
    payload = data if isinstance(data, dict) else {"value": str(data)}
    try:
        get_redis().xadd(
            stream_key,
            {"type": event_type, "data": json.dumps(payload)},
            maxlen=500,  # cap stream size
        )
    except Exception:
        pass  # Never let Redis failures crash the worker
    try:
        conversation_id = payload.get("conversation_id") or get_conversation_id(task_id)
        with registry.SessionLocal() as session:
            session.add(
                ConversationEventORM(
                    conversation_id=uuid.UUID(str(conversation_id)),
                    task_id=uuid.UUID(str(task_id)),
                    event_type=event_type,
                    payload=payload,
                )
            )
            session.commit()
    except (SQLAlchemyError, Exception):
        pass


def summarize_workspace(workspace_root: Path) -> dict:
    """Collect a small artifact summary for the completion event."""
    if not workspace_root.exists():
        return {"pdfs": [], "tex": [], "logs": [], "warning": "Workspace not found."}

    def _relative_files(pattern: str) -> list[str]:
        return sorted(
            str(path.relative_to(workspace_root))
            for path in workspace_root.rglob(pattern)
            if path.is_file()
        )

    pdfs = _relative_files("*.pdf")
    tex_files = _relative_files("*.tex")
    logs = _relative_files("*.log")
    warning = None

    if not pdfs and (tex_files or logs):
        warning = (
            "No PDF was found in the task workspace. "
            "LaTeX may have failed; check the terminal output or .log files."
        )

    return {"pdfs": pdfs, "tex": tex_files, "logs": logs, "warning": warning}


def get_task_record(task_id: str) -> Optional[TaskORM]:
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None:
            return None
        session.expunge(orm)
        return orm


def get_conversation_id(task_id: str) -> str:
    orm = get_task_record(task_id)
    if orm is None:
        return DEFAULT_CONVERSATION_ID
    task_input = orm.input or {}
    if task_input.get("conversation_id"):
        return str(task_input.get("conversation_id"))
    if os.getenv("OPENMANUS_SINGLE_CONVERSATION", "true").lower() != "false":
        return DEFAULT_CONVERSATION_ID
    return str(task_input.get("conversation_id") or DEFAULT_CONVERSATION_ID)


def get_task_model(task_id: str) -> Optional[str]:
    orm = get_task_record(task_id)
    if orm is None:
        return None
    task_input = orm.input or {}
    return task_input.get("model")


def get_task_disabled_tools(task_id: str) -> set[str]:
    orm = get_task_record(task_id)
    if orm is None:
        return set()
    task_input = orm.input or {}
    return {str(name) for name in task_input.get("disabled_tools", [])}


def get_task_requested_context_window(task_id: str) -> Optional[int]:
    orm = get_task_record(task_id)
    if orm is None:
        return None
    task_input = orm.input or {}
    raw = task_input.get("requested_context_window")
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def get_task_auto_context_compress(task_id: str) -> bool:
    orm = get_task_record(task_id)
    if orm is None:
        return True
    task_input = orm.input or {}
    raw = task_input.get("auto_context_compress")
    if raw is None:
        return True
    return bool(raw)


def get_task_disabled_skills(task_id: str) -> set[str]:
    orm = get_task_record(task_id)
    if orm is None:
        return set()
    task_input = orm.input or {}
    return {
        str(name).strip()
        for name in task_input.get("disabled_skills", [])
        if str(name).strip()
    }


def get_task_enable_vendor_skills(task_id: str) -> bool:
    orm = get_task_record(task_id)
    if orm is None:
        return True
    task_input = orm.input or {}
    raw = task_input.get("enable_vendor_skills")
    if raw is None:
        return True
    return bool(raw)


def get_task_pinned_skills(task_id: str) -> list[str]:
    orm = get_task_record(task_id)
    if orm is None:
        return []
    task_input = orm.input or {}
    return [
        str(name).strip()
        for name in task_input.get("pinned_skills", [])
        if str(name).strip()
    ]


def get_task_identity_notes(task_id: str) -> str:
    orm = get_task_record(task_id)
    if orm is None:
        return ""
    task_input = orm.input or {}
    return str(task_input.get("identity_notes") or "").strip()


def conversation_workspace(conversation_id: str) -> Path:
    return (
        Path(os.getenv("OPENMANUS_WORKSPACE_ROOT", "/app/workspace"))
        / "conversations"
        / conversation_id
    )


def host_conversation_workspace(conversation_id: str) -> Path:
    return (
        Path(os.getenv("OPENMANUS_HOST_WORKSPACE_ROOT", "/app/workspace"))
        / "conversations"
        / conversation_id
    )


def build_conversation_context(
    task_id: str, conversation_id: str, workspace_root: Path
) -> str:
    """Build compact continuity context for follow-up tasks in the same conversation."""
    with registry.SessionLocal() as session:
        rows = session.query(TaskORM).order_by(TaskORM.created_at.asc()).all()

    conversation_rows = [
        row
        for row in rows
        if (
            DEFAULT_CONVERSATION_ID
            if os.getenv("OPENMANUS_SINGLE_CONVERSATION", "true").lower() != "false"
            else str(
                (row.input or {}).get("conversation_id") or DEFAULT_CONVERSATION_ID
            )
        )
        == conversation_id
        and str(row.task_id) != task_id
    ][-6:]

    if not conversation_rows and not workspace_root.exists():
        return ""

    lines = [
        "Conversation continuity context:",
        f"- Shared workspace: {workspace_root}",
        "- Treat this as the same ongoing project. Reuse existing files and state.",
        "- Do not restart prior work unless the user explicitly asks; continue from the latest result.",
    ]

    if conversation_rows:
        lines.append("- Previous tasks in this conversation:")
        for row in conversation_rows:
            task_input = row.input or {}
            result = row.result or {}
            output = str(result.get("output") or result.get("error") or "")
            output = output.replace("\n", " ")
            if len(output) > 500:
                output = output[:500] + "..."
            lines.append(
                f"  - {row.status}: {task_input.get('prompt', '(no prompt)')} | {output}"
            )

    if workspace_root.exists():
        files = sorted(
            str(path.relative_to(workspace_root))
            for path in workspace_root.rglob("*")
            if path.is_file()
        )[:80]
        if files:
            lines.append("- Current workspace files:")
            lines.extend(f"  - {file}" for file in files)

    return "\n".join(lines)


def build_obsidian_context(conversation_id: str, max_notes: int = 6) -> str:
    """Build compact persisted Obsidian context from DB notes."""
    with registry.SessionLocal() as session:
        rows = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == uuid.UUID(str(conversation_id)))
            .order_by(ObsidianNoteORM.updated_at.desc())
            .limit(max(1, min(max_notes, 20)))
            .all()
        )

    if not rows:
        return ""

    lines = [
        "Persistent vault context (Obsidian import):",
        "- Use these notes as durable long-term memory for this conversation.",
    ]
    for note in rows:
        snippet = (note.content or "").replace("\n", " ").strip()
        if len(snippet) > 280:
            snippet = snippet[:280] + "..."
        tags = ", ".join(str(tag) for tag in (note.tags or [])[:6])
        tags_part = f" | tags: {tags}" if tags else ""
        lines.append(f"- {note.title} ({note.path}){tags_part}: {snippet}")
    return "\n".join(lines)


def build_agentmemory_context(conversation_id: str, prompt: str) -> str:
    """Build optional long-term recall context from AgentMemory."""
    if not prompt or not agentmemory.enabled:
        return ""
    return agentmemory.format_context(conversation_id=conversation_id, query=prompt)


def build_identity_context(identity_notes: str) -> str:
    if not identity_notes:
        return ""
    return f"Persistent user profile/context for this conversation:\n{identity_notes}"


def update_skill_suggestions(conversation_id: str, task_id: str, prompt: str) -> None:
    if not prompt.strip():
        return
    try:
        cid = uuid.UUID(str(conversation_id))
        tid = uuid.UUID(str(task_id))
    except Exception:
        return
    try:
        with registry.SessionLocal() as session:
            rows = (
                session.query(ConversationEventORM)
                .filter(
                    ConversationEventORM.conversation_id == cid,
                    ConversationEventORM.task_id == tid,
                    ConversationEventORM.event_type == "tool_result",
                )
                .all()
            )
            tools: list[str] = []
            for row in rows:
                payload = row.payload or {}
                tool = str(payload.get("tool") or "").strip()
                if tool and tool not in tools:
                    tools.append(tool)
            if len(tools) < 2:
                return
            conversation = session.get(ConversationORM, cid)
            if conversation is None:
                return
            settings = dict(conversation.settings or {})
            if not bool(settings.get("auto_skill_curator", True)):
                return
            suggestions = settings.get("skill_suggestions", [])
            if not isinstance(suggestions, list):
                suggestions = []
            key = "|".join(tools[:6])
            now = int(time.time())
            updated = False
            for item in suggestions:
                if not isinstance(item, dict):
                    continue
                if item.get("key") == key:
                    item["count"] = int(item.get("count") or 0) + 1
                    item["last_seen"] = now
                    item["last_prompt"] = prompt[:180]
                    updated = True
                    break
            if not updated:
                suggestions.insert(
                    0,
                    {
                        "key": key,
                        "tools": tools[:6],
                        "count": 1,
                        "last_seen": now,
                        "last_prompt": prompt[:180],
                    },
                )
            settings["skill_suggestions"] = suggestions[:30]
            conversation.settings = settings
            session.commit()
    except Exception:
        return


def auto_sync_obsidian_notes(conversation_id: str, workspace_root: Path) -> None:
    """Automatically sync markdown notes from workspace into obsidian_notes + graph edges.

    Resolution fixes vs. upstream:
    - Path-qualified wikilinks (e.g. [[projects/Overview]]) now resolve correctly
      by stripping the .md extension from stored paths before lookup.
    - Duplicate titles are detected: if two notes share a title, title-only links
      are ambiguous and skipped rather than silently picking the wrong one.
    - Edge updates are diff-based: only edges sourced from workspace-synced notes
      are touched. Imported vault edges survive untouched.
    """
    if not workspace_root.exists():
        return
    markdown_files = [
        path
        for path in workspace_root.rglob("*.md")
        if path.is_file()
        and ".git/" not in str(path)
        and "node_modules/" not in str(path)
        and ".venv/" not in str(path)
    ][:200]
    if not markdown_files:
        return

    cid = uuid.UUID(str(conversation_id))
    with registry.SessionLocal() as session:
        existing_notes = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == cid)
            .all()
        )
        by_path = {note.path: note for note in existing_notes}
        touched_paths: set[str] = set()
        touched_notes: list[ObsidianNoteORM] = []

        for file_path in markdown_files:
            rel = str(file_path.relative_to(workspace_root))
            touched_paths.add(rel)
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = content.splitlines()
            first_heading = next(
                (
                    line.lstrip("# ").strip()
                    for line in lines
                    if line.strip().startswith("#") and line.lstrip("# ").strip()
                ),
                "",
            )
            title = first_heading or file_path.stem
            tags = sorted({match[1] for match in TAG_RE.findall(content)})[:40]
            note = by_path.get(rel)
            if note is None:
                note = ObsidianNoteORM(
                    conversation_id=cid,
                    path=rel,
                    title=title,
                    content=content,
                    tags=tags,
                    meta={"source": "workspace-auto-sync"},
                )
                session.add(note)
            else:
                note.title = title
                note.content = content
                note.tags = tags
                note.meta = {"source": "workspace-auto-sync"}
            by_path[rel] = note
            touched_notes.append(note)

        session.flush()

        # keep manually imported notes untouched; only remove old auto-synced missing files
        for old in existing_notes:
            source = (old.meta or {}).get("source")
            if source == "workspace-auto-sync" and old.path not in touched_paths:
                session.delete(old)

        # --- Diff-based edge update (only for edges sourced from touched notes) ---
        # Rebuild the full note index for resolution after flush
        all_notes = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == cid)
            .all()
        )
        all_by_path = {note.path: note for note in all_notes}
        # Path-stem lookup: strip .md so [[projects/Overview]] matches "projects/Overview.md"
        all_by_path_stem = {}
        for note in all_notes:
            stem = note.path
            if stem.endswith(".md"):
                stem = stem[:-3]
            all_by_path_stem.setdefault(stem, []).append(note)
        # Title lookup: track duplicates
        all_by_title: dict[str, list[ObsidianNoteORM]] = {}
        for note in all_notes:
            all_by_title.setdefault(note.title, []).append(note)

        touched_note_ids = {note.note_id for note in touched_notes}

        # Compute desired edges from touched notes
        desired_edges: set[tuple] = set()
        for note in touched_notes:
            content = note.content or ""
            for link in WIKILINK_RE.findall(content):
                target_name = str(link).strip()
                if not target_name:
                    continue
                # Resolution order: path-stem > exact path > unambiguous title
                target = None
                stem_matches = all_by_path_stem.get(target_name, [])
                if len(stem_matches) == 1:
                    target = stem_matches[0]
                elif target_name in all_by_path:
                    target = all_by_path[target_name]
                else:
                    title_matches = all_by_title.get(target_name, [])
                    if len(title_matches) == 1:
                        target = title_matches[0]
                    # else: ambiguous or not found — skip
                if target is not None and target.note_id != note.note_id:
                    desired_edges.add(
                        (note.note_id, target.note_id, "wikilink")
                    )

        # Query existing edges sourced from touched notes only
        existing_edge_rows = (
            session.query(ObsidianEdgeORM)
            .filter(
                ObsidianEdgeORM.conversation_id == cid,
                ObsidianEdgeORM.source_note_id.in_(touched_note_ids),
            )
            .all()
        )
        existing_edges = {
            (e.source_note_id, e.target_note_id, e.relation): e
            for e in existing_edge_rows
        }

        # Delete edges that no longer exist
        for key, edge in existing_edges.items():
            if key not in desired_edges:
                session.delete(edge)

        # Insert new edges
        for src_id, tgt_id, relation in desired_edges:
            if (src_id, tgt_id, relation) not in existing_edges:
                session.add(
                    ObsidianEdgeORM(
                        conversation_id=cid,
                        source_note_id=src_id,
                        target_note_id=tgt_id,
                        relation=relation,
                    )
                )

        session.commit()


class RedisEmittingTask:
    """
    Wraps a Task so that every emit() is also written to a Redis Stream.
    This allows the web server (different process) to stream events to the browser.
    """

    def __init__(self, task_id: str, inner_task):
        self.id = task_id
        self._inner = inner_task

    def emit(self, type: str, data) -> None:
        self._inner.emit(type, data)
        publish_event(
            self.id, type, data if isinstance(data, dict) else {"value": str(data)}
        )

    def is_interrupted(self) -> bool:
        return self._inner.is_interrupted()

    def interrupt(self) -> None:
        self._inner.interrupt()

    def __getattr__(self, name):
        return getattr(self._inner, name)


@celery_app.task(name="run_task")
def run_task(task_id: str, prompt: Optional[str] = None):
    """Celery task: run Manus agent and write events to Redis Stream."""
    task = registry.get_task(task_id)
    if task is None:
        return {"error": "task not found"}

    wrapped = RedisEmittingTask(task_id, task)
    conversation_id = get_conversation_id(task_id)
    model = get_task_model(task_id)
    disabled_tools = get_disabled_tools() | get_task_disabled_tools(task_id)
    requested_context_window = get_task_requested_context_window(task_id)
    auto_context_compress = get_task_auto_context_compress(task_id)
    disabled_skills = get_task_disabled_skills(task_id)
    enable_vendor_skills = get_task_enable_vendor_skills(task_id)
    pinned_skills = get_task_pinned_skills(task_id)
    identity_notes = get_task_identity_notes(task_id)
    llm_connection = get_llm_connection()
    workspace_root = conversation_workspace(conversation_id)
    host_workspace_root = host_conversation_workspace(conversation_id)

    async def _run():
        workspace_root.mkdir(parents=True, exist_ok=True)
        sandbox = None
        sandbox_token = None
        workspace_token = current_workspace.set(str(workspace_root))
        model_token = current_model.set(model)
        requested_context_window_token = current_requested_context_window.set(
            requested_context_window
        )
        auto_context_compress_token = current_auto_context_compress.set(
            auto_context_compress
        )
        selected_connection = resolve_llm_connection(llm_connection, wrapped)
        llm_connection_token = current_llm_connection.set(selected_connection)
        if config.sandbox.use_sandbox:
            sandbox = await ConversationSandbox(
                conversation_id=conversation_id,
                host_workspace=host_workspace_root,
                config=config.sandbox,
            ).ensure()
            sandbox_token = current_sandbox.set(sandbox)

        previous_cwd = os.getcwd()
        os.chdir(workspace_root)
        token = current_task.set(wrapped)
        try:
            sync_lmstudio_context_window(
                conversation_id=conversation_id,
                requested_context_window=requested_context_window,
                llm_connection=selected_connection,
                model=model,
                task=wrapped,
            )
            auto_sync_obsidian_notes(conversation_id, workspace_root)
            continuity = build_conversation_context(
                task_id, conversation_id, workspace_root
            )
            obsidian_context = build_obsidian_context(conversation_id)
            agentmemory_context = build_agentmemory_context(
                conversation_id, prompt or ""
            )
            identity_context = build_identity_context(identity_notes)
            selected_skills = select_skills(
                prompt or "",
                workspace_root,
                include_vendor=enable_vendor_skills,
                disabled_skills=disabled_skills,
            )
            if pinned_skills:
                pool = load_skills(
                    workspace_root,
                    include_vendor=enable_vendor_skills,
                    disabled_skills=disabled_skills,
                )
                names = {skill.name: skill for skill in pool}
                ordered = [names[name] for name in pinned_skills if name in names]
                for skill in selected_skills:
                    if skill.name not in {item.name for item in ordered}:
                        ordered.append(skill)
                selected_skills = ordered
            skill_context = format_skill_context(selected_skills)
            if sandbox is not None:
                continuity = continuity.replace(
                    str(workspace_root), config.sandbox.work_dir
                )
                skill_context = skill_context.replace(
                    str(workspace_root), config.sandbox.work_dir
                )
            context_parts = [
                part
                for part in (
                    continuity,
                    obsidian_context,
                    agentmemory_context,
                    identity_context,
                    skill_context,
                )
                if part
            ]
            combined_context = "\n\n".join(context_parts)
            run_prompt = (
                f"{combined_context}\n\nCurrent user request:\n{prompt}"
                if context_parts and prompt
                else prompt
            )
            agent_workspace = (
                config.sandbox.work_dir if sandbox is not None else str(workspace_root)
            )
            agent = await Manus.create(
                workspace_root=agent_workspace,
                disabled_tools=disabled_tools,
            )
            result = await agent.run(wrapped, run_prompt)
            return result
        finally:
            current_task.reset(token)
            if sandbox_token is not None:
                current_sandbox.reset(sandbox_token)
            current_workspace.reset(workspace_token)
            current_model.reset(model_token)
            current_requested_context_window.reset(requested_context_window_token)
            current_auto_context_compress.reset(auto_context_compress_token)
            current_llm_connection.reset(llm_connection_token)
            os.chdir(previous_cwd)

    try:
        task.status = "RUNNING"
        registry.update_task(task)
        wrapped.emit(
            "agent_state", {"state": "run_started", "conversation_id": conversation_id}
        )
        if config.agentmemory.enabled and prompt:
            agentmemory.remember(
                conversation_id=conversation_id,
                title="User request",
                content=str(prompt),
                metadata={"task_id": task_id, "status": "STARTED"},
            )
        result = asyncio.run(
            asyncio.wait_for(_run(), timeout=max(30, TASK_HARD_TIMEOUT_SECONDS))
        )
        task.status = "COMPLETED"
        workspace_summary = summarize_workspace(workspace_root)
        result_text = str(result or "").strip()
        completion_message = result_text if result_text else "Task completed."
        if config.agentmemory.enabled and config.agentmemory.auto_remember_completion:
            agentmemory.remember(
                conversation_id=conversation_id,
                title="Task completion summary",
                content=completion_message,
                metadata={"task_id": task_id, "status": "COMPLETED"},
            )
        update_skill_suggestions(conversation_id, task_id, prompt or "")
        registry.update_task(
            task,
            result={
                "output": result,
                "workspace": workspace_summary,
                "conversation_id": conversation_id,
            },
        )
        publish_event(
            task_id,
            "finish_signal",
            {
                "message": completion_message,
                "workspace": workspace_summary,
                "conversation_id": conversation_id,
            },
        )
        wrapped.emit(
            "agent_state",
            {"state": "run_completed", "conversation_id": conversation_id},
        )
        return {"status": "COMPLETED", "result": result}
    except asyncio.TimeoutError:
        detail = (
            f"Task exceeded hard timeout ({max(30, TASK_HARD_TIMEOUT_SECONDS)}s) "
            "and was terminated."
        )
        task.status = TaskStatus.FAILED
        registry.update_task(task, result={"error": detail})
        publish_event(
            task_id,
            "error",
            {
                "message": "Task failed",
                "detail": detail,
                "reason": detail,
                "conversation_id": conversation_id,
            },
        )
        wrapped.emit(
            "agent_state",
            {
                "state": "run_failed",
                "conversation_id": conversation_id,
                "error": detail,
            },
        )
        return {"status": "FAILED", "error": detail}
    except Exception as exc:
        task.status = TaskStatus.FAILED
        registry.update_task(task, result={"error": str(exc)})
        publish_event(
            task_id,
            "error",
            {
                "message": "Task failed",
                "detail": str(exc),
                "reason": str(exc),
                "conversation_id": conversation_id,
            },
        )
        wrapped.emit(
            "agent_state",
            {
                "state": "run_failed",
                "conversation_id": conversation_id,
                "error": str(exc),
            },
        )
        return {"status": "FAILED", "error": str(exc)}
    finally:
        # Last-resort guard: never leave task non-terminal.
        if str(task.status) in {"CREATED", "RUNNING"}:
            detail = "Task ended unexpectedly without terminal status."
            task.status = TaskStatus.FAILED
            registry.update_task(task, result={"error": detail})
            publish_event(
                task_id,
                "error",
                {
                    "message": "Task failed",
                    "detail": detail,
                    "reason": detail,
                    "conversation_id": conversation_id,
                },
            )
        # Ensure worker process does not keep a closed loop as current loop.
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass
