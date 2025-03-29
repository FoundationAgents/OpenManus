import asyncio
import base64
from json import dumps
from typing import Optional, cast

from browser_use import DomService
from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import Field

from app.agent.manus import Manus
from app.apis.models.task import Task
from app.apis.services.task_manager import task_manager
from app.config import LLMSettings
from app.llm import LLM
from app.logger import logger
from app.tool.browser_use_tool import BrowserUseTool

router = APIRouter(prefix="/tasks", tags=["tasks"])

AGENT_NAME = "Manus"


async def handle_agent_event(task_id: str, event_name: str, step: int, **kwargs):
    """Handle agent events and update task status.

    Args:
        event_name: Name of the event
        **kwargs: Additional parameters related to the event
    """
    if not task_id:
        logger.warning(f"No task_id provided for event: {event_name}")
        return

    # Update task step
    await task_manager.update_task_progress(
        task_id=task_id, event_name=event_name, step=step, **kwargs
    )


async def run_task(task_id: str):
    """Run the task and set up corresponding event handlers.

    Args:
        task_id: Task ID
        prompt: Task prompt
        llm_config: Optional LLM configuration
    """
    try:
        task = task_manager.tasks[task_id]
        agent = task.agent

        # Set up event handlers based on all event types defined in the Agent class hierarchy
        event_patterns = [r"agent:.*"]

        # Register handlers for each event pattern
        for pattern in event_patterns:
            agent.on(
                pattern,
                lambda event_name, step, **kwargs: handle_agent_event(
                    task_id=task_id,
                    event_name=event_name,
                    step=step,
                    **kwargs,
                ),
            )

        # Run the agent
        result = await agent.run(task.prompt)

        # Ensure all events have been processed
        queue = task_manager.queues[task_id]
        while not queue.empty():
            await asyncio.sleep(0.1)

        await task_manager.complete_task(task_id)

    except Exception as e:
        # Handle task failure
        await task_manager.fail_task(task_id, str(e))


async def event_generator(task_id: str):
    if task_id not in task_manager.queues:
        yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
        return

    queue = task_manager.queues[task_id]

    while True:
        try:
            event = await queue.get()
            formatted_event = dumps(event)

            # Send actual event data
            if event.get("type"):
                yield f"data: {formatted_event}\n\n"
                if event.get("event_name") == Manus.Events.LIFECYCLE_COMPLETE:
                    break

            # Send heartbeat
            yield ":heartbeat\n\n"

        except asyncio.CancelledError:
            logger.info(f"Client disconnected for task {task_id}")
            break
        except Exception as e:
            logger.error(f"Error in event stream: {str(e)}")
            yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
            break


@router.post("")
async def create_task(
    prompt: str = Body(..., embed=True),
    llm_config: Optional[LLMSettings] = Body(None, embed=True),
):
    logger.info(f"Creating task with prompt: {prompt}")
    task = task_manager.create_task(
        prompt,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            llm=(LLM(llm_config=llm_config) if llm_config else None),
            enable_event_queue=True,  # Enable event queue
        ),
    )
    asyncio.create_task(run_task(task.id))
    return {"task_id": task.id}


@router.get("/{task_id}/events")
async def task_events(task_id: str):
    return StreamingResponse(
        event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
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
