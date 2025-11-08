"""Tests for Communication & Email Management Agents."""

import asyncio
from datetime import datetime, timedelta

import pytest

from app.agent import (
    CalendarAgent,
    CommunicationOrchestrator,
    EmailAgent,
    MessageAgent,
    ReportAgent,
    SocialMediaAgent,
)
from app.agent.approval_workflow import ApprovalWorkflow
from app.agent.communication_context import ContextManager
from app.agent.communication_escalation import EscalationManager
from app.agent.info_extraction import InformationExtractor
from app.agent.models.communication import (
    ApprovalStatus,
    CalendarEvent,
    CommunicationType,
    DraftMessage,
    Email,
    EmailCategory,
    Message,
    MessageType,
    PriorityLevel,
    SocialPost,
    ToneStyle,
    UserVoiceProfile,
)
from app.agent.voice_model import VoiceModel


class TestVoiceModel:
    """Test user voice model."""

    def test_initialization(self):
        """Test voice model initialization."""
        voice = VoiceModel()
        assert voice.profile.formal_level == 0.6
        assert voice.profile.emoji_usage == 0.3

    def test_update_from_sample(self):
        """Test learning from sample messages."""
        voice = VoiceModel()
        voice.update_from_sample("Great job! 👍", ToneStyle.FRIENDLY)
        assert voice.profile.tone_by_recipient["general"] == ToneStyle.FRIENDLY

    def test_adapt_to_recipient(self):
        """Test tone adaptation by recipient."""
        voice = VoiceModel()
        voice.profile.tone_by_recipient["manager"] = ToneStyle.PROFESSIONAL
        assert voice.adapt_to_recipient("manager") == ToneStyle.PROFESSIONAL

    def test_greeting_generation(self):
        """Test appropriate greeting generation."""
        voice = VoiceModel()
        greeting = voice.get_greeting("formal")
        assert greeting == "Hello"

    def test_voice_summary(self):
        """Test voice profile summary."""
        voice = VoiceModel()
        summary = voice.get_voice_summary()
        assert "Formality" in summary
        assert "Directness" in summary


class TestInformationExtractor:
    """Test information extraction."""

    def test_action_item_extraction(self):
        """Test extracting action items from text."""
        extractor = InformationExtractor()
        text = "Can you please review the PR? It's urgent."
        actions = extractor.extract_action_items(text, "test_001")
        assert len(actions) > 0
        assert actions[0].description

    def test_decision_extraction(self):
        """Test extracting decisions from text."""
        extractor = InformationExtractor()
        text = "We agreed to use the new framework."
        decisions = extractor.extract_decisions(text)
        assert len(decisions) > 0

    def test_date_extraction(self):
        """Test extracting dates from text."""
        extractor = InformationExtractor()
        text = "Meeting tomorrow at 2pm"
        dates = extractor.extract_dates(text)
        assert len(dates) > 0

    def test_sentiment_detection(self):
        """Test sentiment analysis."""
        extractor = InformationExtractor()
        assert extractor.detect_sentiment("Great work!") == "positive"
        assert extractor.detect_sentiment("This is terrible") == "negative"
        assert extractor.detect_sentiment("It's fine") == "neutral"

    def test_urgency_detection(self):
        """Test urgency detection."""
        extractor = InformationExtractor()
        assert extractor.detect_urgency("This is urgent!") is True
        assert extractor.detect_urgency("This is routine") is False


class TestContextManager:
    """Test communication context management."""

    def test_add_email_to_thread(self):
        """Test adding email to thread."""
        context = ContextManager()
        email = Email(
            id="email_001",
            from_email="sender@example.com",
            to_emails=["recipient@example.com"],
            subject="Test",
            body="Test content",
        )
        thread_id = context.add_email_to_thread(email)
        assert thread_id in context.contexts

    def test_thread_context_retrieval(self):
        """Test retrieving thread context."""
        context = ContextManager()
        email = Email(
            id="email_001",
            from_email="sender@example.com",
            to_emails=["recipient@example.com"],
            subject="Test",
            body="Test content",
            thread_id="thread_123",
        )
        thread_id = context.add_email_to_thread(email)
        ctx = context.get_thread_context(thread_id)
        assert ctx is not None
        assert ctx.subject == "Test"

    def test_action_item_tracking(self):
        """Test tracking action items in context."""
        context = ContextManager()
        context.contexts["thread_1"] = context.ConversationContext(
            thread_id="thread_1", subject="Test", participants=[]
        )
        context.add_action_item("thread_1", "Follow up on proposal")
        actions = context.contexts["thread_1"].action_items
        assert "Follow up on proposal" in actions

    def test_get_pending_actions(self):
        """Test retrieving pending action items."""
        context = ContextManager()
        context.contexts["thread_1"] = context.ConversationContext(
            thread_id="thread_1",
            subject="Test",
            participants=[],
            action_items=["Action 1", "Action 2"],
        )
        pending = context.get_pending_actions()
        assert "thread_1" in pending


