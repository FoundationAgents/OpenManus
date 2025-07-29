"""Basic system events."""

from typing import Any, Dict, Optional

from app.event.core.base import BaseEvent


class SystemEvent(BaseEvent):
    """Base class for all system-related events."""

    def __init__(self, component: str, **kwargs):
        super().__init__(
            event_type=f"system.{self.__class__.__name__.lower().replace('event', '')}",
            data={"component": component},
            **kwargs,
        )


class SystemErrorEvent(SystemEvent):
    """系统错误事件"""

    def __init__(
        self,
        component: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(component=component, **kwargs)
        self.data.update(
            {
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
            }
        )
        if conversation_id:
            self.conversation_id = conversation_id


def create_system_error_event(
    component: str,
    error_type: str,
    error_message: str,
    conversation_id: Optional[str] = None,
) -> SystemErrorEvent:
    """创建系统错误事件"""
    return SystemErrorEvent(
        component=component,
        error_type=error_type,
        error_message=error_message,
        conversation_id=conversation_id,
        source=component,
    )
