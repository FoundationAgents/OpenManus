from app.tool.base import BaseTool


_TERMINATE_DESCRIPTION = """Finish the current task only after verifying the requested outcome.
Use status=success when the work is complete and verified. Use status=failure when blocked.
Always include a concise summary and, for failures, the exact reason/blocker."""


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
            },
            "summary": {
                "type": "string",
                "description": "Concise final answer or completion summary shown to the user.",
            },
            "reason": {
                "type": "string",
                "description": "Why the task is ending, especially for failure or partial completion.",
            },
        },
        "required": ["status"],
    }

    async def execute(self, status: str, summary: str = "", reason: str = "") -> str:
        """Finish the current execution"""
        details = [f"The interaction has been completed with status: {status}."]
        if summary:
            details.append(f"Summary: {summary}")
        if reason:
            details.append(f"Reason: {reason}")
        return "\n".join(details)
