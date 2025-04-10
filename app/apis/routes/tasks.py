import asyncio
import json
from json import dumps
from pathlib import Path
from typing import List, Optional, Union, cast

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.base import BaseAgentEvents
from app.agent.manus import Manus, McpToolConfig
from app.apis.services.task_manager import task_manager
from app.config import LLMSettings, config
from app.llm import LLM
from app.logger import logger

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
                    **{k: v for k, v in kwargs.items() if k != "task_id"},
                ),
            )

        # Run the agent
        await agent.run(task.prompt)

        # Ensure all events have been processed
        queue = task_manager.queues[task_id]
        while not queue.empty():
            await asyncio.sleep(0.1)

    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")


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
                if event.get("event_name") == BaseAgentEvents.LIFECYCLE_COMPLETE:
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
    await task_manager.remove_task(task_id)


def parse_tools(tools: list[str]) -> list[Union[str, McpToolConfig]]:
    """Parse tools list which may contain both tool names and MCP configurations.

    Args:
        tools: List of tool strings, which can be either tool names or MCP config JSON strings

    Returns:
        List of processed tools, containing both tool names and McpToolConfig objects

    Raises:
        HTTPException: If any tool configuration is invalid
    """
    processed_tools = []
    for tool in tools:
        try:
            tool_config = json.loads(tool)
            if isinstance(tool_config, dict):
                mcp_tool = McpToolConfig.model_validate(tool_config)
                processed_tools.append(mcp_tool)
            else:
                processed_tools.append(tool)
        except json.JSONDecodeError:
            processed_tools.append(tool)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tool configuration for '{tool}': {str(e)}",
            )
    return processed_tools


@router.post("")
async def create_task(
    task_id: str = Form(...),
    prompt: str = Form(...),
    tools: list[str] = Form(...),
    preferences: Optional[str] = Form(None),
    llm_config: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    # Parse preferences and llm_config from JSON strings
    preferences_dict = None
    if preferences:
        try:
            preferences_dict = json.loads(preferences)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid preferences JSON format"
            )

    llm_config_obj = None
    if llm_config:
        try:
            llm_config_obj = LLMSettings.model_validate_json(llm_config)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid llm_config format: {str(e)}"
            )

    processed_tools = parse_tools(tools)

    task = task_manager.create_task(
        task_id,
        prompt,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            llm=(
                LLM(config_name=task_id, llm_config=llm_config_obj)
                if llm_config_obj
                else None
            ),
            enable_event_queue=True,  # Enable event queue
        ),
    )

    await task.agent.initialize(
        task_id,
        language=(
            preferences_dict.get("language", "English") if preferences_dict else None
        ),
        tools=processed_tools,
    )

    if files:
        import os

        task_dir = Path(
            os.path.join(
                config.workspace_root,
                task.agent.task_dir.replace("/workspace/", ""),
            )
        )
        task_dir.mkdir(parents=True, exist_ok=True)
        for file in files or []:
            print(task_dir)
            print(file.filename)
            file = cast(UploadFile, file)
            try:
                safe_filename = Path(file.filename).name
                if not safe_filename:
                    raise HTTPException(status_code=400, detail="Invalid filename")

                file_path = task_dir / safe_filename

                MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
                file_content = file.file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large")

                with open(file_path, "wb") as f:
                    f.write(file_content)

            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Error saving file: {str(e)}"
                )

    asyncio.create_task(run_task(task.id))
    return {"task_id": task.id}


@router.get("/{organization_id}/{task_id}/events")
async def task_events(organization_id: str, task_id: str):
    return StreamingResponse(
        event_generator(f"{organization_id}/{task_id}"),
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


@router.post("/restart")
async def restart_task(
    task_id: str = Form(...),
    prompt: str = Form(...),
    tools: list[str] = Form(...),
    preferences: Optional[str] = Form(None),
    llm_config: Optional[str] = Form(None),
    history: Optional[str] = Form(None),
    files: list[UploadFile] = Form([]),
):
    """Restart a task."""
    # Parse JSON strings
    preferences_dict = None
    if preferences:
        try:
            preferences_dict = json.loads(preferences)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid preferences JSON format"
            )

    llm_config_obj = None
    if llm_config:
        try:
            llm_config_obj = LLMSettings.model_validate_json(llm_config)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid llm_config format: {str(e)}"
            )

    history_list = None
    if history:
        try:
            history_list = json.loads(history)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid history JSON format")

    processed_tools = parse_tools(tools)

    if task_id in task_manager.tasks:
        task = task_manager.tasks[task_id]
        await task.agent.terminate()

    task = task_manager.create_task(
        task_id,
        prompt,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            llm=(
                LLM(config_name=task_id, llm_config=llm_config_obj)
                if llm_config_obj
                else None
            ),
            enable_event_queue=True,
        ),
    )

    if history_list:
        for message in history_list:
            if message["role"] == "user":
                task.agent.update_memory(role="user", content=message["message"])
            else:
                task.agent.update_memory(role="assistant", content=message["message"])

    await task.agent.initialize(
        task_id,
        language=(
            preferences_dict.get("language", "English") if preferences_dict else None
        ),
        tools=processed_tools,
    )

    if files:
        import os

        task_dir = Path(os.path.join(config.workspace_root, task.agent.task_dir))
        task_dir.mkdir(parents=True, exist_ok=True)

        for file in files or []:
            file = cast(UploadFile, file)
            try:
                safe_filename = Path(file.filename).name
                if not safe_filename:
                    raise HTTPException(status_code=400, detail="Invalid filename")

                file_path = task_dir / safe_filename

                MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
                file_content = file.file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large")

                with open(file_path, "wb") as f:
                    f.write(file_content)

            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Error saving file: {str(e)}"
                )

    asyncio.create_task(run_task(task.id))
    return {"task_id": task.id}


@router.post("/terminate")
async def terminate_task(task_id: str = Body(..., embed=True)):
    """Terminate a task immediately.

    Args:
        task_id: The ID of the task to terminate
    """
    if task_id not in task_manager.tasks:
        return {"message": f"Task {task_id} not found"}

    task = task_manager.tasks[task_id]
    await task.agent.terminate()

    return {"message": f"Task {task_id} terminated successfully", "task_id": task_id}
