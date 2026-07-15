import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text
from sse_starlette.sse import EventSourceResponse

from app.config import config
from app.memory.agentmemory import agentmemory
from app.sandbox.conversation import ConversationSandbox
from app.skills import load_skills, select_skills
from core.task import TaskStatus
from core.task_registry import TaskRegistry
from server.celery_app import celery_app
from server.models import (
    AppSettingORM,
    ConversationEventORM,
    ConversationORM,
    ObsidianEdgeORM,
    ObsidianNoteORM,
    SessionORM,
    TaskORM,
    UserORM,
)
from server.tasks import run_task


REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
DEFAULT_CONVERSATION_ID = os.getenv("OPENMANUS_DEFAULT_CONVERSATION_ID", "main")
SESSION_COOKIE = "openmanus_session"
SESSION_DAYS = int(os.getenv("OPENMANUS_SESSION_DAYS", "30"))
WORKSPACE_ROOT = os.getenv("OPENMANUS_WORKSPACE_ROOT", "/app/workspace")
HOST_WORKSPACE_ROOT = os.getenv(
    "OPENMANUS_HOST_WORKSPACE_ROOT", "/home/mohamed/OpenManus/workspace"
)


app = FastAPI(title="OpenManus Task API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = TaskRegistry()


def _ensure_schema_updates() -> None:
    from server.models import Base

    Base.metadata.create_all(bind=registry.engine)
    with registry.engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS model VARCHAR")
        )
        connection.execute(
            text(
                "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::jsonb"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_conversation_events_conversation_created "
                "ON conversation_events (conversation_id, created_at, event_id)"
            )
        )
        
        # Ensure Obsidian unique constraints exist
        note_constraint = connection.execute(
            text("SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='uq_obsidian_note_conv_path'")
        ).fetchone()
        if not note_constraint:
            # Clean up duplicate notes keeping the latest one
            connection.execute(
                text(
                    "DELETE FROM obsidian_notes a USING obsidian_notes b "
                    "WHERE a.note_id < b.note_id AND a.conversation_id = b.conversation_id AND a.path = b.path"
                )
            )
            connection.execute(
                text("ALTER TABLE obsidian_notes ADD CONSTRAINT uq_obsidian_note_conv_path UNIQUE (conversation_id, path)")
            )

        edge_constraint = connection.execute(
            text("SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='uq_obsidian_edge_conv_src_tgt_rel'")
        ).fetchone()
        if not edge_constraint:
            # Clean up duplicate edges keeping the latest one
            connection.execute(
                text(
                    "DELETE FROM obsidian_edges a USING obsidian_edges b "
                    "WHERE a.edge_id < b.edge_id AND a.conversation_id = b.conversation_id "
                    "AND a.source_note_id = b.source_note_id AND a.target_note_id = b.target_note_id "
                    "AND a.relation = b.relation"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE obsidian_edges ADD CONSTRAINT uq_obsidian_edge_conv_src_tgt_rel "
                    "UNIQUE (conversation_id, source_note_id, target_note_id, relation)"
                )
            )


AVAILABLE_TOOLS = [
    {"name": "skill_playbook", "label": "Skill Playbook", "scope": "reasoning"},
    {"name": "planning", "label": "Planning", "scope": "reasoning"},
    {"name": "codebase_overview", "label": "Codebase Overview", "scope": "code"},
    {"name": "glob", "label": "Glob Search", "scope": "code"},
    {"name": "grep", "label": "Grep Search", "scope": "code"},
    {"name": "read_files", "label": "Read Files", "scope": "code"},
    {"name": "python_execute", "label": "Python", "scope": "terminal"},
    {"name": "bash", "label": "Bash", "scope": "terminal"},
    {"name": "browser_use", "label": "Browser", "scope": "browser"},
    {"name": "web_search", "label": "Web Search", "scope": "browser"},
    {"name": "apply_patch_editor", "label": "Patch Editor", "scope": "code"},
    {"name": "memory_save", "label": "Memory Save", "scope": "memory"},
    {"name": "memory_recall", "label": "Memory Recall", "scope": "memory"},
    {"name": "ask_human", "label": "Ask Human", "scope": "conversation"},
    {"name": "wait_for_user_input", "label": "Wait For Input", "scope": "conversation"},
    {"name": "terminate", "label": "Terminate", "scope": "control", "locked": True},
]

CONVERSATION_STATES = {
    "CREATED": "running",
    "RUNNING": "running",
    "COMPLETED": "finished",
    "FAILED": "error",
    "INTERRUPTED": "paused",
}


_ensure_schema_updates()


TERMINAL_STATUSES = {"COMPLETED", "FAILED", "INTERRUPTED"}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


