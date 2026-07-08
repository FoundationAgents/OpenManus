<p align="center">
  <img src="assets/logo.jpg" width="180" alt="OpenManus"/>
</p>

English only.

# OpenManus

**A conversation-first agent runtime with persistent sandbox computers, live observability, and practical team workflows.**

This fork focuses on real daily usage: long-running conversations, isolated workspaces, runtime controls, and a UI that makes the agent’s work visible and manageable.

## Why This Repo

OpenManus here is built for people who want an agent they can actually run, inspect, and improve:

- Persistent conversations with replayable history
- Per-conversation sandbox + workspace isolation
- Live tool traces, terminal output, browser screenshots, and token counts
- Runtime controls for processes, ports, and spawned containers
- Optional RL policy scaffold compatible with OpenManus-RL workflows

## What’s Implemented

- Auth + admin bootstrap (first signup becomes admin)
- Session-based web auth and admin settings UI/API
- Conversation model with grouped tasks and follow-up continuity
- Per-conversation files under `workspace/conversations/<conversation_id>/`
- Reused sandbox computer per conversation
- Mid-task user messages to running agents
- Live SSE lifecycle stream (thoughts, tools, terminal, browser, usage)
- Process/container visibility and kill controls (with protection rules)
- Better completion artifacts and warnings (including missing PDF hints)
- OpenHands-style skill loading support
- RL integration scaffold and policy export helper

### Latest Additions

- `apply_patch_editor` as the primary code-editing tool for safer, atomic patch updates
- Live and final GitHub-style change summary (`files changed`, `+added`, `-deleted`)
- Richer tool execution cards with better status and file-change visibility
- Improved conversation reliability around long runs and follow-up continuity
- Runtime context observability (requested window, received window, usage ratio, auto-compress status)

### Agent Loop Architecture & Reliability Refactoring (vs. Upstream)

- **Structural Termination**: Replaced fragile regex finish detection (`_INCOMPLETE_RE`, `_STRONG_FINAL_RE`) with strict structural termination where the LLM must call the `terminate` tool (`status`, `summary`).
- **Typed Error Handling & Auto-Retry**: Replaced string-sniffing (`result.lower().startswith("error")`) with typed `ToolResult.is_error`. When a tool fails, the loop automatically retries with concrete `_error_context` injected into the tool input.
- **State Machine & Lifecycle Tracking**: Introduced explicit `AgentPhase` lifecycle tracking (`PLAN -> ACT -> OBSERVE -> VERIFY -> DONE`) and real-time lifecycle event emissions (`agent:lifecycle:phase`, `reason`, `observe`).
- **Robust Stuck Detection**: Enhanced `is_stuck()` with MD5 content hashing across whitespace-normalized turns and repeated exact tool-call batch detection.
- **Smart Context Compression**: Replaced naive 220-character truncation with structured summarization that preserves pinned artifacts (`pinned_context` such as file paths and diffs).
- **Pydantic V2 & Modernization**: Migrated core schema, tools, and agent models to clean Pydantic v2 `ConfigDict(...)` and resolved silent exception swallowing.

## Architecture

- Backend API: `server/api.py` (FastAPI + SSE)
- Worker runtime: `server/tasks.py` (Celery)
- Agent core: `app/agent/manus.py`, `app/agent/toolcall.py`
- LLM compatibility/runtime: `app/llm.py`
- Sandbox lifecycle: `app/sandbox/conversation.py`
- Frontend: `frontend/` (React + Vite)
- Persistence: PostgreSQL
- Event transport: Redis Streams

## Quick Start (Docker)

1. Copy config:

```bash
cp config/config.example.toml config/config.toml
```

2. Set your model endpoint in `config/config.toml`.

3. Start:

```bash
docker compose up --build
```

Or use the project helper:

```bash
make build
```

`make build` runs a clean Docker builder prune and then starts the stack with `docker compose up -d --build`.

4. Open:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

## Local Python Start

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py
```

## Configuration

Main file: `config/config.toml`

Important sections:

- `[llm]` model, endpoint, key, token limits
- `[sandbox]` runtime limits and network/socket access
- `[agent]` max steps and tool-call behavior
- `[rl]` optional policy integration

Example RL toggle:

```toml
[rl]
enabled = true
policy_mode = "rl"
policy_path = "research/openmanus-rl/artifacts/policy/latest/policy.md"
metadata_path = "research/openmanus-rl/artifacts/policy/latest/metadata.json"
```

## RL Scaffold

This repo includes a clean path for OpenManus-RL style integration:

- `research/openmanus-rl/`
- `app/agent/policy_loader.py`
- `scripts/export_policy.py`

Example:

```bash
python scripts/export_policy.py \
  --policy-file /path/to/policy.md \
  --model qwen3.6-35b-a3b \
  --benchmark gaia \
  --run-id exp-2026-05-14
```

## Semantic Memory with FAISS

OpenManus features local, zero-dependency SQLite-based memory persistence (`AgentMemory`). You can optionally enable local FAISS vector semantic search to enhance memory recall when query wording differs from saved memories:

```toml
[agentmemory]
enabled = true
vector_backend = "faiss" # "none" or "faiss"
embedding_provider = "openai_compatible"
embedding_model = "text-embedding-nomic-embed-text-v1.5"
hybrid_search = true
vector_weight = 0.65
keyword_weight = 0.35
```

When enabled, memories are indexed locally in FAISS alongside SQLite FTS5/BM25 keyword indices, returning weighted hybrid search results. If embedding generation or FAISS lookup fails, recall gracefully falls back to SQLite keyword search.

## DeepSpec Research Path

OpenManus includes an opt-in research integration scaffold for speculative decoding experiments using DeepSeek's DeepSpec framework:

- See `research/deepspec/README.md` for workflow and evaluation instructions.
- Run `scripts/prepare_deepspec_research.sh` to clone or update the upstream repository.

**Note**: DeepSpec is strictly experimental and separate from standard runtime execution or default `make build` container generation. Target cache preparation requires high-capacity storage (e.g. ~38 TB for Qwen3-4B).

## Contributing

Contributions are very welcome.

- Open an issue for bugs or feature proposals
- Keep PRs focused and easy to review
- Add verification steps in your PR description

### Maintainer Commitment

I actively monitor this repo and **I will respond to pull requests quickly**.
If your PR is blocked, tag me in the thread and I’ll help unblock it fast.

### Suggested Team Flow

1. Create feature branches from `main`
2. Open PRs early (draft PRs are welcome)
3. Merge after review + verification

## Runtime Notes

- Sandboxes are scoped to conversation lifecycle.
- Protected system processes/containers are not killable by runtime controls.
- Deleting a conversation clears associated task records, streams, and sandbox state.

## License

MIT (same as project root license).
