"""WebSocket事件转发中间件

这个中间件用于自动将特定类型的事件转发到前端WebSocket连接。
"""

import fnmatch
from typing import Callable, List, Optional

from app.event.core.base import BaseEvent
from app.event.infrastructure.middleware import BaseMiddleware, MiddlewareContext
from app.logger import logger


class WebSocketForwarderMiddleware(BaseMiddleware):
    """WebSocket事件转发中间件

    自动将匹配特定模式的事件转发到前端WebSocket连接。
    """

    def __init__(
        self, websocket_manager=None, forward_patterns: Optional[List[str]] = None
    ):
        super().__init__("websocket_forwarder")
        self.websocket_manager = websocket_manager

        # 默认转发规则 - 这些事件类型会自动转发到前端
        self.forward_patterns = forward_patterns or [
            "agent.*",  # 智能体相关事件
            "tool.*",  # 工具执行事件
            "conversation.*",  # 对话相关事件
            "stream.*",  # 流式输出事件
            "system.*",
        ]

        logger.info(
            f"WebSocketForwarder initialized with patterns: {self.forward_patterns}"
        )

    async def process(
        self, context: MiddlewareContext, next_middleware: Callable
    ) -> bool:
        """处理事件 - 在处理器级别不执行转发，转发由事件级别统一处理

        Args:
            context: 中间件上下文
            next_middleware: 下一个中间件

        Returns:
            bool: 处理是否成功
        """
        # 只执行正常的事件处理链，不在这里转发
        # 转发将在事件级别统一处理，避免重复
        result = await next_middleware(context)

        logger.debug(
            f"Handler-level processing completed for {context.event.event_type}, forwarding will be handled at event level"
        )

        return result

    def should_forward(self, event: BaseEvent) -> bool:
        """检查事件是否需要转发到前端

        Args:
            event: 要检查的事件

        Returns:
            bool: 是否需要转发
        """
        # 检查事件类型是否匹配转发模式
        for pattern in self.forward_patterns:
            if self.match_pattern(event.event_type, pattern):
                logger.debug(
                    f"Event {event.event_type} matches pattern {pattern}, will forward"
                )
                return True

        return False

    def match_pattern(self, event_type: str, pattern: str) -> bool:
        """检查事件类型是否匹配模式

        支持简单的通配符匹配，如 'agent.*' 匹配 'agent.step.start'

        Args:
            event_type: 事件类型
            pattern: 匹配模式

        Returns:
            bool: 是否匹配
        """
        return fnmatch.fnmatch(event_type, pattern)

    async def forward_to_frontend(self, event: BaseEvent):
        """将事件转发到前端WebSocket连接

        Args:
            event: 要转发的事件
        """
        logger.info(
            f"🚀 WebSocketForwarder.forward_to_frontend called for event {event.event_type} (ID: {event.event_id})"
        )

        if not self.websocket_manager:
            logger.debug("No WebSocket manager configured, skipping forward")
            return

        # 获取session_id（从conversation_id或其他字段）
        session_id = self.extract_session_id(event)

        if not session_id:
            logger.debug(
                f"No session_id found for event {event.event_id}, skipping forward"
            )
            return

        # 构造要发送到前端的消息
        message = {
            "type": "event",
            "event_type": event.event_type,
            "event_id": event.event_id,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "source": "backend",
        }

        logger.info(f"📤 Sending event {event.event_type} to session {session_id}")
        try:
            # 发送到指定session的所有WebSocket连接
            await self.websocket_manager.send_to_session(session_id, message)
            logger.info(
                f"✅ Successfully sent event {event.event_type} to session {session_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to send event {event.event_id} to session {session_id}: {e}"
            )
            raise

    def extract_session_id(self, event: BaseEvent) -> Optional[str]:
        """从事件中提取session_id

        尝试从多个可能的字段中获取session_id：
        1. event.conversation_id (如果事件有这个属性)
        2. event.data['conversation_id']
        3. event.data['session_id']

        Args:
            event: 事件对象

        Returns:
            Optional[str]: session_id，如果找不到则返回None
        """
        # 方法1: 直接从事件属性获取
        if hasattr(event, "conversation_id") and event.conversation_id:
            return event.conversation_id

        # 方法2: 从事件数据中获取conversation_id
        if "conversation_id" in event.data and event.data["conversation_id"]:
            return event.data["conversation_id"]

        # 方法3: 从事件数据中获取session_id
        if "session_id" in event.data and event.data["session_id"]:
            return event.data["session_id"]

        return None
