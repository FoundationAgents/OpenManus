# Automation Feature Examples

This example demonstrates the automation capabilities of the AgentBay SDK with different specialized images, including command execution, code execution, and UI automation across different environments.

## Features

- **Command Execution**: Execute Shell commands using linux_latest image
- **Code Execution**: Run Python and JavaScript code using code_latest image
- **Linux UI Automation**: Desktop UI operations using linux_latest image
- **Mobile UI Automation**: Mobile UI operations using mobile_latest image
- **Multi-Image Support**: Demonstrates proper image selection for different use cases

## Running the Example

```bash
# Install dependencies
pip install wuying-agentbay-sdk

# Set environment variables
export AGENTBAY_API_KEY="your-api-key"

# Run the example
python main.py
```

## Example Content

### 1. Command Execution Example (linux_latest)
- Basic system command execution in Linux environment
- File system operations
- System information retrieval
- Proper error handling and session cleanup

### 2. Code Execution Example (code_latest)
- Python code execution with libraries
- JavaScript code execution
- System information and environment details
- Code execution result validation

### 3. Linux UI Automation Example (linux_latest)
- Desktop screen capture
- Keyboard input simulation for desktop applications
- Mouse operation simulation
- Desktop environment interaction

### 4. Mobile UI Automation Example (mobile_latest)
- Mobile interface screen capture
- Touch gesture simulation
- Mobile-specific UI interactions
- Device orientation and touch input handling

## Image Selection Guide

This example demonstrates best practices for selecting appropriate images for different automation tasks:

- **linux_latest**: Best for command execution and Linux desktop UI automation
- **code_latest**: Optimized for code execution with pre-installed development tools
- **mobile_latest**: Specialized for mobile UI testing and automation

## Key Changes from Previous Version

- **Separated UI automation**: Split into Linux and Mobile specific examples to prevent execution conflicts
- **Improved API usage**: Updated to use current SDK API patterns (`.content` for file content, `.data` for response data)
- **Better error handling**: Enhanced error handling and session cleanup
- **Image-specific optimization**: Each example uses the most appropriate image type

## Related Documentation

- [Automation Feature Guide](../../../../docs/guides/automation.md)
- [API Reference Documentation](../api/)
- [More Examples](../)

## Notes

- Ensure the correct API key is set via `AGENTBAY_API_KEY` environment variable
- UI automation features require graphical interface support in the target image
- Mobile UI automation requires mobile_latest image for proper touch input simulation
- Each automation type uses a separate session to prevent interference
- All sessions are properly cleaned up after use