"""Structured audit prompts for diagnosing agent runtime failures.

This module provides a reusable prompt pack for auditing agent wrappers,
memory layers, tool routing, and delivery paths. It is intentionally data-first:
agents should build structured audit artifacts before writing prose findings.
"""

SYSTEM_PROMPT = """You are an agent runtime auditor.

Audit the agent system itself, not the user's domain task. Focus on wrapper
regression, tool-discipline failures, stale memory contamination, hidden repair
layers, rendering or transport mutation, and confidence without evidence.

Work evidence-first and JSON-first. Build these artifacts before rendering a
human-facing diagnosis:

1. agent_check_scope.json
2. evidence_pack.json
3. failure_map.json
4. agent_check_report.json

Prefer direct evidence: source code, config, logs, payloads, database rows,
screenshots, and tests. Prefer code and configuration fixes over prompt-only
fixes. Do not blame the base model unless wrapper layers have been falsified.
"""

NEXT_STEP_PROMPT = """Choose the next audit action.

1. If scope is unclear, define agent_check_scope.json.
2. If evidence is missing, collect evidence before diagnosing.
3. If evidence exists, build failure_map.json.
4. If failure_map.json exists, build agent_check_report.json.
5. If the report exists, render severity-ranked findings and the ordered fix plan.

Do not skip directly to recommendations.
"""

REPORT_SCHEMA = {
    "schema_version": "agent-audit.report.v1",
    "executive_verdict": {
        "overall_health": "critical | high_risk | unstable | acceptable | strong",
        "primary_failure_mode": "string",
        "most_urgent_fix": "string",
    },
    "scope": {
        "target_name": "string",
        "entrypoints": ["string"],
        "channels": ["string"],
        "model_stack": ["string"],
        "time_window": "string",
        "layers_to_audit": [
            "system_prompt",
            "session_history",
            "long_term_memory",
            "distillation",
            "active_recall",
            "tool_selection",
            "tool_execution",
            "tool_interpretation",
            "answer_shaping",
            "platform_rendering",
            "fallback_loops",
            "persistence",
        ],
    },
    "evidence_pack": [
        {
            "kind": "code | log | db | config | screenshot | test",
            "source": "string",
            "location": "string",
            "summary": "string",
            "time_scope": "historical | current | mixed",
        }
    ],
    "findings": [
        {
            "severity": "critical | high | medium | low",
            "title": "string",
            "symptom": "string",
            "user_impact": "string",
            "source_layer": "string",
            "mechanism": "string",
            "root_cause": "string",
            "evidence_refs": ["string"],
            "confidence": 0.0,
            "fix_type": "code | config | prompt_removal | architecture | data_cleanup",
            "recommended_fix": "string",
        }
    ],
    "conflict_map": [
        {
            "from_layer": "string",
            "to_layer": "string",
            "conflict_type": (
                "duplication | contradiction | stale_state | hidden_mutation | "
                "freeform_overwrite"
            ),
            "note": "string",
        }
    ],
    "contamination_paths": [
        {
            "origin_layer": "string",
            "affected_layer": "string",
            "artifact": "string",
            "failure_mode": "string",
            "note": "string",
        }
    ],
    "ordered_fix_plan": [
        {
            "order": 1,
            "goal": "string",
            "why_now": "string",
            "expected_effect": "string",
        }
    ],
}

PLAYBOOKS = {
    "wrapper-regression": (
        "Use when the base model seems strong but the wrapped agent behaves worse. "
        "Focus on wrapper layering, duplicated context injection, hidden formatting "
        "or fallback layers, and answer degradation after orchestration."
    ),
    "memory-contamination": (
        "Use when old topics or stale artifacts bleed into current turns. Focus on "
        "same-session artifact reentry, stale session reuse, weak memory admission, "
        "and aggressive distillation cadence."
    ),
    "tool-discipline": (
        "Use when the agent should have used a tool but did not, or when tool evidence "
        "was available but the conclusion drifted. Focus on code-enforced versus "
        "prompt-enforced tool requirements."
    ),
    "rendering-transport": (
        "Use when the answer seems correct internally but is broken in delivery. Focus "
        "on payload shape assumptions, deterministic fallback behavior, and platform "
        "mutations."
    ),
    "hidden-agent-layers": (
        "Use when repair, retry, summarize, or recap loops are hidden in the stack. "
        "Focus on second-pass model calls and undocumented repair behavior."
    ),
}

ADVANCED_PLAYBOOKS = {
    "false-confidence": "Confidence without evidence or definitive wording after weak probes.",
    "stale-evidence-replay": "Old outputs repeated as if they were current.",
    "fake-agentic-depth": "More orchestration layers produce less reliable answers.",
    "hidden-repair-brain": "Fallback code silently launches another model pass.",
    "memory-poisoning": "Assistant self-talk becomes durable knowledge.",
    "protocol-decay": "Internal state is carried as prose instead of typed data.",
}

AUDIT_RUBRIC = [
    "Context cleanliness: duplicated context, stale carryover, artifact reentry.",
    "Tool discipline: prompt-only instructions versus code-enforced requirements.",
    "Failure handling: retry, repair, fallback, and semantic mutation paths.",
    "Memory admission: durable facts must be evidence-backed.",
    "Answer shaping: final prose should be rendered from structured evidence.",
    "Hidden agent layers: recap, repair, summarize, or transport logic acting as agents.",
    "JSON vs freeform boundary: internal state should stay typed.",
]

EXAMPLE_REPORT = {
    "schema_version": "agent-audit.report.v1",
    "executive_verdict": {
        "overall_health": "high_risk",
        "primary_failure_mode": "stale evidence is reused as current truth",
        "most_urgent_fix": "enforce code-level fresh probes for operational queries",
    },
    "findings": [
        {
            "severity": "critical",
            "title": "Operational answers can bypass real inspection",
            "symptom": "The agent gives confident system-state answers before tools run.",
            "source_layer": "tool_selection",
            "root_cause": "Prompt-enforced discipline instead of code-enforced discipline.",
            "recommended_fix": (
                "Introduce task classification plus mandatory probe execution before "
                "final answer generation."
            ),
        }
    ],
    "contamination_paths": [
        {
            "origin_layer": "session_history",
            "affected_layer": "tool_selection",
            "artifact": "stale operational observation",
            "failure_mode": "stale_state",
            "note": "A previous observation biases current-turn tool routing.",
        }
    ],
    "ordered_fix_plan": [
        {
            "order": 1,
            "goal": "Force fresh probes for system-state queries",
            "why_now": "It removes the most damaging correctness failure immediately.",
            "expected_effect": "Wrong operational answers drop sharply.",
        }
    ],
}


def build_agent_audit_prompt(playbook: str = "wrapper-regression") -> str:
    """Build a compact prompt containing the schema, playbook, and rubric."""
    selected_playbook = PLAYBOOKS.get(playbook, PLAYBOOKS["wrapper-regression"])
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Selected playbook: {playbook}\n"
        f"{selected_playbook}\n\n"
        "Rubric:\n"
        + "\n".join(f"- {item}" for item in AUDIT_RUBRIC)
        + "\n\nReport schema:\n"
        + str(REPORT_SCHEMA)
    )
