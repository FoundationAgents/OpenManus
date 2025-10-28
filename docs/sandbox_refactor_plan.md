# Sandbox 抽象与多后端集成设计草案

## 目标
- 统一封装 Sandbox 能力，运行时可根据配置选择 Daytona 或 AgentBay。
- 尽量保持工具层接口不变，降低对 Prompt/LLM 的影响。
- 兼顾生命周期管理、配置扩展与资源清理，避免不同后端带来的资源泄漏。

## 现状速览

### Daytona
- `SandboxToolsBase` 直接持有 Daytona `Sandbox`，访问 `process`/`fs` 等原生接口。
- `SandboxShellTool` 依赖 tmux 支持后台执行、输出查询、会话终止。
- 文件工具直接操作 `/workspace`，适合高频小文件。
- 浏览器工具经容器内 HTTP API 驱动，同时提供 VNC/Website 预览链接。
- `SandboxManus.cleanup()` 最终调用 `delete_sandbox()` 释放容器。

### AgentBay
- `AgentBay.create()` 创建云 Session 并返回 `Session` 对象，内部通过 MCP 工具提供命令、文件、浏览器等能力。
- Shell：`session.command.execute_command()` 同步返回 stdout，不具备 tmux 等会话管理。
- 文件：`FileSystem` + `FileTransfer` 配合 Context Sync，支持预签名 URL 传输大文件。
- 浏览器：`Browser.initialize()` 获取 CDP/WSS 端点，具体操作由 `BrowserAgent.page_use_*` 完成。
- 资源清理：`AgentBay.delete(session)` 删除会话，可选择触发 Context 同步。

## 抽象层设计思路

### Provider 接口
```python
class SandboxProvider(ABC):
    async def initialize(self) -> None: ...
    async def cleanup(self) -> None: ...
    def shell_service(self) -> ShellService: ...
    def file_service(self) -> FileService: ...
    def browser_service(self) -> Optional[BrowserService]: ...
    def vision_service(self) -> Optional[VisionService]: ...
    def metadata(self) -> SandboxMetadata: ...
```

### Service 接口示例
```python
class ShellService(ABC):
    async def execute(self, command: str, *, cwd: Optional[str],
                      timeout: Optional[int], blocking: bool,
                      session: Optional[str]) -> ShellResult: ...
    async def check(self, session: str) -> ShellResult: ...
    async def terminate(self, session: str) -> None: ...
    async def list_sessions(self) -> list[str]: ...
```

> 说明：AgentBay 原生不支持 `check/list_sessions`，策略模式下可返回“非实现”提示，或在工具描述里声明限制。

### ProviderFactory
- 按 `config.sandbox.provider` 选择具体实现。
- Daytona / AgentBay 配置分节管理，缺省值与兼容逻辑写入 `config`.

### 工具层调整
- `SandboxManus.initialize_sandbox_tools()` 调用 Factory，获取 Service 后构造工具。
- Daytona 版工具迁移到新的 Provider 基类，保持当前功能。
- AgentBay 版工具：
  - Shell：封装同步执行；必要时扩展后台执行策略。
  - Files：整合 `FileSystem` 与 `FileTransfer`，提供读写、列目录、删除。
  - Browser：对接 `BrowserAgent`，把返回内容整理成与现有 Prompt 兼容的数据结构。
  - Vision：基于文件读写或浏览器截图生成 base64。

## 配置扩展
```toml
[sandbox]
provider = "daytona" # or "agentbay"

[sandbox.daytona]
# 复用当前字段

[sandbox.agentbay]
api_key = ""
endpoint = "wuyingai.cn-shanghai.aliyuncs.com"
timeout_ms = 60000
session_defaults = { image_id = "", is_vpc = false }
```

## 风险点
- AgentBay Shell 能力弱，需更新工具提示，避免 LLM 依赖 tmux 功能。
- 文件操作依赖 Context Sync，配置不当会导致读写失败。
- 浏览器初始化成本高，需要良好错误处理与重试。
- 引入 AgentBay SDK 需更新 `requirements.txt`，并保证网络可达。
- 必须确保异常路径也执行 `cleanup()`，防止产生付费 Session。

## 实施顺序
1. 引入 Provider 抽象 & Factory，不改变现有 Daytona 行为。
2. 将 Daytona 工具改造为 Provider 实现，完成兼容验证。
3. 实现 AgentBay Provider，提供 Shell / File / Browser 基础能力。
4. 更新 `SandboxManus` 初始化、配置与文档，执行手动验证。
5. 后续增强：AgentBay Vision、Context Sync 插件化、错误处理完善。

