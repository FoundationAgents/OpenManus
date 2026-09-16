# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

OpenManus is a general-purpose LLM agent framework (Python 3.12). An agent (`Manus` by default) runs a think/act loop, calling tools (Python execution, browser automation, file editing, bash, MCP-based tools, etc.) to accomplish a user-supplied task. It supports single-agent runs, a multi-agent "flow" mode, and running as an MCP server or client.

## Commands

### Setup
```bash
uv pip install -r requirements.txt      # or: pip install -r requirements.txt
playwright install                       # optional, for browser automation tool
cp config/config.example.toml config/config.toml   # then add LLM API keys
```

### Running the agent
```bash
python main.py                    # single Manus agent, interactive or --prompt "..."
python run_flow.py                # multi-agent planning flow (set [runflow] use_data_analysis_agent in config.toml to add the DataAnalysis agent)
python run_mcp.py                 # run as an MCP client (stdio or --connection sse --server-url ...)
python run_mcp_server.py          # run OpenManus tools as an MCP server
```

### Tests
```bash
pytest tests/                                    # run all tests
pytest tests/sandbox/test_sandbox.py             # single file
pytest tests/sandbox/test_sandbox.py::test_name  # single test
```
Async tests use explicit `@pytest.mark.asyncio` markers (no global `asyncio_mode` is configured). Sandbox tests require Docker to be running.

### Lint / format
```bash
pre-commit run --all-files
```
This runs `black`, `isort` (profile=black), `autoflake`, plus trailing-whitespace/EOF/yaml checks. Run this before submitting a PR (enforced in CI via `.github/workflows/pre-commit.yaml`).

## Architecture

### Agent hierarchy (`app/agent/`)
`BaseAgent` (pydantic model, `app/agent/base.py`) → `ReActAgent` (`react.py`, adds abstract `think()`/`act()`) → `ToolCallAgent` (`toolcall.py`, implements think/act around OpenAI-style tool/function calling, tracks `available_tools: ToolCollection`, handles special "terminating" tools) → `Manus` (`manus.py`, the default general-purpose agent) and other specializations (`browser.py`, `swe.py`, `data_analysis.py`, `mcp.py`, `sandbox_agent.py`).

- Agents are pydantic `BaseModel`s with `extra = "allow"`, driven by a `run()` loop in `BaseAgent` that steps until `AgentState.FINISHED` or `max_steps`, and detects/handles "stuck" (repeated identical assistant messages) states.
- `Manus.create()` is the required factory (not `Manus()` directly) because it awaits MCP server initialization; `main.py` shows the canonical usage.
- Each agent owns an `LLM` instance (`app/llm.py`) and a `Memory` of `Message`s (`app/schema.py`).

### Tools (`app/tool/`)
All tools subclass `BaseTool` (`app/tool/base.py`): a pydantic model with `name`, `description`, `parameters` (JSON schema) and an async `execute()`; `to_param()` renders it in OpenAI function-calling format. `ToolCollection` (`tool_collection.py`) aggregates tools for an agent, dispatches `execute(name=..., tool_input=...)`, and is how `Manus.available_tools` is composed/extended (e.g. MCP tools are added/removed dynamically as servers connect/disconnect).

Notable tools: `python_execute.py`, `bash.py`, `browser_use_tool.py` (Playwright-based, via `browser-use`), `str_replace_editor.py`, `file_operators.py`, `ask_human.py`, `web_search.py`/`search/` (engine fallback chain), `chart_visualization/` (data-analysis agent), `crawl4ai.py`, `terminate.py` (a "special tool" that ends the agent run), `mcp.py` (`MCPClients`/`MCPClientTool` — proxies remote MCP tools as local `BaseTool`s).

### Flows (`app/flow/`)
`BaseFlow` coordinates multiple named agents; `FlowFactory` currently only builds `PlanningFlow` (`planning.py`), which drives a plan across the given agents. Used by `run_flow.py`.

### Sandbox (`app/sandbox/`, `app/daytona/`)
Tools that execute code/commands can run inside an isolated environment. `app/sandbox/client.py` exposes `create_sandbox_client()`/`LocalSandboxClient` (Docker-based, config in `SandboxSettings`); `app/daytona/` is an alternative remote sandbox backend (`DaytonaSettings`). `SANDBOX_CLIENT` is cleaned up automatically at the end of `BaseAgent.run()`.

### MCP integration (`app/mcp/`)
OpenManus is both an MCP client (agents can connect to external MCP servers over stdio or SSE — configured via `config/mcp.json`, loaded by `MCPSettings.load_server_config()`) and can itself be exposed as an MCP server (`app/mcp/server.py`, `run_mcp_server.py`), reusing the same tool implementations.

### Configuration (`app/config.py`)
`Config` is a thread-safe singleton (`config = Config()`, imported directly) that loads `config/config.toml` (falling back to `config/config.example.toml`) via `tomllib`. It exposes typed sub-settings: `llm` (dict keyed by name — `"default"` plus any per-model overrides like `llm.vision`), `sandbox`, `browser_config`, `search_config`, `mcp_config`, `run_flow_config`, `daytona`. Per-agent LLM overrides are looked up by lowercased agent name (`LLM(config_name=self.name.lower())` in `BaseAgent.initialize_agent`). Example configs for different providers live in `config/config.example-model-*.toml`.

### Prompts (`app/prompt/`)
System/next-step prompts are plain Python string constants, one module per agent type, imported into the corresponding agent class (e.g. `app/prompt/manus.py` → `Manus.system_prompt`).

## Notes
- `app/tool/base.py` has large commented-out blocks (an earlier `BaseTool` design) — leave as-is unless the task specifically calls for cleaning it up.
- The multi-agent flow (`run_flow.py`) is explicitly called out in the README as unstable.
- Browser automation dependency (`browser-use`) requires `playwright install` to have been run separately from `pip install`.
