"""
OpenManus Backend Manus Service Layer
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Set

from fastapi import WebSocket

from app.agent.manus import Manus
from app.event.domain import AgentEvent, ConversationEvent, SystemEvent, ToolEvent
from app.event.infrastructure.bus import get_global_bus
from app.logger import logger
from backend.app.core.session import session_manager


class ManusService:
    """Manus service class"""

    def __init__(self):
        self.websocket_manager = ManusWebSocketManager()
        # Add message history storage, store message list by session ID
        self.message_history: Dict[str, List[dict]] = {}
        self._setup_websocket_forwarder()
        self._register_event_handlers()

    def _store_message(self, session_id: str, message: dict):
        """Store message to history"""
        if session_id not in self.message_history:
            self.message_history[session_id] = []
        self.message_history[session_id].append(message)

        logger.info(
            f"📝 Stored message for session {session_id}: {message.get('event_type', 'unknown')} (total: {len(self.message_history[session_id])})"
        )

        # Limit message count per session to prevent unlimited memory growth
        max_messages = 1000
        if len(self.message_history[session_id]) > max_messages:
            self.message_history[session_id] = self.message_history[session_id][
                -max_messages:
            ]

    def get_message_history(self, session_id: str) -> List[dict]:
        """Get message history for specified session"""
        history = self.message_history.get(session_id, [])
        logger.info(f"📖 Retrieved {len(history)} messages for session {session_id}")
        return history

    def clear_message_history(self, session_id: str):
        """Clear message history for specified session"""
        if session_id in self.message_history:
            del self.message_history[session_id]

    def _setup_websocket_forwarder(self):
        """设置WebSocket转发中间件到全局事件系统"""
        try:
            from app.event import WebSocketForwarderMiddleware

            # 获取全局事件总线
            bus = get_global_bus()

            # 创建WebSocket转发中间件
            websocket_forwarder = WebSocketForwarderMiddleware(
                websocket_manager=self.websocket_manager
            )

            # 将中间件添加到事件总线的中间件链中（用于事件级别转发）
            if hasattr(bus, "middleware_chain") and bus.middleware_chain:
                bus.middleware_chain.add_middleware(websocket_forwarder)
                logger.info(
                    "WebSocket forwarder middleware added to global event bus for event-level forwarding"
                )
            else:
                logger.warning("Global event bus does not have middleware chain")

        except Exception as e:
            logger.error(f"Failed to setup WebSocket forwarder: {e}")
            # 不抛出异常，让服务继续运行

    def _register_event_handlers(self):
        """Register event handlers to listen for Manus agent events"""
        try:
            from app.event import event_handler

            # Register event handlers for message history storage only
            # WebSocket forwarding is now handled by WebSocketForwarderMiddleware
            @event_handler(["conversation.*"])
            async def handle_conversation_events(event: ConversationEvent):
                """Handle conversation events - store to history only"""
                logger.info(
                    f"Received conversation event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )
                # Only store to message history, WebSocket forwarding handled by middleware
                conversation_id = getattr(event, "conversation_id", None)
                if conversation_id:
                    message = {
                        "type": "agent_event",
                        "event_type": event.event_type,
                        "conversation_id": conversation_id,
                        "data": getattr(event, "data", {}),
                        "content": getattr(event, "data", {}).get("content", ""),
                        "timestamp": datetime.now().isoformat(),
                    }
                    # Store message to history
                    logger.info(
                        f"💾 Storing conversation message for conversation_id: {conversation_id}"
                    )
                    self._store_message(conversation_id, message)
                return True

            @event_handler(["agent.*"])
            async def handle_agent_step_events(event: AgentEvent):
                """Handle Agent step events - store to history only"""
                conversation_id = getattr(event, "conversation_id", None)
                logger.info(
                    f"Received agent event: {event.event_type}, conversation_id: {conversation_id}"
                )

                # Only store to message history, WebSocket forwarding handled by middleware
                if conversation_id:
                    # Get information from event data
                    event_data = getattr(event, "data", {})
                    message = {
                        "type": "agent_event",
                        "event_type": event.event_type,
                        "session_id": conversation_id,
                        "step": event_data.get("step_number", 0),
                        "data": {
                            "agent_name": event_data.get("agent_name", ""),
                            "agent_type": event_data.get("agent_type", ""),
                            "step_number": event_data.get("step_number", 0),
                            "result": event_data.get("result", None),
                            "start_time": event_data.get("start_time", None),
                            "complete_time": event_data.get("complete_time", None),
                        },
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Store message to history
                    self._store_message(conversation_id, message)
                return True

            @event_handler(["tool.*"])
            async def handle_tool_events(event: ToolEvent):
                """Handle tool execution events - store to history only"""
                logger.info(
                    f"Received tool event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )

                # Only store to message history, WebSocket forwarding handled by middleware
                conversation_id = getattr(event, "conversation_id", None)
                if conversation_id:
                    message = {
                        "type": "agent_event",
                        "event_type": event.event_type,
                        "conversation_id": conversation_id,
                        "data": getattr(event, "data", {}),
                        "content": f"Tool: {event.event_type}",
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Store message to history
                    self._store_message(conversation_id, message)
                return True

            @event_handler(["stream.*"])
            async def handle_stream_events(event: SystemEvent):
                """Handle streaming output events - store to history only"""
                logger.info(
                    f"Received stream event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )

                # Only store to message history, WebSocket forwarding handled by middleware
                conversation_id = getattr(event, "conversation_id", None)
                if conversation_id:
                    message = {
                        "type": "agent_event",
                        "event_type": event.event_type,
                        "conversation_id": conversation_id,
                        "data": getattr(event, "data", {}),
                        "content": f"Stream: {event.event_type}",
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Store message to history
                    self._store_message(conversation_id, message)
                return True

            logger.info("Manus event handlers registered successfully")

        except Exception as e:
            logger.error(f"Failed to register Manus event handlers: {e}")

    async def run_manus_task(
        self, session_id: str, prompt: str, max_steps: int, max_observe: int
    ):
        """Run Manus task in background"""
        try:
            # Create Manus instance
            agent = await Manus.create()

            # Update session status
            session_manager.update_session(
                session_id,
                agent=agent,
                status="running",
                current_step=0,
                max_steps=max_steps,
            )

            # Set agent parameters
            agent.max_steps = max_steps
            agent.max_observe = max_observe
            agent.conversation_id = session_id  # Set conversation_id for event tracking

            # Set conversation_id for all tools to enable proper event tracking
            for tool in agent.available_tools.tools:
                if hasattr(tool, "conversation_id"):
                    tool.conversation_id = session_id

            # Run agent
            logger.info(f"Started processing session {session_id} request: {prompt}")
            await agent.run(prompt)

            # Get execution result
            result = ""
            if agent.memory.messages:
                # Get last message as result
                last_message = agent.memory.messages[-1]
                if hasattr(last_message, "content") and last_message.content:
                    result = last_message.content
                elif hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    result = f"Executed {len(last_message.tool_calls)} tool calls"

            # Update session status to completed
            session_manager.update_session(
                session_id,
                status="completed",
                result=result,
                progress=100.0,
            )

            logger.info(f"Session {session_id} processing completed")

        except Exception as e:
            logger.error(f"Session {session_id} processing error: {e}")
            session_manager.update_session(session_id, status="error", error=str(e))


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
