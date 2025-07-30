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
            **kwargs,
        )
        # 设置追踪信息
        self.conversation_id = conversation_id
        self.user_id = user_id


class ConversationCreatedEvent(ConversationEvent):
    """对话创建事件"""

    def __init__(
        self, conversation_id: str, user_id: str, title: Optional[str] = None, **kwargs
    ):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update(
            {
                "title": title,
                "created_at": datetime.now().isoformat(),
            }
        )


class ConversationClosedEvent(ConversationEvent):
    """对话关闭事件"""

    def __init__(
        self, conversation_id: str, user_id: str, reason: str = "user_closed", **kwargs
    ):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update(
            {
                "reason": reason,
                "closed_at": datetime.now().isoformat(),
            }
        )


class UserInputEvent(ConversationEvent):
    """用户输入事件"""

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        message_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update(
            {
                "message": message,
                "message_id": message_id or str(uuid.uuid4()),
                "input_length": len(message),
            }
        )


class UserInterruptEvent(ConversationEvent):
    """用户中断事件"""

    def __init__(self, conversation_id: str, user_id: str, reason: str, **kwargs):
        super().__init__(conversation_id=conversation_id, user_id=user_id, **kwargs)
        self.data.update({"reason": reason})


class AgentResponseEvent(ConversationEvent):
    """智能体响应事件"""

    def __init__(
        self,
        agent_name: str,
        agent_type: str,
        response: str,
        conversation_id: str,
        user_id: Optional[str] = None,
        response_type: str = "text",
        **kwargs,
    ):
        # For conversation events, we need user_id, but for agent responses it might not be directly available
        # We'll use a placeholder or get it from the conversation context
        super().__init__(
            conversation_id=conversation_id,
            user_id=user_id or "system",  # Use system as fallback
            **kwargs,
        )
        self.data.update(
            {
                "response": response,
                "response_type": response_type,
                "response_length": len(response),
                "response_time": datetime.now().isoformat(),
                "agent_name": agent_name,
                "agent_type": agent_type,
            }
        )
