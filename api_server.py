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
from app.prompt.manus import SYSTEM_REPORT_NEXT_STEP


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
        
        # Check if agent is already running and handle interrupt
        from app.schema import AgentState
        if agent.state == AgentState.RUNNING:
            logger.info(f"Agent for user {request.user_id} is already running, requesting interrupt")
            
            # Set interrupt request
            agent.interrupt_requested = True
            agent.interrupt_message = request.prompt
            
            # Wait for interrupt to be processed (max 60 seconds)
            for i in range(600):
                await asyncio.sleep(0.1)
                if not agent.interrupt_requested:
                    logger.info(f"Interrupt processed for user {request.user_id}")
                    break
            else:
                logger.warning(f"Interrupt timeout for user {request.user_id} after 60 seconds")
                # Reset interrupt flags on timeout
                agent.interrupt_requested = False
                agent.interrupt_message = None
            
            return TaskResponse(
                success=True,
                result="Message integrated into ongoing conversation"
            )
        else:
            # Execute the task using the user's agent (only if not running)
            try:
                result = await agent.run(request.prompt)
                
                logger.info(f"Task execution completed successfully for user {request.user_id}")
                
                # Update session last used time
                session_manager.touch_session(request.user_id)
                
                return TaskResponse(
                    success=True,
                    result=result
                )
            finally:
                # Always reset agent state to IDLE for next execution, regardless of success/failure
                from app.schema import AgentState
                agent.state = AgentState.IDLE
                agent.current_step = 0
                # Clear interrupt flags in case of unexpected errors
                agent.interrupt_requested = False
                agent.interrupt_message = None
        
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
    Send a system-generated report about the care recipient to the family
    Uses system report mode for appropriate messaging style
    
    Args:
        request: Task request containing the report content (prompt) and user_id
        
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
        logger.info(f"[SYSTEM REPORT] Sending to family of user {request.user_id}: {request.prompt[:100]}...")
        
        # Get user-specific agent from session manager
        agent = await session_manager.get_agent(request.user_id, request.room_id)
        
        # Enable system report mode for appropriate messaging
        agent.is_system_report = True
        
        # Set the report-specific next step prompt with the report content
        agent.next_step_prompt = SYSTEM_REPORT_NEXT_STEP.format(
            report_content=request.prompt
        )
        
        try:
            # Execute the system report using the modified agent
            result = await agent.run("")  # Empty string as initial request since prompt is in next_step_prompt
            
            logger.info(f"[SYSTEM REPORT] Successfully sent to family of user {request.user_id}")
            
            # Update session last used time
            session_manager.touch_session(request.user_id)
        finally:
            # Always reset agent state and flags for next execution
            from app.schema import AgentState
            agent.state = AgentState.IDLE
            agent.current_step = 0
            agent.is_system_report = False  # Reset system report mode
        
        return TaskResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[SYSTEM REPORT] Failed for user {request.user_id}: {error_msg}")
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