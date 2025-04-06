import asyncio

from app.agent.planning import PlanningAgent
from app.tool import PlanningTool, Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.logger import logger

async def main():
    # Configure and run the agent
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), PythonExecute(), StrReplaceEditor(), Terminate()))
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

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
