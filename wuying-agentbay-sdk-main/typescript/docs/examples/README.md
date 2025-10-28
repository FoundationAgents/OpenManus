# TypeScript SDK Examples

This directory contains TypeScript/JavaScript examples demonstrating various features and capabilities of the Wuying AgentBay SDK.

## Quick Start

### [basic-usage.ts](./basic-usage.ts)
Single-file quick start example:
- Initializing the AgentBay client
- Creating sessions
- Basic operations
- Session cleanup

## Common Features

Examples available across all environment types.

### Basics

**[session-creation/](./session-creation)**
- Creating sessions with different image types
- Session parameter configuration
- Session lifecycle management

**[filesystem-example/](./filesystem-example)**
- **filesystem-example.ts**: Basic file operations
- **filesystem-filetransfer-example.ts**: File transfer between local and cloud
- **watch-directory-example.ts**: Directory monitoring and change detection

**[command-example/](./command-example)**
- Running shell commands in cloud environments
- Capturing command output
- Command execution patterns

**[context-management/](./context-management)**
- Context creation and management
- Data storage and retrieval
- Cross-session data sharing

**[data-persistence/](./data-persistence)**
- **data-persistence.ts**: Basic data persistence and cross-session storage
- **context-sync-demo.ts**: Context synchronization demonstration
- **recycle-policy-example.ts**: Data lifecycle management with RecyclePolicy

### Advanced Features

**[agent-module-example/](./agent-module-example)** or **[agent-module-example.ts](./agent-module-example.ts)**
- Using AI-powered automation
- Agent-based task execution
- Intelligent automation workflows

**[vpc-session-example/](./vpc-session-example)** or **[vpc-session-example.ts](./vpc-session-example.ts)**
- Creating sessions in VPC environments
- Network security groups
- Private network access

## Environment-Specific Features

### Browser Use (`browser_latest`)

**[browser/](./browser)**

Browser automation examples:

**Basic Browser Usage:**
- **basic-usage.ts**: Getting started with browser automation

**Cookie and Session Management:**
- **browser-context-cookie-persistence.ts**: Cookie persistence across sessions

**Browser Configuration:**
- **browser-stealth.ts**: Stealth mode to avoid detection
- **browser-viewport.ts**: Custom viewport configuration
- **browser-proxies.ts**: Proxy configuration

**Real-World Use Cases:**
- **run-2048.ts**: 2048 game automation
- **run-sudoku.ts**: Sudoku game automation
- **captcha_tongcheng.ts**: CAPTCHA handling example
- **call_for_user_jd.ts**: JD.com user interaction automation

**[extension-example/](./extension-example)**
- Loading and using browser extensions
- Extension development workflows
- Automated extension testing

### Computer Use (`windows_latest`, `linux_latest`)

**[automation/](./automation)**
- **automation-example.ts**: Desktop automation workflows
- Complex automation patterns
- Multi-step automation tasks

**[ui-example/](./ui-example)**
- User interface interactions
- Screen automation
- UI element manipulation

### Mobile Use (`mobile_latest`)

Mobile examples are currently not available in TypeScript SDK. Use Python SDK for mobile automation.

### CodeSpace (`code_latest`)

Code execution examples are integrated into session and automation examples.

## Running the Examples

### Option 1: Using Installed Package (Recommended)

1. Install the SDK:
```bash
npm install wuying-agentbay-sdk
```

2. For browser examples, install Playwright:
```bash
npx playwright install chromium
```

3. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

4. Run examples with ts-node:
```bash
npx ts-node basic-usage.ts
npx ts-node session-creation/session-creation.ts
npx ts-node browser/browser-stealth.ts
```

### Option 2: Development from Source

1. Install dependencies and build:
```bash
cd typescript
npm install
npm run build
```

2. For browser examples, install Playwright:
```bash
npx playwright install chromium
```

3. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

4. Run examples:
```bash
# Using ts-node
npx ts-node docs/examples/basic-usage.ts
npx ts-node docs/examples/session-creation/session-creation.ts
npx ts-node docs/examples/browser/browser-stealth.ts

# Or compile and run
tsc docs/examples/basic-usage.ts
node docs/examples/basic-usage.js
```

## File Naming Convention

This SDK follows TypeScript conventions with kebab-case naming:
- Single-file examples: `example-name.ts`
- Directory-based examples: `example-name/example-name.ts` or `example-name/README.md`

## Prerequisites

- Node.js 16 or later
- TypeScript 4.5 or later
- Valid AgentBay API key
- Playwright (for browser examples)
- Internet connection

## Best Practices

1. **Type safety**: Leverage TypeScript's type system for better code quality
2. **Async/await**: Use async/await for better error handling
3. **Proper cleanup**: Always delete sessions when done
4. **Error handling**: Implement try-catch blocks for network operations
5. **Resource management**: Close connections properly
6. **API key security**: Never commit API keys to version control

## Getting Help

For more information, see:
- [TypeScript SDK Documentation](../../)
- [API Reference](../api/)
- [Quick Start Guide](../../../docs/quickstart/)
- [Feature Guides](../../../docs/guides/)
