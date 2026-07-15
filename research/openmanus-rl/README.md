# OpenManus-RL Integration Workspace

This directory is the local integration workspace for reinforcement-learning
experiments and policy export.

## Goal

Keep the production runtime stable while allowing fast RL iteration in one
repository.

## Recommended layout

`research/openmanus-rl/`

- `artifacts/policy/latest/policy.md`: active policy guidance consumed by runtime
- `artifacts/policy/latest/metadata.json`: optional metadata for traceability
- `upstream/`: optional checkout of `OpenManus/OpenManus-RL`

## Pulling upstream code

You can choose one of the following:

1. Submodule:
   `git submodule add https://github.com/OpenManus/OpenManus-RL.git research/openmanus-rl/upstream`
2. Subtree:
   `git subtree add --prefix=research/openmanus-rl/upstream https://github.com/OpenManus/OpenManus-RL.git main --squash`
3. Plain clone (no git linkage):
   `git clone --recursive https://github.com/OpenManus/OpenManus-RL.git research/openmanus-rl/upstream`

## Exporting policies into runtime

Use:

`python scripts/export_policy.py --policy-file <path-to-policy.md> --model <model-name> --benchmark <benchmark-name> --run-id <run-id>`

This updates:

- `research/openmanus-rl/artifacts/policy/latest/policy.md`
- `research/openmanus-rl/artifacts/policy/latest/metadata.json`

Runtime can then consume it by enabling:

```toml
[rl]
enabled = true
policy_mode = "rl"
```
