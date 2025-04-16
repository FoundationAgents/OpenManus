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

    def create_task(self, task_id: str, agent: Manus) -> Task:
        task = Task(
            id=task_id,
            created_at=datetime.now(),
            agent=agent,
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()
        return task

    async def update_task_progress(
        self, task_id: str, event_name: str, step: int, **kwargs
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            # Use the same step value for both progress and message
            await self.queues[task_id].put(
                {
                    "type": "progress",
                    "event_name": event_name,
                    "step": step,
                    "content": kwargs,
                }
            )

    async def terminate_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            await task.agent.terminate()
            await self.remove_task(task_id)

    async def remove_task(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]
            del self.queues[task_id]


task_manager = TaskManager()