def _session_token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def _public_user(user: UserORM) -> dict:
    return {
        "id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def _require_admin(request: Request) -> UserORM:
    user = _require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _require_user(request: Request) -> UserORM:
    token = _session_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    with registry.SessionLocal() as session:
        session_orm = session.get(SessionORM, token)
        if session_orm is None or session_orm.expires_at <= _now():
            raise HTTPException(status_code=401, detail="Session expired")
        user = session.get(UserORM, session_orm.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        session.expunge(user)
        return user


def _create_session(response: Response, user_id: uuid.UUID) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=SESSION_DAYS)
    with registry.SessionLocal() as session:
        session.add(SessionORM(token=token, user_id=user_id, expires_at=expires_at))
        session.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return token


def _conversation_to_dict(session, conversation: ConversationORM) -> dict:
    from sqlalchemy import desc

    latest_task = (
        session.query(TaskORM)
        .filter(
            TaskORM.input["conversation_id"].astext == str(conversation.conversation_id)
        )
        .order_by(desc(TaskORM.created_at))
        .first()
    )
    latest_status = latest_task.status if latest_task else None
    settings = conversation.settings or {}
    requested_context_window = settings.get("requested_context_window")
    auto_context_compress = settings.get("auto_context_compress", True)
    if requested_context_window not in (None, ""):
        try:
            requested_context_window = int(requested_context_window)
        except (TypeError, ValueError):
            requested_context_window = None
    current_input = 0
    if latest_task is not None:
        latest_token_event = (
            session.query(ConversationEventORM)
            .filter(
                ConversationEventORM.task_id == latest_task.task_id,
                ConversationEventORM.event_type == "token_count",
            )
            .order_by(desc(ConversationEventORM.created_at))
            .first()
        )
        if latest_token_event is not None:
            payload = latest_token_event.payload or {}
            current_input = payload.get("total_input") or payload.get("input") or 0
            try:
                current_input = int(current_input)
            except (TypeError, ValueError):
                current_input = 0
    ratio = (
        round(current_input / requested_context_window, 4)
        if requested_context_window and requested_context_window > 0
        else None
    )
    # Effective context window loaded for the current conversation model.
    # Priority:
    # 0) persisted LM Studio load result in conversation settings
    # 1) admin llm_connection.max_input_tokens when model matches or no explicit model is set
    # 2) configured model entry max_input_tokens
    # 3) configured default max_input_tokens
    received_context_window = None
    try:
        persisted_received = settings.get("received_context_window")
        if persisted_received not in (None, ""):
            received_context_window = int(persisted_received)

        selected_model = str(conversation.model or "").strip() or None
        connection = _get_app_setting(session, "llm_connection", {})
        if isinstance(connection, dict):
            conn_model = str(connection.get("model") or "").strip() or None
            conn_window = connection.get("max_input_tokens")
            if conn_window not in (None, "") and (
                selected_model is None or selected_model == conn_model
            ):
                received_context_window = int(conn_window)

        if (
            received_context_window in (None, 0)
            and selected_model
            and isinstance(config.llm, dict)
        ):
            for llm_settings in config.llm.values():
                if getattr(llm_settings, "model", None) == selected_model:
                    value = getattr(llm_settings, "max_input_tokens", None)
                    if value not in (None, 0):
                        received_context_window = int(value)
                        break

        if received_context_window in (None, 0):
            default_llm = (
                config.llm.get("default") if isinstance(config.llm, dict) else None
            )
            value = (
                getattr(default_llm, "max_input_tokens", None) if default_llm else None
            )
            if value not in (None, 0):
                received_context_window = int(value)
    except Exception:
        received_context_window = None

    latest_context = {
        "requested_window": requested_context_window,
        "received_window": received_context_window,
        "received_window_source": settings.get("received_context_window_source")
        or ("fallback_inferred" if received_context_window else None),
        "current_input_tokens": current_input,
        "usage_ratio": ratio,
        "is_near_limit": bool(ratio is not None and ratio >= 0.9),
        "auto_context_compress": bool(auto_context_compress),
    }
    return {
        "id": str(conversation.conversation_id),
        "conversation_id": str(conversation.conversation_id),
        "title": conversation.title,
        "model": conversation.model,
        "settings": settings,
        "context": latest_context,
        "latest_task_id": str(latest_task.task_id) if latest_task else None,
        "latest_status": latest_status,
        "state": CONVERSATION_STATES.get(str(latest_status or ""), "idle"),
        "updated_at": conversation.updated_at.isoformat()
        if conversation.updated_at
        else None,
        "created_at": conversation.created_at.isoformat()
        if conversation.created_at
        else None,
    }


def _task_to_dict(orm: TaskORM) -> dict:
    status = str(orm.status)
    return {
        "id": str(orm.task_id),
        "task_id": str(orm.task_id),
        "status": status,
        "state": CONVERSATION_STATES.get(status, "idle"),
        "result": orm.result,
        "conversation_id": _conversation_id_for(orm),
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
        "request": (orm.input or {}).get("prompt", "Untitled task"),
    }


def _persist_conversation_event(
    session,
    conversation_id: str,
    event_type: str,
    payload: dict,
    task_id: Optional[str] = None,
) -> ConversationEventORM:
    try:
        cid = uuid.UUID(str(conversation_id))
        tid = uuid.UUID(str(task_id)) if task_id else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event id") from exc
    event = ConversationEventORM(
        conversation_id=cid,
        task_id=tid,
        event_type=event_type,
        payload=payload,
    )
    session.add(event)
    session.flush()
    return event


def _conversation_tasks(
    session, conversation_id: str, ascending: bool = True
) -> list[TaskORM]:
    from sqlalchemy import asc, desc

    order = asc(TaskORM.created_at) if ascending else desc(TaskORM.created_at)
    return (
        session.query(TaskORM)
        .filter(TaskORM.input["conversation_id"].astext == str(conversation_id))
        .order_by(order)
        .all()
    )


def _conversation_sandbox(conversation_id: str) -> ConversationSandbox:
    return ConversationSandbox(
        conversation_id=conversation_id,
        host_workspace=Path(HOST_WORKSPACE_ROOT) / "conversations" / conversation_id,
        config=config.sandbox,
    )


def _obsidian_health(session, conversation_id: Optional[str] = None) -> dict:
    payload = {
        "enabled": True,
        "available": True,
        "live": False,
        "reason": "No notes found yet",
        "note_count": 0,
    }
    try:
        query = session.query(func.count(ObsidianNoteORM.note_id))
        if conversation_id:
            query = query.filter(
                ObsidianNoteORM.conversation_id == uuid.UUID(str(conversation_id))
            )
        count = int(query.scalar() or 0)
        payload["note_count"] = count
        if count > 0:
            payload["live"] = True
            payload["reason"] = "Notes indexed"
    except Exception as exc:
        payload["available"] = False
        payload["live"] = False
        payload["reason"] = f"DB error: {exc}"
    return payload


def _agentmemory_health(conversation_id: Optional[str] = None) -> dict:
    vec_health = agentmemory.get_vector_health()
    payload = {
        "enabled": bool(config.agentmemory.enabled),
        "available": False,
        "live": False,
        "reason": "Disabled",
        "base_url": "local_sqlite",
        "project": config.agentmemory.project,
        **vec_health,
    }
    if not config.agentmemory.enabled:
        return payload

    try:
        # Check SQLite DB health by attempting to connect and query
        with agentmemory._get_conn() as conn:
            conn.execute("SELECT 1 FROM memories LIMIT 1")
        payload["available"] = True
        payload["live"] = True
        payload["reason"] = "Live (Local SQLite FTS5)"
    except Exception as exc:
        payload["available"] = False
        payload["live"] = False
        payload["reason"] = f"SQLite failed: {exc}"

    if payload["live"] and conversation_id:
        # Optional lightweight probe for conversation-specific recall viability.
        try:
            hits = agentmemory.search(
                conversation_id=conversation_id, query="summary", limit=1
            )
            payload["conversation_hits"] = len(hits)
        except Exception:
            payload["conversation_hits"] = 0

    payload.update(agentmemory.get_vector_health())
    return payload


def _llm_connection_health(session) -> dict:
    connection = _effective_llm_connection(session)
    payload = {
        "configured": bool(connection),
        "live": False,
        "reason": "Not configured",
        "api_type": str(connection.get("api_type") or ""),
        "base_url": str(connection.get("base_url") or ""),
    }
    base_url = str(connection.get("base_url") or "").strip()
    if not base_url:
        return payload
    api_type = str(connection.get("api_type") or "").strip().lower()
    token = str(connection.get("api_key") or "").strip() or None
    try:
        if api_type in {"lmstudio", "local"}:
            native = _lmstudio_native_base(base_url)
            if not native:
                payload["reason"] = "Invalid LM Studio URL"
                return payload
            data = _http_json("GET", f"{native}/models", token=token)
        else:
            models_url = (
                base_url.rstrip("/") + "/models"
                if base_url.rstrip("/").endswith("/v1")
                else base_url.rstrip("/") + "/v1/models"
            )
            data = _http_json("GET", models_url, token=token)
        rows = _extract_model_rows(data)
        payload["live"] = True
        payload["reason"] = f"OK ({len(rows)} models)"
        payload["model_count"] = len(rows)
        return payload
    except Exception as exc:
        payload["live"] = False
        payload["reason"] = str(exc)
        return payload


def _prune_orphan_conversation_sandboxes(session) -> int:
    """Remove sandbox containers whose conversation row no longer exists."""
    try:
        import docker

        active_ids = {
            str(row[0]) for row in session.query(ConversationORM.conversation_id).all()
        }
        client = docker.from_env()
        removed = 0
        for container in client.containers.list(
            all=True, filters={"label": "openmanus.kind=conversation-sandbox"}
        ):
            conversation_id = container.labels.get("openmanus.conversation_id")
            if conversation_id and conversation_id not in active_ids:
                container.remove(force=True)
                removed += 1
        return removed
    except Exception:
        return 0


def _ensure_default_conversation(session, user_id: uuid.UUID) -> ConversationORM:
    from sqlalchemy import asc

    conversation = (
        session.query(ConversationORM)
        .filter(ConversationORM.user_id == user_id)
        .order_by(asc(ConversationORM.created_at))
        .first()
    )
    if conversation is not None:
        return conversation
    conversation = ConversationORM(user_id=user_id, title="New conversation")
    session.add(conversation)
    session.flush()
    return conversation


def _get_app_setting(session, key: str, default: Any) -> Any:
    setting = session.get(AppSettingORM, key)
    if setting is None:
        return default
    return setting.value


def _set_app_setting(session, key: str, value: Any) -> None:
    setting = session.get(AppSettingORM, key)
    if setting is None:
        session.add(AppSettingORM(key=key, value=value))
    else:
        setting.value = value


def _redact_config(value: Any) -> Any:
    secret_key_names = {
        "api_key",
        "apikey",
        "password",
        "secret",
        "access_token",
        "refresh_token",
        "bearer_token",
        "authorization",
        "auth_token",
    }
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in secret_key_names or lowered.endswith("_api_key"):
                redacted[key] = "********" if item else item
            else:
                redacted[key] = _redact_config(item)
        return redacted
    if isinstance(value, list):
        return [_redact_config(item) for item in value]
    return value


def _loaded_config_defaults() -> dict:
    data = config._config.model_dump(mode="json")
    data["server"] = {
        "database_url": os.getenv("DATABASE_URL", ""),
        "redis_url": REDIS_URL,
        "workspace_root": WORKSPACE_ROOT,
        "single_conversation": os.getenv("OPENMANUS_SINGLE_CONVERSATION", "false"),
        "default_conversation_id": DEFAULT_CONVERSATION_ID,
        "session_days": SESSION_DAYS,
    }
    return _redact_config(data)


def _default_llm_connection() -> dict:
    default = config.llm.get("default")
    if default is None:
        return {}
    return _redact_config(default.model_dump(mode="json"))


def _effective_llm_connection(session) -> dict:
    override = _get_app_setting(session, "llm_connection", {})
    if isinstance(override, dict) and override.get("base_url"):
        return override
    default = config.llm.get("default")
    return default.model_dump(mode="json") if default is not None else {}


def _lmstudio_native_base(base_url: str) -> Optional[str]:
    try:
        parsed = urlparse.urlparse(base_url.strip())
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
    timeout: int = 8,
) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, method=method, headers=headers, data=body)
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if not data:
            return {}
        return json.loads(data.decode("utf-8"))


def _extract_model_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    data_rows = payload.get("data")
    if isinstance(data_rows, list):
        return [item for item in data_rows if isinstance(item, dict)]
    model_rows = payload.get("models")
    if isinstance(model_rows, list):
        return [item for item in model_rows if isinstance(item, dict)]
    return []


def _model_id_from_row(item: dict) -> str:
    return str(
        item.get("id")
        or item.get("key")
        or item.get("model")
        or item.get("name")
        or item.get("instance_id")
        or ""
    ).strip()


def _model_instance_id_from_row(item: dict) -> str:
    loaded_instances = item.get("loaded_instances")
    if isinstance(loaded_instances, list) and loaded_instances:
        first = loaded_instances[0]
        if isinstance(first, dict):
            instance_id = str(first.get("id") or "").strip()
            if instance_id:
                return instance_id
    return str(item.get("instance_id") or "").strip()


def _model_state_from_row(item: dict) -> str:
    state = str(item.get("state") or "").strip().lower()
    if state:
        return state
    loaded_instances = item.get("loaded_instances")
    if isinstance(loaded_instances, list):
        return "loaded" if len(loaded_instances) > 0 else "not-loaded"
    return ""


def _model_variant_tag_from_row(item: dict) -> str:
    quant = item.get("quantization")
    if isinstance(quant, dict):
        name = str(quant.get("name") or "").strip()
        if name:
            return name
    params = str(item.get("params_string") or "").strip()
    if params:
        return params
    fmt = str(item.get("format") or "").strip()
    if fmt:
        return fmt
    return ""


