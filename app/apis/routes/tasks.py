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


class SSELogHandler:
    def __init__(self, task_id):
        self.task_id = task_id

    async def __call__(self, message):
        import re

        # Extract - Subsequent Content
        cleaned_message = re.sub(r"^.*? - ", "", message)

        # default event type
        event_type = "log"
        step = None

        # Parse step from message
        if "Executing step" in cleaned_message:
            step_match = re.search(r"Executing step (\d+)/", cleaned_message)
            if step_match:
                step = int(step_match.group(1))
                event_type = "step"

        # think
        if f"✨ {AGENT_NAME}'s thoughts:" in cleaned_message:
            event_type = "think"
        # error
        elif "📝 Oops!" in cleaned_message:
            event_type = "error"
        # tool related
        # tool selected
        elif f"🛠️ {AGENT_NAME} selected" in cleaned_message:
            event_type = "tool:selected"
        # tool prepared
        elif "🧰 Tools being prepared" in cleaned_message:
            event_type = "tool:prepared"
        # tool arguments
        elif "🔧 Tool arguments" in cleaned_message:
            event_type = "tool:arguments"
        # tool activiting
        elif "🔧 Activating tool" in cleaned_message:
            event_type = "tool:activating"
        # tool completed
        elif "🎯 Tool" in cleaned_message:
            event_type = "tool:completed"
        elif "Token usage" in cleaned_message:
            event_type = "token-usage"

        await task_manager.update_task_step(
            self.task_id, cleaned_message, event_type, step
        )


async def run_task(task_id: str, prompt: str, llm_config: Optional[LLMSettings] = None):
    try:
        task_manager.tasks[task_id].status = "running"
        agent = task_manager.tasks[task_id].agent

        sse_handler = SSELogHandler(task_id)
        logger.add(sse_handler)

        result = await agent.run(prompt)
        # Ensure all logs have been processed
        queue = task_manager.queues[task_id]
        while not queue.empty():
            await asyncio.sleep(0.1)

        await task_manager.update_task_step(task_id, result, "result")
        await task_manager.complete_task(task_id)
    except Exception as e:
        await task_manager.fail_task(task_id, str(e))


async def event_generator(task_id: str):
    if task_id not in task_manager.queues:
        yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
        return

    queue = task_manager.queues[task_id]

    task = task_manager.tasks.get(task_id)
    if task:
        yield f"data: {dumps({'type': 'status', 'status': task.status, 'progress': task.progress})}\n\n"

    while True:
        try:
            event = await queue.get()
            formatted_event = dumps(event)

            # Send actual event data
            if event.get("type"):
                yield f"data: {formatted_event}\n\n"

            # Send heartbeat
            yield ":heartbeat\n\n"

            # If complete or error event, ensure remaining events in queue are processed
            if event.get("type") == "complete" or event.get("type") == "error":
                # Process remaining events in queue
                while not queue.empty():
                    remaining_event = queue.get_nowait()
                    remaining_formatted = dumps(remaining_event)
                    yield f"data: {remaining_formatted}\n\n"
                break

        except asyncio.CancelledError:
            print(f"Client disconnected for task {task_id}")
            break
        except Exception as e:
            print(f"Error in event stream: {str(e)}")
            yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
            break


@router.post("")
async def create_task(
    prompt: str = Body(..., embed=True),
    llm_config: Optional[LLMSettings] = Body(None, embed=True),
):
    print(f"Creating task with prompt: {prompt}")
    print(f"LLM config: {llm_config.model_dump()}")
    task = task_manager.create_task(
        prompt,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            llm=(LLM(llm_config=llm_config) if llm_config else None),
        ),
    )
    print("http://localhost:5172/ws/" + task.id)
    asyncio.create_task(run_task(task.id, prompt, llm_config))
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


@router.get("/{task_id}")
async def get_task(task_id: str):
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_manager.tasks[task_id]


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()

    if task_id not in task_manager.tasks:
        await websocket.send_json({"type": "error", "message": "Task not found"})
        await websocket.close()
        return

    agent = task_manager.tasks[task_id].agent

    try:
        while True:
            # Check task status
            if task_manager.tasks[task_id].status == "completed":
                await websocket.send_json(
                    {"type": "complete", "message": "Task completed"}
                )
                break

            # Try to get browser page
            browser_use_tool = agent.available_tools.get_tool("browser_use")

            if (
                browser_use_tool
                and browser_use_tool.dom_service
                and browser_use_tool.dom_service.page
            ):
                try:
                    browser_use_tool = cast(BrowserUseTool, browser_use_tool)
                    page = (cast(BrowserUseTool, browser_use_tool).dom_service).page
                    # Wait for page to load
                    await page.wait_for_load_state("networkidle")

                    # Get current page screenshot
                    current_screenshot = await page.screenshot(
                        type="png", timeout=30000
                    )
                    current_screenshot_base64 = base64.b64encode(
                        current_screenshot
                    ).decode("utf-8")

                    # Send update to frontend
                    await websocket.send_json(
                        {
                            "type": "screenshot",
                            "data": {
                                "screenshot": f"data:image/png;base64,{current_screenshot_base64}",
                            },
                        }
                    )

                except Exception as e:
                    print(f"Error during screenshot process: {e}")

            # Wait for frontend message or timeout
            try:
                # Set 1 second timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if message == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Continue loop on timeout
                continue

    except WebSocketDisconnect:
        print(f"Client disconnected for task {task_id}")
    except Exception as e:
        print(f"Error in WebSocket connection: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
