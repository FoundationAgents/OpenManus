from pathlib import Path
from typing import Optional

from app.memory.agentmemory import agentmemory
from app.task_context import get_current_workspace
from app.tool.base import BaseTool, ToolResult


def _conversation_id_from_workspace() -> str:
    workspace = get_current_workspace() or ""
    if not workspace:
        return "default"
    path = Path(workspace)
    parts = path.parts
    if "conversations" in parts:
        idx = parts.index("conversations")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return path.name or "default"


class MemorySave(BaseTool):
    name: str = "memory_save"
    description: str = (
        "Save durable long-term memory for this conversation using AgentMemory. "
        "Use for decisions, constraints, discoveries, and key outputs."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Memory content to store.",
            },
            "title": {
                "type": "string",
                "description": "Short title for the memory.",
            },
        },
        "required": ["content"],
    }

    async def execute(self, content: str, title: Optional[str] = None) -> ToolResult:
        if not agentmemory.enabled:
            return ToolResult(
                output="AgentMemory is disabled in config; skipping memory save."
            )
        conversation_id = _conversation_id_from_workspace()
        saved = agentmemory.remember(
            conversation_id=conversation_id,
            title=title or "Conversation memory",
            content=content,
        )
        if not saved:
            return ToolResult(error="Failed to save memory to AgentMemory.")
        return ToolResult(output="Memory saved.")


class MemoryRecall(BaseTool):
    name: str = "memory_recall"
    description: str = "Recall relevant long-term memory snippets from AgentMemory for this conversation."
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to recall.",
            },
            "limit": {
                "type": "integer",
                "description": "Optional max results.",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, limit: Optional[int] = None) -> ToolResult:
        if not agentmemory.enabled:
            return ToolResult(
                output="AgentMemory is disabled in config; no long-term recall available."
            )
        conversation_id = _conversation_id_from_workspace()
        context = agentmemory.format_context(
            conversation_id=conversation_id, query=query, limit=limit
        )
        if not context:
            return ToolResult(output="No matching long-term memories found.")
        return ToolResult(output=context)
