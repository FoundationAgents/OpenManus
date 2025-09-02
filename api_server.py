#!/usr/bin/env python3
"""
Minimal API Server for OpenManus
Exposes OpenManus agent functionality through HTTP endpoints
"""

import asyncio
import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent.manus import Manus
from app.logger import logger
from app.config import config
from app.session_manager import ManusSessionManager


class TaskRequest(BaseModel):
    """Request model for task execution"""
    prompt: str
    user_id: str
    room_id: Optional[str] = None


class TaskResponse(BaseModel):
    """Response model for task execution"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str = "1.0.0"


# Global session manager
session_manager: Optional[ManusSessionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the FastAPI application"""
    global session_manager
    try:
        # Override config with environment variables
        if "OPENAI_API_KEY" in os.environ:
            for llm_name, llm_config in config.llm.items():
                if llm_config.api_key == "OPENAI_API_KEY_PLACEHOLDER":
                    llm_config.api_key = os.environ["OPENAI_API_KEY"]
        
        # Initialize the session manager on startup
        logger.info("Initializing OpenManus session manager...")
        session_manager = ManusSessionManager(
            ttl_minutes=30,  # 30 minutes TTL
            max_sessions=100,  # Max 100 concurrent sessions
            cleanup_interval_minutes=5  # Cleanup every 5 minutes
        )
        await session_manager.start()
        logger.info("OpenManus session manager initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize OpenManus session manager: {e}")
        raise
    finally:
        # Cleanup on shutdown
        if session_manager:
            logger.info("Cleaning up OpenManus session manager...")
            try:
                await session_manager.stop()
            except Exception as e:
                logger.error(f"Error during session manager cleanup: {e}")
            logger.info("OpenManus session manager cleanup completed")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="OpenManus API Server",
    description="Minimal API server for OpenManus agent functionality",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy")


@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    Execute a task using a user-specific OpenManus agent
    
    Args:
        request: Task request containing the prompt and user_id
        
    Returns:
        TaskResponse with execution results
    """
    global session_manager
    
    if not session_manager:
        raise HTTPException(
            status_code=503, 
            detail="OpenManus session manager is not initialized"
        )
    
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400, 
            detail="Prompt cannot be empty"
        )
        
    if not request.user_id.strip():
        raise HTTPException(
            status_code=400, 
            detail="User ID cannot be empty"
        )
    
    try:
        logger.info(f"Executing task for user {request.user_id}: {request.prompt[:100]}...")
        
        # Get user-specific agent from session manager
        agent = await session_manager.get_agent(request.user_id, request.room_id)
        
        # Execute the task using the user's agent
        result = await agent.run(request.prompt)
        
        logger.info(f"Task execution completed successfully for user {request.user_id}")
        
        # Reset agent state to IDLE for next execution
        from app.schema import AgentState
        agent.state = AgentState.IDLE
        agent.current_step = 0
        
        # Update session last used time
        session_manager.touch_session(request.user_id)
        
        return TaskResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Task execution failed for user {request.user_id}: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return TaskResponse(
            success=False,
            error=error_msg
        )


@app.post("/system-message", response_model=TaskResponse)
async def send_system_message(request: TaskRequest):
    """
    Send a system-initiated message to a specific user
    Uses the same flow as execute_task but logs it as a system message
    
    Args:
        request: Task request containing the system message (prompt) and user_id
        
    Returns:
        TaskResponse with execution results
    """
    global session_manager
    
    if not session_manager:
        raise HTTPException(
            status_code=503, 
            detail="OpenManus session manager is not initialized"
        )
    
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400, 
            detail="System message cannot be empty"
        )
        
    if not request.user_id.strip():
        raise HTTPException(
            status_code=400, 
            detail="User ID cannot be empty"
        )
    
    try:
        logger.info(f"[SYSTEM MESSAGE] Sending to user {request.user_id}: {request.prompt[:100]}...")
        
        # Get user-specific agent from session manager
        agent = await session_manager.get_agent(request.user_id, request.room_id)
        
        # Execute the system message using the user's agent
        # Note: Currently uses the same prompt processing as user messages
        # This may produce unexpected behavior depending on the system prompt
        result = await agent.run(request.prompt)
        
        logger.info(f"[SYSTEM MESSAGE] Successfully processed for user {request.user_id}")
        
        # Reset agent state to IDLE for next execution
        from app.schema import AgentState
        agent.state = AgentState.IDLE
        agent.current_step = 0
        
        # Update session last used time
        session_manager.touch_session(request.user_id)
        
        return TaskResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[SYSTEM MESSAGE] Failed for user {request.user_id}: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return TaskResponse(
            success=False,
            error=error_msg
        )


@app.get("/status")
async def get_status():
    """Get the current status of the OpenManus session manager"""
    global session_manager
    
    if not session_manager:
        return {
            "status": "not_initialized",
            "session_manager_available": False,
            "active_sessions": 0
        }
    
    stats = session_manager.get_stats()
    return {
        "status": "ready",
        "session_manager_available": True,
        **stats
    }


@app.get("/sessions")
async def get_sessions():
    """Get detailed session information (for debugging)"""
    global session_manager
    
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
        
    return session_manager.get_stats()


@app.delete("/sessions/{user_id}")
async def remove_user_session(user_id: str):
    """Manually remove a user's session"""
    global session_manager
    
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
        
    await session_manager.remove_session(user_id)
    return {"success": True, "message": f"Session for user {user_id} removed"}


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for production
        log_level="info"
    )