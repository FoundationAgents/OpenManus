"""Chainable tool events."""

from datetime import datetime
from typing import Any, Dict, Optional

from app.event.core.base import ChainableEvent


class ChainableToolEvent(ChainableEvent):
    """支持链式的工具事件基类"""
    
    def __init__(self, tool_name: str, agent_id: str, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=f"tool.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "tool_name": tool_name,
                "agent_id": agent_id,
                "conversation_id": conversation_id,
            },
            **kwargs
        )


class ChainableToolExecutionRequestEvent(ChainableToolEvent):
    """工具执行请求事件（支持链式）"""
    
    def __init__(self, tool_name: str, args: Dict[str, Any], agent_id: str, 
                 conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            tool_name=tool_name,
            agent_id=agent_id,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "args": args,
            "request_time": datetime.now().isoformat(),
        })


class ChainableToolExecutionCompletedEvent(ChainableToolEvent):
    """工具执行完成事件（支持链式）"""
    
    def __init__(self, tool_name: str, agent_id: str, result: Any, success: bool = True,
                 conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            tool_name=tool_name,
            agent_id=agent_id,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "result": result,
            "success": success,
            "complete_time": datetime.now().isoformat(),
        })


def create_chainable_tool_execution_request_event(
    tool_name: str,
    args: Dict[str, Any],
    agent_id: str,
    conversation_id: Optional[str] = None
) -> ChainableToolExecutionRequestEvent:
    """创建工具执行请求事件"""
    return ChainableToolExecutionRequestEvent(
        tool_name=tool_name,
        args=args,
        agent_id=agent_id,
        conversation_id=conversation_id,
        source=agent_id
    )
