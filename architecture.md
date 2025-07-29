# OpenManus Architecture

This document provides an overview of the OpenManus architecture, describing its key components and how they interact.

## System Overview

OpenManus is a versatile AI agent system designed to solve various tasks through a combination of language models, tool usage, and planning. The system follows a ReAct (Reasoning and Acting) pattern, enabling it to think about a problem and then take actions to solve it.

## Core Components

### 1. Agent System

The agent system is built on a hierarchical structure with increasing capabilities:

```
BaseAgent
└── ReActAgent (Abstract)
    └── ToolCallAgent
        └── BrowserAgent
            └── Manus (Main Agent)
```

#### Key Agent Components:

- **BaseAgent**: The foundation of all agents.
- **ReActAgent**: Implements the basic Reasoning-Acting cycle with abstract methods for thinking and acting.
- **ToolCallAgent**: Extends ReActAgent with the ability to call and execute tools.
- **BrowserAgent**: Adds browser control capabilities on top of the ToolCallAgent.
- **Manus**: The primary agent that combines all capabilities, representing the main entry point for user interactions.

### 2. Tool System

Tools provide the agent with capabilities to interact with the environment. The system uses a pluggable tool architecture:

```
BaseTool (Abstract)
├── BrowserUseTool
├── PythonExecute
├── StrReplaceEditor
├── Terminate
├── CreateChatCompletion
└── Various other tools...
```

Tools are organized in a `ToolCollection` for easy access and management by agents.

#### Key Tool Components:

- **BaseTool**: Abstract base class for all tools.
- **ToolResult**: Represents the output of tool execution.
- **BrowserUseTool**: Allows the agent to control a web browser.
- **PythonExecute**: Enables the agent to run Python code.
- **StrReplaceEditor**: Provides file editing capabilities.
- **Terminate**: Special tool to end agent execution.

### 3. LLM Integration

The system is designed to work with various language models through a unified interface:

- Supports different providers (OpenAI, Azure, etc.)
- Configurable through the config system
- Handles token management and context limitations

### 4. Configuration System

Configuration is managed through a singleton `Config` class that loads settings from TOML files:

- **LLMSettings**: Configuration for language models.
- **BrowserSettings**: Configuration for browser automation.
- **SearchSettings**: Configuration for web search capabilities.
- **SandboxSettings**: Configuration for sandboxed execution.

### 5. Memory System

Agents maintain a memory of interactions through the `Memory` class, which stores:
- Previous messages
- Tool call results
- System state

### 6. Prompt System

The system uses carefully crafted prompts to guide the agent's behavior:
- **System prompts**: Define the agent's identity and capabilities.
- **Next step prompts**: Guide the agent in decision-making during task execution.

## Execution Flow

1. **Initialization**: The system initializes the main Manus agent with configured tools and settings.
2. **User Input**: The agent receives a prompt from the user describing a task.
3. **Think Phase**: The agent processes the task and determines the next steps.
4. **Act Phase**: The agent executes the chosen tools based on its thinking.
5. **Observe**: The agent observes the results of its actions.
6. **Repeat**: Steps 3-5 repeat until the task is completed or a maximum number of steps is reached.

## Key Files and Directories

- **/app/agent/**: Contains all agent implementations
- **/app/tool/**: Contains all tool implementations
- **/app/prompt/**: Contains prompt templates
- **/app/config.py**: Configuration management
- **/app/llm.py**: Language model interface
- **/app/schema.py**: Data models and schema definitions
- **/main.py**: Entry point for CLI usage
- **/run_*.py**: Various entry points for different execution modes

## Extensibility

The system is designed to be extensible:
1. **New Tools**: Add new tools by implementing the BaseTool interface
2. **New Agents**: Create specialized agents by extending existing agent classes
3. **New Models**: Support for new LLMs can be added through configuration

## Conclusion

OpenManus follows a modular design pattern that separates concerns between agents (decision making), tools (actions), and configuration. This design allows for flexibility and extensibility while maintaining a clear execution flow.
