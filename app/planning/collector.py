from __future__ import annotations

import json
from typing import Tuple

from pydantic import ValidationError

from . import metrics
from .errors import JSONParseError, JSONRepairFailed, JSONSchemaError
from .json_repair import repair_json, strip_markdown_fences, trim_to_outermost_json
from .models import Plan


def extract_candidate_json(payload: str) -> str:
    """Prefere conteúdo em fences; senão recorta o JSON mais externo e tolera prosa fora."""
    s = strip_markdown_fences(payload)
    s = trim_to_outermost_json(s)
    return s.strip()


def parse_plan_payload(payload: str) -> Tuple[Plan, dict]:
    """Extrai, repara, faz json.loads e valida no schema Plan.
    Retorna (Plan, meta), onde meta contém notas dos reparos aplicados.
    """
    stop_total = metrics.timer()
    raw = extract_candidate_json(payload)
    try:
        repaired, notes = repair_json(raw)
    except Exception as e:
        metrics.inc("planning.repair_fail")
        raise JSONRepairFailed(
            f"Falha ao reparar JSON: {e!s}",
            hint="Verifique fences, vírgulas finais e balanceamento",
        ) from e
    try:
        data = json.loads(repaired)
    except Exception as e:
        metrics.inc("planning.parse_fail")
        raise JSONParseError(
            f"Falha ao fazer json.loads: {e!s}",
            hint="Revise aspas, comentários e caracteres ilegais",
        ) from e
    try:
        plan = Plan.model_validate(data)
    except ValidationError as e:
        metrics.inc("planning.schema_fail")
        raise JSONSchemaError(
            f"Falha de schema Plan: {e!s}",
            hint="Campos extras são proibidos (extra='forbid')",
        ) from e
    metrics.inc("planning.ok")
    stop_total("planning.total")
    return plan, {"notes": notes}


def parse_with_retries(payload: str, max_retries: int = 2) -> Plan:
    """Tenta parsear com até N retries determinísticos (pipeline idempotente)."""
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
