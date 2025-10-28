# AgentBay Golang SDK API Reference

Complete API reference documentation for the AgentBay Golang SDK.

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
> **Note**: Browser Use APIs are not yet available in Golang SDK. Use Python or TypeScript SDK for browser automation.

### Computer Use (`windows_latest`, `linux_latest`)
- [**Computer**](computer.md) - Desktop automation operations
  - Mouse: `ClickMouse()`, `MoveMouse()`, `DragMouse()`, `Scroll()`, `GetCursorPosition()`
  - Keyboard: `InputText()`, `PressKeys()`, `ReleaseKeys()`
  - Screen: `Screenshot()`, `GetScreenSize()`
  - Window: `ListRootWindows()`, `GetActiveWindow()`, `ActivateWindow()`, `CloseWindow()`, `MaximizeWindow()`, `MinimizeWindow()`, `RestoreWindow()`, `ResizeWindow()`, `FullscreenWindow()`, `FocusMode()`
  - Application: `GetInstalledApps()`, `StartApp()`, `ListVisibleApps()`, `StopAppByPName()`, `StopAppByPID()`, `StopAppByCmd()`
- [**UI**](ui.md) - ⚠️ Deprecated, use Computer or Mobile APIs instead
- [**Window**](window.md) - ⚠️ Deprecated, use Computer API instead
- [**Application**](application.md) - ⚠️ Deprecated, use Computer or Mobile APIs instead

### Mobile Use (`mobile_latest`)
- [**Mobile**](mobile.md) - Android mobile device automation
  - Touch: `Tap()`, `Swipe()`
  - Input: `InputText()`, `SendKey()` (with KeyCode constants)
  - UI Elements: `GetClickableUIElements()`, `GetAllUIElements()`
  - Application: `GetInstalledApps()`, `StartApp()`, `StopAppByPName()`
  - Screen: `Screenshot()`

### CodeSpace (`code_latest`)
- [**Code**](code.md) - Execute code in cloud environment
  - `RunCode()` - Run Python or JavaScript code with timeout control
  - Supports: Python, JavaScript
  - Maximum execution time: 60 seconds (gateway limitation)

## 📘 Related Documentation

- [Feature Guides](../../../docs/guides/README.md) - Detailed usage guides and tutorials
- [Code Examples](../examples/README.md) - Complete example implementations
- [Quick Start](../../../docs/quickstart/README.md) - Get started in 5 minutes

---

**Need help?** Check out the [complete documentation](../../../docs/README.md) or [open an issue](https://github.com/aliyun/wuying-agentbay-sdk/issues).
