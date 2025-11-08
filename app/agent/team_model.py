"""Team model for managing human and AI team members."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MemberType(str, Enum):
    """Type of team member."""
    HUMAN = "human"
    AI_AGENT = "ai_agent"


class MemberRole(str, Enum):
    """Role/specialization of team member."""
    BACKEND_ENGINEER = "backend_engineer"
    FRONTEND_ENGINEER = "frontend_engineer"
    FULL_STACK = "full_stack"
    DEVOPS = "devops"
    QA_ENGINEER = "qa_engineer"
    DATA_SCIENTIST = "data_scientist"
    PROJECT_MANAGER = "project_manager"
    PRODUCT_MANAGER = "product_manager"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    OTHER = "other"


class WorkPreferences(BaseModel):
    """Preferences for how a team member likes to work."""
    async_preferred: bool = Field(default=True, description="Prefers async communication")
    pair_programming: bool = Field(default=False, description="Interested in pair programming")
    mentoring: bool = Field(default=False, description="Willing to mentor others")
    max_meetings_per_day: int = Field(default=3, description="Maximum meetings per day")
    focus_hours: Optional[Dict[str, str]] = Field(default=None, description="Time slots for deep work (e.g., {'start': '9:00', 'end': '12:00'})")
    timezone: Optional[str] = Field(default=None, description="Timezone for scheduling")
    notes: Optional[str] = Field(default=None, description="Additional notes about preferences")


class TeamMember(BaseModel):
    """Represents a team member (human or AI agent)."""
    name: str = Field(..., description="Member's name")
    member_type: MemberType = Field(..., description="Type of member (human or AI agent)")
    role: MemberRole = Field(..., description="Primary role/specialization")
    skills: List[str] = Field(default_factory=list, description="List of skills/technologies")
    availability: str = Field(default="24/7", description="Availability window (e.g., 'M-F 9-17')")
    workload_percent: float = Field(default=0.0, description="Current utilization percentage (0-100)")
    capacity_hours_per_week: float = Field(default=40.0, description="Weekly capacity in hours")
    preferences: WorkPreferences = Field(default_factory=WorkPreferences, description="Work preferences")
    joined_date: datetime = Field(default_factory=datetime.now, description="When member joined team")
    is_active: bool = Field(default=True, description="Whether member is currently active")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    @property
    def available_hours_this_week(self) -> float:
        """Calculate available hours this week based on capacity and workload."""
        used_hours = (self.workload_percent / 100.0) * self.capacity_hours_per_week
        return self.capacity_hours_per_week - used_hours

    @property
    def is_overloaded(self) -> bool:
        """Check if member is overloaded (>80% utilization)."""
        return self.workload_percent > 80.0


class Team(BaseModel):
    """Represents a complete team with human and AI members."""
    name: str = Field(..., description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    members: List[TeamMember] = Field(default_factory=list, description="List of team members")
    created_date: datetime = Field(default_factory=datetime.now, description="When team was created")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    def add_member(self, member: TeamMember) -> None:
        """Add a member to the team."""
        # Check for duplicates
        if any(m.name == member.name for m in self.members):
            raise ValueError(f"Member '{member.name}' already exists in team")
        self.members.append(member)

    def remove_member(self, name: str) -> None:
        """Remove a member from the team by name."""
        self.members = [m for m in self.members if m.name != name]

    def get_member(self, name: str) -> Optional[TeamMember]:
        """Get a member by name."""
        for member in self.members:
            if member.name == name:
                return member
        return None

    def get_members_by_role(self, role: MemberRole) -> List[TeamMember]:
        """Get all members with a specific role."""
        return [m for m in self.members if m.role == role]

    def get_members_by_skill(self, skill: str) -> List[TeamMember]:
        """Get all members with a specific skill."""
        return [m for m in self.members if skill in m.skills]

    def get_available_members(self) -> List[TeamMember]:
        """Get all active members with available capacity."""
        return [m for m in self.members if m.is_active and m.available_hours_this_week > 0]

    def get_overloaded_members(self) -> List[TeamMember]:
        """Get all members who are overloaded."""
        return [m for m in self.members if m.is_overloaded]

    def get_humans(self) -> List[TeamMember]:
        """Get all human team members."""
        return [m for m in self.members if m.member_type == MemberType.HUMAN]

    def get_ai_agents(self) -> List[TeamMember]:
        """Get all AI agent team members."""
        return [m for m in self.members if m.member_type == MemberType.AI_AGENT]

    def update_workload(self, name: str, workload_percent: float) -> None:
        """Update a member's workload percentage."""
        member = self.get_member(name)
        if not member:
            raise ValueError(f"Member '{name}' not found")
        if not 0 <= workload_percent <= 100:
            raise ValueError("Workload percentage must be between 0 and 100")
        member.workload_percent = workload_percent

    @property
    def total_capacity_hours(self) -> float:
        """Get total team capacity in hours per week."""
        return sum(m.capacity_hours_per_week for m in self.members if m.is_active)

    @property
    def total_available_hours(self) -> float:
        """Get total available hours across the team."""
        return sum(m.available_hours_this_week for m in self.members if m.is_active)

    @property
    def average_workload(self) -> float:
        """Get average workload across the team."""
        active_members = [m for m in self.members if m.is_active]
        if not active_members:
            return 0.0
        return sum(m.workload_percent for m in active_members) / len(active_members)
