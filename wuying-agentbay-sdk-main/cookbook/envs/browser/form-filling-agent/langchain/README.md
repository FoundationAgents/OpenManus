# LangChain Integration

This directory contains the LangChain-specific integration for the form-filling agent.

## Sample Output

When the agent successfully fills a form, you will see output similar to the following:

```
> Entering new AgentExecutor chain...

Invoking: `analyze_form` with `/path/to/form.html`

Form at /path/to/form.html has been analyzed. Recommended instructions: ["Enter 'John' in the input field with id firstName", "Enter 'Doe' in the input field with id lastName", ...]

Invoking: `fill_form_fields` with `Enter 'John' in the input field with id firstName;Enter 'Smith' in the input field with id lastName;Enter 'john.smith@example.com' in the input field with id email`

Prepared to fill form with 3 instructions: ["Enter 'John' in the input field with id firstName", "Enter 'Smith' in the input field with id lastName", "Enter 'john.smith@example.com' in the input field with id email"]

Invoking: `execute_form_filling` with `/path/to/form.html`

Session created: session-xxxxxxxxxxxxxxxxx
Form file uploaded successfully
Browser instance successfully initialized
Form page loaded successfully

Instruction executed successfully: Enter 'John' in the input field with id firstName
Instruction executed successfully: Enter 'Smith' in the input field with id lastName
Instruction executed successfully: Enter 'john.smith@example.com' in the input field with id email

Form filling completed successfully! The form has been successfully filled with the provided data:

- **First Name:** John  
- **Last Name:** Smith  
- **Email:** john.smith@example.com  

The form at `/path/to/form.html` was analyzed, populated with your custom data, and submitted successfully.
```

## Setup

### 1. Create Virtual Environment

First, create a virtual environment to isolate project dependencies:

```bash
# Create virtual environment
python -m venv form-filling-agent-env

# Activate virtual environment
# On Windows:
form-filling-agent-env\Scripts\activate
# On macOS/Linux:
source form-filling-agent-env/bin/activate
```

### 2. Install Dependencies

Install the required packages:

```bash
# Update pip
pip install --upgrade pip

# Install core dependencies
pip install wuying-agentbay-sdk playwright python-dotenv

# Install LangChain dependencies
pip install langchain langchain-openai

# Install Playwright browsers
playwright install
```

Alternatively, you can install dependencies using the requirements file:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the folder of form-filling-agent/ with your API keys:

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
4. Copy the API Key and paste it as the value of `DASHSCOPE_API_KEY` in your `.env` file

### 4. Available Qwen Models

The following Qwen models are available for use:
- `qwen-turbo`: Fast and efficient model for simple tasks
- `qwen-plus`: Balanced model for most use cases (default)
- `qwen-max`: Most capable model for complex tasks

You can specify which model to use by setting the `DASHSCOPE_MODEL` environment variable in your `.env` file.

## Structure

- [src/](./src/): Contains the LangChain-specific implementation
- [README.md](./README.md): This documentation file

## Integration Details

The LangChain integration uses the core functionality from the [common](../common/) directory and wraps it in LangChain-specific components.

This demonstrates how to:
1. Use LangChain agents with Agent-Bay SDK
2. Structure the code to separate core functionality from framework-specific integration
3. Maintain clean separation of concerns between core logic and framework integration
4. Orchestrate form filling tasks using LangChain's agent framework

## LangChain Orchestration

The form filling agent can be orchestrated using LangChain's agent framework. This provides a more flexible way to interact with the form filling functionality:

1. **Tool-based approach**: The agent exposes tools for analyzing forms, setting filling instructions, and executing the filling process
2. **Natural language interface**: Users can interact with the agent using natural language commands
3. **Sequential workflow**: The agent can automatically determine the correct sequence of operations

### Available Tools

1. `analyze_form`: Analyze a form and suggest filling instructions
2. `fill_form_fields`: Prepare to fill form fields with provided instructions
3. `execute_form_filling`: Execute the form filling process

### Running the Example Script

To run the LangChain orchestration example:

```bash
cd YOUR_PREFIX_PATH/cookbook/envs/browser/form-filling-agent/langchain/
python src/form_filling_agent_example.py
```

This example script demonstrates:
1. Creating a LangChain form filling agent
2. Analyzing a form and suggesting filling instructions
3. Filling the form with custom data
4. Executing the form filling process

### Direct Usage

You can also use the form filling agent directly by instantiating the [LangChainFormFillingAgent](./src/form_filling_agent.py) class and calling its methods.

### Usage Example

```python
from form_filling_agent import create_langchain_form_filling_agent

# Create the agent
agent = create_langchain_form_filling_agent()

# Use the agent with specific instructions
result = agent.invoke({
    "input": "First analyze the form at /path/to/form.html, then fill it with custom data: John as first name, Smith as last name, john.smith@example.com as email, and finally execute the filling process"
})
```