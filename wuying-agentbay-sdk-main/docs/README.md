# AgentBay SDK Documentation Center

> Complete documentation and development guides for the AgentBay SDK

## 📖 Getting Started

### New to AgentBay
- [Installation Guide](quickstart/installation.md) - SDK installation and environment setup
- [Basic Concepts](quickstart/basic-concepts.md) - Understand cloud environments and sessions
- [First Session](quickstart/first-session.md) - 5-minute quick start with hands-on examples


## 🔧 Feature Guides

- [Feature Guides Overview](guides/README.md) - Complete feature guides introduction

### Common Features (All Environments)
- [Common Features Guide](guides/common-features/README.md) - Features available across all environments

#### Basics
- [Session Management](guides/common-features/basics/session-management.md) - Cloud environment lifecycle management
- [Command Execution](guides/common-features/basics/command-execution.md) - Execute shell commands and scripts
- [File Operations](guides/common-features/basics/file-operations.md) - File upload, download, and management
- [Data Persistence](guides/common-features/basics/data-persistence.md) - Cross-session data storage

#### Advanced
- [Session Link Access](guides/common-features/advanced/session-link-access.md) - Session connectivity and URL generation
- [VPC Sessions](guides/common-features/advanced/vpc-sessions.md) - Secure isolated network environments
- [Agent Modules](guides/common-features/advanced/agent-modules.md) - AI-powered task automation
- [OSS Integration](guides/common-features/advanced/oss-integration.md) - Object Storage Service integration

#### Configuration
- [SDK Configuration](guides/common-features/configuration/sdk-configuration.md) - Configuration options and settings

#### Use Cases
- [Use Cases Overview](guides/common-features/use-cases/README.md) - Common use case scenarios and implementations
- [Session Info Use Cases](guides/common-features/use-cases/session-info-use-cases.md) - Session information and connectivity patterns
- [Session Link Use Cases](guides/common-features/use-cases/session-link-use-cases.md) - Connect external tools to cloud sessions

### Environment-Specific Features

#### Browser Use
Complete browser automation for web scraping, testing, and form filling.

- [Browser Usage Guide](guides/browser-use/README.md) - Complete browser automation guide
- [Core Features](guides/browser-use/core-features.md) - Basic browser operations
- [Advanced Features](guides/browser-use/advance-features.md) - Advanced browser capabilities
- [Code Examples](guides/browser-use/code-example.md) - Practical code samples
- [Browser Extensions](guides/browser-use/browser-extensions.md) - Extension management
- [Browser Replay](guides/browser-use/browser-replay.md) - Session replay functionality
- [Integrations](guides/browser-use/integrations.md) - Third-party integrations

**Key Capabilities:**
- [Browser Context](guides/browser-use/core-features/browser-context.md) - Context management
- [Browser Proxies](guides/browser-use/core-features/browser-proxies.md) - Network proxy configuration
- [CAPTCHA Handling](guides/browser-use/core-features/captcha.md) - Automated CAPTCHA solving
- [Extension Support](guides/browser-use/core-features/extension.md) - Browser extension management
- [Stealth Mode](guides/browser-use/core-features/stealth-mode.md) - Anti-detection techniques
- [Call for User](guides/browser-use/core-features/call-for-user.md) - User interaction requests
- [Page Agent](guides/browser-use/advance-features/page-use-agent.md) - AI-driven page operations

#### Computer Use
Windows desktop automation for application control and window management.

- [Computer Use Guide](guides/computer-use/README.md) - Complete Windows desktop automation guide
- [Computer Application Management](guides/computer-use/computer-application-management.md) - Application control and management
- [Computer UI Automation](guides/computer-use/computer-ui-automation.md) - Desktop UI interaction and automation
- [Window Management](guides/computer-use/window-management.md) - Window operations and focus management

**Key Capabilities:**
- Application Management (start, stop, list applications)
- Window Operations (maximize, minimize, resize, close)
- Focus Management
- Desktop Automation Workflows

#### Mobile Use
Mobile UI automation for app testing and gesture-based interactions.

- [Mobile Use Guide](guides/mobile-use/README.md) - Complete mobile automation guide
- [Mobile Application Management](guides/mobile-use/mobile-application-management.md) - Mobile app control and management
- [Mobile UI Automation](guides/mobile-use/mobile-ui-automation.md) - Mobile UI interaction and automation

**Key Capabilities:**
- UI Element Detection
- Click Operations and Text Input
- Key Events and Swipe Gestures
- Screenshot Capture
- Mobile Application Management

#### CodeSpace
Development environment for code execution and scripting.

- [CodeSpace Guide](guides/codespace/README.md) - Complete development environment guide
- [Code Execution](guides/codespace/code-execution.md) - Python and JavaScript code execution

**Key Capabilities:**
- Python and JavaScript Code Execution
- Shell Command Execution
- File System Operations
- Development Tools Integration
- Package Management (pip, npm, etc.)

## 📚 API Reference

- [Python SDK](../python/README.md) - Python version documentation
- [TypeScript SDK](../typescript/README.md) - TypeScript version documentation
- [Golang SDK](../golang/README.md) - Golang version documentation

## 🚀 Learning Paths

Choose the appropriate learning path based on your experience level:

### 🆕 Complete Beginners
Start from the basics and build your knowledge step by step:
1. [Basic Concepts](quickstart/basic-concepts.md) - Understand core concepts
2. [Installation Guide](quickstart/installation.md) - Environment setup
3. [First Session](quickstart/first-session.md) - Hands-on practice
4. [Feature Guides](guides/README.md) - Explore specific features as needed

### 🚀 Experienced Developers
Already familiar with browser automation, computer use, or mobile testing? Start here:

**Quick Start (5 minutes):**
1. [Installation](quickstart/installation.md) - Set up your preferred SDK (Python/TypeScript/Golang)
2. Choose your environment based on your use case:
   - 🌐 [Browser Automation](guides/browser-use/README.md) - Web scraping, testing, form filling with stealth capabilities
   - 🖥️ [Computer/Windows Automation](guides/computer-use/README.md) - Desktop UI automation and window management
   - 📱 [Mobile Automation](guides/mobile-use/README.md) - Android UI testing and gesture automation
   - 💻 [CodeSpace](guides/codespace/README.md) - Cloud-based code execution environments

**What makes AgentBay different:**
- [Session Link](guides/common-features/advanced/session-link-access.md) - Direct URL access to services running in cloud sessions
- [Agent Modules](guides/common-features/advanced/agent-modules.md) - AI-powered automation capabilities
- [VPC Sessions](guides/common-features/advanced/vpc-sessions.md) - Secure isolated network environments

**Need more details?** See [Advanced Features](guides/common-features/advanced/README.md) or language-specific API docs: [Python](../python/README.md) | [TypeScript](../typescript/README.md) | [Golang](../golang/README.md)

## 📞 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues) - Report bugs or request features

---

💡 **Tip**: We recommend starting with the [Quick Start Tutorial](quickstart/README.md), then exploring specific feature guides as needed.
