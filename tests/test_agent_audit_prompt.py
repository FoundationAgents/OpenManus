from app.prompt.agent_audit import (
    ADVANCED_PLAYBOOKS,
    AUDIT_RUBRIC,
    EXAMPLE_REPORT,
    NEXT_STEP_PROMPT,
    PLAYBOOKS,
    REPORT_SCHEMA,
    SYSTEM_PROMPT,
    build_agent_audit_prompt,
)


def test_agent_audit_prompt_exposes_required_artifacts():
    assert "agent_check_scope.json" in SYSTEM_PROMPT
    assert "evidence_pack.json" in SYSTEM_PROMPT
    assert "failure_map.json" in SYSTEM_PROMPT
    assert "agent_check_report.json" in SYSTEM_PROMPT
    assert "Do not skip directly to recommendations." in NEXT_STEP_PROMPT


def test_agent_audit_schema_and_example_include_contamination_paths():
    assert REPORT_SCHEMA["schema_version"] == "agent-audit.report.v1"
    assert "contamination_paths" in REPORT_SCHEMA
    assert EXAMPLE_REPORT["schema_version"] == "agent-audit.report.v1"
    assert "contamination_paths" in EXAMPLE_REPORT
    assert EXAMPLE_REPORT["ordered_fix_plan"][0]["order"] == 1


def test_agent_audit_playbooks_and_rubric_cover_runtime_failure_modes():
    assert "wrapper-regression" in PLAYBOOKS
    assert "tool-discipline" in PLAYBOOKS
    assert "protocol-decay" in ADVANCED_PLAYBOOKS
    assert any("Tool discipline" in item for item in AUDIT_RUBRIC)


def test_build_agent_audit_prompt_includes_selected_playbook_and_schema():
    prompt = build_agent_audit_prompt("tool-discipline")
    assert "Selected playbook: tool-discipline" in prompt
    assert PLAYBOOKS["tool-discipline"] in prompt
    assert "Report schema:" in prompt
    assert "contamination_paths" in prompt
