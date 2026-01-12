from typing import Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.agent.base import TaskInterrupted
from app.agent.manus import Manus
from core.task import TaskStatus
from core.task_registry import TaskRegistry
from core.task_runner import run_with_status
from server.tasks import run_task

app = FastAPI(title="OpenManus Task API", version="0.1.0")
registry = TaskRegistry()


async def _run_agent(task_id: str, prompt: Optional[str]) -> None:
    # Legacy background runner (unused when Celery is available)
    task = registry.get_task(task_id)
    if not task:
        return
    async def _work():
        agent = await Manus.create()
        await agent.run(task, prompt)
    await run_with_status(task, _work())


@app.post("/tasks")
async def create_task(prompt: Optional[str] = None):
    task = registry.create_task(input={"prompt": prompt} if prompt else None)
    task.status = TaskStatus.CREATED
    # enqueue Celery task
    run_task.delay(task.id, prompt)
    return {"id": task.id, "status": task.status}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "status": task.status,
        "interrupt_flag": task.interrupt_flag,
    }


@app.post("/tasks/{task_id}/interrupt")
async def interrupt_task(task_id: str):
    task = registry.interrupt_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "status": task.status, "interrupt_flag": task.interrupt_flag}


@app.get("/", tags=["health"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=8000)
