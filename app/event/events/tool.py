from app.event.base import BaseEvent
from datetime import datetime
from typing import Optional, Dict, Any
from app.event.types import ToolExecutionStatus


class ToolEvent(BaseEvent):
    """Base class for all tool-related events."""

    def __init__(self, tool_name: str, tool_type: str, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=f"tool.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "tool_name": tool_name,
                "tool_type": tool_type,
            },
            **kwargs
        )
        if conversation_id:
            self.conversation_id = conversation_id


class ToolExecutionEvent(ToolEvent):
    """工具执行事件"""

    def __init__(self, tool_name: str, tool_type: str, status: ToolExecutionStatus,
                 parameters: Dict[str, Any], result: Any = None,
                 execution_time: Optional[float] = None, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            tool_name=tool_name,
            tool_type=tool_type,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "status": status.value,
            "parameters": parameters,
            "result": str(result) if result is not None else None,
            "execution_time": execution_time,
        })


class ToolResultEvent(ToolEvent):
    """工具结果事件"""

    def __init__(self, tool_name: str, tool_type: str, result: Any, success: bool = True,
                 error_message: Optional[str] = None, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            tool_name=tool_name,
            tool_type=tool_type,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "result": str(result) if result is not None else None,
            "success": success,
            "error_message": error_message,
        })


def create_tool_execution_event(tool_name: str, tool_type: str, status: str,
                               parameters: Dict[str, Any], conversation_id: Optional[str] = None) -> ToolExecutionEvent:
    """创建工具执行事件"""
    return ToolExecutionEvent(
        tool_name=tool_name,
        tool_type=tool_type,
        status=ToolExecutionStatus(status),
        parameters=parameters,
        conversation_id=conversation_id,
        source="tool_system"
    )
