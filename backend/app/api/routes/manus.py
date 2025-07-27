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

# Create service instance
manus_service = ManusService()


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
        sessions = session_manager.list_sessions()
        return SessionListResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"Error listing Manus sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket routes - for listening to task streaming data


@router.websocket("/sessions/ws/{session_id}")
async def manus_stream_websocket(websocket: WebSocket, session_id: str):
    """Manus streaming data WebSocket interface, only for receiving real-time task processing data"""
    connection_id = None
    try:
        history_messages = manus_service.get_message_history(session_id)

        # Connect WebSocket
        connection_id = await manus_service.websocket_manager.connect(
            websocket, session_id, history_messages
        )

        # Check if session exists
        session_data = session_manager.get_session(session_id)
        if not session_data:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "error": "Session not found",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
            return

        # Keep connection and listen for ping/status queries
        while True:
            try:
                # Receive client messages (only handle control messages)
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.now().isoformat()}
                        )
                    )

            except WebSocketDisconnect:
                logger.info(
                    f"Manus Stream WebSocket client disconnected: {connection_id}"
                )
                break
    except Exception as e:
        logger.error(f"Manus Stream WebSocket error: {e}")
    finally:
        # Clean up connection
        if connection_id:
            manus_service.websocket_manager.disconnect(connection_id, session_id)
