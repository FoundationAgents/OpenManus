"""Data models for communication and email management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    """Email/message priority levels."""

    CRITICAL = "critical"
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EmailCategory(str, Enum):
    """Email categorization."""

    WORK = "work"
    PERSONAL = "personal"
    SPAM = "spam"
    PROMOTIONAL = "promotional"
    ARCHIVE = "archive"


class CommunicationType(str, Enum):
    """Types of communication."""

    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    GITHUB = "github"


class MessageType(str, Enum):
    """Types of messages."""

    QUESTION = "question"
    ANNOUNCEMENT = "announcement"
    URGENT = "urgent"
    SOCIAL = "social"
    ACTION_REQUIRED = "action_required"


class ToneStyle(str, Enum):
    """Communication tone styles."""

    FORMAL = "formal"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    DIPLOMATIC = "diplomatic"


class ApprovalStatus(str, Enum):
    """Status of draft messages waiting for approval."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class Email(BaseModel):
    """Represents an email message."""

    id: str = Field(..., description="Unique email ID")
    from_email: str = Field(..., description="Sender email address")
    to_emails: List[str] = Field(..., description="Recipient email addresses")
    cc: Optional[List[str]] = Field(default=None, description="CC recipients")
    bcc: Optional[List[str]] = Field(default=None, description="BCC recipients")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body/content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Email timestamp")
    category: EmailCategory = Field(default=EmailCategory.PERSONAL, description="Email category")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Email priority")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for grouped emails")
    is_read: bool = Field(default=False, description="Whether email has been read")
    is_starred: bool = Field(default=False, description="Whether email is starred")
    attachments: Optional[List[str]] = Field(default=None, description="Attachment filenames")
    labels: Optional[List[str]] = Field(default=None, description="Email labels/tags")


class Message(BaseModel):
    """Represents a message (Slack, Discord, Teams, etc.)."""

    id: str = Field(..., description="Unique message ID")
    platform: CommunicationType = Field(..., description="Platform (Slack, Discord, etc.)")
    sender: str = Field(..., description="Sender username/ID")
    channel: str = Field(..., description="Channel or conversation ID")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    message_type: MessageType = Field(default=MessageType.SOCIAL, description="Type of message")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Message priority")
    mentions: Optional[List[str]] = Field(default=None, description="@mentions in the message")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation")
    is_mentioned: bool = Field(default=False, description="Whether user was mentioned")
    requires_action: bool = Field(default=False, description="Whether action is required")


class SocialPost(BaseModel):
    """Represents a social media post."""

    id: str = Field(..., description="Unique post ID")
    platform: CommunicationType = Field(..., description="Platform (LinkedIn, Twitter, GitHub)")
    author: str = Field(..., description="Post author")
    content: str = Field(..., description="Post content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Post timestamp")
    mention_type: str = Field(default="mention", description="Type of mention/engagement")
    engagement_count: int = Field(default=0, description="Number of engagements")
    url: Optional[str] = Field(default=None, description="URL of the post")


class CalendarEvent(BaseModel):
    """Represents a calendar event/meeting."""

    id: str = Field(..., description="Unique event ID")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    attendees: List[str] = Field(default_factory=list, description="Attendee email addresses")
    organizer: str = Field(..., description="Event organizer")
    location: Optional[str] = Field(default=None, description="Event location")
    is_recurring: bool = Field(default=False, description="Whether event is recurring")
    reminder_minutes: int = Field(default=15, description="Reminder time in minutes")


class DraftMessage(BaseModel):
    """Represents a draft message waiting for approval or sending."""

    id: str = Field(..., description="Unique draft ID")
    communication_type: CommunicationType = Field(..., description="Type of communication")
    recipient: str = Field(..., description="Recipient(s)")
    subject: Optional[str] = Field(default=None, description="Subject (for emails)")
    body: str = Field(..., description="Message body/content")
    tone: ToneStyle = Field(default=ToneStyle.PROFESSIONAL, description="Tone/style of message")
    status: ApprovalStatus = Field(default=ApprovalStatus.DRAFT, description="Approval status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    reasons: List[str] = Field(default_factory=list, description="Reasons for suggestions/issues")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in draft")
    requires_approval: bool = Field(default=True, description="Whether approval is required")


class UserVoiceProfile(BaseModel):
    """Captures user's communication style and preferences."""

    formal_level: float = Field(default=0.6, ge=0.0, le=1.0, description="Formality level (0=casual, 1=formal)")
    directness: float = Field(default=0.7, ge=0.0, le=1.0, description="How direct to be")
    emoji_usage: float = Field(default=0.3, ge=0.0, le=1.0, description="Emoji usage frequency")
    detail_level: float = Field(default=0.6, ge=0.0, le=1.0, description="Detail level preference")
    preferred_phrases: List[str] = Field(default_factory=list, description="Common phrases/expressions")
    greeting_style: str = Field(default="Hi", description="Preferred greeting")
    closing_style: str = Field(default="Thanks", description="Preferred closing")
    tone_by_recipient: Dict[str, ToneStyle] = Field(
        default_factory=dict, description="Tone adjustments by recipient type"
    )
    communication_preferences: Dict[str, str] = Field(
        default_factory=dict, description="Preferences for different communication types"
    )


class ConversationContext(BaseModel):
    """Stores context for email/message threads."""

    thread_id: str = Field(..., description="Thread identifier")
    subject: str = Field(..., description="Thread subject")
    participants: List[str] = Field(..., description="All participants in thread")
    messages: List[str] = Field(default_factory=list, description="Message IDs in order")
    status: str = Field(default="active", description="Thread status (active, resolved, archived)")
    action_items: List[str] = Field(default_factory=list, description="Action items in thread")
    decisions_made: List[str] = Field(default_factory=list, description="Decisions made in thread")
    important_dates: List[datetime] = Field(default_factory=list, description="Important dates mentioned")


class ActionItem(BaseModel):
    """Represents an extracted action item from communications."""

    id: str = Field(..., description="Unique action ID")
    description: str = Field(..., description="Action description")
    source: str = Field(..., description="Communication source (email/message ID)")
    assigned_to: str = Field(default="user", description="Who this action is assigned to")
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Action priority")
    completed: bool = Field(default=False, description="Whether action is completed")


class CommunicationAuditLog(BaseModel):
    """Audit trail for all outbound communications."""

    id: str = Field(..., description="Log entry ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="When action occurred")
    action: str = Field(..., description="Action type (send, draft, approve, reject)")
    communication_type: CommunicationType = Field(..., description="Type of communication")
    recipient: str = Field(..., description="Recipient(s)")
    content_preview: str = Field(..., description="First 200 chars of content")
    status: str = Field(..., description="Success/failure status")
    reason: Optional[str] = Field(default=None, description="Reason for action/failure")
    approved_by: Optional[str] = Field(default=None, description="Who approved (if applicable)")
