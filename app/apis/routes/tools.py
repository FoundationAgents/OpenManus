from typing import cast

from fastapi import APIRouter

from app.agent.manus import SYSTEM_MCP_TOOLS_MAP, SYSTEM_TOOLS
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
    for tool_key in SYSTEM_MCP_TOOLS_MAP.keys():
        tool_info = SYSTEM_MCP_TOOLS_MAP[tool_key]
        if "description" not in tool_info:
            tool_info["description"] = "Not Specified"
        tools_info.append(
            {
                "name": tool_key,
                "type": "mcp",
                "description": tool_info["description"],
            }
        )

    return tools_info
