from __future__ import annotations

import json
from typing import Tuple

from pydantic import ValidationError

from . import metrics
from .errors import JSONParseError, JSONRepairFailed, JSONSchemaError
from .json_repair import repair_json, strip_markdown_fences, trim_to_outermost_json
from .models import Plan


def extract_candidate_json(payload: str) -> str:
    """Prefer fenced content; otherwise slice the outermost JSON and tolerate trailing prose."""
    s = strip_markdown_fences(payload)
    s = trim_to_outermost_json(s)
    return s.strip()


def parse_plan_payload(payload: str) -> Tuple[Plan, dict]:
    """Extract, repair, json.loads, and validate into Plan.
    Returns (Plan, meta) where meta contains notes of applied repairs.
    """
    stop_total = metrics.timer()
    raw = extract_candidate_json(payload)
    try:
        repaired, notes = repair_json(raw)
    except Exception as e:
        metrics.inc("planning.repair_fail")
        raise JSONRepairFailed(
            f"Failed to repair JSON: {e!s}",
            hint="Check code fences, trailing commas, and brace balance",
        ) from e
    try:
        data = json.loads(repaired)
    except Exception as e:
        metrics.inc("planning.parse_fail")
        raise JSONParseError(
            f"json.loads failed: {e!s}",
            hint="Review quotes, comments, and illegal characters",
        ) from e
    try:
        plan = Plan.model_validate(data)
    except ValidationError as e:
        metrics.inc("planning.schema_fail")
        raise JSONSchemaError(
            f"Plan schema failed: {e!s}",
            hint="Extra fields are forbidden (extra='forbid')",
        ) from e
    metrics.inc("planning.ok")
    stop_total("planning.total")
    return plan, {"notes": notes}


def parse_with_retries(payload: str, max_retries: int = 2) -> Plan:
    """Try to parse with up to N deterministic retries (idempotent pipeline)."""
    last_err: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            plan, _meta = parse_plan_payload(payload)
            return plan
        except (JSONRepairFailed, JSONParseError, JSONSchemaError) as e:
            last_err = e
            metrics.inc("planning.retry")
            continue
    assert last_err is not None
    raise last_err
