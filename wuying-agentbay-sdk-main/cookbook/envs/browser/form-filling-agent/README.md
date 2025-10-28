# Form-Filling Agent

This project demonstrates how to create a form-filling agent using the Agent-Bay SDK. The agent can upload an HTML form to Agent-Bay, open it in a browser, and automatically fill it with data based on natural language instructions.

## Features

- Uploads an HTML form to Agent-Bay environment
- Opens the form in a browser using Agent-Bay's browser capabilities
- Uses natural language instructions to fill form fields
- Submits the form automatically

## Framework Integration Guides

This project is structured to support multiple agent frameworks. Please refer to the specific framework integration guide for detailed setup and usage instructions:

- [LangChain Integration Guide](./langchain/README.md) - Complete setup and usage instructions for LangChain framework

## Project Structure

This project follows a modular structure that separates core functionality from framework-specific integrations:

```
├── README.md            # Documentation
├── .env                 # Environment variables
├── common/              # Public core functionality
│   ├── src/             # Framework-agnostic code
│   │   ├── form.html    # Sample HTML form
│   │   └── form_filler.py # Core form filling functionality
│   └── README.md        # Documentation
├── langchain/           # LangChain integration
│   ├── data/            # Data directory for outputs (screenshots, etc.)
│   ├── src/             # LangChain-specific code
│   │   ├── form_filling_agent.py       # LangChain-specific implementation
│   │   └── form_filling_agent_example.py # Example script for LangChain orchestration
│   └── requirements.txt # Python dependencies
```

### Common Module

The [common](./common/) directory contains all the core functionality that can be used across different agent frameworks. This includes:

- Session management with Agent-Bay
- File upload operations
- Browser initialization and control
- Form filling operations
- Resource cleanup

### Framework Integration Modules

Framework-specific directories (like [langchain](./langchain/)) contain the integration code that uses the core functionality from the common module and wraps it in framework-specific components.

## Customization

You can modify the [form.html](./common/src/form.html) file to use your own form, and update the instructions in the example script to match the fields in your form.

## Agent-Bay SDK Features Used

- Session management
- File system operations (uploading files)
- Browser initialization and control
- BrowserAgent for natural language web automation