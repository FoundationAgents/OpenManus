# DeepSpec Research Integration

## Overview
DeepSpec is an advanced speculative decoding research and evaluation framework developed by DeepSeek for exploring efficient inference acceleration techniques with large language models.

This integration provides an opt-in research path within OpenManus for evaluating speculative decoding draft models against target models.

## Crucial Architecture Notice
- **Not Required for Runtime**: DeepSpec is strictly an optional research and evaluation tool. It is **not enabled** by default and is not built into the standard OpenManus production Docker container (`make build`).
- **Resource Intensive**: Speculative decoding research workflows and target cache generation require substantial GPU compute and storage resources. For instance, default target cache generation for `Qwen/Qwen3-4B` can exceed roughly **38 TB** of disk storage. Use this integration exclusively for dedicated high-performance research environments.

## Configuration
To configure DeepSpec research settings in OpenManus, add or edit the `[deepspec]` section in your `config.toml`:

```toml
[deepspec]
enabled = false
repo_url = "https://github.com/deepseek-ai/DeepSpec"
checkout_dir = "research/deepspec"
mode = "research"
target_model = "Qwen/Qwen3-4B"
```

## Preparation & Setup
To prepare the upstream research repository without triggering any automatic training or cache generation, run the helper script:

```bash
./scripts/prepare_deepspec_research.sh
```

This script clones or updates the upstream DeepSpec repository into `research/deepspec/upstream/`.

## Workflow
Once the upstream repository is prepared:
1. Review the upstream data preparation instructions inside `research/deepspec/upstream/README.md`.
2. Prepare target model logits and hidden state caches on a dedicated high-capacity storage volume.
3. Run evaluation scripts against your draft models using the prepared target cache.