def _require_conversation(
    session, user_id: uuid.UUID, conversation_id: str
) -> ConversationORM:
    try:
        cid = uuid.UUID(str(conversation_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation id")
    conversation = session.get(ConversationORM, cid)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _task_belongs_to_user(session, orm: TaskORM, user_id: uuid.UUID) -> bool:
    conversation_id = (orm.input or {}).get("conversation_id")
    if not conversation_id:
        return False
    try:
        conversation = session.get(ConversationORM, uuid.UUID(str(conversation_id)))
    except ValueError:
        return False
    return conversation is not None and conversation.user_id == user_id


def _extract_wikilinks(content: str) -> list[str]:
    if not content:
        return []
    out: list[str] = []
    for match in WIKILINK_RE.findall(content):
        normalized = str(match).strip()
        if normalized:
            out.append(normalized)
    return out


def _obsidian_graph_payload(session, conversation: ConversationORM) -> dict:
    notes = (
        session.query(ObsidianNoteORM)
        .filter(ObsidianNoteORM.conversation_id == conversation.conversation_id)
        .all()
    )
    edges = (
        session.query(ObsidianEdgeORM)
        .filter(ObsidianEdgeORM.conversation_id == conversation.conversation_id)
        .all()
    )
    node_payload = [
        {
            "id": str(note.note_id),
            "path": note.path,
            "title": note.title,
            "tags": note.tags or [],
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }
        for note in notes
    ]
    edge_payload = [
        {
            "id": str(edge.edge_id),
            "source": str(edge.source_note_id),
            "target": str(edge.target_note_id),
            "relation": edge.relation,
        }
        for edge in edges
    ]
    return {
        "nodes": node_payload,
        "edges": edge_payload,
        "node_count": len(node_payload),
        "edge_count": len(edge_payload),
    }


def _agent_event_to_progress(event: dict) -> list[dict]:
    """
    Convert one internal agent event into one or more SSE progress messages
    that match the frontend's lifecycle type hierarchy.

    Internal types → frontend lifecycle names:
      step_start     → [agent:lifecycle:start (once)] + agent:lifecycle:step:start
                        + agent:lifecycle:step:think:start
      thought        → agent:lifecycle:step:think:tool:selected
                        + agent:lifecycle:step:think:complete
                        + agent:lifecycle:step:act:start
      tool_result    → agent:lifecycle:step:act:tool:execute:complete
                        + agent:lifecycle:step:act:complete
                        + agent:lifecycle:step:complete
      finish_signal  → agent:lifecycle:complete
      final_response  → agent:lifecycle:complete
      terminated     → agent:lifecycle:terminated
      browser_screenshot → agent:lifecycle:step:think:browser:browse:complete
      token_count    → agent:lifecycle:step:think:token:count
      context_compressed → agent:lifecycle:step:think:context:compressed
      terminal_output → agent:lifecycle:step:act:tool:terminal:output
      workspace_file_updated → agent:lifecycle:step:act:tool:file:updated
      error          → agent:lifecycle:step:error
    """
    agent_type = event.get("type", "")
    data = event.get("data", {})

    def _msg(name: str, content=None) -> dict:
        return {"type": "progress", "name": name, "content": content or data}

    if agent_type == "step_start":
        step = data.get("step", 1)
        msgs = []
        if step == 1:
            msgs.append(_msg("agent:lifecycle:start", {"step": step}))
        msgs.append(_msg("agent:lifecycle:step:start", data))
        msgs.append(_msg("agent:lifecycle:step:think:start", data))
        return msgs

    if agent_type == "thought":
        tools = data.get("tools", [])
        tool_calls = data.get("tool_calls", [])
        msgs = [
            _msg(
                "agent:lifecycle:step:think:tool:selected",
                {
                    "tool": (
                        (tool_calls[0].get("function", {}) or {}).get("name")
                        if tool_calls
                        else (tools[0] if tools else None)
                    ),
                    "tool_calls": tool_calls,
                    "content": data.get("content", ""),
                },
            )
        ]
        msgs.append(_msg("agent:lifecycle:step:think:complete", data))
        if tools or tool_calls:
            msgs.append(_msg("agent:lifecycle:step:act:start", data))
            if tool_calls:
                for call in tool_calls:
                    fn = call.get("function", {}) or {}
                    call_id = call.get("id") or fn.get("name")
                    call_name = fn.get("name")
                    call_args = fn.get("arguments")
                    msgs.append(
                        _msg(
                            "agent:lifecycle:step:act:tool:start",
                            {
                                "id": call_id,
                                "name": call_name,
                            },
                        )
                    )
                    msgs.append(
                        _msg(
                            "agent:lifecycle:step:act:tool:execute:start",
                            {
                                "id": call_id,
                                "name": call_name,
                                "arguments": call_args,
                            },
                        )
                    )
            else:
                first_id = tools[0] if tools else None
                first_name = tools[0] if tools else None
                msgs.append(
                    _msg(
                        "agent:lifecycle:step:act:tool:start",
                        {
                            "id": first_id,
                            "name": first_name,
                        },
                    )
                )
                msgs.append(
                    _msg(
                        "agent:lifecycle:step:act:tool:execute:start",
                        {
                            "id": first_id,
                            "name": first_name,
                            "arguments": data.get("arguments"),
                        },
                    )
                )
        return msgs

    if agent_type == "tool_result":
        tool = data.get("tool", "")
        tool_call_id = data.get("tool_call_id") or tool
        msgs = [
            _msg(
                "agent:lifecycle:step:act:tool:execute:complete",
                {
                    "id": tool_call_id,
                    "name": tool,
                    "result": data.get("result", ""),
                },
            )
        ]
        msgs.append(
            _msg(
                "agent:lifecycle:step:act:tool:complete",
                {"id": tool_call_id, "name": tool},
            )
        )
        msgs.append(_msg("agent:lifecycle:step:act:complete", data))
        msgs.append(_msg("agent:lifecycle:step:complete", data))
        return msgs

    if agent_type == "step_result":
        # Secondary step completion — already handled via tool_result path; skip
        return []

    if agent_type == "finish_signal":
        # Only map the final completion from tasks.py (which contains 'workspace')
        # to avoid duplicating the final message that is already shown in the 'thought' bubble.
        if "workspace" in data:
            return [_msg("agent:lifecycle:complete", data)]
        return []

    if agent_type == "final_response":
        # Ignore since the assistant text is already in the 'thought' event,
        # and tasks.py will emit a final finish_signal anyway.
        return []

    if agent_type == "browser_screenshot":
        return [_msg("agent:lifecycle:step:think:browser:browse:complete", data)]

    if agent_type == "token_count":
        return [_msg("agent:lifecycle:step:think:token:count", data)]

    if agent_type == "context_compressed":
        return [_msg("agent:lifecycle:step:think:context:compressed", data)]

    if agent_type == "terminal_output":
        return [_msg("agent:lifecycle:step:act:tool:terminal:output", data)]

    if agent_type == "workspace_file_updated":
        return [_msg("agent:lifecycle:step:act:tool:file:updated", data)]

    if agent_type == "terminated":
        return [_msg("agent:lifecycle:terminated", data)]

    if agent_type == "agent_state":
        return [_msg("agent:lifecycle:state:change", data)]

    if agent_type == "stuck_detected":
        return [_msg("agent:lifecycle:state:change", data)]

    if agent_type == "error":
        msgs = [_msg("agent:lifecycle:step:error", data)]
        if data.get("fatal", True):
            msgs.append(
                _msg(
                    "agent:lifecycle:terminated",
                    {
                        **data,
                        "reason": data.get("detail")
                        or data.get("message")
                        or "Task failed",
                        "status": "failure",
                    },
                )
            )
        return msgs

    # Catch-all: pass through as a generic step event
    return [_msg(f"agent:lifecycle:{agent_type}", data)]


def _task_input(
    prompt: Optional[str],
    conversation_id: str,
    parent_task_id: Optional[str] = None,
    model: Optional[str] = None,
    disabled_tools: Optional[list[str]] = None,
    requested_context_window: Optional[int] = None,
    auto_context_compress: Optional[bool] = None,
    disabled_skills: Optional[list[str]] = None,
    enable_vendor_skills: Optional[bool] = None,
    pinned_skills: Optional[list[str]] = None,
    identity_notes: Optional[str] = None,
) -> dict:
    data = {"conversation_id": conversation_id}
    if prompt:
        data["prompt"] = prompt
    if parent_task_id:
        data["parent_task_id"] = parent_task_id
    if model:
        data["model"] = model
    if disabled_tools:
        data["disabled_tools"] = disabled_tools
    if requested_context_window and requested_context_window > 0:
        data["requested_context_window"] = int(requested_context_window)
    if auto_context_compress is not None:
        data["auto_context_compress"] = bool(auto_context_compress)
    if disabled_skills:
        data["disabled_skills"] = [
            str(name) for name in disabled_skills if str(name).strip()
        ]
    if enable_vendor_skills is not None:
        data["enable_vendor_skills"] = bool(enable_vendor_skills)
    if pinned_skills:
        data["pinned_skills"] = [
            str(name).strip() for name in pinned_skills if str(name).strip()
        ]
    if identity_notes:
        data["identity_notes"] = str(identity_notes).strip()
    return data


def _conversation_id_for(orm: TaskORM) -> str:
    task_input = orm.input or {}
    if task_input.get("conversation_id"):
        return str(task_input.get("conversation_id"))
    if os.getenv("OPENMANUS_SINGLE_CONVERSATION", "true").lower() != "false":
        return DEFAULT_CONVERSATION_ID
    return str(task_input.get("conversation_id") or DEFAULT_CONVERSATION_ID)


# ---------------------------------------------------------------------------
# Auth and conversations
# ---------------------------------------------------------------------------


@app.post("/api/auth/signup")
async def signup(request: Request, response: Response):
    body = await request.json()
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    name = str(body.get("name") or email.split("@")[0] or "User").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    with registry.SessionLocal() as session:
        existing = session.query(UserORM).filter(UserORM.email == email).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email is already registered")
        user_count = session.query(UserORM).count()
        role = "admin" if user_count == 0 else "user"
        user = UserORM(
            email=email,
            name=name,
            password_hash=_hash_password(password),
            role=role,
        )
        session.add(user)
        session.flush()
        _ensure_default_conversation(session, user.user_id)
        session.commit()
        public = _public_user(user)
        user_id = user.user_id
    token = _create_session(response, user_id)
    return {"user": public, "token": token}


@app.post("/api/auth/login")
async def login(request: Request, response: Response):
    body = await request.json()
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    with registry.SessionLocal() as session:
        user = session.query(UserORM).filter(UserORM.email == email).first()
        if user is None or not _verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        public = _public_user(user)
        user_id = user.user_id
    token = _create_session(response, user_id)
    return {"user": public, "token": token}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = _session_token_from_request(request)
    if token:
        with registry.SessionLocal() as session:
            session_orm = session.get(SessionORM, token)
            if session_orm is not None:
                session.delete(session_orm)
                session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(request: Request):
    user = _require_user(request)
    return {"user": _public_user(user)}


@app.get("/api/models")
async def list_models(request: Request):
    _require_user(request)
    with registry.SessionLocal() as session:
        connection = _effective_llm_connection(session)

    configured = [
        {
            "id": settings.model,
            "name": name,
            "api_type": settings.api_type,
            "base_model": settings.model,
            "variant_tag": "",
            "raw_model_key": settings.model,
        }
        for name, settings in config.llm.items()
        if settings.model
    ]
    if isinstance(connection, dict) and connection.get("model"):
        configured.insert(
            0,
            {
                "id": connection["model"],
                "name": "admin",
                "api_type": connection.get("api_type", "openai"),
                "base_model": connection["model"],
                "variant_tag": "",
                "raw_model_key": connection["model"],
            },
        )
    models = configured

    # Enrich with live LM Studio model variants when connected.
    try:
        base_url = str(connection.get("base_url") or "")
        api_type = str(connection.get("api_type") or "").lower()
        api_key = str(connection.get("api_key") or "")
        native_base = _lmstudio_native_base(base_url)
        if native_base and (
            api_type in {"openai", "lmstudio", "local"}
            or "1234" in base_url
            or "lmstudio" in base_url.lower()
        ):
            listing = _http_json("GET", f"{native_base}/models", token=api_key or None)
            lm_models = listing.get("data") if isinstance(listing, dict) else []
            if isinstance(lm_models, list):
                for item in lm_models:
                    if not isinstance(item, dict):
                        continue
                    model_id = _model_id_from_row(item)
                    if not model_id:
                        continue
                    models.insert(
                        0,
                        {
                            "id": model_id,
                            "name": item.get("display_name")
                            or item.get("path")
                            or item.get("name")
                            or "lmstudio",
                            "api_type": "lmstudio",
                            "state": _model_state_from_row(item),
                            "instance_id": _model_instance_id_from_row(item),
                            "base_model": str(item.get("key") or model_id),
                            "variant_tag": _model_variant_tag_from_row(item),
                            "raw_model_key": str(item.get("key") or model_id),
                        },
                    )
    except Exception:
        # Keep model listing resilient if LM Studio native API is unavailable.
        pass

    seen = set()
    unique_models = []
    for model in models:
        if model["id"] in seen:
            continue
        seen.add(model["id"])
        unique_models.append(model)
    return {"models": unique_models}


@app.post("/api/models/query")
async def query_models(request: Request):
    _require_user(request)
    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    host = str((body or {}).get("host") or "").strip()
    api_key = str((body or {}).get("api_key") or "").strip() or None
    style = str((body or {}).get("style") or "custom").strip().lower()
    models_path = str((body or {}).get("models_path") or "").strip()

    if not host:
        raise HTTPException(status_code=400, detail="Host is required")

    models: list[dict] = []
    url = ""
    try:
        if style == "lm-studio":
            native = _lmstudio_native_base(host)
            if not native:
                raise HTTPException(
                    status_code=400, detail="Invalid LM Studio host URL"
                )
            url = f"{native}/models"
            data = _http_json("GET", url, token=api_key, timeout=8)
            rows = _extract_model_rows(data)
            for item in rows:
                if not isinstance(item, dict):
                    continue
                model_id = _model_id_from_row(item)
                if not model_id:
                    continue
                models.append(
                    {
                        "id": model_id,
                        "name": item.get("display_name")
                        or item.get("path")
                        or item.get("name")
                        or model_id,
                        "api_type": "lmstudio",
                        "state": _model_state_from_row(item),
                        "instance_id": _model_instance_id_from_row(item),
                        "base_model": str(item.get("key") or model_id),
                        "variant_tag": _model_variant_tag_from_row(item),
                        "raw_model_key": str(item.get("key") or model_id),
                    }
                )
        elif style == "ollama":
            # Prefer OpenAI-compatible endpoint, fallback to Ollama native tags endpoint.
            url = host.rstrip("/") + "/v1/models"
            try:
                data = _http_json("GET", url, token=api_key, timeout=8)
                rows = _extract_model_rows(data)
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    model_id = _model_id_from_row(item)
                    if model_id:
                        models.append(
                            {
                                "id": model_id,
                                "name": model_id,
                                "api_type": "ollama",
                                "base_model": model_id,
                                "variant_tag": "",
                                "raw_model_key": model_id,
                            }
                        )
            except Exception:
                url = host.rstrip("/") + "/api/tags"
                data = _http_json("GET", url, token=api_key, timeout=8)
                rows = _extract_model_rows(data)
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    model_id = _model_id_from_row(item)
                    if model_id:
                        models.append(
                            {
                                "id": model_id,
                                "name": model_id,
                                "api_type": "ollama",
                                "base_model": model_id,
                                "variant_tag": "",
                                "raw_model_key": model_id,
                            }
                        )
        else:
            if style == "openai":
                suffix = "/v1/models"
            else:
                suffix = models_path or "/v1/models"
                if not suffix.startswith("/"):
                    suffix = "/" + suffix
            url = host.rstrip("/") + suffix
            data = _http_json("GET", url, token=api_key, timeout=8)
            rows = _extract_model_rows(data)
            for item in rows:
                if not isinstance(item, dict):
                    continue
                model_id = _model_id_from_row(item)
                if model_id:
                    models.append(
                        {
                            "id": model_id,
                            "name": model_id,
                            "api_type": style or "custom",
                            "base_model": model_id,
                            "variant_tag": "",
                            "raw_model_key": model_id,
                        }
                    )

        seen: set[str] = set()
        unique_models: list[dict] = []
        for model in models:
            model_id = str(model.get("id") or "")
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            unique_models.append(model)
        return {"models": unique_models, "url": url}
    except HTTPException:
        raise
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=exc.code, detail=detail or f"HTTP {exc.code}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model query failed: {exc}")


@app.post("/api/models/load")
async def load_model(request: Request):
    _require_user(request)
    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    host = str((body or {}).get("host") or "").strip()
    api_key = str((body or {}).get("api_key") or "").strip() or None
    style = str((body or {}).get("style") or "custom").strip().lower()
    model = str((body or {}).get("model") or "").strip()
    context_length_raw = (body or {}).get("context_length")

    if not host:
        raise HTTPException(status_code=400, detail="Host is required")
    if not model:
        raise HTTPException(status_code=400, detail="Model is required")
    if style != "lm-studio":
        raise HTTPException(
            status_code=400,
            detail="Load model is currently supported for LM Studio profiles only",
        )

    native = _lmstudio_native_base(host)
    if not native:
        raise HTTPException(status_code=400, detail="Invalid LM Studio host URL")

    payload: dict[str, Any] = {"model": model, "echo_load_config": True}
    if context_length_raw not in (None, ""):
        try:
            context_length = int(context_length_raw)
            if context_length > 0:
                payload["context_length"] = context_length
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400, detail="context_length must be a positive integer"
            )

    try:
        data = _http_json(
            "POST",
            f"{native}/models/load",
            payload=payload,
            token=api_key,
            timeout=30,
        )
        return {"ok": True, "result": data}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=exc.code, detail=detail or f"HTTP {exc.code}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Load model failed: {exc}")


