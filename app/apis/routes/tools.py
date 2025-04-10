from typing import cast

from fastapi import APIRouter

from app.agent.manus import SYSTEM_TOOLS
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

    return tools_info
