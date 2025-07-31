"""
OpenManus Backend Manus Service Layer
"""

from datetime import datetime
from typing import Dict, List

from app.agent.manus import Manus
from app.event.domain import AgentEvent, ConversationEvent, SystemEvent, ToolEvent
from app.logger import logger
from backend.app.core.session import session_manager
from backend.app.services.manus_socket import ManusWebSocketManager


class ManusService:
    """Manus service class"""

    def __init__(self):
        """Initialize ManusService with WebSocket manager and event handlers"""
        self.websocket_manager = ManusWebSocketManager()
        self.message_history: Dict[str, List[dict]] = {}

        # 注册事件处理器和WebSocket中间件
        self._register_event_handlers()
        self._register_websocket_middleware()

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

    def _register_websocket_middleware(self):
        """注册WebSocket中间件到事件总线"""
        try:
            from app.event.infrastructure.bus import bus
            from backend.app.services.manus_socket import ManusWebSocketMiddleware

            # 创建WebSocket转发中间件
            websocket_forwarder = ManusWebSocketMiddleware(
                websocket_manager=self.websocket_manager
            )

            # 使用新的注册机制注册中间件
            success = bus.register_middleware(websocket_forwarder)
            if success:
                logger.info("WebSocket middleware registered successfully")
            else:
                logger.warning("Failed to register WebSocket middleware")

        except Exception as e:
            logger.error(f"Failed to register WebSocket middleware: {e}")
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

                # Skip user input events from continue_conversation to avoid duplicate storage
                # User input is already stored in continue_conversation method
                if event.event_type == "conversation.userinput":
                    logger.info(
                        f"Skipping user input event storage - already handled by continue_conversation"
                    )
                    return True

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

            # Start filesystem watching for this session
            from backend.app.services.filesystem_watcher import filesystem_watcher

            filesystem_watcher.start_watching_session(session_id)

            # Set conversation_id for all tools to enable proper event tracking
            for tool in agent.available_tools.tools:
                if hasattr(tool, "conversation_id"):
                    tool.conversation_id = session_id

            # Store initial user message to history
            initial_message_data = {
                "type": "agent_event",
                "event_type": "conversation.userinput",
                "conversation_id": session_id,
                "content": prompt,
                "timestamp": datetime.now().isoformat(),
                "data": {"message": prompt, "role": "user"},
            }
            self._store_message(session_id, initial_message_data)
            logger.info(
                f"💾 Stored initial user message to history for session {session_id}"
            )

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
        finally:
            # Stop filesystem watching when session ends
            from backend.app.services.filesystem_watcher import filesystem_watcher

            filesystem_watcher.stop_watching_session(session_id)

    async def continue_conversation(self, session_id: str, user_message: str):
        """Continue conversation with existing agent"""
        try:
            # Ensure filesystem watching is active for this session
            from backend.app.services.filesystem_watcher import filesystem_watcher

            if session_id not in filesystem_watcher.get_watching_sessions():
                filesystem_watcher.start_watching_session(session_id)

            # Get session data
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            agent = session.get("agent")
            if not agent:
                raise ValueError(f"No agent found for session {session_id}")

            # Update session status to running
            session_manager.update_session(
                session_id,
                status="running",
                current_step=agent.current_step,
            )

            # Reset agent state to allow continuation
            from app.agent.base import AgentState

            agent.state = AgentState.IDLE

            # Add user message to agent memory
            agent.update_memory("user", user_message)

            # Store user message to history
            user_message_data = {
                "type": "agent_event",
                "event_type": "conversation.userinput",
                "conversation_id": session_id,
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
                "data": {"message": user_message, "role": "user"},
            }
            self._store_message(session_id, user_message_data)
            logger.info(f"💾 Stored user message to history for session {session_id}")

            # Also publish user input event for real-time frontend display
            from app.event import UserInputEvent, bus

            try:
                user_input_event = UserInputEvent(
                    conversation_id=session_id, message=user_message
                )
                await bus.publish(user_input_event)
                logger.info(
                    f"📡 Published user input event for real-time display: {session_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to publish user input event for real-time display: {e}"
                )

            # Continue agent execution
            logger.info(
                f"Continuing conversation for session {session_id} with message: {user_message}"
            )

            # Import bus for event publishing
            from app.event.infrastructure.bus import bus

            # Run agent with the new input
            result = ""
            async with agent.state_context(AgentState.RUNNING):
                while (
                    agent.current_step < agent.max_steps
                    and agent.state != AgentState.FINISHED
                ):
                    agent.current_step += 1
                    logger.info(
                        f"Executing step {agent.current_step}/{agent.max_steps}"
                    )

                    # Publish step start event
                    if agent.enable_events:
                        try:
                            from app.event import AgentStepStartEvent

                            event = AgentStepStartEvent(
                                agent_name=agent.name,
                                agent_type=agent.__class__.__name__,
                                step_number=agent.current_step,
                                conversation_id=session_id,
                            )
                            await bus.publish(event)
                        except Exception as e:
                            logger.warning(
                                f"Failed to publish agent step start event: {e}"
                            )

                    # Execute agent thinking and action
                    try:
                        should_continue = await agent.think()
                        if not should_continue:
                            logger.info(
                                f"Agent decided to stop at step {agent.current_step}"
                            )
                            break

                        if agent.tool_calls:
                            tool_result = await agent.act()
                            if tool_result:
                                result = tool_result

                        # Publish step complete event
                        if agent.enable_events:
                            try:
                                from app.event import AgentStepCompleteEvent

                                event = AgentStepCompleteEvent(
                                    agent_name=agent.name,
                                    agent_type=agent.__class__.__name__,
                                    step_number=agent.current_step,
                                    conversation_id=session_id,
                                    result=result or "Step completed",
                                )
                                await bus.publish(event)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to publish agent step complete event: {e}"
                                )

                    except Exception as e:
                        logger.error(f"Error in agent step {agent.current_step}: {e}")
                        # Publish error event
                        if agent.enable_events:
                            try:
                                from app.event import AgentErrorEvent

                                event = AgentErrorEvent(
                                    agent_name=agent.name,
                                    agent_type=agent.__class__.__name__,
                                    conversation_id=session_id,
                                    error=str(e),
                                )
                                await bus.publish(event)
                            except Exception as event_error:
                                logger.warning(
                                    f"Failed to publish agent error event: {event_error}"
                                )
                        break

            # Get final result
            if agent.memory.messages:
                last_message = agent.memory.messages[-1]
                if hasattr(last_message, "content") and last_message.content:
                    result = last_message.content
                elif hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    result = f"Executed {len(last_message.tool_calls)} tool calls"

            # Update session status
            final_status = (
                "completed" if agent.state == AgentState.FINISHED else "running"
            )
            session_manager.update_session(
                session_id,
                status=final_status,
                result=result,
                current_step=agent.current_step,
            )

            logger.info(f"Conversation continuation completed for session {session_id}")

        except Exception as e:
            logger.error(f"Error continuing conversation for session {session_id}: {e}")
            session_manager.update_session(session_id, status="error", error=str(e))
            raise
