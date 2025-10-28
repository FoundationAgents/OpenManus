# AgentBay SDK Cookbook

The AgentBay SDK Cookbook is a collection of practical examples and use cases demonstrating how to leverage the AgentBay SDK for various automation scenarios. Each cookbook showcases a specific application of the SDK, providing both basic implementations and integrations with popular frameworks like LangChain.

## Sandbox Environments (envs)

The `envs` directory contains examples organized by sandbox environments. A sandbox environment in AgentBay refers to an isolated cloud computing environment where specific types of operations can be performed safely and efficiently. Each environment provides specialized capabilities for different use cases.

Currently, two distinct sandbox environments are implemented:

1. **browser** - A web browser sandbox environment that provides capabilities for web automation, including form filling, web scraping, and UI interactions.
2. **codespace** - A code execution sandbox environment that provides capabilities for running and testing code in isolated environments.

## Table of Contents

1. [Form-Filling Agent](./envs/browser/form-filling-agent/) - Demonstrates browser automation capabilities by automatically filling HTML forms
2. [Auto Testing Agent](./envs/codespace/auto-testing-agent/) - Shows how to automate Python testing workflows in cloud environments

## Overview

The AgentBay SDK provides a comprehensive suite of tools for efficient interaction with AgentBay cloud environments. These cookbooks demonstrate real-world applications of the SDK across different domains:

### Form-Filling Agent
This cookbook demonstrates how to create a form-filling agent using the Agent-Bay SDK. The agent can:
- Upload an HTML form to Agent-Bay environment
- Open the form in a browser using Agent-Bay's browser capabilities
- Use natural language instructions to fill form fields
- Submit the form automatically

### Auto Testing Agent
This cookbook demonstrates how to create a testing agent using LangChain and Agent-Bay SDK. The agent can:
- Scan Python projects to identify modules that need testing
- Generate test cases using LLMs based on project structure
- Execute tests in isolated AgentBay cloud sessions
- Save test results to local log files

## Framework Integration

Each cookbook is structured to support multiple agent frameworks. Currently, most examples include LangChain integration, with plans to expand to other frameworks. The projects follow a modular structure that separates core functionality from framework-specific integrations:

```
cookbook-name/
├── README.md              # Documentation
├── .env                   # Environment variables
├── common/                # Public core functionality
│   └── src/               # Framework-agnostic code
└── framework-name/        # Framework integration (e.g., langchain)
    ├── data/              # Data directory for outputs
    ├── src/               # Framework-specific code
    └── requirements.txt   # Dependencies (for Python)
```

## Getting Started

To use any of these cookbooks:

1. Ensure you have the AgentBay SDK installed for your preferred language
2. Set up your environment variables, either through:
   - Exporting environment variables directly:
     ```bash
     export AGENTBAY_API_KEY=your_api_key_here
     ```
   - Or using the `.env` file in each cookbook directory (recommended)
3. Some cookbooks may require additional API keys, such as DashScope API key for LLM functionality
4. Navigate to the specific cookbook you're interested in
5. Follow the setup instructions in that cookbook's README.md
6. Run the example scripts to see the SDK in action

## Prerequisites

Before using the cookbooks, you need to:

1. Register an Alibaba Cloud account: [https://aliyun.com](https://aliyun.com)
2. Get APIKEY credentials: [AgentBay Console](https://agentbay.console.aliyun.com/service-management)
3. Install the required dependencies for each cookbook (usually Python packages)

## Contributing

If you'd like to contribute new cookbooks or improve existing ones, please follow the established structure and submit a pull request. Each cookbook should demonstrate a clear, practical use case for the AgentBay SDK.