@app.post("/api/models/eject")
async def eject_model(request: Request):
    _require_user(request)
    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    requested_model = str((body or {}).get("model") or "").strip()

    with registry.SessionLocal() as session:
        connection = _effective_llm_connection(session)

    base_url = str(connection.get("base_url") or "")
    api_type = str(connection.get("api_type") or "").lower()
    api_key = str(connection.get("api_key") or "")

    native_base = _lmstudio_native_base(base_url)
    if not native_base:
        raise HTTPException(status_code=400, detail="LLM base_url is not configured")
    if api_type not in {"openai", "lmstudio", "local"} and "1234" not in base_url:
        raise HTTPException(
            status_code=400, detail="Eject is only supported for LM Studio connections"
        )

    try:
        listing = _http_json("GET", f"{native_base}/models", token=api_key)
        models = listing.get("data") if isinstance(listing, dict) else []
        if not isinstance(models, list):
            models = []

        target_instance_id = requested_model
        if not target_instance_id:
            loaded = [
                m for m in models if isinstance(m, dict) and m.get("state") == "loaded"
            ]
            if len(loaded) == 1:
                target_instance_id = str(
                    loaded[0].get("id") or loaded[0].get("instance_id") or ""
                )
            elif len(loaded) > 1:
                raise HTTPException(
                    status_code=409,
                    detail="Multiple models are loaded. Specify model id.",
                )

        if not target_instance_id:
            raise HTTPException(
                status_code=404, detail="No loaded model found to eject"
            )

        instance_id = target_instance_id
        exact = next(
            (
                m
                for m in models
                if isinstance(m, dict) and str(m.get("id") or "") == target_instance_id
            ),
            None,
        )
        if exact:
            instance_id = str(
                exact.get("instance_id") or exact.get("id") or target_instance_id
            )

        unloaded = _http_json(
            "POST",
            f"{native_base}/models/unload",
            payload={"instance_id": instance_id},
            token=api_key,
        )
        return {
            "ok": True,
            "requested_model": requested_model or instance_id,
            "instance_id": unloaded.get("instance_id", instance_id)
            if isinstance(unloaded, dict)
            else instance_id,
        }
    except HTTPException:
        raise
    except urlerror.HTTPError as exc:
        detail_raw = exc.read().decode("utf-8", errors="ignore")
        # Idempotent behavior: unloading an already-unloaded model should not fail UX.
        try:
            parsed = json.loads(detail_raw) if detail_raw else {}
            err = parsed.get("error") if isinstance(parsed, dict) else None
            err_type = str((err or {}).get("type") or "")
            if err_type == "model_not_found":
                return {
                    "ok": True,
                    "requested_model": requested_model or "",
                    "instance_id": requested_model or "",
                    "already_unloaded": True,
                }
        except Exception:
            pass
        raise HTTPException(
            status_code=exc.code, detail=detail_raw or "LM Studio eject failed"
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio eject failed: {exc}")


@app.post("/api/connection/verify")
@app.post("/connection/verify")
async def verify_connection(request: Request):
    _require_user(request)
    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    host = str((body or {}).get("host") or "").strip()
    api_key = str((body or {}).get("api_key") or "").strip() or None
    style = str((body or {}).get("style") or "custom").strip().lower()
    models_path = str((body or {}).get("models_path") or "").strip()

    if not host:
        raise HTTPException(status_code=400, detail="Host is required")

    # Build URL from host + style/path
    if style == "lm-studio":
        native = _lmstudio_native_base(host)
        if not native:
            raise HTTPException(status_code=400, detail="Invalid LM Studio host URL")
        url = f"{native}/models"
    elif style in {"openai", "ollama"}:
        suffix = "/v1/models"
        url = host.rstrip("/") + suffix
    else:
        suffix = models_path or "/v1/models"
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        url = host.rstrip("/") + suffix

    try:
        data = _http_json("GET", url, token=api_key, timeout=8)
        count = len(_extract_model_rows(data))
        return {"ok": True, "url": url, "models_count": count}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=exc.code, detail=detail or f"HTTP {exc.code}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connection verify failed: {exc}")


@app.get("/api/tools")
async def list_tools(request: Request):
    _require_user(request)
    with registry.SessionLocal() as session:
        global_tools = _get_app_setting(session, "tools", {})
    disabled = (
        set(global_tools.get("disabled", []))
        if isinstance(global_tools, dict)
        else set()
    )
    return {
        "tools": [
            {**tool, "enabled": tool["name"] not in disabled}
            for tool in AVAILABLE_TOOLS
        ]
    }


