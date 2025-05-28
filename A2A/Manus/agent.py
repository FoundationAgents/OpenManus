import httpx
from typing import Any, Dict, AsyncIterable, Literal, List, ClassVar
from pydantic import BaseModel
from app.agent.manus import Manus

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class A2AManus(Manus):

    async def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        response = await self.run(query)
        return self.get_agent_response(config,response)

    async def stream(self, query: str) -> AsyncIterable[Dict[str, Any]]:
        """Streaming is not supported by Manus."""
        raise NotImplementedError("Streaming is not supported by Manus yet.")


    def get_agent_response(self, config,agent_response):
        return {
            "is_task_complete": True,
            "require_user_input": False,
            "content": agent_response,
        }

    SUPPORTED_CONTENT_TYPES : ClassVar[List[str]] = ["text", "text/plain"]
