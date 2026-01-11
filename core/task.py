from __future__ import annotations

import asyncio
import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


EventQueue = Union[asyncio.Queue, queue.Queue]


@dataclass
class Task:
    """Generic task container for agents/tools."""

    id: str
    status: TaskStatus = TaskStatus.CREATED
    interrupt_flag: bool = False
    event_queue: EventQueue = field(default_factory=asyncio.Queue)
    _loop: Optional[asyncio.AbstractEventLoop] = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        # Capture the running loop if we are created inside one; helps thread-safe emits.
        if isinstance(self.event_queue, asyncio.Queue) and self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

    def emit(self, type: str, data: Any) -> None:
        """Push an event into the queue."""
        event = {"type": type, "data": data}

        if isinstance(self.event_queue, asyncio.Queue):
            loop = self._loop
            if loop is None or not loop.is_running():
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

            if loop and loop.is_running():
                # Schedule thread-safe put when an event loop is available.
                loop.call_soon_threadsafe(self.event_queue.put_nowait, event)
            else:
                # Fallback for cases without a running loop.
                self.event_queue.put_nowait(event)
        elif isinstance(self.event_queue, queue.Queue):
            self.event_queue.put_nowait(event)
        else:
            raise TypeError("event_queue must be an asyncio.Queue or queue.Queue instance")

    def interrupt(self) -> None:
        """Mark task as interrupted."""
        self.interrupt_flag = True
        if self.status not in (TaskStatus.DONE, TaskStatus.FAILED):
            self.status = TaskStatus.INTERRUPTED

    def is_interrupted(self) -> bool:
        """Return whether the task has been interrupted."""
        return self.interrupt_flag


__all__ = ["Task", "TaskStatus", "EventQueue"]
