# Communication & Email Management Agent System

This module implements a comprehensive autonomous communication management system that handles emails, messages, calendar events, and reporting while maintaining the user's communication voice and preferences.

## Architecture Overview

The system consists of 10 integrated components:

### 1. **Email Agent** (`app/agent/email_agent.py`)
Manages email communications with automatic categorization and response drafting.

**Features:**
- Read and analyze incoming emails
- Automatic categorization (work, personal, spam, promotional)
- Priority scoring (critical, urgent, high, normal, low)
- Draft responses maintaining user's voice
- Thread management and context awareness
- Action item extraction from emails
- Audit trail for all operations

**Usage:**
```python
from app.agent import EmailAgent

agent = EmailAgent()
# Add emails to process
agent.emails[email.id] = email
# Run processing
result = await agent.run()
```

### 2. **Message Agent** (`app/agent/message_agent.py`)
Handles messages across platforms (Slack, Discord, Teams, etc.).

**Features:**
- Monitor @mentions across platforms
- Auto-respond to common questions
- Escalate complex issues
- Platform-specific handling (Slack, Discord, Teams)
- Message type detection (question, announcement, urgent, action_required)
- Conversation threading

**Usage:**
```python
from app.agent import MessageAgent

agent = MessageAgent()
agent.stored_messages[msg.id] = msg
result = await agent.run()
```

### 3. **Social Media Agent** (`app/agent/social_media_agent.py`)
Manages social media interactions and engagement.

**Features:**
- Monitor mentions on LinkedIn, Twitter, GitHub
- Respond to comments maintaining brand voice
- Engagement strategy determination
- Platform-specific tone adjustment
- Automatic or manual approval workflows

**Usage:**
```python
from app.agent import SocialMediaAgent

agent = SocialMediaAgent()
agent.posts[post.id] = post
result = await agent.run()
```

### 4. **Calendar Agent** (`app/agent/calendar_agent.py`)
Intelligent calendar and meeting management.

**Features:**
- Analyze meeting invitations against preferences
- Propose optimal meeting times
- Automatically decline unnecessary meetings
- Respect working hours and meeting limits
- Meeting preparation and reminder management

**Configuration:**
```python
calendar_preferences = {
    "working_hours_start": 9,
    "working_hours_end": 17,
    "no_meetings_before": 10,
    "max_hours_per_day": 2.0,
    "decline_if_less_notice_hours": 24,
}
```

### 5. **Report Agent** (`app/agent/report_agent.py`)
Generates status reports, summaries, and metrics.

**Features:**
- Weekly status reports
- Daily digest summaries
- Activity tracking
- Metrics reporting
- Timeline generation
- Custom report generation

**Usage:**
```python
from app.agent import ReportAgent

agent = ReportAgent()
agent.log_activity("code_review", "Reviewed PR #123", duration_minutes=30)
agent.add_accomplishment("Completed feature X")
report = await agent._generate_weekly_report()
```

### 6. **Voice Model** (`app/agent/voice_model.py`)
Learns and maintains user's communication style.

**Features:**
- Profile user's formality, directness, emoji usage
- Learn common phrases and expressions
- Adapt tone by recipient type
- Generate styled responses
- Profile persistence (JSON)

**Usage:**
```python
from app.agent.voice_model import VoiceModel

voice = VoiceModel()
voice.update_from_sample("Great work on that!", ToneStyle.FRIENDLY)
greeting = voice.get_greeting("team")
styled = voice.generate_styled_response(base_response, "manager")
```

### 7. **Approval Workflow** (`app/agent/approval_workflow.py`)
Manages approval process for outbound communications.

**Features:**
- Automatic categorization (important, routine, uncertain, escalate)
- Confidence scoring for drafts
- Auto-send for routine responses
- Require approval for commitments, apologies, sensitive topics
- Comprehensive audit trail

**Usage:**
```python
from app.agent.approval_workflow import ApprovalWorkflow

workflow = ApprovalWorkflow()
requires_approval, reason = workflow.should_require_approval(draft)
assessment = workflow.assess_draft(draft)
workflow.approve_draft(draft_id, approved_by="user")
```

### 8. **Information Extraction** (`app/agent/info_extraction.py`)
Extracts important information from communications.

