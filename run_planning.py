import asyncio

from app.agent.planning import PlanningAgent
from app.tool import PlanningTool, Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor

async def main():
    # Configure and run the agent
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), Terminate()))
    #agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), PythonExecute(), BrowserUseTool(), StrReplaceEditor(), Terminate()))
    result = await agent.run("Help me plan a trip to the moon")
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
