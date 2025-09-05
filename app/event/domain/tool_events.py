"""Basic tool events."""

from typing import Any, Dict, Optional

from app.event.core.base import BaseEvent


class ToolEvent(BaseEvent):
    """Base class for all tool-related events."""

    def __init__(
        self,
        tool_name: str,
        tool_type: str,
        execution_id: str,
        conversation_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            event_type=f"tool.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "tool_name": tool_name,
                "tool_type": tool_type,
                "execution_id": execution_id,
            },
            **kwargs,
        )
        if conversation_id:
            self.conversation_id = conversation_id


class ToolExecutionEvent(ToolEvent):
    """工具执行事件"""

    def __init__(
        self,
        tool_name: str,
        tool_type: str,
        execution_id: str,
        parameters: Dict[str, Any],
        result: Optional[Any] = None,
        execution_time: Optional[float] = None,
        conversation_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            execution_id=execution_id,
            tool_name=tool_name,
            tool_type=tool_type,
            conversation_id=conversation_id,
            **kwargs,
        )
        self.data.update(
            {
                "parameters": parameters,
                "result": str(result) if result is not None else None,
                "execution_time": execution_time,
            }
        )


class ToolResultEvent(ToolEvent):
    """工具结果事件"""

    def __init__(
        self,
        tool_name: str,
        tool_type: str,
        execution_id: str,
        result: Optional[Any],
        success: bool = True,
        error_message: Optional[str] = None,
        conversation_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            execution_id=execution_id,
            tool_name=tool_name,
            tool_type=tool_type,
            conversation_id=conversation_id,
            **kwargs,
        )
        self.data.update(
            {
                "execution_id": execution_id,
                "result": str(result) if result is not None else None,
                "success": success,
                "error_message": error_message,
            }
        )
