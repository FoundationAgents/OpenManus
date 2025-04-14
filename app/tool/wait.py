from app.tool.base import BaseTool


_WAIT_DESCRIPTION = """Wait to request user input when the agent need user to provide more information.
When you need user to provide more information, call this tool to wait user input."""


class Wait(BaseTool):
    name: str = "wait"
    description: str = _WAIT_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self) -> str:
        """Wait user input"""
        prompt = input("Input to continue: ")
        return f"User input: {prompt}"
