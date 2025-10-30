import json

import pytest

from app.planning.collector import (
    extract_candidate_json,
    parse_plan_payload,
    parse_with_retries,
)


def fenced_payload(body: str) -> str:
    backticks = "`" * 3
    return f"blabla\n{backticks}json\n{body}\n{backticks}\nfim\n"


def test_extract_candidate_json_prefers_fences():
    payload = fenced_payload('{"k": 1}')
    s = extract_candidate_json(payload)
    assert s.startswith("{") and s.endswith("}")
    assert json.loads(s) == {"k": 1}


def test_parse_plan_payload_ok():
    plan_json = """
    {
      "version": "1.0",
      "objective": "Demo",
      "constraints": [],
      "success_criteria": ["ok"],
      "steps": [
        {"id":"s1","title":"T1","description":"D","depends_on":[],
         "tool":"python","inputs":{"x":1},"expected_output":"Y"}
      ],
      "notes": "teste"
    }
    """
    payload = fenced_payload(plan_json.strip())
    plan, meta = parse_plan_payload(payload)
    assert plan.version == "1.0"
    assert plan.steps[0].tool == "python"
    assert "notes" in meta


def test_parse_with_retries_stops_within_budget():
    bad = "not a json at all"
    with pytest.raises(Exception) as exc:
        parse_with_retries(bad, max_retries=2)
    assert any(
        k in type(exc.value).__name__ for k in ("JSONRepairFailed", "JSONParseError")
    )
