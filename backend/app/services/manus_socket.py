"""WebSocket事件转发中间件

这个中间件用于自动将特定类型的事件转发到前端WebSocket连接。
"""

import fnmatch
import json
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

from fastapi import WebSocket

from app.event.core.base import BaseEvent
from app.event.infrastructure.middleware import BaseMiddleware, MiddlewareContext
from app.logger import logger


class ManusWebSocketManager:
    """Manus WebSocket connection manager"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = (
            {}
        )  # session_id -> set of connection_ids
        self.connection_sessions: Dict[str, str] = {}  # connection_id -> session_id

    async def connect(
        self, websocket: WebSocket, session_id: str, history_messages: List[dict] = None
    ) -> str:
        """Connect WebSocket and return connection ID"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket

        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)

        logger.info(
            f"Manus WebSocket connected: {connection_id} for session: {session_id}"
        )

        # Push history messages
        if history_messages:
            await self._send_history_messages(websocket, session_id, history_messages)

        return connection_id

    def register_connection(
        self, connection_id: str, session_id: str, websocket: WebSocket
    ):
        """Register a new WebSocket connection"""
        self.active_connections[connection_id] = websocket
        self.connection_sessions[connection_id] = session_id

        # Add to session connections
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)

        logger.info(f"🔌 WebSocket registered: {connection_id} for task: {session_id}")
        logger.info(f"📊 Active connections: {len(self.active_connections)}")
        logger.info(
            f"📋 Session {session_id} connections: {len(self.session_connections[session_id])} - {list(self.session_connections[session_id])}"
        )

    def unregister_connection(self, connection_id: str, session_id: str):
        """Unregister a WebSocket connection"""
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Remove from connection sessions
        if connection_id in self.connection_sessions:
            del self.connection_sessions[connection_id]

        # Remove from session connections
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            # Clean up empty session sets
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]

        logger.info(f"WebSocket unregistered: {connection_id} for task: {session_id}")

    async def _send_history_messages(
        self, websocket: WebSocket, session_id: str, history_messages: List[dict]
    ):
        """Send history messages to newly connected client"""
        try:
            if not history_messages:
                logger.info(f"No history messages found for session {session_id}")
                return

            logger.info(
                f"Sending {len(history_messages)} history messages to session {session_id}"
            )

            # Send original history messages directly, maintaining original message types
            for idx, original_message in enumerate(history_messages):
                try:
                    await websocket.send_text(json.dumps(original_message))
                except Exception as e:
                    logger.error(
                        f"Failed to send history message {idx} to {session_id}: {e}"
                    )
                    break

            # Send completion indicator for history message push
            completion_event = {
                "type": "history_complete",
                "session_id": session_id,
                "total_messages": len(history_messages),
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_text(json.dumps(completion_event))

            logger.info(f"History messages sent successfully to session {session_id}")

        except Exception as e:
            logger.error(
                f"Failed to send history messages to session {session_id}: {e}"
            )

    def disconnect(self, connection_id: str, session_id: str):
        """Disconnect WebSocket connection (legacy method)"""
        self.unregister_connection(connection_id, session_id)

    def disconnect_session(self, session_id: str):
        """Disconnect all WebSocket connections for a session"""
        if session_id in self.session_connections:
            connection_ids = list(self.session_connections[session_id])
            for connection_id in connection_ids:
                self.unregister_connection(connection_id, session_id)
            logger.info(f"Disconnected all connections for session {session_id}")

    def has_active_connections(self, session_id: str) -> bool:
        """Check if session has any active WebSocket connections"""
        return (
            session_id in self.session_connections
            and len(self.session_connections[session_id]) > 0
        )

    def get_connection_count(self, session_id: str) -> int:
        """Get number of active connections for a session"""
        return len(self.session_connections.get(session_id, set()))

    async def send_to_session(self, session_id: str, message: dict):
        """Send message to all connections of specified session"""
        if session_id in self.session_connections:
            connection_ids = self.session_connections[session_id]
            disconnected = []

            for connection_id in connection_ids:
                if connection_id in self.active_connections:
                    try:
                        message_json = json.dumps(message)
                        await self.active_connections[connection_id].send_text(
                            message_json
                        )
                    except Exception as e:
                        logger.error(f"Failed to send message to {connection_id}: {e}")
                        disconnected.append(connection_id)
                else:
                    disconnected.append(connection_id)

            # Clean up disconnected connections
            for connection_id in disconnected:
                self.disconnect(connection_id, session_id)
        else:
            logger.debug(f"No connections found for session {session_id}")


class ManusWebSocketMiddleware(BaseMiddleware):
    """WebSocket事件转发中间件

    自动将匹配特定模式的事件转发到前端WebSocket连接。
    """

    def __init__(
        self,
        websocket_manager: "ManusWebSocketManager" = None,
        forward_patterns: Optional[List[str]] = None,
    ):
        super().__init__("websocket_forwarder")
        self.websocket_manager = websocket_manager

        # 默认转发规则 - 这些事件类型会自动转发到前端
        self.forward_patterns = forward_patterns or [
            "agent.*",  # 智能体相关事件
            "tool.*",  # 工具执行事件
            "conversation.*",  # 对话相关事件
            "stream.*",  # 流式输出事件
            "system.*",  # 系统事件
            "filesystem.*",  # 文件系统事件
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
