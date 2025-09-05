"""Chainable agent events."""

from datetime import datetime
from typing import Optional

from app.event.core.base import ChainableEvent


class ChainableAgentEvent(ChainableEvent):
    """支持链式的智能体事件基类"""
    
    def __init__(self, agent_name: str, agent_type: str, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=f"agent.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "agent_name": agent_name,
                "agent_type": agent_type,
                "conversation_id": conversation_id,
                "agent_id": agent_name  # 用于上下文管理
            },
            **kwargs
        )


class ChainableAgentStepStartEvent(ChainableAgentEvent):
    """智能体开始处理步骤事件（支持链式）"""
    
    def __init__(self, agent_name: str, agent_type: str, step_number: int,
                 conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            agent_name=agent_name,
            agent_type=agent_type,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "step_number": step_number,
            "start_time": datetime.now().isoformat(),
        })


class ChainableAgentStepCompleteEvent(ChainableAgentEvent):
    """智能体完成处理步骤事件（支持链式）"""
    
    def __init__(self, agent_name: str, agent_type: str, step_number: int,
                 result: Optional[str] = None, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            agent_name=agent_name,
            agent_type=agent_type,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "step_number": step_number,
            "result": result,
            "complete_time": datetime.now().isoformat(),
        })


def create_chainable_agent_step_start_event(
    agent_name: str, 
    agent_type: str, 
    step_number: int,
    conversation_id: Optional[str] = None
) -> ChainableAgentStepStartEvent:
    """创建智能体步骤开始事件"""
    return ChainableAgentStepStartEvent(
        agent_name=agent_name,
        agent_type=agent_type,
        step_number=step_number,
        conversation_id=conversation_id,
        source=agent_name
    )
