import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.manus import Manus
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])

AGENT_NAME = "Manus"


@router.post("")
async def create_task(
    task_id: Optional[str] = Form(None),
    prompt: str = Form(...),
):
    task_id = task_id or str(uuid.uuid4())
    agent = await Manus.create()

    task = task_manager.create_task(task_id, agent)

    asyncio.create_task(task_manager.run_task(task.id, prompt))
    return {"task_id": task.id}


@router.get("/{task_id}/events")
async def task_events(task_id: str):
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


@router.get("")
async def get_tasks():
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content=[task.model_dump() for task in sorted_tasks],
        headers={"Content-Type": "application/json"},
    )


@router.post("/{task_id}/terminate")
async def terminate_task(task_id: str):
    task = task_manager.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.agent.terminate()
    return JSONResponse(
        content={"message": "Task terminated"},
        headers={"Content-Type": "application/json"},
    )
