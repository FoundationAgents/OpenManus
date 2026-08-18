from app.tool.base import BaseTool


_EARLY_TERMINATE_DESCRIPTION = """A tool determined whether a problem has been solved earlier than plan completed."""


class EarlyTerminateTool(BaseTool):
    name: str = "early_terminate"
    description: str = _EARLY_TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "is_end_early": {
                "type": "string",
                "description": "Whether problem ends earlier than plan completed.",
                "enum": ["yes", "no"],
            }
        },
        "required": ["is_end_early"],
    }

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        pass
