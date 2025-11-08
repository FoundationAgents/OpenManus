"""Team learning and development system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LearningType(str, Enum):
    """Type of learning resource."""
    COURSE = "course"
    BOOK = "book"
    VIDEO = "video"
    TUTORIAL = "tutorial"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    CERTIFICATION = "certification"
    PROJECT = "project"
    OTHER = "other"


class SkillLevel(str, Enum):
    """Proficiency level for a skill."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningResource(BaseModel):
    """A learning resource for skill development."""
    id: str = Field(..., description="Resource ID")
    title: str = Field(..., description="Resource title")
    description: str = Field(..., description="Description")
    learning_type: LearningType = Field(..., description="Type of learning resource")
    skill: str = Field(..., description="Skill this teaches")
    target_level: SkillLevel = Field(default=SkillLevel.INTERMEDIATE, description="Target skill level")
    estimated_hours: float = Field(default=10.0, description="Estimated hours to complete")
    difficulty: int = Field(default=3, ge=1, le=5, description="Difficulty level (1-5)")
    url: Optional[str] = Field(None, description="URL to resource")
    cost: float = Field(default=0.0, description="Cost in dollars")
    provider: Optional[str] = Field(None, description="Provider/platform")
    rating: float = Field(default=0.0, ge=0, le=5, description="User rating (0-5)")
    prerequisites: List[str] = Field(default_factory=list, description="Required prerequisites")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class SkillGap(BaseModel):
    """Represents a skill gap in the team."""
    skill: str = Field(..., description="Skill name")
    current_level: SkillLevel = Field(..., description="Current proficiency level")
    target_level: SkillLevel = Field(..., description="Target proficiency level")
    members_needing: List[str] = Field(default_factory=list, description="Members who need this skill")
    priority: int = Field(default=5, ge=1, le=5, description="Priority level (5=highest)")
    impact: str = Field(default="", description="Impact on team capability")
    learning_plan: Optional[str] = Field(None, description="Recommended learning path")


class LearningPlan(BaseModel):
    """Learning plan for a team member."""
    id: str = Field(..., description="Plan ID")
    member_name: str = Field(..., description="Team member name")
    created_date: datetime = Field(default_factory=datetime.now, description="When plan was created")
    target_skills: List[str] = Field(default_factory=list, description="Skills to develop")
    resources: List[str] = Field(default_factory=list, description="Resource IDs to use")
    estimated_weeks: int = Field(default=4, description="Estimated weeks to complete")
    mentor: Optional[str] = Field(None, description="Assigned mentor if any")
    check_in_frequency: str = Field(default="weekly", description="Check-in frequency")
    goals: List[str] = Field(default_factory=list, description="Specific learning goals")
    progress_percent: float = Field(default=0.0, description="Progress percentage (0-100)")
    completed: bool = Field(default=False, description="Whether plan is completed")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class PairingSession(BaseModel):
    """Pair programming or pair learning session."""
    id: str = Field(..., description="Session ID")
    member1: str = Field(..., description="First participant")
    member2: str = Field(..., description="Second participant (human or AI)")
    skill_focus: str = Field(..., description="Skill being practiced")
    session_date: datetime = Field(default_factory=datetime.now, description="Session date/time")
    duration_minutes: int = Field(default=60, description="Session duration in minutes")
    outcome: Optional[str] = Field(None, description="Learning outcome/notes")
    completed: bool = Field(default=False, description="Whether session was completed")


