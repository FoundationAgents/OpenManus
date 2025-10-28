# OpenManus 项目概览与 Sandbox 机制梳理

## 1. 项目定位与运行入口
- OpenManus 致力于复刻并拓展 Manus 智能体，可通过命令行收集指令并在多种工具之间编排任务。默认入口为 `main.py`，会实例化 `app/agent/manus.py` 中的 `Manus` 智能体；日常使用时提供提示语后即可自动迭代直至终止。
- `sandbox_main.py` 提供了沙箱版的入口，调用 `SandboxManus`（见 `app/agent/sandbox_agent.py`），使智能体在远程、安全的执行环境中操作浏览器、终端与文件。
- 所有代理均继承自 `BaseAgent`（`app/agent/base.py`），该类封装了记忆、状态机、循环步长控制，并在 `run()` 结束时调用 `app/sandbox/client.py` 中的 `SANDBOX_CLIENT.cleanup()` 统一回收资源。

## 2. 整体架构快速映射
- **配置层**：`app/config.py` 读取 `config/config.toml`，构建 LLM、Daytona、Sandbox、MCP 等配置对象；`config/config.example-daytona.toml` 给出沙箱模式所需的字段。
- **LLM 与推理**：`app/llm`（此处未详述）封装对大模型的调用；`ToolCallAgent`（`app/agent/toolcall.py`）在推理过程中根据 `available_tools` 和工具调用记录驱动下一步动作。
- **工具体系**：`app/tool` 下提供常规工具（如 `PythonExecute`、`BrowserUseTool`、`StrReplaceEditor`）。沙箱场景会额外注入 `sandbox_*` 系列工具。
- **MCP 支持**：`SandboxManus` 与 `Manus` 均可通过 `app/tool/mcp.py` 中的 `MCPClients` 连接外部 Model Context Protocol 服务器，把远端工具纳入一次会话。

## 3. Provider 化的 Sandbox 结构
- 新增 `app/sandbox/providers` 层，定义 `SandboxProvider` 抽象以及 `Shell/File/Browser/Vision` service 接口。运行时根据 `config.toml` 中的 `sandbox.provider` 选择具体实现。
- `create_sandbox_provider()` 会读取配置并实例化对应后端（目前支持 `daytona` 与 `agentbay`），统一返回 `SandboxMetadata`（链接、ID 等）以及标准化 service。
- `SandboxManus.initialize_sandbox_tools()` 仅负责创建 provider、注册工具，不再直接依赖某个 IaaS SDK；`cleanup()` 则调用 provider 的 `cleanup()` 完成资源回收。

## 4. Daytona Provider
- `app/sandbox/providers/daytona_provider.py` 复用 Daytona SDK 创建远程容器，生成 VNC/Website 预览链接，并构建四类 service：
  - Shell：复用 tmux 会话，支持 execute/check/terminate/list，全流程与旧实现一致。
  - File：基于 `sandbox.fs` 提供读写/列目录/删除等操作。
  - Browser：继续通过容器内 `curl` 调用 automation API，返回结构化结果。
  - Vision：读取 `/workspace` 下图片并压缩为 base64。
- `docs/sandbox_refactor_plan.md` 中记录了 provider 的职责划分与扩展策略。

## 5. AgentBay Provider（实验性）
- `app/sandbox/providers/agentbay_provider.py` 调用 AgentBay SDK 创建云端 Session，当前提供 Shell 与 File service：
  - Shell：同步执行命令，返回 stdout；因缺乏 tmux，`check/list/terminate` 会返回错误提示。
  - File：复用 AgentBay FileSystem API 完成读/写/列目录；删除操作通过 shell `rm` 实现。
- Browser / Vision service 暂未接入（返回 `None`），因此在 AgentBay 模式下不会注册对应工具。
- 配置项位于 `[sandbox.agentbay]`，支持自定义 API endpoint、超时与 session 默认参数。

## 6. Sandbox 工具适配
- `SandboxShellTool` / `SandboxFilesTool` / `SandboxBrowserTool` / `SandboxVisionTool` 现在只依赖标准 service 接口，自动适配不同 provider。
  - Shell 工具会根据 service 能力返回统一的 JSON 结构；对于不支持的动作（如 AgentBay 的 check），会返回失败提示。
  - File 工具利用 `exists/read/write/delete` 等方法，保持与旧版同样的命令语义。
  - Browser 工具仍沿用原始的 action 名称（`navigate_to`、`click_element` 等），具体行为由 service 决定。
  - Vision 工具仅在 provider 提供实现时注册，返回 base64 编码的图片。

## 7. 生命周期与资源管理
- Provider 负责整个沙箱生命周期；`SandboxManus` 只与抽象接口交互，并在 metadata 中记录可用链接。
- Daytona 模式下仍提供 VNC/Website 预览地址；AgentBay 模式则回传控制台 resource URL。
- 本地 Docker 支持仍保留在 `app/sandbox/core/` 内，可按需扩展成新的 provider。

## 8. 与默认 Manus 的差异
- 默认 `Manus` 使用本地工具集（Python 执行、浏览器控制、字符串编辑等），直接作用于宿主机。
- `SandboxManus` 把所有高风险操作迁移至 Daytona 托管环境，通过浏览器/VNC 预览提供可视化反馈，消除了对宿主机的潜在破坏，同时仍复用了 MCP 扩展、记忆体系与调度逻辑。

## 9. 使用与扩展建议
- 在 `config/config.toml` 中填入 Daytona `daytona_api_key`、自定义 `sandbox_image_name`、`VNC_password` 等字段后再运行 `python sandbox_main.py`。
- 若需要扩展能力，可在 provider 层实现新的 service，并在 `initialize_sandbox_tools()` 中注册对应工具实例。
- 结合 `SandboxManager`（`app/sandbox/core/manager.py`）可实现本地批量容器调度，或与 Daytona 接入形成多环境选择。
- 生产环境建议对 `auto_stop_interval`、`auto_archive_interval`（见 `app/daytona/sandbox.py`）进行调优，以控制成本并缩短冷启动时间。