@app.get("/api/skills")
async def list_skills(
    request: Request,
    conversation_id: Optional[str] = None,
    prompt: Optional[str] = None,
):
    user = _require_user(request)
    workspace = None
    include_vendor = True
    disabled_skills: set[str] = set()
    if conversation_id:
        with registry.SessionLocal() as session:
            conversation = _require_conversation(session, user.user_id, conversation_id)
            settings = conversation.settings or {}
            include_vendor = bool(settings.get("enable_vendor_skills", True))
            disabled_skills = {
                str(name)
                for name in (settings.get("disabled_skills") or [])
                if str(name).strip()
            }
        workspace = Path(WORKSPACE_ROOT) / "conversations" / conversation_id
    skills = (
        select_skills(
            prompt or "",
            workspace,
            include_vendor=include_vendor,
            disabled_skills=disabled_skills,
        )
        if prompt
        else load_skills(
            workspace,
            include_vendor=include_vendor,
            disabled_skills=set(),
        )
    )
    output = []
    for skill in skills:
        item = skill.summary()
        item["enabled"] = skill.name not in disabled_skills
        output.append(item)
    return {"skills": output}


async def _task_stream_progress(task: TaskORM) -> list[dict]:
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    stream_key = f"task:{task.task_id}:stream"
    progress_events: list[dict] = []
    try:
        entries = await redis.xrange(stream_key, min="-", max="+")
    finally:
        await redis.aclose()

    prompt = (task.input or {}).get("prompt", "")
    has_emitted_complete = False
    for msg_id, fields in entries:
        event_type = fields.get("type", "")
        try:
            data = json.loads(fields.get("data", "{}"))
        except Exception:
            data = {}

        progress_list = _agent_event_to_progress({"type": event_type, "data": data})
        for progress_index, progress in enumerate(progress_list):
            if progress.get("name") == "agent:lifecycle:start":
                content = dict(progress.get("content") or {})
                content.setdefault("request", prompt)
                content.setdefault("task_id", str(task.task_id))
                content.setdefault("conversation_id", _conversation_id_for(task))
                progress["content"] = content
            else:
                content = dict(progress.get("content") or {})
                content.setdefault("task_id", str(task.task_id))
                content.setdefault("conversation_id", _conversation_id_for(task))
                progress["content"] = content

            # Deduplicate agent:lifecycle:complete events
            is_complete_event = progress.get("name") == "agent:lifecycle:complete"
            if is_complete_event and has_emitted_complete:
                continue
            if is_complete_event:
                has_emitted_complete = True

            progress_events.append(
                {
                    **progress,
                    "id": f"{task.task_id}:{msg_id}:{progress_index}:{progress.get('name')}",
                    "task_id": str(task.task_id),
                    "created_at": task.created_at.isoformat()
                    if task.created_at
                    else None,
                }
            )

    if not progress_events and task.status in TERMINAL_STATUSES:
        progress_events = [
            {
                "id": f"{task.task_id}:synthetic:start",
                "type": "progress",
                "name": "agent:lifecycle:start",
                "task_id": str(task.task_id),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "content": {
                    "request": prompt,
                    "task_id": str(task.task_id),
                    "conversation_id": _conversation_id_for(task),
                },
            },
            {
                "id": f"{task.task_id}:synthetic:complete",
                "type": "progress",
                "name": "agent:lifecycle:complete",
                "task_id": str(task.task_id),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "content": {
                    "message": "Task already completed",
                    "task_id": str(task.task_id),
                    "conversation_id": _conversation_id_for(task),
                },
            },
        ]

    return progress_events


def _event_row_to_progress(
    row: ConversationEventORM, task: Optional[TaskORM] = None
) -> list[dict]:
    task_id = str(row.task_id) if row.task_id else ""
    prompt = (task.input or {}).get("prompt", "") if task is not None else ""
    progress_items = _agent_event_to_progress(
        {"type": row.event_type, "data": row.payload or {}}
    )
    output: list[dict] = []
    for index, progress in enumerate(progress_items):
        content = dict(progress.get("content") or {})
        if task_id:
            content.setdefault("task_id", task_id)
        content.setdefault("conversation_id", str(row.conversation_id))
        if progress.get("name") == "agent:lifecycle:start":
            content.setdefault("request", prompt)
        output.append(
            {
                **progress,
                "id": f"event:{row.event_id}:{index}:{progress.get('name')}",
                "event_id": row.event_id,
                "task_id": task_id or None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "content": content,
            }
        )
    return output


