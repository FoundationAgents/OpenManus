# Browser Examples

This directory contains Python examples demonstrating browser automation capabilities of the AgentBay SDK.

## Examples

### 1. browser_context_cookie_persistence.py
Demonstrates how to use Browser Context to persist cookies across multiple sessions. This example shows:
- Creating sessions with Browser Context
- Setting cookies manually using Playwright
- Deleting sessions with context synchronization (`sync_context=True`)
- Verifying cookie persistence in new sessions
- Complete cleanup of resources

**Key features demonstrated:**
- Browser Context configuration with `auto_upload=True`
- Manual cookie setting and verification
- Cross-session cookie persistence
- Proper resource cleanup

### 2. search_agentbay_doc.py
Demonstrates basic browser automation using direct Playwright interactions:
- Connecting to AgentBay browser via CDP
- Manual element selection and interaction
- Search operations on websites

### 3. search_agentbay_doc_by_agent.py
Shows how to use the Agent module for intelligent browser automation:
- Using natural language commands with `session.browser.agent.act_async()`
- AI-powered element detection and interaction
- Simplified automation for complex web interactions

### 4. visit_aliyun.py
Basic browser usage example showing:
- Browser initialization
- Simple page navigation
- Basic browser operations

### 5. run_2048.py & run_sudoku.py
Game automation examples demonstrating:
- Complex interaction patterns
- Agent-based automation for games
- Advanced browser control

## Running the Examples

1. Install required dependencies:
```bash
pip install wuying-agentbay-sdk playwright
playwright install chromium
```

2. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Run any example:
```bash
python browser_context_cookie_persistence.py
python search_agentbay_doc.py
# ... etc
```

## Browser Context vs Regular Browser Sessions

| Feature | Regular Browser Session | Browser Context Session |
|---------|------------------------|-------------------------|
| Cookie Persistence | No, cookies lost after session ends | Yes, cookies persist across sessions |
| Setup Complexity | Simple | Requires context creation |
| Use Case | One-time automation | Multi-session workflows |
| Data Synchronization | None | Automatic with `auto_upload=True` |

## Best Practices

1. **Always use context synchronization**: When deleting sessions with important browser data, use `sync_context=True`
2. **Proper cleanup**: Always delete sessions and contexts when done
3. **Error handling**: Implement proper error handling for network and browser operations
4. **Resource management**: Close browser connections properly
5. **Unique context names**: Use unique context names to avoid conflicts

## Related Documentation

- [Browser Extension Examples](../extension/README.md) - Dedicated extension management examples
- [Browser Automation Guide](../../../guides/browser-automation.md)
- [Browser Context Tutorial](../../../tutorials/browser-context.md)
- [Context Management Guide](../../../guides/context-management.md)
- [API Reference - Browser](../../../api-reference/python/browser.md) 