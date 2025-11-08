"""Progress tracking and early warning system for tasks and team."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent.work_distributor import Task, TaskStatus


class RiskLevel(str, Enum):
    """Risk level assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BlockerSeverity(str, Enum):
    """Severity of a blocker."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProgressUpdate(BaseModel):
    """Daily progress update for a task."""
    task_id: str = Field(..., description="Task ID")
    date: datetime = Field(default_factory=datetime.now, description="Update date")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    work_completed: str = Field(default="", description="What was completed")
    work_planned: str = Field(default="", description="What's planned next")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    notes: str = Field(default="", description="Additional notes")
    estimated_hours_used: float = Field(default=0.0, description="Hours worked on this update")


class Standup(BaseModel):
    """Async daily standup from a team member."""
    member_name: str = Field(..., description="Member providing standup")
    date: datetime = Field(default_factory=datetime.now, description="Standup date")
    yesterday_completed: str = Field(default="", description="What was completed yesterday")
    today_planned: str = Field(default="", description="What's planned today")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    notes: Optional[str] = Field(None, description="Additional notes")
    mood: Optional[str] = Field(None, description="Team member mood/energy level")


class RiskAssessment(BaseModel):
    """Risk assessment for a task or milestone."""
    task_id: str = Field(..., description="Task ID")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    reasons: List[str] = Field(default_factory=list, description="Reasons for risk level")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended mitigations")
    confidence: float = Field(default=0.8, description="Confidence in assessment (0-1)")


class ProgressTracker:
    """Tracks team and task progress with early warning system."""

    def __init__(self):
        """Initialize the progress tracker."""
        self.progress_updates: Dict[str, List[ProgressUpdate]] = {}
        self.standups: Dict[str, List[Standup]] = {}
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to track."""
        self.tasks[task.id] = task
        if task.id not in self.progress_updates:
            self.progress_updates[task.id] = []

    def record_progress(self, update: ProgressUpdate) -> None:
        """Record a progress update for a task.
        
        Args:
            update: The progress update to record
        """
        if update.task_id not in self.tasks:
            raise ValueError(f"Task '{update.task_id}' not found")

        # Update task progress
        task = self.tasks[update.task_id]
        task.progress_percent = update.progress_percent
        if update.blockers:
            task.blocker = update.blockers[0]
        else:
            task.blocker = None

        # Store update
        if update.task_id not in self.progress_updates:
            self.progress_updates[update.task_id] = []
        self.progress_updates[update.task_id].append(update)

    def record_standup(self, standup: Standup) -> None:
        """Record a daily standup from a team member.
        
        Args:
            standup: The standup to record
        """
        if standup.member_name not in self.standups:
            self.standups[standup.member_name] = []
        self.standups[standup.member_name].append(standup)

    def get_latest_standup(self, member_name: str) -> Optional[Standup]:
        """Get the latest standup from a member."""
        if member_name not in self.standups or not self.standups[member_name]:
            return None
        return self.standups[member_name][-1]

    def get_recent_standups(self, member_name: str, days: int = 7) -> List[Standup]:
        """Get recent standups from a member.
        
        Args:
            member_name: Member name
            days: Number of days to look back
            
        Returns:
            List of standups from the past N days
        """
        if member_name not in self.standups:
            return []

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        return [
            s for s in self.standups[member_name]
            if s.date.timestamp() > cutoff
        ]

    def assess_task_risk(self, task_id: str) -> RiskAssessment:
        """Assess the risk level for a task.
        
        Factors:
        - Task is behind schedule
        - Task is overdue
        - Has blockers
        - Assignee is overloaded
        - Estimated hours exceeded
        
        Returns:
            RiskAssessment with risk level and recommendations
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        task = self.tasks[task_id]
        assessment = RiskAssessment(task_id=task_id, risk_level=RiskLevel.LOW, reasons=[], recommended_actions=[])

        reasons = []
        risk_score = 0

        # Check if overdue
        if task.is_overdue():
            reasons.append(f"Task overdue since {task.due_date}")
            risk_score += 40

        # Check if behind schedule
        if task.is_behind_schedule():
            expected = task.expected_progress_by_now()
            reasons.append(f"Behind schedule: {task.progress_percent:.0f}% done, expected {expected:.0f}%")
            risk_score += 30

        # Check for blockers
        if task.blocker:
            reasons.append(f"Blocker: {task.blocker}")
            risk_score += 20

        # Get latest progress update to estimate velocity
        if task.id in self.progress_updates and self.progress_updates[task.id]:
            updates = self.progress_updates[task.id]
            if len(updates) >= 2:
                # Check if progress is stalling
                recent_updates = updates[-3:]
                progress_values = [u.progress_percent for u in recent_updates]
                if progress_values[-1] == progress_values[-2]:
                    reasons.append("Progress appears to be stalling")
                    risk_score += 10

        # Determine risk level
        if risk_score >= 70:
            assessment.risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            assessment.risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            assessment.risk_level = RiskLevel.MEDIUM
        else:
            assessment.risk_level = RiskLevel.LOW

        assessment.reasons = reasons
        assessment.confidence = min(0.95, 0.6 + (len(reasons) * 0.1))

        # Recommend actions
        if task.blocker:
            assessment.recommended_actions.append(f"Resolve blocker: {task.blocker}")

        if risk_score >= 50:
            if task.supporters:
                assessment.recommended_actions.append(f"Allocate additional support from {task.supporters[0]}")
            else:
                assessment.recommended_actions.append("Allocate AI agent for debugging/support")

        if task.is_overdue():
            assessment.recommended_actions.append("Review scope with stakeholders; consider descoping")

        if task.is_behind_schedule():
            assessment.recommended_actions.append("Increase team focus on this task; reduce distractions")

        return assessment

    def get_all_risk_assessments(self) -> Dict[str, RiskAssessment]:
        """Get risk assessments for all tasks.
        
        Returns:
            Dictionary mapping task IDs to risk assessments
        """
        assessments = {}
        for task_id in self.tasks.keys():
            assessments[task_id] = self.assess_task_risk(task_id)
        return assessments

    def get_high_risk_tasks(self) -> List[str]:
        """Get all high-risk or critical tasks.
        
        Returns:
            List of task IDs that are high risk or critical
        """
        return [
            task_id for task_id, assessment in self.get_all_risk_assessments().items()
            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

    def get_velocity(self, task_id: str, days: int = 7) -> float:
        """Calculate task progress velocity (percent per day).
        
        Args:
            task_id: Task ID
            days: Number of days to look back
            
        Returns:
            Average progress percentage gained per day
        """
        if task_id not in self.progress_updates:
            return 0.0

        updates = self.progress_updates[task_id]
        if len(updates) < 2:
            return 0.0

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        recent_updates = [u for u in updates if u.date.timestamp() > cutoff]

        if len(recent_updates) < 2:
            return 0.0

        # Calculate progress over time period
        progress_delta = recent_updates[-1].progress_percent - recent_updates[0].progress_percent
        time_delta_hours = (recent_updates[-1].date - recent_updates[0].date).total_seconds() / 3600

        if time_delta_hours == 0:
            return 0.0

        velocity_per_day = (progress_delta / time_delta_hours) * 24
        return velocity_per_day

    def estimate_completion_date(self, task_id: str) -> Optional[datetime]:
        """Estimate when a task will be completed based on current velocity.
        
        Args:
            task_id: Task ID
            
        Returns:
            Estimated completion date, or None if cannot be estimated
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        velocity = self.get_velocity(task_id)

        if velocity <= 0:
            return None

        # Calculate hours remaining
        hours_remaining = task.estimated_hours * (100 - task.progress_percent) / 100
        days_remaining = hours_remaining / (velocity * task.estimated_hours / 100 / 24)

        return datetime.now() + (datetime.timedelta(days=days_remaining) if hasattr(datetime, 'timedelta') else None)

    def generate_daily_summary(self) -> str:
        """Generate a daily summary of team progress and issues.
        
        Returns:
            Formatted summary string
        """
        summary = ["# Daily Team Progress Summary", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

        # High-risk tasks
        high_risk = self.get_high_risk_tasks()
        if high_risk:
            summary.append("## ⚠️ High Risk Tasks")
            for task_id in high_risk:
                assessment = self.assess_task_risk(task_id)
                task = self.tasks[task_id]
                summary.append(f"- **{task.title}** ({task_id})")
                summary.append(f"  - Risk: {assessment.risk_level.value.upper()}")
                if assessment.reasons:
                    summary.append(f"  - Reason: {assessment.reasons[0]}")
                if assessment.recommended_actions:
                    summary.append(f"  - Action: {assessment.recommended_actions[0]}")
            summary.append("")

        # Tasks behind schedule
        behind = [t for t in self.tasks.values() if t.is_behind_schedule()]
        if behind:
            summary.append("## 📉 Behind Schedule")
            for task in behind:
                expected = task.expected_progress_by_now()
                summary.append(f"- **{task.title}**: {task.progress_percent:.0f}% done (expected {expected:.0f}%)")
            summary.append("")

        # Blockers
        blocked = [t for t in self.tasks.values() if t.blocker]
        if blocked:
            summary.append("## 🚫 Current Blockers")
            for task in blocked:
                summary.append(f"- **{task.title}**: {task.blocker}")
            summary.append("")

        # Recent standups summary
        if self.standups:
            summary.append("## 👥 Team Standups")
            summary.append(f"Received from {len(self.standups)} members")
            summary.append("")

        return "\n".join(summary)
