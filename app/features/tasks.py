"""Tasks Management Module

Handles task creation, management, and tracking for FreEco.AI.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """Task data class."""

    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", "medium")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            due_date=(
                datetime.fromisoformat(data["due_date"])
                if data.get("due_date")
                else None
            ),
            tags=data.get("tags", []),
        )


class TaskManager:
    """Manages task operations."""

    def __init__(self, storage_path: str = ".freeco/tasks.json"):
        """Initialize task manager.

        Args:
            storage_path: Path to store tasks JSON file.
        """
        self.storage_path = storage_path
        self.tasks: dict[str, Task] = {}
        self._ensure_storage()
        self._load_tasks()

    def _ensure_storage(self):
        """Ensure storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_tasks(self):
        """Load tasks from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.tasks = {
                        task_id: Task.from_dict(task_data)
                        for task_id, task_data in data.items()
                    }
            except Exception as e:
                print(f"Error loading tasks: {e}")
                self.tasks = {}

    def _save_tasks(self):
        """Save tasks to storage."""
        try:
            with open(self.storage_path, "w") as f:
                data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: str = "medium",
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        """Create a new task.

        Args:
            task_id: Unique task identifier.
            title: Task title.
            description: Task description.
            priority: Task priority (low, medium, high, critical).
            due_date: Optional due date.
            tags: Optional list of tags.

        Returns:
            Created Task object.
        """
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=TaskPriority(priority),
            due_date=due_date,
            tags=tags or [],
        )
        self.tasks[task_id] = task
        self._save_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Task object or None if not found.
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status.
            priority: Filter by priority.
            tag: Filter by tag.

        Returns:
            List of filtered tasks.
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status.value == status]
        if priority:
            tasks = [t for t in tasks if t.priority.value == priority]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Task]:
        """Update a task.

        Args:
            task_id: Task identifier.
            title: New title (optional).
            description: New description (optional).
            status: New status (optional).
            priority: New priority (optional).
            due_date: New due date (optional).
            tags: New tags (optional).

        Returns:
            Updated Task object or None if not found.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        if title:
            task.title = title
        if description:
            task.description = description
        if status:
            task.status = TaskStatus(status)
        if priority:
            task.priority = TaskPriority(priority)
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags

        task.updated_at = datetime.now()
        self._save_tasks()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task identifier.

        Returns:
            True if deleted, False if not found.
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False

    def get_statistics(self) -> dict:
        """Get task statistics.

        Returns:
            Dictionary with task statistics.
        """
        tasks = list(self.tasks.values())
        return {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "in_progress": len(
                [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
            ),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "cancelled": len([t for t in tasks if t.status == TaskStatus.CANCELLED]),
            "high_priority": len([t for t in tasks if t.priority == TaskPriority.HIGH]),
            "critical": len([t for t in tasks if t.priority == TaskPriority.CRITICAL]),
        }
