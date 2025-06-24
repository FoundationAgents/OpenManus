import asyncio
from datetime import datetime
from json import dumps
from typing import Dict

from app.agent.manus import Manus
from app.event import BaseAgentEvents, EventItem
from app.logger import logger
from backend.model.task import Task


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.histories: Dict[str, list] = {}

    async def run_task(self, task_id: str, prompt: str):
        """Run the task and set up corresponding event handlers.

        Args:
            task_id: Task ID
            prompt: Task prompt
            llm_config: Optional LLM configuration
        """
        try:
            task = self.tasks[task_id]
            agent = task.agent

            # Set up event handlers based on all event types defined in the Agent class hierarchy
            event_patterns = [r"agent:.*"]
            # Register handlers for each event pattern
            for pattern in event_patterns:
                agent.event_bus.on(
                    pattern,
                    lambda event: self.update_task_progress(
                        task_id=task_id,
                        event=event,
                    ),
                )

            # Run the agent
            await agent.run(prompt)
            await agent.cleanup()
            asyncio.create_task(self.delayed_remove(task_id))

        except Exception as e:
            logger.error(f"Error in task {task_id}: {str(e)}")

    def create_task(self, task_id: str, agent: Manus) -> Task:
        task = Task(
            id=task_id,
            created_at=datetime.now(),
            agent=agent,
        )
        self.tasks[task_id] = task
        self.histories[task_id] = []
        return task

    async def update_task_progress(self, task_id: str, event: EventItem):
        if task_id in self.tasks:
            event_dict = {
                "index": len(self.histories[task_id]),
                "id": event.id,
                "parent_id": event.parent_id,
                "type": "progress",
                "name": event.name,
                "content": event.content,
                "timestamp": event.timestamp.timestamp(),
            }
            self.histories[task_id].append(event_dict)

    async def remove_task(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]
            del self.histories[task_id]

    async def event_generator(self, task_id: str):
        if task_id not in self.histories:
            yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
            return

        last_index = 0
        heartbeat_interval = 5  # heartbeat interval in seconds
        last_event_time = asyncio.get_event_loop().time()
        while True:
            history = self.histories.get(task_id, [])
            new_events = history[last_index:]
            if new_events:
                for event in new_events:
                    yield f"data: {dumps(event)}\n\n"
                    if event.get("name") == BaseAgentEvents.LIFECYCLE_COMPLETE:
                        return
                last_index = len(history)
                last_event_time = asyncio.get_event_loop().time()
            else:
                now = asyncio.get_event_loop().time()
                if now - last_event_time >= heartbeat_interval:
                    yield ":heartbeat\n\n"
                    last_event_time = now
            await asyncio.sleep(0.5)

    async def delayed_remove(self, task_id: str, delay: int = 1800):
        await asyncio.sleep(delay)
        await self.remove_task(task_id)


task_manager = TaskManager()
