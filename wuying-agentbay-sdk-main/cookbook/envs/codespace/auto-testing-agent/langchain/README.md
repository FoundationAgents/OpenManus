# LangChain Integration

This directory contains the LangChain-specific integration for the testing agent.

## Sample Output

When the agent successfully tests a Python project, you will see output similar to the following:

```
> Entering new AgentExecutor chain...

Invoking: `scan_project` with `/path/to/sample_project`

Project root: /path/to/sample_project

Directories:

Python files:
  calculator.py
    Classes:
      - Calculator (methods: add, subtract, multiply, divide)
    Functions: add, subtract, multiply, divide, is_even

Invoking: `generate_tests` with `Project root: /path/to/sample_project...`

Generated 1 test case files:
test_calculator.py

Invoking: `execute_tests` with `test_calculator.py`

Session created with ID: session-xxxxxxxxxxxxxxxxx
Uploaded calculator.py to AgentBay environment at calculator.py
Executing test case test_calculator.py

......................
----------------------------------------------------------------------
Ran 22 tests in 0.001s

OK

Executed 1 tests. 1 passed, 0 failed.

Test file: test_calculator.py
Status: PASS

The testing process for the Python project at `/path/to/sample_project` has been successfully completed. Here's a summary:

1. **Project Structure Scanned**: The project contains a single Python file, `calculator.py`, which includes:
   - A `Calculator` class with methods: `add`, `subtract`, `multiply`, and `divide`.
   - Standalone functions: `add`, `subtract`, `multiply`, `divide`, and `is_even`.

2. **Test Cases Generated**: One test file, `test_calculator.py`, was generated to cover the functionality of the `calculator.py` module.

3. **Tests Executed**: The test suite in `test_calculator.py` was executed.
   - **Result**: All 22 tests passed.
   - **Status**: ✅ PASS

No failures were detected. The code appears to be functioning as expected based on the test coverage.
```

## Setup

### 1. Create Virtual Environment

First, create a virtual environment to isolate project dependencies:

```bash
# Create virtual environment
python -m venv auto-testing-agent-env

# Activate virtual environment
# On Windows:
auto-testing-agent-env\Scripts\activate
# On macOS/Linux:
source auto-testing-agent-env/bin/activate
```

### 2. Install Dependencies

Install the required packages:

```bash
# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install wuying-agentbay-sdk python-dotenv

# Install LangChain dependencies
pip install langchain langchain-openai

# Install other dependencies
pip install pytest
```

Alternatively, you can install dependencies using the requirements file:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the n the folder of auto-testing-agent/ with your API keys:

```env
# AgentBay API Key (required)
AGENTBAY_API_KEY=your_actual_api_key_here

# DashScope (Alibaba Cloud) API Key for Qwen LLM (required for LangChain orchestration)
DASHSCOPE_API_KEY=your_qwen_api_key_here

# Optional: specify which Qwen model to use (default: qwen-plus)
DASHSCOPE_MODEL=qwen-plus
```

You can get your Agent-Bay API key from the Agent-Bay platform dashboard:
1. Visit [Agent-Bay Console](https://agentbay.console.aliyun.com/service-management)
2. Sign up or log in to your Alibaba Cloud account
3. Navigate to the Service Management section
4. Create a new API KEY or select an existing one
5. Copy the API Key and paste it as the value of `AGENTBAY_API_KEY` in your `.env` file

For the DashScope API key, you need to register on the Alibaba Cloud DashScope platform:
1. Visit [DashScope Platform](https://bailian.console.aliyun.com/#/home)
2. Sign up or log in to your account
3. Navigate to the API Key management section
4. Create a new API Key and copy it for use in your `.env` file

### 4. Available Qwen Models

The following Qwen models are available for use:
- `qwen-turbo`: Fast and efficient model for simple tasks
- `qwen-plus`: Balanced model for most use cases (default)
- `qwen-max`: Most capable model for complex tasks

You can specify which model to use by setting the `DASHSCOPE_MODEL` environment variable in your `.env` file.

## Structure

- [src/](./src/): Contains the LangChain-specific implementation
- [data/](./data/): Data directory for outputs (test results, etc.)
- [README.md](./README.md): This documentation file

## Integration Details

The LangChain integration uses the core functionality from the [common](../common/) directory and wraps it in LangChain-specific components.

This demonstrates how to:
1. Use LangChain agents with Agent-Bay SDK
2. Structure the code to separate core functionality from framework-specific integration
3. Maintain clean separation of concerns between core logic and framework integration
4. Orchestrate testing tasks using LangChain's agent framework

## LangChain Orchestration

The testing agent can be orchestrated using LangChain's agent framework. This provides a more flexible way to interact with the testing functionality:

1. **Tool-based approach**: The agent exposes tools for scanning projects, generating tests, and executing them
2. **Natural language interface**: Users can interact with the agent using natural language commands
3. **Sequential workflow**: The agent can automatically determine the correct sequence of operations

### Available Tools

1. `scan_project`: Scan a project directory to identify Python files that need testing
2. `generate_tests`: Generate test cases for the loaded project using LLM
3. `execute_tests`: Execute generated test cases in AgentBay session
4. `save_results`: Save test results to a local log file

### Running the Example Script

To run the LangChain orchestration example:

```bash
cd YOUR_PREFIX_PATH/cookbook/envs/codespace/auto-testing-agent/langchain/
python src/auto_testing_agent_example.py
```

This example script demonstrates:
1. Creating a LangChain testing agent
2. Scanning a project structure
3. Generating tests using LLM
4. Executing the tests in AgentBay session
5. Saving the results to a log file

### Direct Usage

You can also use the testing agent directly by instantiating the [LangChainTestingAgent](./src/auto_testing_agent.py) class and calling its methods.

### Usage Example

```python
from auto_testing_agent import create_langchain_agent

# Create the agent
agent = create_langchain_agent()

# Use the agent
result = agent.invoke({
    "input": "Test the Python project at path/to/your/project"
})
```

## Troubleshooting

If you encounter issues:

1. Ensure your API key is correct and properly set in the `.env` file
2. Check that you have network connectivity to Agent-Bay services
3. Verify that all required packages are installed:
   ```bash
   pip list | grep -E "(wuying-agentbay-sdk|langchain)"
   ```
4. Check that you've activated your virtual environment before running the scripts
5. Make sure the project path specified in PROJECT_PATH exists and contains Python files