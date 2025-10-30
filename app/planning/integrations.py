from __future__ import annotations

import json
import os

from .collector import parse_with_retries
from .models import Plan


def parse_plan_text(
    text: str, *, max_retries: int = 2, env_var: str = "OPENMANUS_PLANNING_REPAIR"
) -> Plan:
    """
    Parse a plan JSON string from an LLM into a Plan.

    If the env var is unset or not "0", run robust repair+validate (parse_with_retries).
    If the env var equals "0", run the strict fallback: json.loads -> Plan.model_validate.
    """
    if os.getenv(env_var, "1") != "0":
        return parse_with_retries(text, max_retries=max_retries)
    data = json.loads(text)  # strict mode
    return Plan.model_validate(data)