**Features:**
- Action item extraction
- Decision tracking
- Date/deadline extraction
- Relationship extraction
- Sentiment analysis
- Urgency detection

**Usage:**
```python
from app.agent.info_extraction import InformationExtractor

extractor = InformationExtractor()
actions = extractor.extract_action_items(text, source_id)
decisions = extractor.extract_decisions(text)
dates = extractor.extract_dates(text)
sentiment = extractor.detect_sentiment(text)
```

### 9. **Communication Context** (`app/agent/communication_context.py`)
Maintains conversation thread context and history.

**Features:**
- Thread management for emails and messages
- Action item tracking per thread
- Decision logging
- Thread summarization
- Relationship mapping

**Usage:**
```python
from app.agent.communication_context import ContextManager

context = ContextManager()
thread_id = context.add_email_to_thread(email)
context.add_action_item(thread_id, "Follow up on proposal")
summary = context.get_thread_summary(thread_id)
```

### 10. **Escalation Management** (`app/agent/communication_escalation.py`)
Handles escalation of sensitive or important communications.

**Features:**
- Customizable escalation rules
- Automatic escalation triggers
- Suspicious content detection
- Harassment detection
- Harsh tone detection
- Priority-based escalation queue

**Usage:**
```python
from app.agent.communication_escalation import EscalationManager

escalator = EscalationManager()
should_escalate, reason, priority = escalator.should_escalate_email(email)
escalator.escalate(item_id, item_type, reason, priority)
pending = escalator.get_pending_escalations()
```

## Communication Orchestrator

The `CommunicationOrchestrator` coordinates all agents:

```python
from app.agent import CommunicationOrchestrator

orchestrator = CommunicationOrchestrator()

# Process all communications
result = await orchestrator.process_communications()

# Get approvals and escalations
approvals = orchestrator.get_pending_approvals()
escalations = orchestrator.get_pending_escalations()

# Approve or reject drafts
orchestrator.approve_draft(draft_id, "user")
orchestrator.reject_draft(draft_id, "Needs revision", "user")

# Get audit trail
audit = orchestrator.get_audit_trail(limit=50)

# Get comprehensive summary
summary = orchestrator.get_communication_summary()
```

## Data Models

All data structures are defined in `app/agent/models/communication.py`:

- **Email**: Email message with metadata
- **Message**: Chat/platform message
- **SocialPost**: Social media post
- **CalendarEvent**: Meeting/calendar entry
- **DraftMessage**: Message awaiting approval
- **UserVoiceProfile**: User's communication style
- **ConversationContext**: Thread context and history
- **ActionItem**: Extracted action item
- **CommunicationAuditLog**: Audit trail entry

### Enums:
- **PriorityLevel**: critical, urgent, high, normal, low
- **EmailCategory**: work, personal, spam, promotional, archive
- **CommunicationType**: email, slack, discord, teams, linkedin, twitter, github
- **MessageType**: question, announcement, urgent, action_required, social
- **ToneStyle**: formal, professional, friendly, casual, diplomatic
- **ApprovalStatus**: draft, pending_approval, approved, rejected, sent

## System Prompts

Communication-specific prompts are in `app/prompt/communication.py`:

- `SYSTEM_PROMPT`: Main system instruction
- `EMAIL_ANALYSIS_PROMPT`: Email analysis template
- `DRAFT_RESPONSE_PROMPT`: Response drafting template
- `CALENDAR_MANAGEMENT_PROMPT`: Meeting analysis template
- `REPORT_GENERATION_PROMPT`: Report template
- `ESCALATION_PROMPT`: Escalation assessment template
- `APPROVAL_WORKFLOW_PROMPT`: Approval decision template

## Configuration

Communication preferences are configurable per agent:

```python
# Email agent
email_preferences = {
    "auto_categorize": True,
    "auto_prioritize": True,
    "draft_mode": "auto_send_routine",  # or "all_need_approval", "review_important"
    "work_hours_start": 9,
    "work_hours_end": 17,
}

# Calendar agent
calendar_preferences = {
    "working_hours_start": 9,
    "working_hours_end": 17,
    "no_meetings_before": 10,
    "max_hours_per_day": 2.0,
    "min_meeting_duration": 15,
    "prefer_async": True,
    "meeting_buffer_minutes": 15,
    "decline_if_less_notice_hours": 24,
}

# Message agent
platform_settings = {
    "slack": {"auto_respond": True, "escalate_mentions": True},
    "discord": {"auto_respond": False, "escalate_mentions": True},
    "teams": {"auto_respond": True, "escalate_mentions": True},
}
```

