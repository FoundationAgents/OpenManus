from typing import Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.agent.manus import Manus
from app.agent.base import TaskInterrupted
from core.task import TaskStatus
from core.task_registry import TaskRegistry


app = FastAPI(title="OpenManus Task API", version="0.1.0")
registry = TaskRegistry()


async def _run_agent(task_id: str, prompt: Optional[str]) -> None:
    task = registry.get_task(task_id)
    if not task:
        return

    task.status = TaskStatus.RUNNING
    try:
        agent = await Manus.create()
        await agent.run(task, prompt)
        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.DONE
    except TaskInterrupted:
        task.status = TaskStatus.INTERRUPTED
    except Exception as exc:  # pragma: no cover - background safety
        task.status = TaskStatus.FAILED
        task.emit("error", {"message": str(exc)})


@app.post("/tasks")
async def create_task(prompt: Optional[str] = None, background: BackgroundTasks = None):
    task = registry.create_task()
    task.status = TaskStatus.CREATED
    if background is not None:
        background.add_task(_run_agent, task.id, prompt)
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


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=8000)
