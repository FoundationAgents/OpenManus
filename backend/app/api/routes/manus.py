"""
OpenManus Backend Manus API Routes
Contains HTTP API and WebSocket interfaces
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Set

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

from app.event import BaseEvent, bus
from app.logger import logger
from backend.app.api.models import (
    ManusRunRequest,
    ManusRunResponse,
    SessionListResponse,
)
from backend.app.core.session import session_manager
from backend.app.services.manus_service import ManusService

# Create router
router = APIRouter(prefix="/api/manus", tags=["manus"])

# Create service instance (singleton pattern)
_manus_service_instance = None


def get_manus_service():
    """获取ManusService单例实例"""
    global _manus_service_instance
    if _manus_service_instance is None:
        _manus_service_instance = ManusService()
        logger.info("Created new ManusService instance")
    return _manus_service_instance


manus_service = get_manus_service()


async def handle_frontend_event(message: dict, session_id: str):
    """处理前端发送的事件

    Args:
        message: 前端发送的消息
        session_id: 会话ID
    """
    try:
        # 创建BaseEvent对象
        event = BaseEvent(
            event_type=message.get("event_type"),
            data=message.get("data", {}),
            source="frontend",
        )

        # 确保事件数据中包含session信息
        if "conversation_id" not in event.data:
            event.data["conversation_id"] = session_id
        if "session_id" not in event.data:
            event.data["session_id"] = session_id

        # 使用现有的事件系统发布事件
        await bus.publish(event)

        logger.info(
            f"Successfully processed frontend event: {event.event_type} for session {session_id}"
        )

    except Exception as e:
        logger.error(f"Error handling frontend event for session {session_id}: {e}")
        raise


# HTTP API routes
@router.post("/sessions", response_model=ManusRunResponse)
async def create_session(request: ManusRunRequest, background_tasks: BackgroundTasks):
    """Create chat session and start task"""
    try:
        # Generate session ID
        session_id = request.session_id or str(uuid.uuid4())

        # Create session
        session_manager.create_session(
            session_id,
            prompt=request.prompt,
            max_steps=request.max_steps,
            max_observe=request.max_observe,
        )

        # Run task in background
        background_tasks.add_task(
            manus_service.run_manus_task,
            session_id,
            request.prompt,
            request.max_steps,
            request.max_observe,
        )

        return ManusRunResponse(
            session_id=session_id,
            status="started",
            result=None,
            error=None,
        )

    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_manus_sessions():
    """List all Manus sessions"""
    try:
        sessions_dict = session_manager.list_sessions()
        # Convert dict to list of session objects
        sessions_list = list(sessions_dict.values())
        return SessionListResponse(sessions=sessions_list)

    except Exception as e:
        logger.error(f"Error listing Manus sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_manus_session(session_id: str):
    """Delete a Manus session"""
    try:
        success = session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        # Also disconnect any WebSocket connections for this session
        if hasattr(manus_service, "websocket_manager"):
            manus_service.websocket_manager.disconnect_session(session_id)

        return {"message": f"Session {session_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Manus session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket routes - for listening to task streaming data


@router.websocket("/sessions/ws/{session_id}")
async def manus_stream_websocket(websocket: WebSocket, session_id: str):
    """Manus WebSocket interface - maintains persistent connection for task communication"""
    connection_id = None
    try:
        # Accept WebSocket connection immediately - no session dependency
        await websocket.accept()
        connection_id = str(uuid.uuid4())

        # Register connection with WebSocket manager
        manus_service.websocket_manager.register_connection(
            connection_id, session_id, websocket
        )

        logger.info(f"WebSocket connected: {connection_id} for task: {session_id}")

        # Send connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "connection_id": connection_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        # Send any existing message history if available
        logger.info(f"🔍 Checking history for session: {session_id}")
        history_messages = manus_service.get_message_history(session_id)
        logger.info(
            f"📚 Found {len(history_messages)} history messages for session {session_id}"
        )

        if history_messages:
            for i, message in enumerate(history_messages):
                logger.info(
                    f"📤 Sending history message {i+1}/{len(history_messages)}: {message.get('event_type', 'unknown')}"
                )
                await websocket.send_text(json.dumps(message))
            logger.info(
                f"✅ Sent {len(history_messages)} history messages to {session_id}"
            )
        else:
            logger.info(f"❌ No history messages found for session {session_id}")

        # Keep connection alive and listen for messages
        while True:
            try:
                # Receive client messages
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    # Handle ping messages
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.now().isoformat()}
                        )
                    )
                elif message.get("type") == "event":
                    # Handle frontend events
                    await handle_frontend_event(message, session_id)

                    # Send acknowledgment back to frontend
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "event_ack",
                                "event_id": message.get("event_id"),
                                "status": "received",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )
                else:
                    # Log unknown message types
                    logger.warning(
                        f"Unknown message type received: {message.get('type')}"
                    )

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket client disconnected: {connection_id} for task: {session_id}"
                )
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from client: {e}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                # Send error response to client
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "error": str(e),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )
                except:
                    # If we can't send error response, connection is probably broken
                    break
    except Exception as e:
        logger.error(f"WebSocket error for task {session_id}: {e}")
    finally:
        # Clean up connection
        if connection_id:
            manus_service.websocket_manager.unregister_connection(
                connection_id, session_id
            )
            logger.info(
                f"WebSocket connection cleaned up: {connection_id} for task: {session_id}"
            )
