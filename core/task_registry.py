from __future__ import annotations

import asyncio
import os
import threading
import uuid
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.task import Task, TaskStatus
from server.models import Base, TaskORM


class TaskRegistry:
    """Database-backed registry for Task objects using SQLAlchemy."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self.db_url = db_url or os.getenv(
            "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/openmanus"
        )
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def _to_task(self, orm: TaskORM) -> Task:
        status = TaskStatus(orm.status) if orm.status in TaskStatus._value2member_map_ else TaskStatus.CREATED
        # Use fresh queue per retrieval; events are in-memory only
        return Task(
            id=str(orm.task_id),
            status=status,
            event_queue=asyncio.Queue(),
            interrupt_flag=False,
        )

    def create_task(
        self, task_id: Optional[str] = None, input: Optional[dict] = None, **task_kwargs
    ) -> Task:
        with self._lock:
            tid = task_id or str(uuid.uuid4())
            session = self.SessionLocal()
            try:
                orm = TaskORM(task_id=tid, status=TaskStatus.CREATED.value, input=input)
                session.add(orm)
                session.commit()
                task = Task(id=tid, status=TaskStatus.CREATED, **task_kwargs)
                return task
            finally:
                session.close()

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            session = self.SessionLocal()
            try:
                orm = session.get(TaskORM, task_id)
                if orm is None:
                    return None
                return self._to_task(orm)
            finally:
                session.close()

    def update_task(self, task: Task, result: Optional[dict] = None) -> Task:
        with self._lock:
            session = self.SessionLocal()
            try:
                orm = session.get(TaskORM, task.id)
                if orm is None:
                    orm = TaskORM(task_id=task.id)
                    session.add(orm)
                orm.status = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
                if hasattr(task, "input"):
                    orm.input = getattr(task, "input")
                orm.result = result if result is not None else orm.result
                session.commit()
                return task
            finally:
                session.close()

    def interrupt_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            session = self.SessionLocal()
            try:
                orm = session.get(TaskORM, task_id)
                if orm is None:
                    return None
                orm.status = TaskStatus.INTERRUPTED.value
                session.commit()
                task = self._to_task(orm)
                task.interrupt()
                return task
            finally:
                session.close()


__all__ = ["TaskRegistry"]
