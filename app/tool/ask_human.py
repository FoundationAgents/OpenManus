from app.tool import BaseTool
from app.tool.user_input_tool import WaitForUserInput


class AskHuman(BaseTool):
    """Add a tool to ask human for help."""

    name: str = "ask_human"
    description: str = (
        "Legacy alias for optional mid-task user input. Do not use this to block task "
        "progress or ask for clarification; continue autonomously if no reply arrives."
    )
    parameters: str = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The question you want to ask human.",
            }
        },
        "required": ["inquire"],
    }

    async def execute(self, inquire: str) -> str:
        result = await WaitForUserInput().execute(message=inquire, timeout_seconds=30)
        return str(result)
