# AgentBay Python SDK API Reference

Complete API reference documentation for the AgentBay Python SDK.

## 📚 Common Features

APIs available across all environments:

### Basics
- [**AgentBay**](agentbay.md) - Main client for creating and managing sessions
- [**Session**](session.md) - Session lifecycle and operations management
- [**Command**](command.md) - Execute shell commands in cloud environments
- [**FileSystem**](filesystem.md) - File and directory operations
- [**Context**](context.md) - Data persistence and context management
- [**ContextManager**](context-manager.md) - Context operations and file synchronization

### Advanced
- [**Agent**](agent.md) - AI agent integration and MCP tools
- [**OSS**](oss.md) - Object Storage Service integration

## 🚀 Environment-Specific Features

### Browser Use (`browser_latest`)
- **Browser** - Browser initialization and CDP connection
  - `initialize()` / `initialize_async()` - Initialize browser with configuration options
  - `get_endpoint_url()` - Get CDP WebSocket endpoint for Playwright/Puppeteer connection
  - Options: Stealth mode, proxy (custom/wuying), fingerprint, viewport, CAPTCHA solving
  - AI Agent: `agent.act()`, `agent.observe()`, `agent.extract()` for natural language automation
- [**Extension**](extension.md) - Browser extension management and deployment

### Computer Use (`windows_latest`, `linux_latest`)
- [**Computer**](computer.md) - Desktop automation operations
  - Mouse: `click_mouse()`, `move_mouse()`, `drag_mouse()`, `scroll()`, `get_cursor_position()`
  - Keyboard: `input_text()`, `press_keys()`, `release_keys()`
  - Screen: `screenshot()`, `get_screen_size()`
  - Window: `list_root_windows()`, `get_active_window()`, `activate_window()`, `close_window()`, `maximize_window()`, `minimize_window()`, `restore_window()`, `resize_window()`, `fullscreen_window()`, `focus_mode()`
  - Application: `get_installed_apps()`, `start_app()`, `list_visible_apps()`, `stop_app_by_pname()`, `stop_app_by_pid()`, `stop_app_by_cmd()`
- [**UI**](ui.md) - ⚠️ Deprecated, use Computer or Mobile APIs instead
- [**Window**](window.md) - ⚠️ Deprecated, use Computer API instead
- [**Application**](application.md) - ⚠️ Deprecated, use Computer or Mobile APIs instead

### Mobile Use (`mobile_latest`)
- [**Mobile**](mobile.md) - Android mobile device automation
  - Touch: `tap()`, `swipe()`
  - Input: `input_text()`, `send_key()` (with KeyCode constants)
  - UI Elements: `get_clickable_ui_elements()`, `get_all_ui_elements()`
  - Application: `get_installed_apps()`, `start_app()`, `stop_app_by_cmd()`
  - Screen: `screenshot()`

### CodeSpace (`code_latest`)
- [**Code**](code.md) - Execute code in cloud environment
  - `run_code()` - Run Python or JavaScript code with timeout control
  - Supports: Python, JavaScript
  - Maximum execution time: 60 seconds (gateway limitation)

## 📘 Related Documentation

- [Feature Guides](../../../docs/guides/README.md) - Detailed usage guides and tutorials
- [Code Examples](../examples/README.md) - Complete example implementations
- [Quick Start](../../../docs/quickstart/README.md) - Get started in 5 minutes

---

**Need help?** Check out the [complete documentation](../../../docs/README.md) or [open an issue](https://github.com/aliyun/wuying-agentbay-sdk/issues).
