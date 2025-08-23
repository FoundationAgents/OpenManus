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


class TaskRequest(BaseModel):
    """Request model for task execution"""
    prompt: str
    task_id: Optional[str] = None


class TaskResponse(BaseModel):
    """Response model for task execution"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    task_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str = "1.0.0"


# Global agent instance
agent: Optional[Manus] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the FastAPI application"""
    global agent
    try:
        # Override config with environment variables
        if "OPENAI_API_KEY" in os.environ:
            for llm_name, llm_config in config.llm.items():
                if llm_config.api_key == "OPENAI_API_KEY_PLACEHOLDER":
                    llm_config.api_key = os.environ["OPENAI_API_KEY"]
        
        # Initialize the agent on startup
        logger.info("Initializing OpenManus agent...")
        agent = await Manus.create()
        logger.info("OpenManus agent initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize OpenManus agent: {e}")
        raise
    finally:
        # Cleanup on shutdown
        if agent:
            logger.info("Cleaning up OpenManus agent...")
            try:
                await agent.cleanup()
            except Exception as e:
                logger.error(f"Error during agent cleanup: {e}")
            logger.info("OpenManus agent cleanup completed")


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
    Execute a task using the OpenManus agent
    
    Args:
        request: Task request containing the prompt to execute
        
    Returns:
        TaskResponse with execution results
    """
    global agent
    
    if not agent:
        raise HTTPException(
            status_code=503, 
            detail="OpenManus agent is not initialized"
        )
    
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400, 
            detail="Prompt cannot be empty"
        )
    
    try:
        logger.info(f"Executing task: {request.prompt[:100]}...")
        
        # Execute the task using the agent
        result = await agent.run(request.prompt)
        
        logger.info("Task execution completed successfully")
        
        return TaskResponse(
            success=True,
            result=result,
            task_id=request.task_id
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Task execution failed: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return TaskResponse(
            success=False,
            error=error_msg,
            task_id=request.task_id
        )


@app.get("/status")
async def get_status():
    """Get the current status of the OpenManus agent"""
    global agent
    
    if not agent:
        return {
            "status": "not_initialized",
            "agent_available": False,
            "connected_mcp_servers": {}
        }
    
    return {
        "status": "ready",
        "agent_available": True,
        "connected_mcp_servers": dict(agent.connected_servers) if hasattr(agent, 'connected_servers') else {}
    }


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