import asyncio
import argparse
import sys

from app.agent.manus import Manus
from app.agent.planning import PlanningAgent
from app.logger import logger
from app.tool import ToolCollection, PlanningTool, Terminate, CodeAct
from app.tool.web_search import WebSearch
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.file_operators import FileOperator


async def run_agent(agent_type: str, prompt: str, advanced: bool = False):
    """Run specified agent type with given prompt.

    Args:
        agent_type: Type of agent to run ('manus' or 'planning')
        prompt: User input prompt to process
        advanced: Whether to use advanced tools for the agent
    """
    if agent_type == 'planning':
        tools = ToolCollection(
            PlanningTool(),
            Terminate(),
            CodeAct(),
        )

        if advanced:
            # Add more advanced capabilities
            tools.add_tool(WebSearch())
            tools.add_tool(BrowserUseTool())
            tools.add_tool(FileOperator())

        agent = PlanningAgent(available_tools=tools)
        logger.info(f"Running enhanced planning agent with {len(tools.tool_map)} tools")
    else:
        # Default to Manus agent
        agent = Manus()
        logger.info("Running standard Manus agent")

    try:
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    except Exception as e:
        logger.error(f"Error during agent execution: {str(e)}")


async def simple_main():
    """Simple main function that works like the original - just ask for prompt and run."""
    agent = Manus()
    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


async def main():
    # If no command line args provided, run in simple mode
    if len(sys.argv) == 1:
        await simple_main()
        return

    # Otherwise, parse arguments for advanced mode
    parser = argparse.ArgumentParser(description="Run an AI agent with specified configuration")
    parser.add_argument('--agent', '-a', type=str, default='manus', choices=['manus', 'planning'],
                        help='Agent type to use (manus or planning)')
    parser.add_argument('--advanced', action='store_true',
                        help='Use advanced tools (browser, file operations, etc)')
    parser.add_argument('--prompt', '-p', type=str,
                        help='Prompt to process (if not provided, will ask interactively)')

    args = parser.parse_args()

    # Get prompt either from command line or interactively
    prompt = args.prompt if args.prompt else input("Enter your prompt: ")

    await run_agent(args.agent, prompt, args.advanced)


if __name__ == "__main__":
    asyncio.run(main())
