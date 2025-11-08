"""
Tool Calling Emulation Demo

This demo shows how to use the tool calling emulation system with LLMs
that don't natively support tool calling.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool_calling import (
    create_emulator,
    ToolCallingEmulator,
)


# Example: Create custom tools
class CalculatorTool(BaseTool):
    """Simple calculator tool."""
    
    name: str = "calculator"
    description: str = "Perform basic arithmetic calculations"
    parameters: dict = {
        "expression": {
            "type": "string",
            "description": "Mathematical expression to evaluate",
            "required": True
        }
    }
    
    async def execute(self, **kwargs):
        """Execute calculation."""
        expression = kwargs.get("expression", "")
        try:
            # Safe eval for simple math
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(output=f"Result: {result}")
        except Exception as e:
            return ToolResult(error=f"Calculation error: {e}")


class WeatherTool(BaseTool):
    """Mock weather tool."""
    
    name: str = "get_weather"
    description: str = "Get current weather for a location"
    parameters: dict = {
        "location": {
            "type": "string",
            "description": "City name or location",
            "required": True
        }
    }
    
    async def execute(self, **kwargs):
        """Execute weather lookup (mock)."""
        location = kwargs.get("location", "Unknown")
        # Mock response
        return ToolResult(
            output=f"Weather in {location}: Sunny, 72°F, Light breeze"
        )


async def demo_basic_usage():
    """Demo: Basic tool calling usage."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Tool Calling")
    print("="*60 + "\n")
    
    # Create tool registry
    tools = {
        "calculator": CalculatorTool(),
        "get_weather": WeatherTool()
    }
    
    # Create emulator
    config = {
        'max_iterations': 3,
        'timeout_per_tool': 10.0,
        'parallel_execution': False,
        'caching_enabled': True
    }
    emulator = create_emulator(tools, config)
    
    # Generate system prompt
    system_prompt = emulator.generate_system_prompt()
    print("System Prompt Generated:")
    print("-" * 60)
    print(system_prompt[:500] + "...")
    print("-" * 60)
    
    # Simulate LLM response with tool call
    llm_response = """
    I'll calculate that for you.
    
    <tool_call>
    {"name": "calculator", "args": {"expression": "15 * 8 + 3"}}
    </tool_call>
    
    Let me get the result.
    """
    
    print("\nLLM Response:")
    print("-" * 60)
    print(llm_response)
    print("-" * 60)
    
    # Process response
    result = await emulator.process_response(llm_response)
    
    print("\nProcessing Result:")
    print("-" * 60)
    print(f"Has Tool Calls: {result['has_tool_calls']}")
    print(f"Number of Results: {len(result['tool_results'])}")
    print(f"\nFormatted Results:")
    print(result['formatted_results'])
    print("-" * 60)


async def demo_multiple_tools():
    """Demo: Multiple tool calls in one response."""
    print("\n" + "="*60)
    print("DEMO 2: Multiple Tool Calls")
    print("="*60 + "\n")
    
    tools = {
        "calculator": CalculatorTool(),
        "get_weather": WeatherTool()
    }
    
    emulator = create_emulator(tools)
    
    # LLM response with multiple tool calls
    llm_response = """
    I'll help you with both requests.
    
    First, let me calculate:
    <tool_call>
    {"name": "calculator", "args": {"expression": "100 / 4"}}
    </tool_call>
    
    And check the weather:
    <tool_call>
    {"name": "get_weather", "args": {"location": "New York"}}
    </tool_call>
    """
    
    print("LLM Response with Multiple Tool Calls:")
    print("-" * 60)
    print(llm_response)
    print("-" * 60)
    
    result = await emulator.process_response(llm_response)
    
    print("\nProcessing Result:")
    print("-" * 60)
    print(f"Number of Tool Calls: {len(result['tool_results'])}")
    print(f"\nFormatted Results:")
    print(result['formatted_results'])
    print("-" * 60)


async def demo_error_handling():
    """Demo: Error handling."""
    print("\n" + "="*60)
    print("DEMO 3: Error Handling")
    print("="*60 + "\n")
    
    tools = {
        "calculator": CalculatorTool(),
    }
    
    emulator = create_emulator(tools)
    
    # LLM response with error
    llm_response = """
    <tool_call>
    {"name": "calculator", "args": {"expression": "1/0"}}
    </tool_call>
    """
    
    print("LLM Response with Invalid Calculation:")
    print("-" * 60)
    print(llm_response)
    print("-" * 60)
    
    result = await emulator.process_response(llm_response)
    
    print("\nProcessing Result:")
    print("-" * 60)
    for call_id, tool_result in result['tool_results'].items():
        if tool_result.error:
            print(f"Error Detected: {tool_result.error}")
    print("-" * 60)
    
    # Unknown tool
    llm_response = """
    <tool_call>
    {"name": "unknown_tool", "args": {}}
    </tool_call>
    """
    
    print("\n\nLLM Response with Unknown Tool:")
    print("-" * 60)
    print(llm_response)
    print("-" * 60)
    
    result = await emulator.process_response(llm_response)
    
    print("\nProcessing Result:")
    print("-" * 60)
    for call_id, tool_result in result['tool_results'].items():
        if tool_result.error:
            print(f"Error Message: {tool_result.error}")
    print("-" * 60)


async def demo_caching():
    """Demo: Result caching."""
    print("\n" + "="*60)
    print("DEMO 4: Result Caching")
    print("="*60 + "\n")
    
    tools = {
        "calculator": CalculatorTool(),
    }
    
    config = {
        'caching_enabled': True,
        'cache_ttl': 60
    }
    emulator = create_emulator(tools, config)
    
    llm_response = """
    <tool_call>
    {"name": "calculator", "args": {"expression": "123 * 456"}}
    </tool_call>
    """
    
    # First call
    print("First Call (no cache):")
    result1 = await emulator.process_response(llm_response)
    print("-" * 60)
    print(result1['formatted_results'][:200] + "...")
    print("-" * 60)
    
    # Second call (should be cached)
    print("\nSecond Call (should use cache):")
    result2 = await emulator.process_response(llm_response)
    print("-" * 60)
    print(result2['formatted_results'][:200] + "...")
    print("-" * 60)


async def demo_tool_info():
    """Demo: Getting tool information."""
    print("\n" + "="*60)
    print("DEMO 5: Tool Information")
    print("="*60 + "\n")
    
    tools = {
        "calculator": CalculatorTool(),
        "get_weather": WeatherTool()
    }
    
    emulator = create_emulator(tools)
    
    print("Available Tools:")
    print("-" * 60)
    for tool_name in emulator.get_available_tools():
        info = emulator.get_tool_info(tool_name)
        print(f"\nTool: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Parameters: {info['parameters']}")
    print("-" * 60)


async def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("TOOL CALLING EMULATION SYSTEM - DEMO")
    print("="*60)
    
    try:
        await demo_basic_usage()
        await demo_multiple_tools()
        await demo_error_handling()
        await demo_caching()
        await demo_tool_info()
        
        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
