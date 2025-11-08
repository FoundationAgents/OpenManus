"""Meeting optimization to minimize unnecessary meetings and prefer async communication."""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MeetingPurpose(str, Enum):
    """Purpose of a meeting."""
    STATUS_UPDATE = "status_update"
    DECISION_MAKING = "decision_making"
    PROBLEM_SOLVING = "problem_solving"
    BRAINSTORMING = "brainstorming"
    ALIGNMENT = "alignment"
    RELATIONSHIP_BUILDING = "relationship_building"
    TRAINING = "training"
    RETROSPECTIVE = "retrospective"
    OTHER = "other"


class MeetingType(str, Enum):
    """Type of meeting."""
    SYNC = "sync"
    ASYNC = "async"
    HYBRID = "hybrid"


class MeetingRecommendation(str, Enum):
    """Recommendation on whether a meeting is needed."""
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"
    OPTIONAL = "optional"


class Meeting(BaseModel):
    """Represents a team meeting."""
    id: str = Field(..., description="Meeting ID")
    title: str = Field(..., description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    purpose: MeetingPurpose = Field(..., description="Purpose of meeting")
    duration_minutes: int = Field(default=30, description="Expected duration in minutes")
    attendees: List[str] = Field(default_factory=list, description="Required attendees")
    optional_attendees: List[str] = Field(default_factory=list, description="Optional attendees")
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled meeting time")
    meeting_type: MeetingType = Field(default=MeetingType.SYNC, description="Type of meeting")
    agenda: str = Field(default="", description="Meeting agenda")
    decision_maker_present: bool = Field(default=False, description="Is decision maker attending")
    time_sensitive: bool = Field(default=False, description="Is this time-sensitive")
    urgency: int = Field(default=3, ge=1, le=5, description="Urgency level (1-5)")
    async_alternative: Optional[str] = Field(None, description="Suggested async alternative")
    created_date: datetime = Field(default_factory=datetime.now, description="When meeting was scheduled")
    is_completed: bool = Field(default=False, description="Whether meeting has occurred")
    notes: Optional[str] = Field(None, description="Meeting notes/outcomes")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    def get_context_switching_cost(self, num_attendees: int) -> float:
        """Calculate context switching cost in person-hours.
        
        Args:
            num_attendees: Number of people attending
            
        Returns:
            Total person-hours of context switching
        """
        # Each person loses 15 minutes before and after
        context_loss_per_person = 0.5  # 30 minutes
        return (self.duration_minutes / 60 + context_loss_per_person) * num_attendees


class MeetingOptimizer:
    """Optimizes meeting scheduling and helps reduce unnecessary meetings."""

    def __init__(self):
        """Initialize the meeting optimizer."""
        self.meetings: dict = {}
        self.rules = self._initialize_rules()

    def _initialize_rules(self) -> dict:
        """Initialize meeting decision rules."""
        return {
            "dont_schedule_if": [
                "Can be solved with email/document",
                "No decisions needed",
                "Decision maker not present",
                "Topic time-sensitive but no real urgency",
                "Just a status update (use async standup instead)",
            ],
            "do_schedule_if": [
                "Complex discussion requiring multiple perspectives",
                "Relationship building or team bonding needed",
                "Real-time problem solving required",
                "Quick alignment needed with time-sensitive deadline",
                "Brainstorming session with creative input",
            ],
        }

    def should_schedule_meeting(self, purpose: MeetingPurpose, attributes: dict) -> MeetingRecommendation:
        """Determine if a meeting should be scheduled.
        
        Args:
            purpose: Purpose of the meeting
            attributes: Dictionary with context attributes
                - can_be_async (bool): Can this be handled async
                - decisions_needed (bool): Are decisions needed
                - decision_maker_present (bool): Is decision maker present
                - time_sensitive (bool): Is it time-sensitive
                - urgency (int): Urgency level (1-5)
                - num_attendees (int): Expected attendees
                
        Returns:
            Recommendation whether to schedule
        """
        # Extract attributes with defaults
        can_be_async = attributes.get("can_be_async", False)
        decisions_needed = attributes.get("decisions_needed", False)
        decision_maker_present = attributes.get("decision_maker_present", False)
        time_sensitive = attributes.get("time_sensitive", False)
        urgency = attributes.get("urgency", 3)
        num_attendees = attributes.get("num_attendees", 1)

        # Apply rules
        # Rule 1: Status updates should be async
        if purpose == MeetingPurpose.STATUS_UPDATE:
            return MeetingRecommendation.NOT_RECOMMENDED

        # Rule 2: If can be done async and no decisions, don't schedule
        if can_be_async and not decisions_needed:
            return MeetingRecommendation.NOT_RECOMMENDED

        # Rule 3: Decisions needed but decision maker not present
        if decisions_needed and not decision_maker_present:
            return MeetingRecommendation.NOT_RECOMMENDED

        # Rule 4: Brainstorming and complex discussions should be sync
        if purpose in [MeetingPurpose.BRAINSTORMING, MeetingPurpose.DECISION_MAKING, MeetingPurpose.PROBLEM_SOLVING]:
            return MeetingRecommendation.RECOMMENDED

        # Rule 5: Time-sensitive decisions need urgency to warrant meeting
        if time_sensitive and urgency < 4 and not decisions_needed:
            return MeetingRecommendation.OPTIONAL

        # Rule 6: Relationship building should happen but not frequently
        if purpose == MeetingPurpose.RELATIONSHIP_BUILDING:
            return MeetingRecommendation.OPTIONAL

        # Default: optional if can be async
        if can_be_async:
            return MeetingRecommendation.OPTIONAL

        return MeetingRecommendation.RECOMMENDED

    def suggest_async_alternative(self, purpose: MeetingPurpose, attendees: int) -> Optional[str]:
        """Suggest an async alternative to a meeting.
        
        Args:
            purpose: Purpose of the meeting
            attendees: Number of attendees
            
        Returns:
            Suggested async alternative
        """
        alternatives = {
            MeetingPurpose.STATUS_UPDATE: f"Daily async standup: {attendees} person-hours saved",
            MeetingPurpose.ALIGNMENT: f"Shared document with async Q&A thread: {attendees * 0.5:.1f} person-hours saved",
            MeetingPurpose.DECISION_MAKING: f"Decision document with async feedback rounds: {attendees * 0.75:.1f} person-hours saved",
            MeetingPurpose.TRAINING: f"Recorded video + async Q&A: {attendees * 0.3:.1f} person-hours saved",
            MeetingPurpose.RETROSPECTIVE: f"Retro doc with async comments: {attendees * 0.5:.1f} person-hours saved",
        }
        return alternatives.get(purpose)

    def optimize_schedule(self, meetings: List[Meeting]) -> dict:
        """Optimize a list of meetings.
        
        Returns report with:
        - Meetings that should be cancelled/made async
        - Recommended consolidations
        - Context switch reduction opportunities
        
        Args:
            meetings: List of meetings to optimize
            
        Returns:
            Optimization report
        """
        report = {
            "total_meetings": len(meetings),
            "recommended_cancellations": [],
            "recommended_async_conversions": [],
            "consolidation_opportunities": [],
            "context_switch_savings": 0.0,
            "total_person_hours_saved": 0.0,
        }

        # Check each meeting
        for meeting in meetings:
            if meeting.is_completed:
                continue

            # Get attributes for decision
            attributes = {
                "can_be_async": meeting.purpose in [
                    MeetingPurpose.STATUS_UPDATE,
                    MeetingPurpose.TRAINING,
                    MeetingPurpose.RETROSPECTIVE,
                ],
                "decisions_needed": meeting.decision_maker_present,
                "decision_maker_present": meeting.decision_maker_present,
                "time_sensitive": meeting.time_sensitive,
                "urgency": meeting.urgency,
                "num_attendees": len(meeting.attendees) + len(meeting.optional_attendees),
            }

            recommendation = self.should_schedule_meeting(meeting.purpose, attributes)

            num_attendees = len(meeting.attendees) + len(meeting.optional_attendees)
            context_cost = meeting.get_context_switching_cost(num_attendees)

            if recommendation == MeetingRecommendation.NOT_RECOMMENDED:
                report["recommended_cancellations"].append({
                    "meeting_id": meeting.id,
                    "title": meeting.title,
                    "reason": "Can be handled async",
                    "person_hours_saved": context_cost,
                })
                report["total_person_hours_saved"] += context_cost

            elif recommendation == MeetingRecommendation.OPTIONAL:
                async_alt = self.suggest_async_alternative(meeting.purpose, num_attendees)
                if async_alt:
                    report["recommended_async_conversions"].append({
                        "meeting_id": meeting.id,
                        "title": meeting.title,
                        "alternative": async_alt,
                        "person_hours_saved": context_cost * 0.7,  # Async still has some overhead
                    })

        # Look for consolidation opportunities
        # Group meetings by day and attendees
        meeting_by_day = {}
        for meeting in meetings:
            if not meeting.scheduled_time or meeting.is_completed:
                continue
            day = meeting.scheduled_time.date()
            if day not in meeting_by_day:
                meeting_by_day[day] = []
            meeting_by_day[day].append(meeting)

        # Suggest consolidations
        for day, day_meetings in meeting_by_day.items():
            if len(day_meetings) > 2:
                # Look for similar purposes
                purposes = [m.purpose for m in day_meetings]
                if len(set(purposes)) < len(purposes):
                    total_attendees = set()
                    for m in day_meetings:
                        total_attendees.update(m.attendees)
                    report["consolidation_opportunities"].append({
                        "day": str(day),
                        "num_meetings": len(day_meetings),
                        "could_consolidate_to": len(set(purposes)),
                        "unique_attendees": len(total_attendees),
                    })

        report["context_switch_savings"] = len(report["recommended_cancellations"]) + len(report["recommended_async_conversions"])

        return report

    def find_optimal_meeting_time(
        self,
        attendees: List[tuple],  # List of (name, availability_windows)
        duration_minutes: int = 30,
        min_attendees: int = None,
    ) -> Optional[datetime]:
        """Find optimal meeting time that works for most attendees.
        
        Args:
            attendees: List of (name, availability) tuples
            duration_minutes: Duration needed
            min_attendees: Minimum attendees needed (defaults to all)
            
        Returns:
            Suggested meeting time or None if no good slot found
        """
        if not attendees:
            return None

        min_attendees = min_attendees or len(attendees)

        # This is a simplified implementation
        # In a real system, you'd check against calendar data
        suggested_time = datetime.now() + timedelta(days=1, hours=9)

        # Round to next hour boundary for cleanliness
        suggested_time = suggested_time.replace(minute=0, second=0, microsecond=0)

        return suggested_time

    def suggest_meeting_frequency(self, meeting_type: str, team_size: int) -> dict:
        """Suggest optimal meeting frequency for different meeting types.
        
        Args:
            meeting_type: Type of meeting (standup, retro, planning, etc)
            team_size: Size of team
            
        Returns:
            Recommendation with frequency and format
        """
        suggestions = {
            "daily_standup": {
                "frequency": "Daily",
                "format": "Async (written standup)",
                "duration": "5 min read/write per person",
                "rationale": "Keeps team aligned without disruption",
                "sync_fallback": "Weekly sync if async not working",
            },
            "weekly_planning": {
                "frequency": "Weekly",
                "format": "Sync meeting",
                "duration": f"{30 + (team_size * 2)} minutes",
                "rationale": "Team needs face-time for planning",
            },
            "retrospective": {
                "frequency": "Weekly or Bi-weekly",
                "format": "Sync meeting",
                "duration": f"{30 + (team_size * 3)} minutes",
                "rationale": "Important for team growth and morale",
            },
            "1_on_1": {
                "frequency": "Bi-weekly or Monthly",
                "format": "Sync meeting (30 min)",
                "duration": "30 minutes",
                "rationale": "Manager-report relationship building",
            },
        }

        return suggestions.get(meeting_type, {})
