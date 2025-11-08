"""Async-first team communication system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UpdateType(str, Enum):
    """Type of async update."""
    STANDUP = "standup"
    DECISION = "decision"
    ANNOUNCEMENT = "announcement"
    QUESTION = "question"
    BLOCKER = "blocker"
    CELEBRATION = "celebration"
    RETROSPECTIVE = "retrospective"


class DecisionStatus(str, Enum):
    """Status of a decision."""
    PROPOSED = "proposed"
    OPEN_FOR_FEEDBACK = "open_for_feedback"
    FEEDBACK_RECEIVED = "feedback_received"
    DECIDED = "decided"
    IMPLEMENTED = "implemented"


class AsyncUpdate(BaseModel):
    """An async team update."""
    id: str = Field(..., description="Update ID")
    update_type: UpdateType = Field(..., description="Type of update")
    author: str = Field(..., description="Who posted the update")
    title: str = Field(..., description="Update title")
    content: str = Field(..., description="Update content")
    created_date: datetime = Field(default_factory=datetime.now, description="When posted")
    channel: str = Field(default="general", description="Channel or thread")
    priority: int = Field(default=3, ge=1, le=5, description="Priority level (1-5)")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    mentions: List[str] = Field(default_factory=list, description="@mentions")
    reactions: Dict[str, int] = Field(default_factory=dict, description="Emoji reactions")
    thread_replies: List['ThreadReply'] = Field(default_factory=list, description="Thread replies")
    requires_response: bool = Field(default=False, description="Needs responses")
    requires_decision: bool = Field(default=False, description="Needs decision")
    decision_deadline: Optional[datetime] = Field(None, description="Decision deadline")
    read_by: List[str] = Field(default_factory=list, description="Who has read this")


class ThreadReply(BaseModel):
    """Reply in an async thread."""
    author: str = Field(..., description="Reply author")
    content: str = Field(..., description="Reply content")
    created_date: datetime = Field(default_factory=datetime.now, description="When posted")
    reactions: Dict[str, int] = Field(default_factory=dict, description="Emoji reactions")
    mentions: List[str] = Field(default_factory=list, description="@mentions")


class Decision(BaseModel):
    """A documented decision."""
    id: str = Field(..., description="Decision ID")
    title: str = Field(..., description="Decision title")
    context: str = Field(..., description="Context and background")
    options_considered: List[str] = Field(..., description="Options evaluated")
    chosen_option: str = Field(..., description="The chosen option")
    rationale: str = Field(..., description="Why this option was chosen")
    stakeholders: List[str] = Field(..., description="Who was consulted")
    decided_by: str = Field(..., description="Who made the decision")
    decision_date: datetime = Field(default_factory=datetime.now, description="When decided")
    implementation_date: Optional[datetime] = Field(None, description="When implemented")
    reversible: bool = Field(default=True, description="Can this be reversed?")
    impact: str = Field(default="", description="Impact on team/project")
    review_date: Optional[datetime] = Field(None, description="When to review")
    status: DecisionStatus = Field(default=DecisionStatus.PROPOSED, description="Decision status")


class Standup(BaseModel):
    """Daily async standup."""
    id: str = Field(..., description="Standup ID")
    member_name: str = Field(..., description="Team member")
    date: datetime = Field(default_factory=datetime.now, description="Standup date")
    completed_yesterday: str = Field(default="", description="What was completed yesterday")
    planned_today: str = Field(default="", description="What's planned today")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    mood: str = Field(default="neutral", description="Energy/mood level")
    help_needed: Optional[str] = Field(None, description="What help is needed")
    notes: Optional[str] = Field(None, description="Additional notes")


class AsyncCommunicationManager:
    """Manages async-first team communication."""

    def __init__(self):
        """Initialize the communication manager."""
        self.updates: Dict[str, AsyncUpdate] = {}
        self.decisions: Dict[str, Decision] = {}
        self.standups: Dict[str, Standup] = {}
        self.channels: Dict[str, List[str]] = {}  # channel -> update IDs

    def post_update(self, update: AsyncUpdate) -> str:
        """Post an async update.
        
        Args:
            update: The update to post
            
        Returns:
            Update ID
        """
        if update.id in self.updates:
            raise ValueError(f"Update {update.id} already exists")

        self.updates[update.id] = update

        # Add to channel
        if update.channel not in self.channels:
            self.channels[update.channel] = []
        self.channels[update.channel].append(update.id)

        return update.id

    def add_standup(self, standup: Standup) -> str:
        """Add a daily standup.
        
        Args:
            standup: The standup to add
            
        Returns:
            Standup ID
        """
        if standup.id in self.standups:
            raise ValueError(f"Standup {standup.id} already exists")

        self.standups[standup.id] = standup
        return standup.id

    def create_decision(self, decision: Decision) -> str:
        """Create a documented decision.
        
        Args:
            decision: The decision to document
            
        Returns:
            Decision ID
        """
        if decision.id in self.decisions:
            raise ValueError(f"Decision {decision.id} already exists")

        self.decisions[decision.id] = decision
        return decision.id

    def add_thread_reply(self, update_id: str, reply: ThreadReply) -> None:
        """Add a reply to an update thread.
        
        Args:
            update_id: Update ID
            reply: The reply to add
        """
        if update_id not in self.updates:
            raise ValueError(f"Update {update_id} not found")

        self.updates[update_id].thread_replies.append(reply)

    def mark_as_read(self, update_id: str, member: str) -> None:
        """Mark an update as read.
        
        Args:
            update_id: Update ID
            member: Team member
        """
        if update_id not in self.updates:
            raise ValueError(f"Update {update_id} not found")

        update = self.updates[update_id]
        if member not in update.read_by:
            update.read_by.append(member)

    def add_reaction(self, update_id: str, emoji: str) -> None:
        """Add an emoji reaction to an update.
        
        Args:
            update_id: Update ID
            emoji: Emoji reaction
        """
        if update_id not in self.updates:
            raise ValueError(f"Update {update_id} not found")

        update = self.updates[update_id]
        update.reactions[emoji] = update.reactions.get(emoji, 0) + 1

    def finalize_decision(self, decision_id: str, implementation_plan: Optional[str] = None) -> None:
        """Finalize a decision (move from proposed to decided).
        
        Args:
            decision_id: Decision ID
            implementation_plan: Optional implementation notes
        """
        if decision_id not in self.decisions:
            raise ValueError(f"Decision {decision_id} not found")

        decision = self.decisions[decision_id]
        decision.status = DecisionStatus.DECIDED
        if implementation_plan:
            decision.impact = implementation_plan

    def get_recent_standups(self, member_name: str, days: int = 7) -> List[Standup]:
        """Get recent standups from a member.
        
        Args:
            member_name: Team member
            days: Days to look back
            
        Returns:
            List of standups
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        return [
            s for s in self.standups.values()
            if s.member_name == member_name and s.date.timestamp() > cutoff
        ]

    def get_updates_needing_attention(self) -> List[AsyncUpdate]:
        """Get updates that need attention.
        
        Returns:
            Updates that require response or decision
        """
        updates = []
        for update in self.updates.values():
            if update.requires_response or update.requires_decision:
                # Check if still open (not old)
                age_days = (datetime.now() - update.created_date).days
                if age_days < 14:  # Less than 2 weeks old
                    updates.append(update)

        return sorted(updates, key=lambda u: (-u.priority, u.created_date))

    def get_pending_decisions(self) -> List[Decision]:
        """Get decisions pending implementation.
        
        Returns:
            List of decisions not yet implemented
        """
        return [
            d for d in self.decisions.values()
            if d.status != DecisionStatus.IMPLEMENTED
        ]

    def get_recent_updates(self, channel: Optional[str] = None, days: int = 7) -> List[AsyncUpdate]:
        """Get recent updates.
        
        Args:
            channel: Optional channel filter
            days: Days to look back
            
        Returns:
            Recent updates
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)

        updates = [
            u for u in self.updates.values()
            if u.created_date.timestamp() > cutoff
        ]

        if channel:
            updates = [u for u in updates if u.channel == channel]

        return sorted(updates, key=lambda u: -u.created_date.timestamp())

    def get_daily_standup_summary(self, date: Optional[datetime] = None) -> str:
        """Generate a daily standup summary.
        
        Args:
            date: Date to summarize (defaults to today)
            
        Returns:
            Formatted summary
        """
        if date is None:
            date = datetime.now()

        day_start = datetime(date.year, date.month, date.day)
        day_end = datetime(date.year, date.month, date.day, 23, 59, 59)

        daily_standups = [
            s for s in self.standups.values()
            if day_start <= s.date <= day_end
        ]

        summary = [
            "# Daily Standup Summary",
            f"Date: {date.strftime('%Y-%m-%d')}",
            f"Reports: {len(daily_standups)} members",
            ""
        ]

        # Group by mood
        by_mood = {}
        for standup in daily_standups:
            mood = standup.mood
            by_mood[mood] = by_mood.get(mood, 0) + 1

        if by_mood:
            summary.append("## Team Mood")
            for mood, count in sorted(by_mood.items()):
                emoji = {"energized": "⚡", "good": "😊", "neutral": "😐", "tired": "😴", "stressed": "😟"}.get(mood, "❓")
                summary.append(f"- {emoji} {mood}: {count} members")
            summary.append("")

        # Aggregate blockers
        all_blockers = []
        for standup in daily_standups:
            all_blockers.extend(standup.blockers)

        if all_blockers:
            summary.append("## Blockers")
            for blocker in all_blockers:
                summary.append(f"- {blocker}")
            summary.append("")

        # Help needed
        help_requests = [s for s in daily_standups if s.help_needed]
        if help_requests:
            summary.append("## Help Needed")
            for standup in help_requests:
                summary.append(f"- {standup.member_name}: {standup.help_needed}")
            summary.append("")

        return "\n".join(summary)

    def suggest_meeting_topics(self) -> List[str]:
        """Suggest topics that need synchronous discussion.
        
        Returns:
            List of suggested meeting topics
        """
        topics = []

        # Complex decisions still in discussion
        for decision in self.decisions.values():
            if decision.status == DecisionStatus.OPEN_FOR_FEEDBACK:
                # Check if still getting feedback
                age_days = (datetime.now() - decision.decision_date).days
                if age_days >= 3:  # Been open for 3+ days
                    topics.append(f"Finalize decision: {decision.title}")

        # Blocked items needing discussion
        blockers = []
        for standup in self.standups.values():
            blockers.extend(standup.blockers)

        if len(set(blockers)) > 2:  # Multiple blockers
            topics.append("Discuss and resolve blockers")

        # High priority unresolved items
        pending = self.get_updates_needing_attention()
        if len(pending) > 5:
            topics.append("Process backlog of pending items")

        return topics[:5]  # Top 5 suggestions

    def generate_async_digest(self, period_days: int = 7) -> str:
        """Generate a digest of async communications.
        
        Args:
            period_days: Days to cover
            
        Returns:
            Formatted digest
        """
        cutoff = datetime.now().timestamp() - (period_days * 24 * 3600)

        recent_updates = [
            u for u in self.updates.values()
            if u.created_date.timestamp() > cutoff
        ]

        recent_decisions = [
            d for d in self.decisions.values()
            if d.decision_date.timestamp() > cutoff
        ]

        recent_standups = [
            s for s in self.standups.values()
            if s.date.timestamp() > cutoff
        ]

        digest = [
            f"# Async Communications Digest",
            f"Period: Last {period_days} days",
            "",
            f"📊 Stats:",
            f"- Updates: {len(recent_updates)}",
            f"- Decisions: {len(recent_decisions)}",
            f"- Standups: {len(recent_standups)}",
            "",
        ]

        # Top updates by engagement
        by_replies = sorted(recent_updates, key=lambda u: len(u.thread_replies), reverse=True)
        if by_replies[:3]:
            digest.append("## 🔥 Most Discussed")
            for update in by_replies[:3]:
                digest.append(f"- {update.title} ({len(update.thread_replies)} replies)")
            digest.append("")

        # Recent decisions
        if recent_decisions:
            digest.append("## 📋 Decisions Made")
            for decision in recent_decisions[:5]:
                digest.append(f"- {decision.title}: {decision.chosen_option}")
            digest.append("")

        # Pending attention
        pending = self.get_updates_needing_attention()
        if pending:
            digest.append("## ⚠️ Needs Your Attention")
            for update in pending[:5]:
                digest.append(f"- {update.title}")

        return "\n".join(digest)
