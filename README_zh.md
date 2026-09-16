<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

[English](README.md) | 中文 | [한국어](README_ko.md) | [日本語](README_ja.md)

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15186407.svg)](https://doi.org/10.5281/zenodo.15186407)

# 👋 OpenManus

Manus 非常棒，但 OpenManus 无需邀请码即可实现任何创意 🛫！

我们的团队成员 [@Xinbing Liang](https://github.com/mannaandpoem) 和 [@Jinyu Xiang](https://github.com/XiangJinyu)（核心作者），以及 [@Zhaoyang Yu](https://github.com/MoshiQAQ)、[@Jiayi Zhang](https://github.com/didiforgithub) 和 [@Sirui Hong](https://github.com/stellaHSR)，来自 [@MetaGPT](https://github.com/geekan/MetaGPT)团队。我们在 3
小时内完成了开发并持续迭代中！

这是一个简洁的实现方案，欢迎任何建议、贡献和反馈！

用 OpenManus 开启你的智能体之旅吧！

我们也非常高兴地向大家介绍 [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL)，这是一个专注于基于强化学习（RL，例如 GRPO）的方法来优化大语言模型（LLM）智能体的开源项目，由来自UIUC 和 OpenManus 的研究人员合作开发。

## 项目演示

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## 安装指南

我们提供两种安装方式。推荐使用方式二（uv），因为它能提供更快的安装速度和更好的依赖管理。

### 方式一：使用 conda

1. 创建新的 conda 环境：

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. 克隆仓库：

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

### 方式二：使用 uv（推荐）

1. 安装 uv（一个快速的 Python 包管理器）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. 克隆仓库：

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. 创建并激活虚拟环境：

```bash
uv venv --python 3.12
source .venv/bin/activate  # Unix/macOS 系统
# Windows 系统使用：
# .venv\Scripts\activate
```

4. 安装依赖：

```bash
uv pip install -r requirements.txt
```

### 浏览器自动化工具（可选）
```bash
playwright install
```

## 配置说明

OpenManus 需要配置使用的 LLM API，请按以下步骤设置：

1. 在 `config` 目录创建 `config.toml` 文件（可从示例复制）：

```bash
cp config/config.example.toml config/config.toml
```

2. 编辑 `config/config.toml` 添加 API 密钥和自定义设置：

```toml
# 全局 LLM 配置
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 替换为真实 API 密钥
max_tokens = 4096
temperature = 0.0

# 可选特定 LLM 模型配置
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 替换为真实 API 密钥
```

## 快速启动

一行命令运行 OpenManus：

```bash
python main.py
```

然后通过终端输入你的创意！

如需使用 MCP 工具版本，可运行：
```bash
python run_mcp.py
```

如需体验不稳定的多智能体版本，可运行：

```bash
python run_flow.py
```

## OrcaRouter

[OrcaRouter](https://www.orcarouter.ai) 是一个 OpenAI 兼容的 AI 网关，OpenManus 通过与其他 OpenAI 兼容服务商相同的 `api_type` 机制接入。提供两个 provider 入口，对应两种认证方式，最终都使用同一个 `sk-orca-...` 密钥访问 `https://api.orcarouter.ai/v1`。

| `api_type` | 认证方式 |
| --- | --- |
| `orcarouter` | 将已有的 `sk-orca-...` 密钥填入 `api_key`，或设置 `ORCAROUTER_API_KEY`。 |
| `orcarouter-oauth` | 运行 `orcarouter login`，在浏览器中授权（OAuth 2.0 + PKCE）。 |

```bash
# 方式一：使用已有密钥
export ORCAROUTER_API_KEY=sk-orca-...
# 方式二：使用 OrcaRouter 账号登录（打开浏览器，无需复制密钥）
orcarouter login
```

```toml
[llm]
api_type = "orcarouter"          # 或登录后使用 "orcarouter-oauth"
model = "orcarouter/auto"
base_url = "https://api.orcarouter.ai/v1"
api_key = "your OrcaRouter api key"   # 可留空以使用已存储或环境变量中的密钥
max_tokens = 16000
temperature = 0.0

[llm.vision]
api_type = "orcarouter"
model = "google/gemini-3.5-flash"     # 目录中任意支持图片输入的模型
base_url = "https://api.orcarouter.ai/v1"
api_key = "your OrcaRouter api key"
```

密钥属于你的 OrcaRouter 账号：计费归属于你，并可随时在 <https://www.orcarouter.ai/console/authorized-apps> 撤销。密钥保存在 `~/.openmanus/orcarouter.json`（权限 `0600`），不会写入本仓库。

```bash
orcarouter login            # 授权（API Key 或通过浏览器进行 PKCE 登录）
orcarouter login --code X   # 授权页显示 code 时使用 PKCE 完成登录
orcarouter status           # 查看已存储的凭据，以及是否需要重新认证
orcarouter models           # 通过 GET /v1/models 列出该密钥可调用的模型
orcarouter logout           # 删除已存储的凭据
```

自建 OrcaRouter 部署可通过 `ORCA_BASE_URL`（共用同一来源）或 `ORCA_AUTH_BASE_URL` / `ORCA_API_BASE_URL`（认证与推理分离）指向自有地址。除回环地址外必须使用 HTTPS。

模型 ID 完全沿用目录中的写法，保留 vendor 命名空间（`orcarouter/auto`、`google/gemini-3.5-flash`）。所有入口都通过同一个模型目录服务解析候选模型，因此选择器给出的选项始终是目录确认过的模型：chat 入口会排除图像/视频/rerank 模型，而会附带截图上传的入口只提供目录记录中显式声明 `image` 输入的模型。给纯文本模型附加图像会被拒绝，并给出模型 ID 与修复方式，而不是静默丢弃图像。`orcarouter models` 会按能力分别打印同样的过滤结果，并标记当前能力下已不再允许的已存模型。


## 添加自定义多智能体

目前除了通用的 OpenManus Agent, 我们还内置了DataAnalysis Agent，适用于数据分析和数据可视化任务，你可以在`config.toml`中将这个智能体加入到`run_flow`中
```toml
# run-flow可选配置
[runflow]
use_data_analysis_agent = true     # 默认关闭，将其改为true则为激活
```
除此之外，你还需要安装相关的依赖来确保智能体正常运行：[具体安装指南](app/tool/chart_visualization/README_zh.md##安装)


## 贡献指南

我们欢迎任何友好的建议和有价值的贡献！可以直接创建 issue 或提交 pull request。

或通过 📧 邮件联系 @mannaandpoem：mannaandpoem@gmail.com

**注意**: 在提交 pull request 之前，请使用 pre-commit 工具检查您的更改。运行 `pre-commit run --all-files` 来执行检查。

## 交流群

加入我们的飞书交流群，与其他开发者分享经验！

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star 数量

[![Star History Chart](https://api.star-history.com/svg?repos=FoundationAgents/OpenManus&type=Date)](https://star-history.com/#FoundationAgents/OpenManus&Date)


## 赞助商
感谢[PPIO](https://ppinfra.com/user/register?invited_by=OCPKCN&utm_source=github_openmanus&utm_medium=github_readme&utm_campaign=link) 提供的算力支持。
> PPIO派欧云：一键调用高性价比的开源模型API和GPU容器

## 致谢

特别感谢 [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
和 [browser-use](https://github.com/browser-use/browser-use) 为本项目提供的基础支持！

此外，我们感谢 [AAAJ](https://github.com/metauto-ai/agent-as-a-judge)，[MetaGPT](https://github.com/geekan/MetaGPT)，[OpenHands](https://github.com/All-Hands-AI/OpenHands) 和 [SWE-agent](https://github.com/SWE-agent/SWE-agent).

我们也感谢阶跃星辰 (stepfun) 提供的 Hugging Face 演示空间支持。

OpenManus 由 MetaGPT 社区的贡献者共同构建，感谢这个充满活力的智能体开发者社区！

## 引用
```bibtex
@misc{openmanus2025,
  author = {Xinbing Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Sheng Fan and Xiao Tang},
  title = {OpenManus: An open-source framework for building general AI agents},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.15186407},
  url = {https://doi.org/10.5281/zenodo.15186407},
}
```
