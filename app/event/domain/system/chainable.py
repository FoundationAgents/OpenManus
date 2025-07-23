"""Chainable system events."""

from datetime import datetime
from typing import Any, Optional

from app.event.core.base import ChainableEvent


class ChainableSystemEvent(ChainableEvent):
    """支持链式的系统事件基类"""
    
    def __init__(self, component: str, conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=f"system.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "component": component,
                "conversation_id": conversation_id,
            },
            **kwargs
        )


class ChainableLogWriteEvent(ChainableSystemEvent):
    """日志写入事件（支持链式）"""
    
    def __init__(self, component: str, log_level: str, message: str,
                 conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            component=component,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "log_level": log_level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })


class ChainableMetricsUpdateEvent(ChainableSystemEvent):
    """指标更新事件（支持链式）"""
    
    def __init__(self, component: str, metric_name: str, value: Any,
                 conversation_id: Optional[str] = None, **kwargs):
        super().__init__(
            component=component,
            conversation_id=conversation_id,
            **kwargs
        )
        self.data.update({
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        })


class ChainableStreamEvent(ChainableEvent):
    """支持链式的流式输出事件基类"""
    
    def __init__(self, agent_id: str, conversation_id: str, stream_id: str, **kwargs):
        super().__init__(
            event_type=f"stream.{self.__class__.__name__.lower().replace('event', '')}",
            data={
                "agent_id": agent_id,
                "conversation_id": conversation_id,
                "stream_id": stream_id,
            },
            **kwargs
        )


class ChainableStreamStartEvent(ChainableStreamEvent):
    """流式输出开始事件（支持链式）"""
    
    def __init__(self, agent_id: str, conversation_id: str, stream_id: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            conversation_id=conversation_id,
            stream_id=stream_id,
            **kwargs
        )
        self.data.update({
            "start_time": datetime.now().isoformat(),
        })


class ChainableStreamChunkEvent(ChainableStreamEvent):
    """流式输出片段事件（支持链式）"""
    
    def __init__(self, agent_id: str, conversation_id: str, stream_id: str, 
                 chunk_data: str, chunk_index: int, **kwargs):
        super().__init__(
            agent_id=agent_id,
            conversation_id=conversation_id,
            stream_id=stream_id,
            **kwargs
        )
        self.data.update({
            "chunk_data": chunk_data,
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
        })


class ChainableStreamEndEvent(ChainableStreamEvent):
    """流式输出结束事件（支持链式）"""
    
    def __init__(self, agent_id: str, conversation_id: str, stream_id: str, 
                 total_chunks: int, **kwargs):
        super().__init__(
            agent_id=agent_id,
            conversation_id=conversation_id,
            stream_id=stream_id,
            **kwargs
        )
        self.data.update({
            "total_chunks": total_chunks,
            "end_time": datetime.now().isoformat(),
        })


class ChainableStreamInterruptEvent(ChainableStreamEvent):
    """流式输出中断事件（支持链式）"""
    
    def __init__(self, agent_id: str, conversation_id: str, stream_id: str, 
                 new_user_input: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            conversation_id=conversation_id,
            stream_id=stream_id,
            **kwargs
        )
        self.data.update({
            "new_user_input": new_user_input,
            "interrupt_time": datetime.now().isoformat(),
        })
