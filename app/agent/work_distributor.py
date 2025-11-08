"""Intelligent task distribution and assignment system."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.agent.team_model import MemberRole, Team, TeamMember, MemberType


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status of a task."""
    BACKLOG = "backlog"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Represents a task to be assigned to team members."""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    estimated_hours: float = Field(default=8.0, description="Estimated hours to complete")
    required_skills: List[str] = Field(default_factory=list, description="Required skills")
    preferred_roles: List[MemberRole] = Field(default_factory=list, description="Preferred roles")
    status: TaskStatus = Field(default=TaskStatus.BACKLOG, description="Current task status")
    assigned_to: Optional[str] = Field(None, description="Name of assigned member")
    supporters: List[str] = Field(default_factory=list, description="Supporting members")
    created_date: datetime = Field(default_factory=datetime.now, description="When task was created")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    start_date: Optional[datetime] = Field(None, description="When task was started")
    completed_date: Optional[datetime] = Field(None, description="When task was completed")
    blocker: Optional[str] = Field(None, description="Current blocker if any")
    progress_percent: float = Field(default=0.0, description="Progress percentage (0-100)")
    async_preferred: bool = Field(default=True, description="Can be done async")
    meeting_required: bool = Field(default=False, description="Meeting required")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date

    def expected_progress_by_now(self) -> float:
        """Calculate expected progress based on dates."""
        if not self.start_date or not self.due_date:
            return 0.0
        total_duration = (self.due_date - self.start_date).total_seconds()
        elapsed_duration = (datetime.now() - self.start_date).total_seconds()
        if total_duration <= 0:
            return 0.0
        expected = (elapsed_duration / total_duration) * 100
        return min(100.0, expected)

    def is_behind_schedule(self) -> bool:
        """Check if task is behind schedule."""
        expected = self.expected_progress_by_now()
        return self.progress_percent < (expected - 10)  # Allow 10% margin


class AssignmentAnalysis(BaseModel):
    """Analysis of potential task assignments."""
    task_id: str = Field(..., description="Task ID")
    candidates: List[Tuple[str, float]] = Field(default_factory=list, description="Candidate members and match scores (0-1)")
    recommended_primary: Optional[str] = Field(None, description="Recommended primary assignee")
    recommended_supporters: List[str] = Field(default_factory=list, description="Recommended supporters")
    rationale: str = Field(default="", description="Explanation of the assignment")


class WorkDistributor:
    """Intelligently distributes work across the team."""

    def __init__(self, team: Team):
        """Initialize the work distributor.
        
        Args:
            team: The team to distribute work for
        """
        self.team = team
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to the system."""
        if task.id in self.tasks:
            raise ValueError(f"Task '{task.id}' already exists")
        self.tasks[task.id] = task

    def analyze_assignment(self, task_id: str) -> AssignmentAnalysis:
        """Analyze potential assignments for a task.
        
        Returns:
            AssignmentAnalysis with recommended assignments and scores
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        task = self.tasks[task_id]
        analysis = AssignmentAnalysis(task_id=task_id)

        # Score all available members
        scores: Dict[str, float] = {}
        for member in self.team.get_available_members():
            score = self._calculate_member_score(task, member)
            if score > 0:
                scores[member.name] = score

        if not scores:
            analysis.rationale = "No suitable members available for this task"
            return analysis

        # Sort by score (descending)
        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        analysis.candidates = sorted_candidates

        # Assign primary
        if sorted_candidates:
            primary = sorted_candidates[0][0]
            analysis.recommended_primary = primary
            analysis.rationale = f"Primary: {primary} (score: {sorted_candidates[0][1]:.2f})"

            # Assign supporters from remaining qualified candidates
            supporters = []
            for member_name, score in sorted_candidates[1:]:
                if len(supporters) < 2 and score > 0.3:  # Support threshold
                    supporters.append(member_name)
            analysis.recommended_supporters = supporters

            if supporters:
                analysis.rationale += f", Supporters: {', '.join(supporters)}"

        return analysis

    def _calculate_member_score(self, task: Task, member: TeamMember) -> float:
        """Calculate how well a member matches a task.
        
        Scoring factors:
        - Skill match (0-40%)
        - Role match (0-30%)
        - Availability (0-20%)
        - Current workload (0-10%)
        
        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Skill match (0-0.4)
        if task.required_skills:
            skill_matches = sum(1 for skill in task.required_skills if skill in member.skills)
            skill_score = skill_matches / len(task.required_skills)
            score += skill_score * 0.4
        else:
            score += 0.4  # Full points if no specific skills required

        # Role match (0-0.3)
        if task.preferred_roles:
            if member.role in task.preferred_roles:
                score += 0.3
            else:
                score += 0.15  # Partial credit for close roles
        else:
            score += 0.3  # Full points if no specific role required

        # Availability (0-0.2)
        available_hours = member.available_hours_this_week
        if available_hours >= task.estimated_hours:
            score += 0.2
        elif available_hours > 0:
            score += (available_hours / task.estimated_hours) * 0.2
        # else: 0 points if no availability

        # Current workload (0-0.1) - prefer less loaded members
        workload_factor = (100 - member.workload_percent) / 100
        score += workload_factor * 0.1

        return min(1.0, score)  # Cap at 1.0

    def assign_task(self, task_id: str, primary: str, supporters: Optional[List[str]] = None) -> None:
        """Assign a task to specific members.
        
        Args:
            task_id: ID of the task to assign
            primary: Name of primary assignee
            supporters: Optional list of supporting members
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        task = self.tasks[task_id]

        # Validate members exist
        primary_member = self.team.get_member(primary)
        if not primary_member:
            raise ValueError(f"Member '{primary}' not found in team")

        if supporters:
            for supporter in supporters:
                if not self.team.get_member(supporter):
                    raise ValueError(f"Member '{supporter}' not found in team")

        # Check capacity
        if primary_member.available_hours_this_week < task.estimated_hours:
            raise ValueError(
                f"Member '{primary}' has insufficient capacity "
                f"({primary_member.available_hours_this_week:.1f}h available, "
                f"{task.estimated_hours}h required)"
            )

        # Assign task
        task.assigned_to = primary
        task.supporters = supporters or []
        task.status = TaskStatus.ASSIGNED
        task.start_date = datetime.now()

        # Update member workload
        hours_factor = task.estimated_hours / primary_member.capacity_hours_per_week
        new_workload = min(100.0, primary_member.workload_percent + (hours_factor * 100))
        self.team.update_workload(primary, new_workload)

    def get_available_tasks(self) -> List[Task]:
        """Get all tasks that are ready to be assigned."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.BACKLOG]

    def get_assigned_tasks(self) -> List[Task]:
        """Get all currently assigned tasks."""
        return [t for t in self.tasks.values() if t.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]]

    def get_tasks_for_member(self, member_name: str) -> List[Task]:
        """Get all tasks assigned to a member."""
        return [
            t for t in self.tasks.values()
            if t.assigned_to == member_name or member_name in t.supporters
        ]

    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks."""
        return [t for t in self.tasks.values() if t.is_overdue() and t.status != TaskStatus.COMPLETED]

    def get_blocked_tasks(self) -> List[Task]:
        """Get all blocked tasks."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]

    def get_behind_schedule_tasks(self) -> List[Task]:
        """Get all tasks that are behind schedule."""
        return [t for t in self.tasks.values() if t.is_behind_schedule() and t.status == TaskStatus.IN_PROGRESS]

    def suggest_load_balancing(self) -> Dict[str, str]:
        """Suggest workload rebalancing for overloaded members.
        
        Returns:
            Dictionary mapping member names to suggested actions
        """
        suggestions = {}
        overloaded = self.team.get_overloaded_members()

        for member in overloaded:
            # Get tasks assigned to this member
            member_tasks = self.get_tasks_for_member(member.name)
            assigned_tasks = [t for t in member_tasks if t.assigned_to == member.name]

            if assigned_tasks:
                # Suggest reassigning lower priority tasks
                sorted_tasks = sorted(assigned_tasks, key=lambda t: (t.priority.value, -t.progress_percent))
                reassignable = next(
                    (t for t in sorted_tasks if t.priority in [TaskPriority.LOW, TaskPriority.MEDIUM]),
                    None
                )

                if reassignable:
                    suggestions[member.name] = f"Consider reassigning '{reassignable.title}' (ID: {reassignable.id})"
                else:
                    suggestions[member.name] = "No lower priority tasks to reassign; consider extending deadlines"

        return suggestions
