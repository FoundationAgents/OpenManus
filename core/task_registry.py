from __future__ import annotations

import threading
import uuid
from typing import Dict, Optional

from core.task import Task


class TaskRegistry:
    """In-memory registry for Task objects.

    Designed to be framework-agnostic so it can back future HTTP or WebSocket
    layers without introducing those dependencies here.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()

    def create_task(self, task_id: Optional[str] = None, **task_kwargs) -> Task:
        """Create and register a new task.

        task_id: Optional explicit id; if omitted, a UUID4 string is used.
        task_kwargs: Forwarded to Task constructor (e.g., custom event_queue).
        """
        with self._lock:
            tid = task_id or str(uuid.uuid4())
            if tid in self._tasks:
                raise ValueError(f"Task with id '{tid}' already exists")

            task = Task(id=tid, **task_kwargs)
            self._tasks[tid] = task
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by id."""
        with self._lock:
            return self._tasks.get(task_id)

    def interrupt_task(self, task_id: str) -> Optional[Task]:
        """Interrupt a task if it exists; returns the task or None."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.interrupt()
            return task


__all__ = ["TaskRegistry"]
