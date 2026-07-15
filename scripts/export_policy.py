#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export RL policy artifacts into OpenManus runtime layout."
    )
    parser.add_argument(
        "--policy-file",
        required=True,
        help="Path to policy markdown text.",
    )
    parser.add_argument("--model", default="unknown", help="Model name.")
    parser.add_argument("--benchmark", default="unknown", help="Benchmark name.")
    parser.add_argument("--run-id", default="manual", help="Run identifier.")
    parser.add_argument("--notes", default="", help="Optional notes.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    source_policy = Path(args.policy_file).resolve()
    if not source_policy.exists():
        raise FileNotFoundError(f"Policy file not found: {source_policy}")

    target_dir = root / "research" / "openmanus-rl" / "artifacts" / "policy" / "latest"
    target_dir.mkdir(parents=True, exist_ok=True)

    policy_text = source_policy.read_text(encoding="utf-8").strip()
    if not policy_text:
        raise ValueError("Policy file is empty")

    (target_dir / "policy.md").write_text(policy_text + "\n", encoding="utf-8")
    metadata = {
        "run_id": args.run_id,
        "model": args.model,
        "benchmark": args.benchmark,
        "notes": args.notes,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_policy_file": str(source_policy),
    }
    (target_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Exported policy to: {target_dir / 'policy.md'}")
    print(f"Exported metadata to: {target_dir / 'metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