class TeamLearningManager:
    """Manages team learning and development."""

    def __init__(self):
        """Initialize the learning manager."""
        self.resources: Dict[str, LearningResource] = {}
        self.skill_gaps: Dict[str, SkillGap] = {}
        self.learning_plans: Dict[str, LearningPlan] = {}
        self.pairing_sessions: Dict[str, PairingSession] = {}
        self.member_skills: Dict[str, Dict[str, SkillLevel]] = {}  # member -> skill -> level

    def add_resource(self, resource: LearningResource) -> None:
        """Add a learning resource.
        
        Args:
            resource: The resource to add
        """
        if resource.id in self.resources:
            raise ValueError(f"Resource {resource.id} already exists")
        self.resources[resource.id] = resource

    def identify_skill_gaps(self, team_required_skills: List[str], team_current_skills: Dict[str, Dict[str, SkillLevel]]) -> Dict[str, SkillGap]:
        """Identify skill gaps in the team.
        
        Args:
            team_required_skills: List of skills needed by the team
            team_current_skills: Dictionary mapping members to their skills/levels
            
        Returns:
            Dictionary mapping skill names to SkillGap objects
        """
        gaps = {}

        for skill in team_required_skills:
            members_lacking = []
            avg_level = SkillLevel.BEGINNER

            for member, skills in team_current_skills.items():
                level = skills.get(skill, SkillLevel.BEGINNER)
                if level != SkillLevel.EXPERT:
                    members_lacking.append(member)

            if members_lacking:
                gap = SkillGap(
                    skill=skill,
                    current_level=avg_level,
                    target_level=SkillLevel.ADVANCED,
                    members_needing=members_lacking,
                    impact=f"{len(members_lacking)} team members need development in {skill}"
                )
                gaps[skill] = gap

        self.skill_gaps.update(gaps)
        return gaps

    def create_learning_plan(self, member_name: str, target_skills: List[str]) -> LearningPlan:
        """Create a learning plan for a team member.
        
        Args:
            member_name: Name of team member
            target_skills: Skills to develop
            
        Returns:
            Created learning plan
        """
        plan_id = f"plan-{member_name}-{datetime.now().strftime('%Y%m%d')}"

        # Find relevant resources
        selected_resources = []
        for skill in target_skills:
            # Find resources for this skill
            skill_resources = [
                r for r in self.resources.values()
                if r.skill == skill
            ]
            # Sort by rating and difficulty
            skill_resources.sort(key=lambda r: (-r.rating, r.difficulty))
            # Add top 2 resources
            selected_resources.extend([r.id for r in skill_resources[:2]])

        # Estimate total hours
        total_hours = sum(
            self.resources[rid].estimated_hours
            for rid in selected_resources
            if rid in self.resources
        )
        estimated_weeks = max(1, int(total_hours / 5))  # Assume 5 hours/week available

        plan = LearningPlan(
            id=plan_id,
            member_name=member_name,
            target_skills=target_skills,
            resources=selected_resources,
            estimated_weeks=estimated_weeks,
            goals=[
                f"Reach {SkillLevel.INTERMEDIATE.value} level in {', '.join(target_skills)}",
                "Complete at least one project using new skills",
                "Share knowledge with team"
            ]
        )

        self.learning_plans[plan_id] = plan
        return plan

    def schedule_pairing_session(
        self,
        member1: str,
        member2: str,
        skill_focus: str,
        duration_minutes: int = 60
    ) -> PairingSession:
        """Schedule a pairing session between two members.
        
        Args:
            member1: First participant
            member2: Second participant
            skill_focus: Skill to focus on
            duration_minutes: Session duration
            
        Returns:
            Created pairing session
        """
        session_id = f"pair-{member1}-{member2}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        session = PairingSession(
            id=session_id,
            member1=member1,
            member2=member2,
            skill_focus=skill_focus,
            duration_minutes=duration_minutes
        )

        self.pairing_sessions[session_id] = session
        return session

    def suggest_learning_path(self, current_skill: SkillLevel, target_skill: SkillLevel) -> List[SkillLevel]:
        """Suggest a learning progression path.
        
        Args:
            current_skill: Current skill level
            target_skill: Target skill level
            
        Returns:
            List of intermediate levels to target
        """
        levels = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT]
        current_idx = levels.index(current_skill)
        target_idx = levels.index(target_skill)

        if target_idx <= current_idx:
            return []

        return levels[current_idx + 1:target_idx + 1]

    def recommend_resources(self, skill: str, current_level: SkillLevel, count: int = 3) -> List[LearningResource]:
        """Recommend learning resources for a skill.
        
        Args:
            skill: Skill name
            current_level: Current proficiency level
            count: Number of resources to recommend
            
        Returns:
            List of recommended resources
        """
        # Find resources for this skill at appropriate level
        matching = []
        for resource in self.resources.values():
            if resource.skill == skill:
                # Find resources slightly above current level
                level_order = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT]
                current_idx = level_order.index(current_level)
                target_idx = level_order.index(resource.target_level)

                # Prefer resources 1-2 levels above current
                if target_idx <= current_idx + 2:
                    matching.append(resource)

        # Sort by rating and difficulty
        matching.sort(key=lambda r: (-r.rating, r.difficulty, r.cost))

        return matching[:count]

    def update_member_skill(self, member: str, skill: str, new_level: SkillLevel) -> None:
        """Update a member's skill level.
        
        Args:
            member: Member name
            skill: Skill name
            new_level: New skill level
        """
        if member not in self.member_skills:
            self.member_skills[member] = {}
        self.member_skills[member][skill] = new_level

    def get_member_learning_plan(self, member_name: str) -> Optional[LearningPlan]:
        """Get active learning plan for a member.
        
        Args:
            member_name: Member name
            
        Returns:
            Active learning plan or None
        """
        for plan in self.learning_plans.values():
            if plan.member_name == member_name and not plan.completed:
                return plan
        return None

    def complete_learning_plan(self, plan_id: str) -> None:
        """Mark a learning plan as completed.
        
        Args:
            plan_id: Plan ID
        """
        if plan_id not in self.learning_plans:
            raise ValueError(f"Plan {plan_id} not found")

        plan = self.learning_plans[plan_id]
        plan.completed = True
        plan.progress_percent = 100.0

    def complete_pairing_session(self, session_id: str, outcome: str) -> None:
        """Mark a pairing session as completed.
        
        Args:
            session_id: Session ID
            outcome: Learning outcome/notes
        """
        if session_id not in self.pairing_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.pairing_sessions[session_id]
        session.completed = True
        session.outcome = outcome

    def get_active_pairing_sessions(self) -> List[PairingSession]:
        """Get all active (incomplete) pairing sessions.
        
        Returns:
            List of active sessions
        """
        return [s for s in self.pairing_sessions.values() if not s.completed]

    def get_team_learning_summary(self) -> str:
        """Generate a summary of team learning activities.
        
        Returns:
            Formatted summary string
        """
        summary = ["# Team Learning Summary", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

        # Active learning plans
        active_plans = [p for p in self.learning_plans.values() if not p.completed]
        if active_plans:
            summary.append(f"## Active Learning Plans ({len(active_plans)})")
            for plan in active_plans:
                summary.append(f"- {plan.member_name}: {', '.join(plan.target_skills)}")
            summary.append("")

        # Pairing sessions
        active_pairs = self.get_active_pairing_sessions()
        if active_pairs:
            summary.append(f"## Pairing Sessions ({len(active_pairs)})")
            for session in active_pairs[:5]:
                summary.append(f"- {session.member1} + {session.member2}: {session.skill_focus}")
            if len(active_pairs) > 5:
                summary.append(f"- ... and {len(active_pairs) - 5} more")
            summary.append("")

        # Skill gaps
        if self.skill_gaps:
            summary.append(f"## Team Skill Gaps ({len(self.skill_gaps)})")
            for skill, gap in sorted(self.skill_gaps.items(), key=lambda x: -x[1].priority)[:5]:
                summary.append(f"- {skill}: {len(gap.members_needing)} members need development")
            summary.append("")

        return "\n".join(summary)