def _truncate_text(value: str, limit: int = 8000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"


def _compact_history_value(value, *, text_limit: int = 8000):
    """Compact oversized event payloads for history endpoint stability."""
    if isinstance(value, str):
        return _truncate_text(value, text_limit)
    if isinstance(value, list):
        return [
            _compact_history_value(item, text_limit=text_limit) for item in value[:200]
        ]
    if isinstance(value, dict):
        compacted = {}
        for key, item in value.items():
            key_s = str(key)
            # Avoid shipping giant inline screenshots in history payloads.
            if key_s in {"screenshot", "base64_image", "image"} and isinstance(
                item, str
            ):
                compacted[key_s] = f"[omitted base64 payload: {len(item)} chars]"
                continue
            compacted[key_s] = _compact_history_value(item, text_limit=text_limit)
        return compacted
    return value


def _compact_history_event(event: dict) -> dict:
    compacted = dict(event)
    compacted["content"] = _compact_history_value(event.get("content") or {})
    return compacted


@app.get("/api/admin/settings")
async def get_admin_settings(request: Request):
    _require_admin(request)
    with registry.SessionLocal() as session:
        llm_connection = _get_app_setting(session, "llm_connection", {})
        return {
            "llm_connection": llm_connection or _default_llm_connection(),
            "llm_connection_override": llm_connection,
            "tools": _get_app_setting(session, "tools", {"disabled": []}),
            "config_defaults": _loaded_config_defaults(),
            "config_overrides": _get_app_setting(session, "config_overrides", {}),
            "available_tools": AVAILABLE_TOOLS,
            "models": (await list_models(request))["models"],
        }


@app.put("/api/admin/settings")
async def update_admin_settings(request: Request):
    _require_admin(request)
    body = await request.json()
    with registry.SessionLocal() as session:
        if "llm_connection" in body:
            allowed = {
                key: body["llm_connection"].get(key)
                for key in [
                    "model",
                    "base_url",
                    "api_key",
                    "api_type",
                    "max_tokens",
                    "temperature",
                    "fallback_chain",
                ]
                if body["llm_connection"].get(key) not in (None, "")
            }
            if "fallback_chain" in allowed and not isinstance(
                allowed["fallback_chain"], list
            ):
                raise HTTPException(
                    status_code=400,
                    detail="llm_connection.fallback_chain must be a list of connection objects",
                )
            _set_app_setting(session, "llm_connection", allowed)
        if "tools" in body:
            disabled = [
                str(name)
                for name in body["tools"].get("disabled", [])
                if str(name) not in {"terminate"}
            ]
            _set_app_setting(session, "tools", {"disabled": disabled})
        if "config_overrides" in body:
            overrides = body["config_overrides"]
            if not isinstance(overrides, dict):
                raise HTTPException(
                    status_code=400, detail="config_overrides must be an object"
                )
            _set_app_setting(session, "config_overrides", overrides)
        session.commit()
        llm_connection = _get_app_setting(session, "llm_connection", {})
        return {
            "llm_connection": llm_connection or _default_llm_connection(),
            "llm_connection_override": llm_connection,
            "tools": _get_app_setting(session, "tools", {"disabled": []}),
            "config_defaults": _loaded_config_defaults(),
            "config_overrides": _get_app_setting(session, "config_overrides", {}),
            "available_tools": AVAILABLE_TOOLS,
        }


@app.get("/api/conversations")
async def list_conversations(request: Request):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        from sqlalchemy import desc

        _prune_orphan_conversation_sandboxes(session)

        conversations = (
            session.query(ConversationORM)
            .filter(ConversationORM.user_id == user.user_id)
            .order_by(
                desc(ConversationORM.updated_at), desc(ConversationORM.created_at)
            )
            .all()
        )
        if not conversations:
            conversations = [_ensure_default_conversation(session, user.user_id)]
            session.commit()
        return {
            "conversations": [
                _conversation_to_dict(session, conversation)
                for conversation in conversations
            ]
        }


@app.post("/api/conversations")
async def create_conversation(request: Request):
    user = _require_user(request)
    title = "New conversation"
    model = None
    try:
        body = await request.json()
        title = str(body.get("title") or title).strip() or title
        model = str(body.get("model") or "").strip() or None
    except Exception:
        pass
    with registry.SessionLocal() as session:
        conversation = ConversationORM(
            user_id=user.user_id, title=title[:120], model=model
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return _conversation_to_dict(session, conversation)


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        return _conversation_to_dict(session, conversation)


@app.get("/api/conversations/{conversation_id}/tasks")
async def get_conversation_tasks(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        tasks = _conversation_tasks(
            session, str(conversation.conversation_id), ascending=True
        )
        return {"tasks": [_task_to_dict(task) for task in tasks]}


@app.get("/api/conversations/{conversation_id}/events/history")
async def get_conversation_event_history(
    request: Request,
    conversation_id: str,
    limit: int = 160,
    before_event_id: Optional[int] = None,
    kind: Optional[str] = None,
):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        tasks = _conversation_tasks(
            session, str(conversation.conversation_id), ascending=True
        )
        # Recover stale non-terminal tasks during history load so UI does not
        # keep trying to tail a dead SSE stream forever.
        now = _now()
        stale_seconds = 300
        for task in tasks:
            # Only recover stale CREATED tasks here.
            # RUNNING tasks may legitimately execute for a long time.
            if str(task.status) != "CREATED":
                continue
            created_at = task.created_at or now
            age = (now - created_at).total_seconds()
            if age <= stale_seconds:
                continue
            task.status = "FAILED"
            task.result = {
                "error": "Stale task recovered while loading conversation history."
            }
            session.commit()
        tasks = _conversation_tasks(
            session, str(conversation.conversation_id), ascending=True
        )
        conversation_payload = _conversation_to_dict(session, conversation)
        task_payloads = [_task_to_dict(task) for task in tasks]
        task_by_id = {str(task.task_id): task for task in tasks}

        query = session.query(ConversationEventORM).filter(
            ConversationEventORM.conversation_id == conversation.conversation_id
        )
        if before_event_id is not None:
            query = query.filter(ConversationEventORM.event_id < before_event_id)
        if kind:
            query = query.filter(ConversationEventORM.event_type == kind)
        page_size = max(1, min(limit, 2000))
        # Load the newest page first for responsive conversation open.
        rows = (
            query.order_by(ConversationEventORM.event_id.desc()).limit(page_size).all()
        )
        rows = list(reversed(rows))

    events: list[dict] = []
    if rows:
        has_emitted_complete_by_task: set[str] = set()
        for row in rows:
            task_key = str(row.task_id) if row.task_id else ""
            for event in _event_row_to_progress(row, task_by_id.get(task_key)):
                is_complete = event.get("name") == "agent:lifecycle:complete"
                if is_complete and task_key in has_emitted_complete_by_task:
                    continue
                if is_complete and task_key:
                    has_emitted_complete_by_task.add(task_key)
                events.append(_compact_history_event(event))
    else:
        for task in tasks:
            events.extend(
                [
                    _compact_history_event(item)
                    for item in await _task_stream_progress(task)
                ]
            )

    next_before_event_id = rows[0].event_id if rows else None
    return {
        "conversation": conversation_payload,
        "tasks": task_payloads,
        "events": events,
        "pagination": {
            "limit": page_size,
            "next_before_event_id": next_before_event_id,
            "has_more": len(rows) == page_size and next_before_event_id is not None,
        },
    }


@app.post("/api/conversations/{conversation_id}/obsidian/import")
async def import_obsidian_context(request: Request, conversation_id: str):
    """Import Obsidian notes and build a wikilink graph for this conversation.

    Resolution fixes:
    - Path-qualified wikilinks resolve via .md-stripped path lookup.
    - Duplicate titles detected and skipped instead of silent last-wins.
    - Diff-based edge update: existing edges from notes NOT in this batch are preserved.
    """
    user = _require_user(request)
    body = await request.json()
    notes = body.get("notes") or []
    if not isinstance(notes, list) or not notes:
        raise HTTPException(status_code=400, detail="notes[] is required")

    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        cid = conversation.conversation_id
        existing = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == cid)
            .all()
        )
        by_path = {note.path: note for note in existing}

        upserted: list[ObsidianNoteORM] = []
        for raw in notes:
            if not isinstance(raw, dict):
                continue
            path = str(raw.get("path") or raw.get("title") or "").strip()
            title = str(raw.get("title") or Path(path).stem or "").strip()
            content = str(raw.get("content") or "")
            tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
            meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
            if not path or not title:
                continue
            note = by_path.get(path)
            if note is None:
                note = ObsidianNoteORM(
                    conversation_id=cid,
                    path=path,
                    title=title,
                    content=content,
                    tags=tags,
                    meta=meta,
                )
                session.add(note)
            else:
                note.title = title
                note.content = content
                note.tags = tags
                note.meta = meta
            upserted.append(note)
            by_path[path] = note

        session.flush()

        # --- Diff-based edge update ---
        # Rebuild the full note index after flush (includes both imported and existing)
        all_notes = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == cid)
            .all()
        )
        all_by_path = {note.path: note for note in all_notes}
        # Path-stem lookup: strip .md so [[projects/Overview]] matches "projects/Overview.md"
        all_by_path_stem: dict[str, list[ObsidianNoteORM]] = {}
        for note in all_notes:
            stem = note.path
            if stem.endswith(".md"):
                stem = stem[:-3]
            all_by_path_stem.setdefault(stem, []).append(note)
        # Title lookup: track duplicates for disambiguation
        all_by_title: dict[str, list[ObsidianNoteORM]] = {}
        for note in all_notes:
            all_by_title.setdefault(note.title, []).append(note)

        upserted_ids = {note.note_id for note in upserted}

        # Compute desired edges from upserted notes
        desired_edges: set[tuple] = set()
        for note in upserted:
            for target_name in _extract_wikilinks(note.content):
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

        # Query existing edges sourced from upserted notes only
        existing_edge_rows = (
            session.query(ObsidianEdgeORM)
            .filter(
                ObsidianEdgeORM.conversation_id == cid,
                ObsidianEdgeORM.source_note_id.in_(upserted_ids),
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
        edges_created = 0
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
                edges_created += 1

        conversation.updated_at = _now()
        session.commit()

        payload = _obsidian_graph_payload(session, conversation)
        return {
            "conversation_id": conversation_id,
            "imported_notes": len(upserted),
            "edges_created": edges_created,
            "graph": payload,
        }


@app.get("/api/conversations/{conversation_id}/obsidian/graph")
async def get_obsidian_graph(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        return {
            "conversation_id": conversation_id,
            **_obsidian_graph_payload(session, conversation),
        }


@app.get("/api/conversations/{conversation_id}/obsidian/context")
async def get_obsidian_context(request: Request, conversation_id: str, limit: int = 8):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        notes = (
            session.query(ObsidianNoteORM)
            .filter(ObsidianNoteORM.conversation_id == conversation.conversation_id)
            .order_by(ObsidianNoteORM.updated_at.desc())
            .limit(max(1, min(limit, 30)))
            .all()
        )
    items = []
    for note in notes:
        content = (note.content or "").strip()
        if len(content) > 900:
            content = content[:900] + "..."
        items.append(
            {
                "id": str(note.note_id),
                "path": note.path,
                "title": note.title,
                "tags": note.tags or [],
                "content": content,
            }
        )
    return {"conversation_id": conversation_id, "notes": items, "count": len(items)}


@app.get("/api/conversations/{conversation_id}/events/count")
async def get_conversation_event_count(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        counts = (
            session.query(
                ConversationEventORM.event_type,
                func.count(ConversationEventORM.event_id),
            )
            .filter(
                ConversationEventORM.conversation_id == conversation.conversation_id
            )
            .group_by(ConversationEventORM.event_type)
            .all()
        )
        return {
            "conversation_id": conversation_id,
            "total": sum(int(count) for _, count in counts),
            "by_type": {event_type: int(count) for event_type, count in counts},
        }


@app.get("/api/conversations/{conversation_id}/runtime")
async def get_conversation_runtime(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)

    sandbox = _conversation_sandbox(conversation_id)
    try:
        sandbox_status = await sandbox.status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    status_value = str((sandbox_status or {}).get("status") or "").lower()
    # Do not hard-fail runtime view when sandbox is paused/stopped/missing.
    # In these states process/container inspection may fail by design.
    if status_value in {"paused", "exited", "dead", "missing", ""}:
        return {
            "conversation_id": conversation_id,
            "sandbox": sandbox_status,
            "status": "paused" if status_value == "paused" else "idle",
            "processes": [],
            "containers": [],
            "urls": [],
            "hidden_system_containers": 0,
            "running_count": 0,
        }

    try:
        processes, containers, urls = await asyncio.gather(
            sandbox.list_processes(),
            sandbox.list_docker_containers(),
            sandbox.list_exposed_urls(),
        )
    except Exception:
        # Runtime panel should stay available even when deep inspection fails.
        processes, containers, urls = [], [], []

    killable_processes = [
        item
        for item in processes
        if not item.get("protected") and not item.get("zombie")
    ]
    visible_containers = [item for item in containers if not item.get("protected")]
    killable_containers = visible_containers
    return {
        "conversation_id": conversation_id,
        "sandbox": sandbox_status,
        "status": "running" if killable_processes or killable_containers else "idle",
        "processes": processes,
        "containers": visible_containers,
        "urls": urls,
        "hidden_system_containers": len(containers) - len(visible_containers),
        "running_count": len(killable_processes) + len(killable_containers),
        "agentmemory": _agentmemory_health(conversation_id),
    }


@app.get("/api/conversations/{conversation_id}/state")
async def get_conversation_state(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        conversation_payload = _conversation_to_dict(session, conversation)
    sandbox_status = await _conversation_sandbox(conversation_id).status()
    return {
        "conversation_id": conversation_id,
        "state": conversation_payload.get("state", "idle"),
        "latest_status": conversation_payload.get("latest_status"),
        "sandbox": sandbox_status,
    }


@app.get("/api/conversations/{conversation_id}/integrations/health")
async def get_conversation_integrations_health(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)
        return {
            "conversation_id": conversation_id,
            "agentmemory": _agentmemory_health(conversation_id),
            "obsidian": _obsidian_health(session, conversation_id),
            "llm_connection": _llm_connection_health(session),
        }


@app.post("/api/conversations/{conversation_id}/sandbox/start")
async def start_conversation_sandbox(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)
    sandbox = await _conversation_sandbox(conversation_id).ensure()
    return {"conversation_id": conversation_id, "sandbox": await sandbox.status()}


@app.post("/api/conversations/{conversation_id}/sandbox/pause")
async def pause_conversation_sandbox(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)
    sandbox = _conversation_sandbox(conversation_id)
    await sandbox.pause()
    return {"conversation_id": conversation_id, "sandbox": await sandbox.status()}


@app.post("/api/conversations/{conversation_id}/sandbox/resume")
async def resume_conversation_sandbox(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)
    sandbox = _conversation_sandbox(conversation_id)
    await sandbox.resume()
    return {"conversation_id": conversation_id, "sandbox": await sandbox.status()}


@app.delete("/api/conversations/{conversation_id}/sandbox")
async def delete_conversation_sandbox(request: Request, conversation_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)
    await _conversation_sandbox(conversation_id).delete()
    return {"conversation_id": conversation_id, "deleted": True}


@app.post("/api/conversations/{conversation_id}/runtime/processes/{pid}/kill")
async def kill_conversation_process(request: Request, conversation_id: str, pid: int):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    signal = str(body.get("signal") or "TERM")
    try:
        await _conversation_sandbox(conversation_id).kill_process(pid, signal=signal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"conversation_id": conversation_id, "pid": pid, "killed": True}


@app.post("/api/conversations/{conversation_id}/runtime/containers/{container_id}/stop")
async def stop_conversation_container(
    request: Request, conversation_id: str, container_id: str
):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        _require_conversation(session, user.user_id, conversation_id)

    try:
        await _conversation_sandbox(conversation_id).stop_docker_container(container_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "conversation_id": conversation_id,
        "container_id": container_id,
        "stopped": True,
    }


@app.put("/api/conversations/{conversation_id}/settings")
async def update_conversation_settings(request: Request, conversation_id: str):
    user = _require_user(request)
    body = await request.json()
    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        settings = dict(conversation.settings or {})
        if "model" in body:
            model = str(body.get("model") or "").strip()
            conversation.model = model or None
        if "disabled_tools" in body:
            settings["disabled_tools"] = [
                str(name)
                for name in body.get("disabled_tools", [])
                if str(name) != "terminate"
            ]
        if "requested_context_window" in body:
            raw_window = body.get("requested_context_window")
            if raw_window in (None, "", 0):
                settings.pop("requested_context_window", None)
            else:
                try:
                    value = int(raw_window)
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail="requested_context_window must be a positive integer",
                    )
                if value <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="requested_context_window must be a positive integer",
                    )
                settings["requested_context_window"] = value
        if "auto_context_compress" in body:
            settings["auto_context_compress"] = bool(body.get("auto_context_compress"))
        if "disabled_skills" in body:
            settings["disabled_skills"] = [
                str(name).strip()
                for name in body.get("disabled_skills", [])
                if str(name).strip()
            ]
        if "enable_vendor_skills" in body:
            settings["enable_vendor_skills"] = bool(body.get("enable_vendor_skills"))
        if "pinned_skills" in body:
            settings["pinned_skills"] = [
                str(name).strip()
                for name in body.get("pinned_skills", [])
                if str(name).strip()
            ]
        if "identity_notes" in body:
            settings["identity_notes"] = str(body.get("identity_notes") or "").strip()
        if "auto_skill_curator" in body:
            settings["auto_skill_curator"] = bool(body.get("auto_skill_curator"))
        conversation.settings = settings
        conversation.updated_at = _now()
        session.commit()
        session.refresh(conversation)
        return _conversation_to_dict(session, conversation)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str):
    user = _require_user(request)
    import redis as redis_lib

    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        tasks = (
            session.query(TaskORM)
            .filter(
                TaskORM.input["conversation_id"].astext
                == str(conversation.conversation_id)
            )
            .all()
        )
        task_ids = [str(task.task_id) for task in tasks]
        session.query(ConversationEventORM).filter(
            ConversationEventORM.conversation_id == conversation.conversation_id
        ).delete(synchronize_session=False)
        # Remove Obsidian graph rows before deleting the conversation row
        # to satisfy foreign key constraints.
        session.query(ObsidianEdgeORM).filter(
            ObsidianEdgeORM.conversation_id == conversation.conversation_id
        ).delete(synchronize_session=False)
        session.query(ObsidianNoteORM).filter(
            ObsidianNoteORM.conversation_id == conversation.conversation_id
        ).delete(synchronize_session=False)
        for task in tasks:
            session.delete(task)
        session.delete(conversation)
        session.commit()

    try:
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        for tid in task_ids:
            r.delete(f"task:{tid}:stream")
            r.delete(f"task:{tid}:inbox")
        r.close()
    except Exception:
        pass

    workspace_path = os.path.join(WORKSPACE_ROOT, "conversations", conversation_id)
    shutil.rmtree(workspace_path, ignore_errors=True)

    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(f"openmanus_sandbox_{conversation_id}")
        container.remove(force=True)
    except Exception:
        pass

    return {"id": conversation_id, "deleted": True}


# ---------------------------------------------------------------------------
# Task list (sidebar history)
# ---------------------------------------------------------------------------


@app.get("/api/tasks")
async def list_tasks(request: Request, page: int = 1, pageSize: int = 30):
    """List tasks from the database for the sidebar."""
    user = _require_user(request)
    with registry.SessionLocal() as session:
        from sqlalchemy import desc

        conversation_ids = [
            str(row[0])
            for row in session.query(ConversationORM.conversation_id)
            .filter(ConversationORM.user_id == user.user_id)
            .all()
        ]
        offset = (page - 1) * pageSize
        orms = (
            session.query(TaskORM)
            .filter(TaskORM.input["conversation_id"].astext.in_(conversation_ids))
            .order_by(desc(TaskORM.created_at))
            .offset(offset)
            .limit(pageSize)
            .all()
        )

        # The hook does: res.data?.tasks  so we must nest it under "tasks"
        tasks = [
            {
                "id": str(orm.task_id),
                "task_id": str(orm.task_id),
                "status": orm.status,
                "conversation_id": _conversation_id_for(orm),
                "created_at": orm.created_at.isoformat() if orm.created_at else None,
                # The sidebar uses 'request' as the display label
                "request": (orm.input or {}).get("prompt", "Untitled task"),
            }
            for orm in orms
        ]

        return {"tasks": tasks, "total": len(tasks)}


# ---------------------------------------------------------------------------
# SSE event stream
# ---------------------------------------------------------------------------


@app.get("/api/tasks/{task_id}/events")
async def task_events(request: Request, task_id: str):
    """SSE endpoint: read from Redis Stream so events are never missed."""
    user = _require_user(request)

    # Check current task status from DB before opening the stream
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None or not _task_belongs_to_user(session, orm, user.user_id):
            raise HTTPException(status_code=404, detail="Task not found")
        task_is_done = orm is not None and orm.status in (
            "COMPLETED",
            "FAILED",
            "INTERRUPTED",
        )
        task_prompt = (orm.input or {}).get("prompt", "")
        task_conversation_id = _conversation_id_for(orm)

    async def event_generator():
        redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        stream_key = f"task:{task_id}:stream"
        last_id = "0"  # start from the very beginning of the stream
        empty_polls = 0
        has_emitted_complete = False

        try:
            while True:
                if await request.is_disconnected():
                    break

                # XREAD blocks up to 1 second waiting for new entries
                results = await redis.xread({stream_key: last_id}, count=10, block=1000)

                if not results:
                    if task_is_done:
                        # Task is completed in DB but no stream data exists
                        # (task ran before Redis Streams were added, or stream expired).
                        # Send synthetic lifecycle events so the UI can close cleanly.
                        empty_polls += 1
                        if empty_polls >= 2:  # wait 2 seconds then synthesize
                            yield {
                                "data": json.dumps(
                                    {
                                        "type": "progress",
                                        "name": "agent:lifecycle:start",
                                        "content": {},
                                    }
                                )
                            }
                            yield {
                                "data": json.dumps(
                                    {
                                        "type": "progress",
                                        "name": "agent:lifecycle:complete",
                                        "content": {
                                            "message": "Task already completed"
                                        },
                                    }
                                )
                            }
                            # Grace period: let browser receive and process before we close
                            await asyncio.sleep(3)
                            return
                    # Active task with no events yet — send keep-alive ping
                    yield {"data": json.dumps({"type": "ping"})}
                    continue

                # Reset empty poll counter whenever we get events
                empty_polls = 0

                done = False
                for _stream, messages in results:
                    for msg_id, fields in messages:
                        last_id = msg_id
                        event_type = fields.get("type", "")
                        try:
                            data = json.loads(fields.get("data", "{}"))
                        except Exception:
                            data = {}

                        progress_list = _agent_event_to_progress(
                            {"type": event_type, "data": data}
                        )
                        for progress_index, progress in enumerate(progress_list):
                            content = dict(progress.get("content") or {})
                            content.setdefault("task_id", task_id)
                            content.setdefault("conversation_id", task_conversation_id)
                            if progress.get("name") == "agent:lifecycle:start":
                                content.setdefault("request", task_prompt)
                            progress["content"] = content

                            is_complete = (
                                progress.get("name") == "agent:lifecycle:complete"
                            )
                            if is_complete and has_emitted_complete:
                                continue
                            if is_complete:
                                has_emitted_complete = True

                            progress[
                                "id"
                            ] = f"{task_id}:{msg_id}:{progress_index}:{progress.get('name')}"
                            progress["task_id"] = task_id
                            yield {"data": json.dumps(progress)}
                            if progress["name"] in (
                                "agent:lifecycle:complete",
                                "agent:lifecycle:terminated",
                                "agent:lifecycle:step:error",
                            ):
                                done = True
                                break
                        if done:
                            break
                    if done:
                        break

                if done:
                    # Grace period: give the browser time to receive the completion
                    # event and call eventSource.close() itself, BEFORE we close the
                    # TCP connection — this prevents the browser firing onerror and
                    # showing the "connection failed" toast.
                    await asyncio.sleep(3)
                    return

        finally:
            await redis.aclose()

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Create task — frontend sends multipart/form-data
# ---------------------------------------------------------------------------


@app.post("/api/tasks")
async def create_task(
    request: Request,
    prompt: Optional[str] = Form(None),
    task_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
):
    """Create a new task, or queue a follow-up run on an existing task."""
    user = _require_user(request)

    if task_id:
        # Check if this task already exists (follow-up message in a conversation)
        with registry.SessionLocal() as session:
            existing_orm = session.get(TaskORM, task_id)
            if existing_orm is not None and not _task_belongs_to_user(
                session, existing_orm, user.user_id
            ):
                raise HTTPException(status_code=404, detail="Task not found")

        if existing_orm is not None:
            conversation_id = _conversation_id_for(existing_orm)
            with registry.SessionLocal() as session:
                conversation = session.get(
                    ConversationORM, uuid.UUID(str(conversation_id))
                )
                conversation_settings = (
                    conversation.settings if conversation is not None else {}
                )
                run_model = model or (
                    conversation.model if conversation is not None else None
                )
                disabled_tools = list(
                    (conversation_settings or {}).get("disabled_tools", [])
                )
                requested_context_window = (conversation_settings or {}).get(
                    "requested_context_window"
                )
                auto_context_compress = (conversation_settings or {}).get(
                    "auto_context_compress", True
                )
                disabled_skills = list(
                    (conversation_settings or {}).get("disabled_skills", [])
                )
                enable_vendor_skills = bool(
                    (conversation_settings or {}).get("enable_vendor_skills", True)
                )
                pinned_skills = list(
                    (conversation_settings or {}).get("pinned_skills", [])
                )
                identity_notes = str(
                    (conversation_settings or {}).get("identity_notes", "")
                )
                if conversation is not None:
                    conversation.updated_at = _now()
                    session.commit()
            if existing_orm.status in TERMINAL_STATUSES:
                task = registry.create_task(
                    input=_task_input(
                        prompt,
                        conversation_id,
                        parent_task_id=task_id,
                        model=run_model,
                        disabled_tools=disabled_tools,
                        requested_context_window=requested_context_window,
                        auto_context_compress=auto_context_compress,
                        disabled_skills=disabled_skills,
                        enable_vendor_skills=enable_vendor_skills,
                        pinned_skills=pinned_skills,
                        identity_notes=identity_notes,
                    )
                )
                task.status = TaskStatus.CREATED
                run_task.apply_async(args=[task.id, prompt], task_id=task.id)
                return {
                    "task_id": task.id,
                    "status": str(task.status),
                    "conversation_id": conversation_id,
                    "data": {
                        "task_id": task.id,
                        "status": str(task.status),
                        "conversation_id": conversation_id,
                    },
                }

            # Recovery path: if a task stayed non-terminal for too long
            # (typically after worker restart/crash), mark it failed so the
            # conversation can continue with a fresh run.
            age_seconds = (_now() - (existing_orm.updated_at or _now())).total_seconds()
            if existing_orm.status == "CREATED" and age_seconds > 300:
                with registry.SessionLocal() as session:
                    stale = session.get(TaskORM, existing_orm.task_id)
                    if stale is not None and stale.status == "CREATED":
                        stale.status = "FAILED"
                        stale.result = {
                            "error": "Stale task recovered after worker interruption."
                        }
                        session.commit()
                # Re-read latest state after recovery mark.
                with registry.SessionLocal() as session:
                    refreshed = session.get(TaskORM, existing_orm.task_id)
                    if refreshed is not None and refreshed.status in TERMINAL_STATUSES:
                        existing_orm = refreshed
                        task = registry.create_task(
                            input=_task_input(
                                prompt,
                                conversation_id,
                                parent_task_id=task_id,
                                model=run_model,
                                disabled_tools=disabled_tools,
                                requested_context_window=requested_context_window,
                                auto_context_compress=auto_context_compress,
                                disabled_skills=disabled_skills,
                                enable_vendor_skills=enable_vendor_skills,
                                pinned_skills=pinned_skills,
                                identity_notes=identity_notes,
                            )
                        )
                        task.status = TaskStatus.CREATED
                        run_task.apply_async(args=[task.id, prompt], task_id=task.id)
                        return {
                            "task_id": task.id,
                            "status": str(task.status),
                            "conversation_id": conversation_id,
                            "data": {
                                "task_id": task.id,
                                "status": str(task.status),
                                "conversation_id": conversation_id,
                            },
                        }

            # Task exists but is NOT in a terminal status.
            # We must not queue another Celery task for the exact same task ID,
            # otherwise two agents will run concurrently and exhaust the server.
            raise HTTPException(
                status_code=409,
                detail="Task is currently running. Please wait for it to finish or interrupt it before sending a new prompt.",
            )

    # New task — create a DB record and queue it. When the caller did not
    # provide an id, use one generated id for both the first task and the
    # conversation so the workspace path stays easy to reason about.
    new_task_id = str(task_id or uuid.uuid4())
    with registry.SessionLocal() as session:
        if conversation_id:
            conversation = _require_conversation(session, user.user_id, conversation_id)
        else:
            conversation = _ensure_default_conversation(session, user.user_id)
        if prompt and conversation.title == "New conversation":
            conversation.title = (
                prompt.strip().splitlines()[0][:80] or conversation.title
            )
        if model:
            conversation.model = model
        run_model = model or conversation.model
        disabled_tools = list((conversation.settings or {}).get("disabled_tools", []))
        requested_context_window = (conversation.settings or {}).get(
            "requested_context_window"
        )
        auto_context_compress = (conversation.settings or {}).get(
            "auto_context_compress", True
        )
        disabled_skills = list((conversation.settings or {}).get("disabled_skills", []))
        enable_vendor_skills = bool(
            (conversation.settings or {}).get("enable_vendor_skills", True)
        )
        pinned_skills = list((conversation.settings or {}).get("pinned_skills", []))
        identity_notes = str((conversation.settings or {}).get("identity_notes", ""))
        conversation.updated_at = _now()
        session.commit()
        conversation_id = str(conversation.conversation_id)

    task = registry.create_task(
        task_id=new_task_id,
        input=_task_input(
            prompt,
            conversation_id,
            model=run_model,
            disabled_tools=disabled_tools,
            requested_context_window=requested_context_window,
            auto_context_compress=auto_context_compress,
            disabled_skills=disabled_skills,
            enable_vendor_skills=enable_vendor_skills,
            pinned_skills=pinned_skills,
            identity_notes=identity_notes,
        ),
    )
    task.status = TaskStatus.CREATED
    run_task.apply_async(args=[task.id, prompt], task_id=task.id)

    return {
        "task_id": task.id,
        "status": str(task.status),
        "conversation_id": conversation_id,
        "data": {
            "task_id": task.id,
            "status": str(task.status),
            "conversation_id": conversation_id,
        },
    }


@app.post("/api/tasks/{task_id}/message")
async def send_task_message(request: Request, task_id: str):
    """Queue a user message for a running task to consume."""
    user = _require_user(request)
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None or not _task_belongs_to_user(session, orm, user.user_id):
            raise HTTPException(status_code=404, detail="Task not found")

    message = ""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            message = str(body.get("message") or body.get("prompt") or "")
        except Exception:
            message = ""
    else:
        form = await request.form()
        message = str(form.get("message") or form.get("prompt") or "")

    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.rpush(f"task:{task_id}:inbox", message)
    finally:
        await redis.aclose()

    return {"id": task_id, "queued": True}


@app.post("/api/conversations/{conversation_id}/messages")
async def send_conversation_message(request: Request, conversation_id: str):
    """OpenHands-style pending message endpoint.

    If the conversation has a running task, queue the message into that task inbox.
    Otherwise create a new task in the same conversation.
    """
    user = _require_user(request)
    body = await request.json()
    message = str(body.get("message") or body.get("prompt") or "").strip()
    requested_model = str(body.get("model") or "").strip() or None
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    with registry.SessionLocal() as session:
        conversation = _require_conversation(session, user.user_id, conversation_id)
        active_task = next(
            (
                task
                for task in reversed(
                    _conversation_tasks(
                        session, str(conversation.conversation_id), ascending=True
                    )
                )
                if task.status not in TERMINAL_STATUSES
            ),
            None,
        )
        if active_task is not None:
            age_seconds = (_now() - (active_task.updated_at or _now())).total_seconds()
            if active_task.status == "CREATED" and age_seconds > 300:
                active_task.status = "FAILED"
                active_task.result = {
                    "error": "Stale task recovered after worker interruption."
                }
                session.commit()
                active_task = None

        if active_task is not None:
            active_task_id = str(active_task.task_id)
        else:
            active_task_id = None
            run_model = requested_model or conversation.model
            if requested_model:
                conversation.model = requested_model
            disabled_tools = list(
                (conversation.settings or {}).get("disabled_tools", [])
            )
            requested_context_window = (conversation.settings or {}).get(
                "requested_context_window"
            )
            auto_context_compress = (conversation.settings or {}).get(
                "auto_context_compress", True
            )
            disabled_skills = list(
                (conversation.settings or {}).get("disabled_skills", [])
            )
            enable_vendor_skills = bool(
                (conversation.settings or {}).get("enable_vendor_skills", True)
            )
            pinned_skills = list((conversation.settings or {}).get("pinned_skills", []))
            identity_notes = str(
                (conversation.settings or {}).get("identity_notes", "")
            )
            conversation.updated_at = _now()
            session.commit()

    if active_task_id:
        redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        try:
            await redis.rpush(f"task:{active_task_id}:inbox", message)
        finally:
            await redis.aclose()
        return {
            "conversation_id": conversation_id,
            "task_id": active_task_id,
            "queued": True,
            "created_task": False,
        }

    task = registry.create_task(
        input=_task_input(
            message,
            conversation_id,
            model=run_model,
            disabled_tools=disabled_tools,
            requested_context_window=requested_context_window,
            auto_context_compress=auto_context_compress,
            disabled_skills=disabled_skills,
            enable_vendor_skills=enable_vendor_skills,
            pinned_skills=pinned_skills,
            identity_notes=identity_notes,
        )
    )
    task.status = TaskStatus.CREATED
    run_task.apply_async(args=[task.id, message], task_id=task.id)
    return {
        "conversation_id": conversation_id,
        "task_id": task.id,
        "queued": True,
        "created_task": True,
    }


# ---------------------------------------------------------------------------
# Single task detail
# ---------------------------------------------------------------------------


@app.get("/api/tasks/{task_id}")
async def get_task(request: Request, task_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None or not _task_belongs_to_user(session, orm, user.user_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "id": str(orm.task_id),
            "status": orm.status,
            "result": orm.result,
            "conversation_id": _conversation_id_for(orm),
        }


# ---------------------------------------------------------------------------
# Interrupt / terminate
# ---------------------------------------------------------------------------


@app.post("/api/tasks/{task_id}/interrupt")
@app.post("/api/tasks/{task_id}/terminate")
async def interrupt_task(request: Request, task_id: str):
    user = _require_user(request)
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None or not _task_belongs_to_user(session, orm, user.user_id):
            raise HTTPException(status_code=404, detail="Task not found")
        orm.status = TaskStatus.INTERRUPTED.value
        session.commit()
    registry.interrupt_task(task_id)
    try:
        celery_app.control.revoke(task_id, terminate=True)
    except Exception:
        pass
    return {"id": task_id, "status": TaskStatus.INTERRUPTED.value}


@app.delete("/api/tasks/{task_id}")
async def delete_task(request: Request, task_id: str):
    """Delete a task and its Redis stream."""
    import redis as redis_lib

    user = _require_user(request)
    with registry.SessionLocal() as session:
        orm = session.get(TaskORM, task_id)
        if orm is None or not _task_belongs_to_user(session, orm, user.user_id):
            raise HTTPException(status_code=404, detail="Task not found")
        session.query(ConversationEventORM).filter(
            ConversationEventORM.task_id == orm.task_id
        ).delete(synchronize_session=False)
        session.delete(orm)
        session.commit()
    try:
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        r.delete(f"task:{task_id}:stream")
        r.delete(f"task:{task_id}:inbox")
        r.close()
    except Exception:
        pass
    return {"id": task_id, "deleted": True}


@app.get("/api/workspace/{path:path}")
async def get_workspace(path: str = ""):
    """List files in /app/workspace or return file content."""
    import datetime
    import os

    from fastapi.responses import FileResponse

    base = "/app/workspace"
    target = os.path.normpath(os.path.join(base, path)) if path else base

    # Security: block path traversal
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(target):
        return []  # Empty workspace

    if os.path.isfile(target):
        return FileResponse(target, filename=os.path.basename(target))

    entries = []
    try:
        for entry in sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name)):
            s = entry.stat()
            entries.append(
                {
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": s.st_size,
                    "modifiedTime": datetime.datetime.fromtimestamp(
                        s.st_mtime
                    ).isoformat(),
                }
            )
    except PermissionError:
        pass
    return entries


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=8000)