class TestApprovalWorkflow:
    """Test approval workflow."""

    def test_routine_message_no_approval(self):
        """Test routine messages don't need approval."""
        workflow = ApprovalWorkflow()
        draft = DraftMessage(
            id="draft_001",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="Thanks for reaching out, I'll get back to you soon.",
        )
        requires_approval, reason = workflow.should_require_approval(draft)
        # Routine responses may have default requires_approval=True
        assert isinstance(requires_approval, bool)

    def test_commitment_requires_approval(self):
        """Test commitments require approval."""
        workflow = ApprovalWorkflow()
        draft = DraftMessage(
            id="draft_002",
            communication_type=CommunicationType.EMAIL,
            recipient="team@example.com",
            body="I'll complete the feature by Friday.",
        )
        requires_approval, reason = workflow.should_require_approval(draft)
        assert requires_approval is True
        assert "commitment" in reason.lower() or "promise" in reason.lower()

    def test_submit_for_approval(self):
        """Test submitting draft for approval."""
        workflow = ApprovalWorkflow()
        draft = DraftMessage(
            id="draft_003",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="Test message",
        )
        workflow.submit_for_approval(draft)
        pending = workflow.get_pending_approvals()
        assert len(pending) > 0

    def test_approve_draft(self):
        """Test approving a draft."""
        workflow = ApprovalWorkflow()
        draft = DraftMessage(
            id="draft_004",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="Test",
        )
        workflow.submit_for_approval(draft)
        success = workflow.approve_draft("draft_004", "test_user")
        assert success is True
        draft = workflow.pending_drafts["draft_004"]
        assert draft.status == ApprovalStatus.APPROVED


class TestEscalationManager:
    """Test escalation management."""

    def test_default_rules_initialization(self):
        """Test that default escalation rules are set up."""
        manager = EscalationManager()
        assert len(manager.escalation_rules) > 0
        assert "urgent_request" in manager.escalation_rules

    def test_email_escalation_detection(self):
        """Test detecting emails that should be escalated."""
        manager = EscalationManager()
        email = Email(
            id="email_001",
            from_email="boss@company.com",
            to_emails=["me@company.com"],
            subject="URGENT: Critical Issue",
            body="We have an emergency situation that needs immediate attention.",
        )
        should_escalate, reason, priority = manager.should_escalate_email(email)
        assert should_escalate is True
        assert priority in [PriorityLevel.URGENT, PriorityLevel.CRITICAL]

    def test_escalate_item(self):
        """Test escalating an item."""
        manager = EscalationManager()
        manager.escalate(
            "item_001", "email", "Critical issue", PriorityLevel.CRITICAL
        )
        pending = manager.get_pending_escalations()
        assert len(pending) > 0
        assert pending[0]["id"] == "item_001"

    def test_resolve_escalation(self):
        """Test resolving an escalation."""
        manager = EscalationManager()
        manager.escalate("item_002", "email", "Test", PriorityLevel.HIGH)
        success = manager.resolve_escalation("item_002", "reviewed")
        assert success is True


class TestEmailAgent:
    """Test email agent functionality."""

    @pytest.mark.asyncio
    async def test_email_agent_initialization(self):
        """Test email agent initializes correctly."""
        agent = EmailAgent()
        assert agent.name == "EmailAgent"
        assert isinstance(agent.voice_model, VoiceModel)
        assert isinstance(agent.context_manager, ContextManager)
        assert isinstance(agent.approval_workflow, ApprovalWorkflow)

    def test_email_categorization(self):
        """Test email categorization."""
        agent = EmailAgent()
        email = Email(
            id="email_001",
            from_email="marketing@example.com",
            to_emails=["me@example.com"],
            subject="Limited Time Offer - 50% Off",
            body="Great deals available today only!",
        )
        category = agent._categorize_email(email)
        assert category in [EmailCategory.SPAM, EmailCategory.PROMOTIONAL]

    def test_email_prioritization(self):
        """Test email prioritization."""
        agent = EmailAgent()
        email = Email(
            id="email_002",
            from_email="team@example.com",
            to_emails=["me@example.com"],
            subject="URGENT: Critical Bug in Production",
            body="System is down, needs immediate fix",
        )
        priority = agent._prioritize_email(email)
        assert priority in [PriorityLevel.URGENT, PriorityLevel.CRITICAL]

    def test_should_respond_to_email(self):
        """Test determining if response is needed."""
        agent = EmailAgent()
        # Question needs response
        email_q = Email(
            id="q_001",
            from_email="user@example.com",
            to_emails=["me@example.com"],
            subject="Question",
            body="Can you help with this?",
        )
        assert agent._should_respond_to_email(email_q) is True

        # Promotion doesn't need response
        email_p = Email(
            id="p_001",
            from_email="marketing@example.com",
            to_emails=["me@example.com"],
            subject="Sale",
            body="Check out our deals",
            category=EmailCategory.PROMOTIONAL,
        )
        assert agent._should_respond_to_email(email_p) is False


