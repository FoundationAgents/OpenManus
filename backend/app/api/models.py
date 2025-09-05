"""
OpenManus Backend API Data Models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.core.config import config


class ManusRequest(BaseModel):
    """Manus task request model"""

    prompt: str = Field(..., description="Input prompt for Manus")
    session_id: Optional[str] = Field(
        None, description="Session ID, will be auto-generated if not provided"
    )
    max_steps: Optional[int] = Field(
        config.default_max_steps, description="Maximum execution steps"
    )
    max_observe: Optional[int] = Field(
        config.default_max_observe, description="Maximum observation length"
    )


class ManusRunRequest(BaseModel):
    """Manus run request model"""

    prompt: str = Field(..., description="Input prompt for Manus")
    session_id: Optional[str] = Field(
        None, description="Session ID, will be auto-generated if not provided"
    )
    max_steps: Optional[int] = Field(
        config.default_max_steps, description="Maximum execution steps"
    )
    max_observe: Optional[int] = Field(
        config.default_max_observe, description="Maximum observation length"
    )


class ManusRunResponse(BaseModel):
    """Manus run response model"""

    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Execution status")
    result: Optional[str] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message")


class ManusStatusResponse(BaseModel):
    """Manus status response model"""

    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    progress: Optional[float] = Field(None, description="Execution progress")
    current_step: Optional[int] = Field(None, description="Current step")


class ManusResultResponse(BaseModel):
    """Manus result response model"""

    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Execution status")
    result: Optional[str] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message")
    message: Optional[str] = Field(None, description="Operation result message")


class ManusResponse(BaseModel):
    """Manus task response model"""

    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Execution status")
    result: Optional[str] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message")
    steps: Optional[List[Dict[str, Any]]] = Field(None, description="Execution steps")


class SessionStatus(BaseModel):
    """Session status model"""

    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    progress: Optional[float] = Field(None, description="Execution progress")
    current_step: Optional[int] = Field(None, description="Current step")


class SessionListResponse(BaseModel):
    """Session list response model"""

    sessions: List[Dict[str, Any]] = Field(..., description="Session list")


class DeleteSessionResponse(BaseModel):
    """Delete session response model"""

    message: str = Field(..., description="Operation result message")


class HealthResponse(BaseModel):
    """Health check response model"""

    message: str = Field(..., description="Service status message")
    version: str = Field(..., description="API version")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints")
