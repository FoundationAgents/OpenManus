# Auto Testing Agent

This project demonstrates how to create a testing agent using LangChain and Agent-Bay SDK. The agent can scan Python projects, generate test cases using LLMs, and execute them in isolated cloud environments.

## Features

- Scan Python projects to identify modules that need testing
- Generate test cases using LLMs based on project structure
- Execute tests in isolated AgentBay cloud sessions
- Save test results to local log files
- Support for multiple agent frameworks (currently LangChain, with plans for others)

## Framework Integration Guides

This project is structured to support multiple agent frameworks. Please refer to the specific framework integration guide for detailed setup and usage instructions:

- [LangChain Integration Guide](./langchain/README.md) - Complete setup and usage instructions for LangChain framework

## Project Structure

This project follows a modular structure that separates core functionality from framework-specific integrations:

```
├── README.md              # Documentation
├── .env                   # Environment variables
├── common/                # Public core functionality
│   ├── sample_project/    # Sample project for testing
│   └── src/               # Framework-agnostic code
│       └── base_auto_testing_agent.py # Base testing agent class
├── langchain/             # LangChain integration
│   ├── data/              # Data directory for outputs (test results, etc.)
│   ├── src/               # LangChain-specific code
│   │   ├── auto_testing_agent.py          # LangChain-specific implementation
│   │   └── auto_testing_agent_example.py  # Example script for LangChain orchestration
│   └── requirements.txt   # Python dependencies
```

### Common Module

The [common](./common/) directory contains all the core functionality that can be used across different agent frameworks. This includes:

- Base testing agent class with shared functionality
- Project scanning and analysis capabilities
- Test case generation logic
- Session management with Agent-Bay
- Test execution and result saving functionality

### Framework Integration Modules

Framework-specific directories (like [langchain](./langchain/)) contain the integration code that uses the core functionality from the common module and wraps it in framework-specific components.

## Customization

You can modify the code in the [common/sample_project/](./common/sample_project/) directory to test with your own Python projects, and update the instructions in the example script to match your specific testing requirements.

## Agent-Bay SDK Features Used

- Session management
- File system operations (synchronizing project files)
- Command execution (running tests)
- Context management (isolated testing environments)