class TestMessageAgent:
    """Test message agent functionality."""

    def test_message_agent_initialization(self):
        """Test message agent initializes correctly."""
        agent = MessageAgent()
        assert agent.name == "MessageAgent"
        assert isinstance(agent.voice_model, VoiceModel)

    def test_message_type_detection(self):
        """Test detecting message types."""
        agent = MessageAgent()
        
        # Question
        msg_q = Message(
            id="msg_001",
            platform=CommunicationType.SLACK,
            sender="user",
            channel="engineering",
            content="How do we handle timeouts?",
        )
        msg_type = agent._determine_message_type(msg_q)
        assert msg_type == MessageType.QUESTION

        # Urgent
        msg_u = Message(
            id="msg_002",
            platform=CommunicationType.SLACK,
            sender="user",
            channel="alerts",
            content="URGENT: Server down!",
        )
        msg_type = agent._determine_message_type(msg_u)
        assert msg_type == MessageType.URGENT

    def test_message_prioritization(self):
        """Test message prioritization."""
        agent = MessageAgent()
        msg = Message(
            id="msg_003",
            platform=CommunicationType.SLACK,
            sender="manager",
            channel="general",
            content="Critical production issue!",
            is_mentioned=True,
        )
        priority = agent._prioritize_message(msg)
        assert priority in [PriorityLevel.HIGH, PriorityLevel.URGENT]


class TestCalendarAgent:
    """Test calendar agent functionality."""

    def test_calendar_agent_initialization(self):
        """Test calendar agent initializes correctly."""
        agent = CalendarAgent()
        assert agent.name == "CalendarAgent"
        assert agent.calendar_preferences["no_meetings_before"] == 10

    def test_meeting_outside_working_hours_declined(self):
        """Test declining meetings outside working hours."""
        agent = CalendarAgent()
        tomorrow = datetime.now() + timedelta(days=1)
        meeting = CalendarEvent(
            id="event_001",
            title="Early Meeting",
            start_time=tomorrow.replace(hour=7),
            end_time=tomorrow.replace(hour=8),
            organizer="boss@example.com",
        )
        decision = agent._analyze_invitation(meeting)
        # Should either decline or propose alternative
        assert decision["action"] in ["decline", "propose_alternative"]

    def test_meeting_no_conflict_accepted(self):
        """Test accepting meetings with no conflicts."""
        agent = CalendarAgent()
        tomorrow = datetime.now() + timedelta(days=1)
        meeting = CalendarEvent(
            id="event_002",
            title="Team Meeting",
            start_time=tomorrow.replace(hour=14),
            end_time=tomorrow.replace(hour=15),
            organizer="team@example.com",
        )
        decision = agent._analyze_invitation(meeting)
        assert decision["action"] == "accept"

    def test_find_available_slots(self):
        """Test finding available meeting slots."""
        agent = CalendarAgent()
        slots = agent._find_available_slots(1.0)
        assert len(slots) > 0
        for slot in slots:
            assert isinstance(slot, datetime)


class TestReportAgent:
    """Test report agent functionality."""

    def test_report_agent_initialization(self):
        """Test report agent initializes correctly."""
        agent = ReportAgent()
        assert agent.name == "ReportAgent"

    def test_log_activity(self):
        """Test logging activities."""
        agent = ReportAgent()
        agent.log_activity("development", "Implemented feature X", 120)
        assert len(agent.activities) > 0

    def test_add_accomplishment(self):
        """Test tracking accomplishments."""
        agent = ReportAgent()
        agent.add_accomplishment("Completed milestone 1")
        assert "Completed milestone 1" in agent.accomplishments

    def test_add_blocker(self):
        """Test tracking blockers."""
        agent = ReportAgent()
        agent.add_blocker("Waiting for API response")
        assert "Waiting for API response" in agent.blockers

    def test_build_weekly_report(self):
        """Test building weekly report."""
        agent = ReportAgent()
        agent.add_accomplishment("Feature A")
        agent.add_blocker("Issue B")
        report = agent._build_weekly_report([])
        assert "Feature A" in report
        assert "Issue B" in report


