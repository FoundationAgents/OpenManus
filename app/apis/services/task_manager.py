import asyncio
import uuid
from datetime import datetime
from typing import Dict

from app.agent.manus import Manus
from app.apis.models.task import Task


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.queues: Dict[str, asyncio.Queue] = {}

    def create_task(self, prompt: str, agent: Manus) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            prompt=prompt,
            created_at=datetime.now(),
            status="pending",
            agent=agent,
            current_step=0,
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()
        return task

    async def update_task_step(
        self, task_id: str, result: str, step_type: str, step: int = None
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if step is not None:
                task.current_step = step
            # Use the same step value for both progress and message
            step_data = {"step": task.current_step, "result": result, "type": step_type}
            task.progress.append(step_data)
            await self.queues[task_id].put(
                {"type": step_type, "step": task.current_step, "result": result}
            )

    async def complete_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"

            # Ensure all progress updates have been sent
            await asyncio.sleep(0.1)

            # Send status update
            await self.queues[task_id].put(
                {
                    "type": "status",
                    "status": task.status,
                    "progress": task.progress,
                    "step": task.current_step,
                }
            )

            # Wait for queue processing
            await asyncio.sleep(0.1)

            # Send completion event
            await self.queues[task_id].put(
                {"type": "complete", "step": task.current_step}
            )

    async def fail_task(self, task_id: str, error: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = f"failed: {error}"
            await self.queues[task_id].put(
                {"type": "error", "message": error, "step": task.current_step}
            )


task_manager = TaskManager()
