from app.tool.base import BaseTool


_TERMINATE_DESCRIPTION = """ALWAYS call this tool to end the interaction after providing your response.
Use this for ALL responses - whether simple greetings, complex tasks, or anything in between.
This tool MUST be called to complete every interaction."""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        return f"The interaction has been completed with status: {status}"
