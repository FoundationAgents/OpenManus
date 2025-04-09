from typing import cast

from fastapi import APIRouter

from app.agent.manus import SYSTEM_MCP_TOOLS, SYSTEM_TOOLS
from app.tool.base import BaseTool

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def get_tools_info():
    tools_info = []
    for tool in SYSTEM_TOOLS:
        t = cast(BaseTool, tool)
        tools_info.append(
            {
                "name": t.name,
                "type": "tool",
                "description": t.description,
                "parameters": t.parameters,
            }
        )
    for tool in SYSTEM_MCP_TOOLS:
        tools_info.append(
            {
                "name": tool["client_id"],
                "type": "mcp",
                "description": tool["description"],
            }
        )

    return tools_info
