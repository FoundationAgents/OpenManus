"""System-wide event types for OpenManus project.

This module defines concrete event classes for different system components,
ensuring all data flows through the event bus for monitoring and processing.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import Field

from app.event.base import BaseEvent
from app.event.types import ToolExecutionStatus


# ============================================================================
# Conversation Events (对话事件)
# ============================================================================

class ConversationEvent(BaseEvent):
    """对话相关事件基类"""

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


# ============================================================================
# Agent Events
# ============================================================================

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
    """LLM流式响应事件"""

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
    """工具执行结果显示事件"""

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
# Tool Events
# ============================================================================

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


# ============================================================================
# System Events
# ============================================================================

class SystemEvent(BaseEvent):
    """Base class for all system-related events."""

    def __init__(self, component: str, **kwargs):
        super().__init__(
            event_type=f"system.{self.__class__.__name__.lower().replace('event', '')}",
            data={"component": component},
            **kwargs
        )


class SystemErrorEvent(SystemEvent):
    """系统错误事件"""

    def __init__(self, component: str, error_type: str, error_message: str,
                 context: Optional[Dict[str, Any]] = None, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            component=component,
            priority=999,
            **kwargs
        )
        self.data.update({
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
        })
        if conversation_id:
            self.conversation_id = conversation_id


# ============================================================================
# System Events
# ============================================================================

class TestEvent(BaseEvent):
    "Test Event"
    def __init__(self, a, b, **kwargs):
        super().__init__(
            event_type=f"test.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "a": a,
                "b": b
            },
            **kwargs
        )

class TestAddEvent(TestEvent):
    "Test Add Event"
    def __init__(self, a, b, **kwargs):
        super().__init__(
            a=a,
            b=b,
            **kwargs
        )


# ============================================================================
# Event Factory Functions (事件工厂函数)
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


def create_system_error_event(component: str, error_type: str, error_message: str,
                             conversation_id: Optional[str] = None) -> SystemErrorEvent:
    """创建系统错误事件"""
    return SystemErrorEvent(
        component=component,
        error_type=error_type,
        error_message=error_message,
        conversation_id=conversation_id,
        source=component
    )
