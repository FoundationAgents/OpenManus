# Sandbox Providers Overview

This directory hosts the sandbox integration layer for OpenManus. The sandbox is responsible for executing high‑risk operations (shell, browser automation, desktop control, mobile actions, etc.) in isolated environments. Two providers are currently supported:

| Provider | Capabilities | Key files | Notes |
|----------|--------------|-----------|-------|
| **Daytona** | Shell, File, Browser, Vision | `app/daytona/` and `app/sandbox/providers/daytona_provider.py` | Requires a Daytona account and API key. |
| **AgentBay** | Shell, File, Browser, Computer (desktop), Mobile | `app/sandbox/providers/agentbay_provider.py` | Requires access to AgentBay cloud resources. |

## How it works

1. `app/sandbox/providers/base.py` defines common service interfaces (`ShellService`, `BrowserService`, `ComputerService`, etc.) and the `SandboxProvider` base class.
2. `app/sandbox/providers/factory.py` reads `config/config.toml` to instantiate the correct provider.
3. `SandboxManus` (`app/agent/sandbox_agent.py`) requests the provider and injects the provider-specific tools (e.g., `sandbox_shell`, `sandbox_browser`, `sandbox_mobile`) into the agent.
4. Cleanup is unified through `SandboxProvider.cleanup()`, ensuring remote sessions are released when the agent stops.

## Choosing a provider

Set the provider in `config/config.toml`:

```toml
[sandbox]
provider = "agentbay"  # or "daytona"
use_sandbox = true
```

### AgentBay setup

1. Install dependencies (already declared in `requirements.txt`, including `wuying-agentbay-sdk`).
2. Create an AgentBay API key by following the official guide: https://help.aliyun.com/zh/agentbay/user-guide/service-management. The service provides a limited trial quota after the key is created—make sure you finish the console steps before running the agent.
3. Copy `config/config.example-agentbay.toml` to your working config and fill in the `[sandbox.agentbay]` section with your API key and image IDs.
4. Run `python sandbox_main.py`. The agent will register shell, file, browser, desktop, and mobile tools backed by AgentBay.
5. Watch the logs for session links to inspect the remote desktop or device.

### Daytona setup

1. Follow the instructions in `app/daytona/README.md` to configure your Daytona API key and sandbox image.
2. Ensure `provider = "daytona"` in `config/config.toml`.
3. Launch `python sandbox_main.py` to use the Daytona-backed tools (shell, file, browser, vision).

## Adding new providers

1. Implement a new provider class in `app/sandbox/providers/` that inherits from `SandboxProvider`.
2. Provide concrete service implementations for any capabilities you support.
3. Register the provider name in `app/sandbox/providers/factory.py`.
4. Update this README and the configuration examples to document the new option.

Keeping the provider abstraction consistent allows the agents and tools to remain agnostic about the underlying execution environment.
