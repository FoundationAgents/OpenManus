# Planning JSON Repair & Integration

This document describes the robust JSON parsing pipeline for LLM-produced plans, how it is integrated, how to toggle it, and how to test/troubleshoot it.

---

## What problem this solves

LLMs often output “almost JSON” with:
- Markdown code fences
- Smart quotes (“ ” ‘ ’)
- JS-style comments (//, /* ... */)
- Trailing commas ([1,2,] / {"a":1,})
- Missing closing braces/brackets by one
- Raw newlines/tabs inside string values

The repair pipeline normalizes these safely before validation, so downstream code doesn’t break on minor formatting defects.

---

## Public API (Python)

**Models**
- app.planning.models.Step
- app.planning.models.Plan

**Repair / Parse**
- app.planning.integrations.parse_plan_text(text: str, max_retries=2) -> Plan
  The recommended entry point. Enabled by default (repair+validate). Respects OPENMANUS_PLANNING_REPAIR env toggle.
- app.planning.collector.parse_with_retries(payload: str, max_retries=2) -> Plan
  Lower-level helper (used by parse_plan_text when the toggle is on).
- app.planning.collector.parse_plan_payload(payload: str) -> tuple[Plan, dict]
  Returns (Plan, meta) where meta["notes"] lists which repair passes were applied.

**Errors**
- JSONRepairFailed, JSONParseError, JSONSchemaError (all inherit PlanningError)

**Metrics**
- app.planning.metrics.snapshot() -> dict[str, int] returns counters such as:
  - planning.ok, planning.repair_fail, planning.parse_fail, planning.schema_fail, planning.retry
  - planning.total_ms_total, planning.total_count

---

## Integration point

The robust parse is wired in app/flow/planning.py where we convert the LLM’s tool call arguments into a plan:

    from app.planning.integrations import parse_plan_text

    # args is a string returned by the LLM:
    _plan_obj = parse_plan_text(args, max_retries=2)
    args = _plan_obj.model_dump()  # keep original dict-based behavior downstream

A compatibility fallback to strict json.loads is kept in a try/except so we can quickly revert behavior if needed.

---

## Environment toggle

- Default (enabled): Repair + validation are ON.
- Disable (strict mode):

    export OPENMANUS_PLANNING_REPAIR=0

In strict mode we do:

    json.loads(text) -> Plan.model_validate(data)

(No repair is attempted; invalid JSON will raise immediately.)

---

## How the repair works (high level)

1) Safe structural slicing
   - Remove Markdown code fences if present
   - Slice from the first '{' to the last '}' (tolerate prose outside)
   - Establish a sanity baseline after these two steps

2) Normalization & cleanup (string-aware)
   - Normalize Unicode/smart quotes to ASCII quotes
   - Remove // and /* … */ comments outside strings
   - Remove trailing commas even if whitespace/newlines precede ']' or '}'
   - Escape
//	 only inside strings
   - Append exactly one missing '}' or ']' if that single closure fixes balance

3) Safety guard
   - Reject repairs that remove more than 30% of characters vs. baseline

If the pipeline succeeds, we json.loads() then validate using Pydantic (Plan.model_validate).

---

## Quick usage examples

Robust parse (default ON):

    from app.planning.integrations import parse_plan_text

    raw = "```json\n{“version”: \"1.0\", \"objective\": \"Demo\", \"steps\":[{\"id\":\"s1\",\"title\":\"T\",\"description\":\"D\",\"tool\":\"python\",\"expected_output\":\"Y\"}],}\n```"
    plan = parse_plan_text(raw)  # -> Plan
    print(plan.version, plan.objective)

Strict mode (no repair):

    export OPENMANUS_PLANNING_REPAIR=0

    from app.planning.integrations import parse_plan_text
    parse_plan_text('{"version": "1.0", "steps":[1,2,], }')  # raises JSONDecodeError (as expected)

---

## Metrics and logging

In PlanningFlow, after parsing:

    from app.planning.metrics import snapshot as planning_metrics_snapshot
    logger.info("planning_metrics=%s", planning_metrics_snapshot())

Example snapshot:

    {'planning.ok': 1, 'planning.total_ms_total': 2, 'planning.total_count': 1}

---

## Tests

Run only the planning tests:

    export PYTHONPATH=$PWD
    pytest -q tests/planning

They cover:
- Fence extraction, smart quotes, comments removal
- Trailing commas (with and without whitespace/newlines)
- Single-missing brace/bracket repair
- Full repair pipeline
- Collector behavior and retry budget
- Pydantic schema strictness (extra='forbid')

---

## Troubleshooting

- ModuleNotFoundError: No module named 'app'
  Ensure 'export PYTHONPATH=$PWD' when running tests locally.

- Pre-commit hooks reformat files and abort commit
  Run 'git add -A && pre-commit run -a' and then commit again.

- Repair rejected with “Unsafe repair delta”
  The pipeline avoids large destructive edits. If you intentionally pass huge comments or non-JSON prose, either fix the prompt to return cleaner JSON or (temporarily) use strict mode with OPENMANUS_PLANNING_REPAIR=0.

---

## File map

- Core:
  - app/planning/models.py — Pydantic Plan and Step
  - app/planning/json_repair.py — Repair passes
  - app/planning/collector.py — Extract → repair → json.loads → validate
  - app/planning/integrations.py — parse_plan_text adapter with env toggle
  - app/planning/metrics.py — lightweight counters

- Tests:
  - tests/planning/ — unit tests for repair, collector, models

- Integration:
  - app/flow/planning.py — robust parsing wired into PlanningFlow

---

## Design notes

- Deterministic, string-aware passes; no regex-only “parse JSON” tricks.
- Conservative autoclosing (at most one missing '}' or ']' is appended).
- Repair notes are available via parse_plan_payload if introspection is needed.
- Env toggle provides an easy kill-switch for debugging or if your model starts producing fully-valid JSON and you want strictness.
