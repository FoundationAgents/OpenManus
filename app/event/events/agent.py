from app.event.base import BaseEvent
from datetime import datetime
from typing import Optional

class AgentEvent(BaseEvent):
    """Base class for all agent-related events."""

    def __init__(self, agent_name: str, agent_type: str, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=f"agent.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "agent_name": agent_name,
                "agent_type": agent_type,
            },
            **kwargs
        )
        if conversation_id:
            self.conversation_id = conversation_id


class AgentStepStartEvent(AgentEvent):
    """智能体开始处理事件"""

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


class AgentStepCompleteEvent(AgentEvent):
    """智能体完成处理事件"""

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


def create_agent_step_start_event(agent_name: str, agent_type: str, step_number: int,
                                conversation_id: Optional[str] = None) -> AgentStepStartEvent:
    """创建智能体开始处理事件"""
    return AgentStepStartEvent(
        agent_name=agent_name,
        agent_type=agent_type,
        step_number=step_number,
        conversation_id=conversation_id,
        source=agent_name
    )
