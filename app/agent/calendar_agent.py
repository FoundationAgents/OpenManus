"""Calendar and meeting management agent."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pydantic import Field

from app.agent.models.communication import CalendarEvent
from app.agent.toolcall import ToolCallAgent
from app.agent.voice_model import VoiceModel
from app.config import config
from app.logger import logger
from app.prompt.communication import SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection


class CalendarAgent(ToolCallAgent):
    """Agent for managing calendar events and meetings."""

    name: str = "CalendarAgent"
    description: str = (
        "An intelligent calendar management agent that proposes optimal meeting times, "
        "declines unnecessary meetings, and manages scheduling preferences"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "Process the next calendar event or meeting invitation."

    max_steps: int = 20
    max_observe: int = 10000

    # Core components
    voice_model: VoiceModel = Field(
        default_factory=VoiceModel, description="User's communication voice"
    )

    # Calendar events
    events: Dict[str, CalendarEvent] = Field(
        default_factory=dict, description="Calendar events"
    )
    pending_invitations: Dict[str, CalendarEvent] = Field(
        default_factory=dict, description="Pending meeting invitations"
    )

    # User preferences
    calendar_preferences: Dict = Field(
        default_factory=lambda: {
            "working_hours_start": 9,
            "working_hours_end": 17,
            "no_meetings_before": 10,
            "max_hours_per_day": 2.0,
            "min_meeting_duration": 15,
            "prefer_async": True,
            "meeting_buffer_minutes": 15,
            "decline_if_less_notice_hours": 24,
            "timezone": "UTC",
        },
        description="Calendar and meeting preferences",
    )

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    class Config:
        arbitrary_types_allowed = True

    async def step(self) -> str:
        """Execute a single step in calendar management."""
        try:
            # Check for pending invitations first
            if self.pending_invitations:
                return await self._process_invitation()

            # Check for upcoming events that need prep
            if self.events:
                return await self._prepare_upcoming_event()

            return "Calendar processed"

        except Exception as e:
            logger.error(f"Error in calendar agent step: {e}")
            return f"Error: {str(e)}"

    async def _process_invitation(self) -> str:
        """Process a pending meeting invitation."""
        # Get first pending invitation
        invitation = next(iter(self.pending_invitations.values()))

        # Analyze invitation
        decision = self._analyze_invitation(invitation)

        # Take action based on decision
        if decision["action"] == "accept":
            self._accept_meeting(invitation)
            summary = f"Accepted meeting: {invitation.title}"
            await self._prepare_meeting(invitation)
        elif decision["action"] == "decline":
            reason = decision.get("reason", "Schedule conflict")
            self._decline_meeting(invitation, reason)
            summary = f"Declined meeting: {invitation.title} ({reason})"
        else:  # propose_alternative
            alternatives = decision.get("alternatives", [])
            self._propose_alternatives(invitation, alternatives)
            summary = f"Proposed alternatives for {invitation.title}"

        self.pending_invitations.pop(invitation.id)
        self.update_memory("assistant", summary)
        return summary

    def _analyze_invitation(self, invitation: CalendarEvent) -> Dict:
        """Analyze meeting invitation against preferences."""
        now = datetime.now()
        time_until_meeting = invitation.start_time - now
        hours_until = time_until_meeting.total_seconds() / 3600
        meeting_duration = (invitation.end_time - invitation.start_time).total_seconds() / 3600

        # Check notice period
        min_notice = self.calendar_preferences.get("decline_if_less_notice_hours", 24)
        if hours_until < min_notice and "urgent" not in invitation.title.lower():
            return {
                "action": "decline",
                "reason": f"Insufficient notice ({hours_until:.1f} hours)",
            }

        # Check working hours
        start_hour = invitation.start_time.hour
        end_hour = invitation.end_time.hour
        working_start = self.calendar_preferences.get("working_hours_start", 9)
        working_end = self.calendar_preferences.get("working_hours_end", 17)

        if start_hour < working_start and not "urgent" in invitation.title.lower():
            return {
                "action": "decline",
                "reason": f"Outside working hours (starts at {start_hour}:00)",
            }

        # Check no meetings before preference
        no_meetings_before = self.calendar_preferences.get("no_meetings_before", 10)
        if start_hour < no_meetings_before and not "critical" in invitation.title.lower():
            return {
                "action": "propose_alternative",
                "reason": "Too early - proposing later time",
                "alternatives": [
                    invitation.start_time.replace(hour=no_meetings_before),
                ],
            }

        # Check daily meeting limit
        meetings_today = [
            e
            for e in self.events.values()
            if e.start_time.date() == invitation.start_time.date()
        ]
        total_meeting_hours = sum(
            (e.end_time - e.start_time).total_seconds() / 3600 for e in meetings_today
        )
        max_daily = self.calendar_preferences.get("max_hours_per_day", 2.0)

        if total_meeting_hours + meeting_duration > max_daily:
            return {
                "action": "propose_alternative",
                "reason": "Would exceed daily meeting limit",
                "alternatives": self._find_available_slots(meeting_duration),
            }

        # Check for conflicts
        conflicts = self._find_conflicts(invitation)
        if conflicts:
            return {
                "action": "propose_alternative",
                "reason": "Schedule conflict",
                "alternatives": self._find_available_slots(meeting_duration),
            }

        # Meeting is acceptable
        return {"action": "accept", "reason": "Fits schedule"}

    async def _prepare_meeting(self, meeting: CalendarEvent) -> None:
        """Prepare for an upcoming meeting."""
        # Calculate preparation items
        time_until = meeting.start_time - datetime.now()
        hours_until = time_until.total_seconds() / 3600

        prep_items = []

        # If meeting is soon, start preparing
        if hours_until <= 24:
            prep_items.append(f"Prepare materials for {meeting.title}")
            prep_items.append("Review attendee list and recent discussions")

            if meeting.description:
                prep_items.append(f"Review agenda: {meeting.description[:100]}")

        logger.info(f"✓ Meeting preparation items: {prep_items}")

    async def _prepare_upcoming_event(self) -> str:
        """Prepare for an upcoming event."""
        now = datetime.now()
        upcoming = [e for e in self.events.values() if e.start_time > now]

        if not upcoming:
            return "No upcoming events"

        # Get next event
        next_event = min(upcoming, key=lambda e: e.start_time)
        time_until = next_event.start_time - now

        # If event is within an hour, prepare
        if time_until.total_seconds() < 3600:
            await self._prepare_meeting(next_event)
            return f"Preparing for: {next_event.title} (in {time_until.total_seconds() / 60:.0f} minutes)"

        return f"Next event: {next_event.title} at {next_event.start_time.strftime('%H:%M')}"

    def _find_conflicts(self, event: CalendarEvent) -> List[CalendarEvent]:
        """Find schedule conflicts for event."""
        conflicts = []
        for other in self.events.values():
            # Check for overlap
            if not (event.end_time <= other.start_time or event.start_time >= other.end_time):
                conflicts.append(other)

        return conflicts

    def _find_available_slots(self, duration_hours: float) -> List[datetime]:
        """Find available time slots for meeting."""
        available_slots = []
        working_start = self.calendar_preferences.get("working_hours_start", 9)
        working_end = self.calendar_preferences.get("working_hours_end", 17)

        # Check next 5 business days
        for days_ahead in range(1, 6):
            check_date = datetime.now() + timedelta(days=days_ahead)

            # Skip weekends
            if check_date.weekday() > 4:  # 5, 6 = Saturday, Sunday
                continue

            # Check hourly slots during working hours
            for hour in range(working_start, working_end - int(duration_hours)):
                slot_start = check_date.replace(hour=hour, minute=0, second=0)
                slot_end = slot_start + timedelta(hours=duration_hours)

                # Check if slot is free
                conflicts = [
                    e
                    for e in self.events.values()
                    if not (slot_end <= e.start_time or slot_start >= e.end_time)
                ]

                if not conflicts:
                    available_slots.append(slot_start)
                    if len(available_slots) >= 3:
                        return available_slots

        return available_slots

    def _accept_meeting(self, meeting: CalendarEvent) -> None:
        """Accept a meeting invitation."""
        self.events[meeting.id] = meeting
        logger.info(f"✓ Accepted meeting: {meeting.title}")

    def _decline_meeting(self, meeting: CalendarEvent, reason: str) -> None:
        """Decline a meeting invitation."""
        logger.info(f"✓ Declined meeting: {meeting.title} ({reason})")
        # In real implementation, would send decline message
        self.update_memory(
            "assistant",
            f"Declined {meeting.title} - {reason}",
        )

    def _propose_alternatives(
        self, meeting: CalendarEvent, alternatives: List[datetime]
    ) -> None:
        """Propose alternative meeting times."""
        alt_times = [alt.strftime("%Y-%m-%d %H:%M") for alt in alternatives[:3]]
        logger.info(f"✓ Proposed alternatives for {meeting.title}: {alt_times}")

    def get_calendar_summary(self) -> str:
        """Get summary of calendar."""
        total_events = len(self.events)
        pending = len(self.pending_invitations)

        # Calculate daily meeting load
        today = datetime.now().date()
        today_events = [
            e for e in self.events.values() if e.start_time.date() == today
        ]
        today_hours = sum(
            (e.end_time - e.start_time).total_seconds() / 3600
            for e in today_events
        )

        summary = f"""Calendar Summary:
- Total events: {total_events}
- Pending invitations: {pending}
- Today's events: {len(today_events)}
- Today's meeting hours: {today_hours:.1f}
- Max daily preference: {self.calendar_preferences.get('max_hours_per_day', 2.0)} hours"""

        return summary
