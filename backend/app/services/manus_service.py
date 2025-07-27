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
from app.logger import logger
from backend.app.core.session import session_manager


class ManusService:
    """Manus service class"""

    def __init__(self):
        self.websocket_manager = ManusWebSocketManager()
        # Add message history storage, store message list by session ID
        self.message_history: Dict[str, List[dict]] = {}
        self._register_event_handlers()

    def _store_message(self, session_id: str, message: dict):
        """Store message to history"""
        if session_id not in self.message_history:
            self.message_history[session_id] = []
        self.message_history[session_id].append(message)

        # Limit message count per session to prevent unlimited memory growth
        max_messages = 1000
        if len(self.message_history[session_id]) > max_messages:
            self.message_history[session_id] = self.message_history[session_id][
                -max_messages:
            ]

    def get_message_history(self, session_id: str) -> List[dict]:
        """Get message history for specified session"""
        return self.message_history.get(session_id, [])

    def clear_message_history(self, session_id: str):
        """Clear message history for specified session"""
        if session_id in self.message_history:
            del self.message_history[session_id]

    def _register_event_handlers(self):
        """Register event handlers to listen for Manus agent events"""
        try:
            from app.event import event_handler
            from app.event.init import ensure_event_system_initialized

            # Ensure event system is initialized
            ensure_event_system_initialized()

            # Register event handlers
            @event_handler(["conversation.*"])
            async def handle_conversation_events(event: ConversationEvent):
                """Handle conversation events"""
                logger.info(
                    f"Received conversation event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )
                if self.websocket_manager:
                    conversation_id = getattr(event, "conversation_id", None)
                    if conversation_id:
                        message = {
                            "type": "conversation_event",
                            "event_type": event.event_type,
                            "conversation_id": conversation_id,
                            "data": getattr(event, "data", {}),
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Store message to history
                        self._store_message(conversation_id, message)

                        await self.websocket_manager.send_to_session(
                            conversation_id, message
                        )
                        logger.info(
                            f"Conversation event forwarded to WebSocket: {conversation_id}"
                        )
                return True

            @event_handler(["agent.*"])
            async def handle_agent_step_events(event: AgentEvent):
                """Handle Agent step events"""
                conversation_id = getattr(event, "conversation_id", None)
                logger.info(
                    f"Received agent event: {event.event_type}, conversation_id: {conversation_id}"
                )
                logger.info(
                    f"WebSocket manager exists: {self.websocket_manager is not None}"
                )

                if self.websocket_manager:
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

                        await self.websocket_manager.send_to_session(
                            conversation_id, message
                        )
                        logger.info(f"Event forwarded to WebSocket: {conversation_id}")
                    else:
                        logger.warning(
                            f"Event has no conversation_id: {event.event_type}"
                        )
                return True

            @event_handler(["tool.*"])
            async def handle_tool_events(event: ToolEvent):
                """Handle tool execution events"""
                logger.info(
                    f"Received tool event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )

                if self.websocket_manager:
                    conversation_id = getattr(event, "conversation_id", None)
                    if conversation_id:
                        message = {
                            "type": "tool_event",
                            "event_type": event.event_type,
                            "conversation_id": conversation_id,
                            "data": getattr(event, "data", {}),
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Store message to history
                        self._store_message(conversation_id, message)

                        await self.websocket_manager.send_to_session(
                            conversation_id, message
                        )
                        logger.info(
                            f"Tool event forwarded to WebSocket: {conversation_id}"
                        )
                return True

            @event_handler(["stream.*"])
            async def handle_stream_events(event: SystemEvent):
                """Handle streaming output events"""
                logger.info(
                    f"Received stream event: {event.event_type}, conversation_id: {getattr(event, 'conversation_id', None)}"
                )

                if self.websocket_manager:
                    conversation_id = getattr(event, "conversation_id", None)
                    if conversation_id:
                        message = {
                            "type": "stream_event",
                            "event_type": event.event_type,
                            "conversation_id": conversation_id,
                            "data": getattr(event, "data", {}),
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Store message to history
                        self._store_message(conversation_id, message)

                        await self.websocket_manager.send_to_session(
                            conversation_id, message
                        )
                        logger.info(
                            f"Stream event forwarded to WebSocket: {conversation_id}"
                        )
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
        """Disconnect WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]

        logger.info(
            f"Manus WebSocket disconnected: {connection_id} from session: {session_id}"
        )

    async def send_to_session(self, session_id: str, message: dict):
        """Send message to all connections of specified session"""
        if session_id in self.session_connections:
            disconnected = []
            for connection_id in self.session_connections[session_id]:
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(
                            json.dumps(message)
                        )
                    except Exception as e:
                        logger.error(f"Failed to send message to {connection_id}: {e}")
                        disconnected.append(connection_id)

            # Clean up disconnected connections
            for connection_id in disconnected:
                self.disconnect(connection_id, session_id)
