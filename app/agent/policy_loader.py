import json
from pathlib import Path
from typing import Optional

from app.config import config


def _read_text(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_json(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_rl_policy_context() -> str:
    """Return an optional RL policy context block for Manus.

    This hook is intentionally lightweight: if policy files are missing, the
    default behavior remains unchanged.
    """
    if not config.rl.enabled or config.rl.policy_mode.lower() != "rl":
        return ""

    root = config.root_path
    policy_path = root / config.rl.policy_path
    metadata_path = root / config.rl.metadata_path

    policy_text = _read_text(policy_path)
    if not policy_text:
        return ""

    metadata = _read_json(metadata_path) or {}
    benchmark = metadata.get("benchmark", "unknown")
    model_name = metadata.get("model", "unknown")
    run_id = metadata.get("run_id", "unknown")

    return (
        "RL policy context is enabled for this run.\n"
        f"- Benchmark source: {benchmark}\n"
        f"- Tuned model family: {model_name}\n"
        f"- Policy run id: {run_id}\n\n"
        "Policy guidance:\n"
        f"{policy_text}"
    )
