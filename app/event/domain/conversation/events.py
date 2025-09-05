"""Conversation domain events."""

import uuid
from datetime import datetime
from typing import Optional

from app.event.core.base import BaseEvent


class ConversationEvent(BaseEvent):
    """Base class for all conversation-related events."""
    
    def __init__(self, conversation_id: str, user_id: str, **kwargs):
        super().__init__(
            event_type=f"conversation.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
            **kwargs
        )
        # 设置追踪信息
        self.conversation_id = conversation_id
        self.user_id = user_id


class ConversationCreatedEvent(ConversationEvent):
    """对话创建事件"""
    
    def __init__(self, conversation_id: str, user_id: str, title: Optional[str] = None, **kwargs):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update({
            "title": title,
            "created_at": datetime.now().isoformat(),
        })


class ConversationClosedEvent(ConversationEvent):
    """对话关闭事件"""
    
    def __init__(self, conversation_id: str, user_id: str, reason: str = "user_closed", **kwargs):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update({
            "reason": reason,
            "closed_at": datetime.now().isoformat(),
        })


class UserInputEvent(ConversationEvent):
    """用户输入事件"""
    
    def __init__(self, conversation_id: str, user_id: str, message: str,
                 message_id: Optional[str] = None, **kwargs):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update({
            "message": message,
            "message_id": message_id or str(uuid.uuid4()),
            "input_length": len(message),
        })


class InterruptEvent(ConversationEvent):
    """中断事件"""
    
    def __init__(self, conversation_id: str, user_id: str, reason: str = "user_interrupt",
                 interrupted_event_id: Optional[str] = None, **kwargs):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update({
            "reason": reason,
            "interrupted_event_id": interrupted_event_id,
            "interrupt_time": datetime.now().isoformat(),
        })


class AgentResponseEvent(ConversationEvent):
    """智能体响应事件"""
    
    def __init__(self, agent_name: str, agent_type: str, response: str,
                 conversation_id: str, user_id: Optional[str] = None, response_type: str = "text", **kwargs):
        # For conversation events, we need user_id, but for agent responses it might not be directly available
        # We'll use a placeholder or get it from the conversation context
        super().__init__(
            conversation_id=conversation_id,
            user_id=user_id or "system",  # Use system as fallback
            **kwargs
        )
        self.data.update({
            "response": response,
            "response_type": response_type,
            "response_length": len(response),
            "response_time": datetime.now().isoformat(),
            "agent_name": agent_name,
            "agent_type": agent_type,
        })


class LLMStreamEvent(ConversationEvent):
    """LLM流式输出事件"""
    
    def __init__(self, agent_name: str, agent_type: str, content: str,
                 is_complete: bool = False, conversation_id: str = None,
                 user_id: Optional[str] = None, **kwargs):
        super().__init__(
            conversation_id=conversation_id,
            user_id=user_id or "system",
            **kwargs
        )
        self.data.update({
            "content": content,
            "is_complete": is_complete,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "timestamp": datetime.now().isoformat(),
        })


class ToolResultDisplayEvent(ConversationEvent):
    """工具结果显示事件"""
    
    def __init__(self, tool_name: str, result: str, conversation_id: str = None,
                 user_id: Optional[str] = None, truncated: bool = False, **kwargs):
        super().__init__(
            conversation_id=conversation_id,
            user_id=user_id or "system",
            **kwargs
        )
        self.data.update({
            "tool_name": tool_name,
            "result": result,
            "truncated": truncated,
            "timestamp": datetime.now().isoformat(),
        })


# ============================================================================
# Event Factory Functions
# ============================================================================

def create_conversation_created_event(conversation_id: str, user_id: str,
                                    title: Optional[str] = None) -> ConversationCreatedEvent:
    """创建对话创建事件"""
    return ConversationCreatedEvent(
        conversation_id=conversation_id,
        user_id=user_id,
        title=title,
        source="conversation_service"
    )


def create_user_input_event(conversation_id: str, user_id: str, message: str,
                           parent_event_id: Optional[str] = None) -> UserInputEvent:
    """创建用户输入事件"""
    event = UserInputEvent(
        conversation_id=conversation_id,
        user_id=user_id,
        message=message,
        source="user_interface"
    )
    if parent_event_id:
        event.parent_events = [parent_event_id]
    return event


def create_interrupt_event(conversation_id: str, user_id: str,
                         interrupted_event_id: Optional[str] = None) -> InterruptEvent:
    """创建中断事件"""
    return InterruptEvent(
        conversation_id=conversation_id,
        user_id=user_id,
        interrupted_event_id=interrupted_event_id,
        source="user_interface"
    )