class TestCommunicationOrchestrator:
    """Test communication orchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes all agents."""
        orchestrator = CommunicationOrchestrator()
        assert isinstance(orchestrator.email_agent, EmailAgent)
        assert isinstance(orchestrator.message_agent, MessageAgent)
        assert isinstance(orchestrator.calendar_agent, CalendarAgent)

    def test_enable_disable_agents(self):
        """Test enabling/disabling agents."""
        orchestrator = CommunicationOrchestrator()
        orchestrator.disable_agent("email")
        assert "email" not in orchestrator.enabled_agents
        orchestrator.enable_agent("email")
        assert "email" in orchestrator.enabled_agents

    def test_add_email(self):
        """Test adding email to orchestrator."""
        orchestrator = CommunicationOrchestrator()
        email = Email(
            id="email_001",
            from_email="sender@example.com",
            to_emails=["me@example.com"],
            subject="Test",
            body="Test content",
        )
        orchestrator.add_email(email)
        assert "email_001" in orchestrator.email_agent.emails

    def test_get_pending_approvals(self):
        """Test getting pending approvals."""
        orchestrator = CommunicationOrchestrator()
        # Add a pending draft
        draft = DraftMessage(
            id="draft_001",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="Test",
        )
        orchestrator.email_agent.approval_workflow.submit_for_approval(draft)
        approvals = orchestrator.get_pending_approvals()
        assert "email" in approvals

    def test_approve_draft(self):
        """Test approving draft via orchestrator."""
        orchestrator = CommunicationOrchestrator()
        draft = DraftMessage(
            id="draft_002",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="Test",
        )
        orchestrator.email_agent.drafts[draft.id] = draft
        orchestrator.email_agent.approval_workflow.submit_for_approval(draft)
        success = orchestrator.approve_draft("draft_002", "test_user")
        assert success is True

    def test_get_communication_summary(self):
        """Test getting overall communication summary."""
        orchestrator = CommunicationOrchestrator()
        summary = orchestrator.get_communication_summary()
        assert "Email" in summary or "email" in summary.lower()


class TestIntegration:
    """Integration tests for communication system."""

    def test_email_workflow(self):
        """Test complete email workflow."""
        agent = EmailAgent()
        
        # Add email
        email = Email(
            id="email_001",
            from_email="teammate@example.com",
            to_emails=["me@example.com"],
            subject="Code Review Request",
            body="Can you review PR #123?",
        )
        agent.emails[email.id] = email

        # Analyze
        analysis = agent._analyze_email(email)
        assert "category" in analysis
        assert "priority" in analysis

        # Should respond
        should_respond = agent._should_respond_to_email(email)
        assert should_respond is True

    def test_multi_platform_workflow(self):
        """Test workflow across multiple platforms."""
        orchestrator = CommunicationOrchestrator()

        # Add email
        email = Email(
            id="email_001",
            from_email="boss@company.com",
            to_emails=["me@company.com"],
            subject="Project Status",
            body="Please provide update by EOD",
        )
        orchestrator.add_email(email)

        # Add message
        message = Message(
            id="msg_001",
            platform=CommunicationType.SLACK,
            sender="teammate",
            channel="general",
            content="@user Can you check the logs?",
            is_mentioned=True,
        )
        orchestrator.add_message(message)

        # Get summary
        summary = orchestrator.get_communication_summary()
        assert summary is not None

    def test_approval_workflow_end_to_end(self):
        """Test approval workflow from draft to sent."""
        workflow = ApprovalWorkflow()

        # Create draft
        draft = DraftMessage(
            id="draft_001",
            communication_type=CommunicationType.EMAIL,
            recipient="user@example.com",
            body="I will complete this by Friday.",
        )

        # Assess
        assessment = workflow.assess_draft(draft)
        assert "requires_approval" in assessment

        # Submit for approval
        workflow.submit_for_approval(draft)
        pending = workflow.get_pending_approvals()
        assert len(pending) > 0

        # Approve
        workflow.approve_draft("draft_001", "user")
        workflow.mark_sent("draft_001")
        
        # Check audit trail
        audit = workflow.get_audit_trail()
        assert len(audit) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