## Audit & Compliance

All outbound communications have comprehensive audit trails:

```python
audit_log = orchestrator.get_audit_trail(limit=50)
for log_entry in audit_log:
    print(f"{log_entry.timestamp}: {log_entry.action} -> {log_entry.status}")
    print(f"  {log_entry.reason}")
```

Exported contexts for analysis:

```python
contexts = orchestrator.export_all_contexts()
# {
#   "email": { thread_id: { "subject": ..., "status": ... } },
#   "message": { thread_id: { "subject": ..., "status": ... } }
# }
```

## Workflow Examples

### Example 1: Email with Required Approval

```python
email = Email(
    id="email_123",
    from_email="team.lead@company.com",
    subject="Code Review Request",
    body="Can you review PR #234 this afternoon?",
    # ...
)

agent = EmailAgent()
agent.emails[email.id] = email
await agent.run()

# Agent automatically:
# 1. Categorizes as WORK/HIGH priority
# 2. Detects it's a question needing response
# 3. Drafts response in user's voice
# 4. Submits for approval (contains question)
# 5. Returns draft for user review
```

### Example 2: Slack Mention Auto-Response

```python
message = Message(
    id="msg_456",
    platform=CommunicationType.SLACK,
    sender="colleague",
    channel="engineering",
    content="@user How do we handle timeout errors?",
    is_mentioned=True,
    # ...
)

agent = MessageAgent()
agent.stored_messages[message.id] = message
await agent.run()

# Agent automatically:
# 1. Detects mention and question
# 2. Checks Slack auto_respond setting (True)
# 3. Drafts concise response
# 4. Checks confidence score (high for technical Q)
# 5. Auto-sends if confidence > 0.8
# 6. Logs to audit trail
```

### Example 3: Meeting Invitation Analysis

```python
invitation = CalendarEvent(
    id="event_789",
    title="Team Standup",
    start_time=datetime.now().replace(hour=8),  # 8 AM
    # ...
)

agent = CalendarAgent()
agent.pending_invitations[invitation.id] = invitation
await agent.run()

# Agent:
# 1. Checks preferences (no meetings before 10 AM)
# 2. Proposes alternative time (10 AM)
# 3. Sends counter-proposal with reasons
```

## Error Handling

The system handles various error scenarios:

- **TokenLimitExceeded**: Context compression and truncation
- **Network errors**: Graceful degradation and retry logic
- **Invalid input**: Validation and sanitization
- **Escalation triggers**: Automatic user notification

## Performance Considerations

- Agents run independently and can be parallelized
- Context caching for thread efficiency
- Lazy loading of voice profiles
- Audit log pruning (configurable retention)
- Batch processing for daily digests

## Future Enhancements

- Machine learning for voice profile refinement
- Multi-language support
- Calendar integration with external providers (Google, Outlook)
- Email provider integrations (Gmail, Outlook via MCP)
- Real-time notification system
- Sentiment-based response suggestions
- Templates for common scenarios
- Integration with knowledge base for auto-answering
- Collaborative workflows (team approvals)

## Testing

See `tests/test_communication_agents.py` for comprehensive test suite covering:
- Email categorization and prioritization
- Voice profile learning
- Approval workflow decisions
- Escalation triggers
- Information extraction
- Context management
- Orchestrator coordination

## Debugging

Enable detailed logging:

```python
import logging
logging.getLogger("app.agent").setLevel(logging.DEBUG)
```

View orchestrator state:

```python
summary = orchestrator.get_communication_summary()
print(summary)

# See pending items
approvals = orchestrator.get_pending_approvals()
escalations = orchestrator.get_pending_escalations()
actions = orchestrator.get_action_items()
```

Export contexts for analysis:

```python
contexts = orchestrator.export_all_contexts()
import json
print(json.dumps(contexts, indent=2))
```
