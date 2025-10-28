# Python SDK Examples

This directory contains Python examples demonstrating various features and capabilities of the Wuying AgentBay SDK.

## Quick Start

### [basic_usage.py](./basic_usage.py)
Single-file quick start example:
- Initializing the AgentBay client
- Creating sessions
- Basic operations
- Session cleanup

## Common Features

Examples available across all environment types.

### Basics

**[session_creation/](./session_creation)**
- Creating sessions with different image types
- Session parameter configuration
- Session lifecycle management

**[file_system/](./file_system)**
- File upload and download
- Directory operations
- File manipulation
- Large file handling with chunking

**[filesystem_example/](./filesystem_example)**
- **file_transfer_example.py**: File transfer between local and cloud
- **watch_directory_example.py**: Directory monitoring and change detection

**[context_management/](./context_management)**
- Context creation and management
- Data storage and retrieval
- Cross-session data sharing

**[data_persistence/](./data_persistence)**
- Storing data across sessions
- Data retrieval patterns
- **context_sync_demo.py**: Context synchronization demonstration

**[label_management/](./label_management)**
- Organizing sessions with labels
- Filtering and searching sessions
- Label-based session management

### Advanced Features

**[agent_module/](./agent_module)**
- Using AI-powered automation
- Agent-based task execution
- Intelligent automation workflows

**[oss_management/](./oss_management)**
- OSS file operations
- Cloud storage management
- File upload/download with OSS

**[vpc_session/](./vpc_session)**
- Creating sessions in VPC environments
- Network security groups
- Private network access

## Environment-Specific Features

### Browser Use (`browser_latest`)

**[browser/](./browser)**

Browser automation examples:

**Cookie and Session Management:**
- **browser_context_cookie_persistence.py**: Cookie persistence across sessions
- **browser_replay.py**: Browser session replay

**Browser Configuration:**
- **browser_stealth.py**: Stealth mode to avoid detection
- **browser_viewport.py**: Custom viewport configuration
- **browser-proxies.py**: Proxy configuration

**AI-Powered Automation:**
- **search_agentbay_doc.py**: Manual browser automation with Playwright
- **search_agentbay_doc_by_agent.py**: AI-powered automation using Agent module

**Real-World Use Cases:**
- **game_2048.py**: 2048 game automation
- **game_sudoku.py**: Sudoku game automation
- **sudoku_solver.py**: Advanced Sudoku solving
- **captcha_tongcheng.py**: CAPTCHA handling example
- **visit_aliyun.py**: Basic website navigation
- **mini_max.py**: MiniMax platform automation
- **call_for_user_jd.py**: JD.com user interaction
- **admin_add_product.py**: Product management automation
- **expense_upload_invoices.py**: Invoice upload automation
- **shop_inspector.py**: E-commerce shop inspection
- **gv_quick_buy_seat.py**: Quick seat booking
- **alimeeting_availability.py**: Meeting availability checking

**[extension/](./extension)**
- **basic_extension_usage.py**: Loading and using browser extensions
- **extension_development_workflow.py**: Extension development patterns
- **extension_testing_automation.py**: Automated extension testing

### Computer Use (`windows_latest`, `linux_latest`)

**[automation/](./automation)**
- Desktop automation workflows
- Complex automation patterns
- Multi-step automation tasks

### Mobile Use (`mobile_latest`)

**[mobile_system/](./mobile_system)**
- Mobile UI interaction
- Mobile app automation
- Touch gestures and input
- Screenshot capture

### CodeSpace (`code_latest`)

Code execution examples are integrated into session and automation examples.

## Running the Examples

### Option 1: Using Installed Package (Recommended)

1. Install the SDK:
```bash
pip install wuying-agentbay-sdk
```

2. For browser examples, install Playwright:
```bash
playwright install chromium
```

3. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

4. Run any example:
```bash
python basic_usage.py
python session_creation/main.py
python browser/browser_stealth.py
```

### Option 2: Development from Source

1. Install dependencies:
```bash
cd python
poetry install
```

2. For browser examples, install Playwright:
```bash
poetry run playwright install chromium
```

3. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

4. Run examples with poetry:
```bash
poetry run python docs/examples/basic_usage.py
poetry run python docs/examples/session_creation/main.py
poetry run python docs/examples/browser/browser_stealth.py
```

## Prerequisites

- Python 3.8 or later
- Poetry (for dependency management)
- Valid AgentBay API key
- Playwright (for browser examples)
- Internet connection

## Best Practices

1. **Always use virtual environments**: Activate poetry shell or use `poetry run`
2. **Proper cleanup**: Always delete sessions when done
3. **Error handling**: Implement proper error handling for network operations
4. **Resource management**: Close connections properly
5. **API key security**: Never commit API keys to version control

## Getting Help

For more information, see:
- [Python SDK Documentation](../../)
- [API Reference](../api/)
- [Quick Start Guide](../../../docs/quickstart/)
- [Feature Guides](../../../docs/guides/)
