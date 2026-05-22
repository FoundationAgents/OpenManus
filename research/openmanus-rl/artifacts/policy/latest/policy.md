# OpenManus Execution Policy
# Source: Distilled from SWE-Bench, WebArena, and AgentBench failure analysis
# + observed failure patterns from this OpenManus deployment
# Effective: 2026-05-22

---

## 1. SEARCH & INTERNET BROWSING

**Rule S-1 (Search-First, Python-Never):**
When you need to look something up on the internet, ALWAYS use the `web_search` tool first.
Never use `python_execute` with `requests`, `httpx`, or `urllib` to scrape or search — these share
the same network restrictions and will fail with the same errors. If `web_search` returns an error
saying all engines failed, do NOT fall back to `python_execute`. Instead:
- Rephrase the query into a shorter, more specific form.
- Try a second `web_search` call with the rephrased query.
- Use `browser_use` with `go_to_url` to visit a specific known URL directly.

**Rule S-2 (Query Decomposition):**
If a search returns off-topic results (e.g. wrong language, wrong domain), the query was too
ambiguous. Break it into a more specific English-language query.
Example: instead of "AI agents" try "site:arxiv.org AI agent planning benchmark 2024".

**Rule S-3 (Browser as Last Resort):**
Only escalate to `browser_use` after `web_search` succeeds and you need the full page body.
Do not open new browser tabs unnecessarily — navigate within the current tab sequentially.

---

## 2. FILE EDITING

**Rule E-1 (Read Before Write):**
NEVER call `line_edit`, `apply_patch_editor`, or `str_replace_editor` on a file you have not
read in the current step sequence. Always confirm exact line numbers first. Editing without
reading causes 80%+ of code errors in benchmarks.

**Rule E-2 (Single-Tool Discipline):**
Do not mix `line_edit` and `str_replace_editor` on the same file in the same task.
Preferred hierarchy: `line_edit` > `apply_patch_editor` > `str_replace_editor`.

**Rule E-3 (Verify After Every Edit):**
After every file edit, read back the modified lines to confirm the change landed correctly.
For Python/TypeScript: run a syntax check (`python -m py_compile <file>` or `npx tsc --noEmit`)
before claiming the task is done.

---

## 3. CODE EXECUTION & BASH

**Rule B-1 (Short Chains):**
Do not chain more than 3 commands with `&&` in a single bash call. Long chains make it impossible
to identify which command failed. Run commands individually or in pairs, check the result, then
continue.

**Rule B-2 (Double Failure = Rethink):**
If the same bash command fails twice in a row, STOP. Do not try a third time immediately.
Call `planning` to write out your understanding of the failure and a revised plan.

**Rule B-3 (Exit Code Discipline):**
Always check that commands exit 0. Read the FULL stderr output before deciding on a fix.
Never silently ignore stderr.

---

## 4. PLANNING & TASK DECOMPOSITION

**Rule P-1 (Plan Before Complex Work):**
For any task with more than ~5 logical steps (refactoring, multi-file changes, Docker builds,
multi-stage research), call `planning` at the start to write a numbered execution plan.
Update the plan after each phase completes or fails. This creates a recovery checkpoint.

**Rule P-2 (Parallelise Independent Reads):**
When you need information from multiple files or searches, issue them as parallel tool calls in
one response. Do not chain: read A, then read B, then read C — issue all three at once.
This is the single highest-impact latency optimization available.

**Rule P-3 (Scope Guard):**
Before starting any task, identify what is explicitly asked vs. what you are assuming.
Work on what was asked. Do not add unrequested refactors or features as side effects.

---

## 5. SELF-CORRECTION

**Rule SC-1 (Failure Logging):**
When a tool call returns an error, internally note:
  - What you tried
  - What the error said
  - What you believe the root cause is
Then make exactly ONE targeted fix attempt. If it fails again, escalate (rethink or terminate
with a clear failure report).

**Rule SC-2 (Success Verification):**
Never call `terminate` claiming success without verifying the deliverable exists.
- For files: check `ls` or `read_files`.
- For API tasks: check the response body.
- For web tasks: confirm the page title or URL matches the target.
At least 40% of agent failures in benchmarks are premature terminations where the deliverable
was never confirmed.

**Rule SC-3 (No Hallucinated Paths):**
Do not reference file paths, function names, or variable names you have not confirmed exist
via `read_files`, `glob_search`, or `bash ls`. Always check before referencing.

---

## 6. MEMORY & CONTEXT

**Rule M-1 (Use Workspace Memory):**
For multi-step or multi-session tasks, use `memory_save` to record key decisions, file
locations, and partial results. Use `memory_recall` at the start of a new session to recover
context before doing any fresh work.

**Rule M-2 (Don't Duplicate Workspaces):**
Check whether a related task was already started in the workspace before creating new files.
Use `codebase_overview` and `glob_search` to identify existing work. Continue from existing
progress rather than restarting.

---

## 7. TERMINATION

**Rule T-1 (Structured Termination):**
Always call `terminate` with all three fields filled:
  - `status`: "success" | "failure" | "partial"
  - `summary`: what was actually accomplished (not what was attempted)
  - `reason`: the specific cause of any failure or blocker

**Rule T-2 (No Silent Exits):**
Do not end a task by simply stopping tool calls. If the max step limit is approaching, use the
second-to-last step to call `planning` to summarize state, then `terminate` with a full report.
