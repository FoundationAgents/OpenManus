"""System prompts for teaching LLMs to use tool calling emulation.

This module generates system prompts that instruct LLMs to output
tool calls in a specific structured format.
"""

from typing import Dict, List, Optional

from app.logger import logger


class SystemPromptGenerator:
    """Generate system prompts for tool calling emulation."""
    
    TOOL_CALL_FORMAT = """
When you need to use a tool, output it in this exact format:

<tool_call>
{
  "name": "tool_name",
  "args": {"arg1": "value1", "arg2": "value2"}
}
</tool_call>

Important rules:
1. Place tool calls anywhere in your response (before, during, or after your explanation)
2. You can use multiple tool calls in one response
3. Always wait for tool results before continuing your reasoning
4. Tool calls will be executed automatically and results will be provided
5. If a tool fails, you'll receive an error message - adapt accordingly
"""
    
    EXAMPLE_USAGE = """
Example 1 - Single tool call:
User: "What's the weather in Paris?"
You: Let me check that for you.
<tool_call>
{
  "name": "web_search",
  "args": {"query": "weather in Paris today"}
}
</tool_call>

Example 2 - Multiple tool calls:
User: "Compare Python and JavaScript popularity"
You: I'll search for information on both languages.
<tool_call>
{
  "name": "web_search",
  "args": {"query": "Python programming language popularity 2024"}
}
</tool_call>
<tool_call>
{
  "name": "web_search",
  "args": {"query": "JavaScript programming language popularity 2024"}
}
</tool_call>

Example 3 - Code execution:
User: "Calculate fibonacci(10)"
You: I'll calculate that using Python.
<tool_call>
{
  "name": "python_execute",
  "args": {"code": "def fib(n):\\n    if n <= 1:\\n        return n\\n    return fib(n-1) + fib(n-2)\\nprint(fib(10))"}
}
</tool_call>
"""
    
    def __init__(self):
        self._tool_descriptions = {}
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, any],
        examples: Optional[List[str]] = None
    ):
        """Register a tool with its description and schema.
        
        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter schema
            examples: Optional usage examples
        """
        self._tool_descriptions[name] = {
            "description": description,
            "parameters": parameters,
            "examples": examples or []
        }
        logger.debug(f"Registered tool for prompt generation: {name}")
    
    def generate_tool_list(self) -> str:
        """Generate a formatted list of available tools.
        
        Returns:
            Formatted tool list string
        """
        if not self._tool_descriptions:
            return "No tools available."
        
        tool_list = "AVAILABLE TOOLS:\n\n"
        
        for i, (name, info) in enumerate(self._tool_descriptions.items(), 1):
            tool_list += f"{i}. {name}\n"
            tool_list += f"   Description: {info['description']}\n"
            
            # Add parameters
            if info['parameters']:
                tool_list += f"   Parameters:\n"
                for param_name, param_info in info['parameters'].items():
                    param_type = param_info.get('type', 'any')
                    param_desc = param_info.get('description', '')
                    required = param_info.get('required', False)
                    req_str = " (required)" if required else " (optional)"
                    tool_list += f"     - {param_name} ({param_type}){req_str}: {param_desc}\n"
            
            # Add examples
            if info['examples']:
                tool_list += f"   Examples:\n"
                for example in info['examples']:
                    tool_list += f"     {example}\n"
            
            tool_list += "\n"
        
        return tool_list
    
    def generate_system_prompt(
        self,
        include_examples: bool = True,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Generate complete system prompt for tool calling.
        
        Args:
            include_examples: Whether to include usage examples
            custom_instructions: Additional custom instructions
            
        Returns:
            Complete system prompt
        """
        prompt = "You are an AI assistant with access to various tools.\n\n"
        
        # Add tool list
        prompt += self.generate_tool_list()
        
        # Add format instructions
        prompt += self.TOOL_CALL_FORMAT
        
        # Add examples if requested
        if include_examples:
            prompt += "\n" + self.EXAMPLE_USAGE
        
        # Add custom instructions
        if custom_instructions:
            prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}\n"
        
        # Add final reminders
        prompt += """
IMPORTANT REMINDERS:
- Use tools whenever you need to get real-time information, execute code, or perform actions
- Don't make up information when you can use a tool to get accurate data
- If a tool fails, try a different approach or tool
- Always explain what you're doing before and after using tools
- Tool results will be injected into the conversation automatically
"""
        
        return prompt
    
    def generate_error_guidance(
        self,
        error_type: str,
        available_tools: List[str]
    ) -> str:
        """Generate helpful error guidance for common mistakes.
        
        Args:
            error_type: Type of error (e.g., 'tool_not_found', 'invalid_json')
            available_tools: List of available tool names
            
        Returns:
            Error guidance message
        """
        if error_type == 'tool_not_found':
            return (
                f"The tool you tried to use is not available.\n"
                f"Available tools: {', '.join(available_tools)}\n"
                f"Please use one of the available tools."
            )
        elif error_type == 'invalid_json':
            return (
                "Your tool call had invalid JSON syntax.\n"
                "Make sure to use proper JSON format:\n"
                '<tool_call>\n{\n  "name": "tool_name",\n  "args": {"key": "value"}\n}\n</tool_call>'
            )
        elif error_type == 'missing_args':
            return (
                "Your tool call is missing required arguments.\n"
                "Check the tool's parameter list and include all required arguments."
            )
        else:
            return "An error occurred. Please check your tool call format and try again."


def build_tool_calling_prompt(
    tools: Dict[str, Dict],
    include_examples: bool = True,
    custom_instructions: Optional[str] = None
) -> str:
    """Build a complete tool calling system prompt.
    
    Args:
        tools: Dictionary mapping tool names to their metadata
        include_examples: Whether to include usage examples
        custom_instructions: Additional instructions
        
    Returns:
        Complete system prompt
    """
    generator = SystemPromptGenerator()
    
    # Register all tools
    for name, info in tools.items():
        generator.register_tool(
            name=name,
            description=info.get('description', ''),
            parameters=info.get('parameters', {}),
            examples=info.get('examples', [])
        )
    
    return generator.generate_system_prompt(
        include_examples=include_examples,
        custom_instructions=custom_instructions
    )


# Pre-built prompt templates for common scenarios
MINIMAL_PROMPT = """You are an AI assistant with tool access. When you need to use a tool, format it as:
<tool_call>
{"name": "tool_name", "args": {"key": "value"}}
</tool_call>

Available tools will be listed separately. Use tools whenever you need to get real-time data or perform actions."""


VERBOSE_PROMPT = """You are a highly capable AI assistant with access to various tools that allow you to:
- Search the web for information
- Execute code (Python, Bash)
- Read and edit files
- Browse websites
- Make HTTP requests
- Perform DNS lookups and network diagnostics

When you need to use a tool, output it in this EXACT format:

<tool_call>
{
  "name": "tool_name",
  "args": {"argument_name": "argument_value"}
}
</tool_call>

Key guidelines:
1. Use tools liberally - don't guess when you can verify
2. You can call multiple tools in one response
3. Wait for tool results before drawing conclusions
4. If a tool fails, try an alternative approach
5. Always explain your reasoning and what you're doing

The system will automatically execute your tool calls and inject the results back into our conversation.
"""
