import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Path
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.agent.manus import Manus
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

AGENT_NAME = "Manus"


class TaskCreateResponse(BaseModel):
    task_id: str
    message: str = "Task created successfully"


class TaskListResponse(BaseModel):
    tasks: list[dict]


class TaskTerminateResponse(BaseModel):
    message: str


@router.post("", response_model=TaskCreateResponse, summary="Create new task")
async def create_task(
    task_id: Optional[str] = Form(
        None, description="Optional task ID, if not provided will generate UUID"
    ),
    prompt: str = Form(..., description="Task prompt"),
):
    """
    Create a new Manus agent task

    - **task_id**: Optional task ID, if not provided will generate UUID
    - **prompt**: Task prompt, used to guide the agent to execute the task

    Return created task ID
    """
    task_id = task_id or str(uuid.uuid4())
    agent = await Manus.create()

    task = task_manager.create_task(task_id, agent, prompt)

    asyncio.create_task(task_manager.run_task(task.id))
    return {"task_id": task.id, "message": "Task created successfully"}


@router.get("/{task_id}/events", summary="Get task event stream")
async def task_events(task_id: str = Path(..., description="Task ID")):
    """
    Get real-time event stream of the specified task

    Use Server-Sent Events (SSE) format to return real-time status updates of the task

    - **task_id**: Task ID to monitor
    """
    return StreamingResponse(
        task_manager.event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        },
    )


@router.get("", response_model=TaskListResponse, summary="Get all tasks")
async def get_tasks():
    """
    Get all tasks list

    Return tasks list sorted by creation time in descending order
    """
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content={
            "tasks": [
                {
                    "id": task.id,
                    "created_at": task.created_at.isoformat(),
                    "request": task.request,
                }
                for task in sorted_tasks
            ]
        },
        headers={"Content-Type": "application/json"},
    )


@router.post(
    "/{task_id}/terminate",
    response_model=TaskTerminateResponse,
    summary="Terminate task",
)
async def terminate_task(task_id: str = Path(..., description="Task ID to terminate")):
    """
    Terminate the specified task

    - **task_id**: Task ID to terminate

    Return termination confirmation message
    """
    task = task_manager.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.agent.terminate()
    return JSONResponse(
        content={"message": "Task terminated"},
        headers={"Content-Type": "application/json"},
    )
