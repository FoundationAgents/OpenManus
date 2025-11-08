"""Email management agent for handling email communications."""

from typing import Dict, List, Optional

from pydantic import Field

from app.agent.approval_workflow import ApprovalWorkflow
from app.agent.communication_context import ContextManager
from app.agent.communication_escalation import EscalationManager
from app.agent.info_extraction import InformationExtractor
from app.agent.models.communication import (
    ApprovalStatus,
    DraftMessage,
    Email,
    EmailCategory,
    PriorityLevel,
)
from app.agent.toolcall import ToolCallAgent
from app.agent.voice_model import VoiceModel
from app.config import config
from app.logger import logger
from app.prompt.communication import EMAIL_ANALYSIS_PROMPT, SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection


class EmailAgent(ToolCallAgent):
    """Agent for managing email communications with categorization, prioritization, and draft responses."""

    name: str = "EmailAgent"
    description: str = (
        "An intelligent email management agent that reads, categorizes, prioritizes, "
        "and drafts responses to emails while maintaining the user's voice and preferences"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "Process the next email or email task."

    max_steps: int = 20
    max_observe: int = 10000

    # Core components
    voice_model: VoiceModel = Field(default_factory=VoiceModel, description="User's communication voice")
    context_manager: ContextManager = Field(
        default_factory=ContextManager, description="Conversation context management"
    )
    approval_workflow: ApprovalWorkflow = Field(
        default_factory=ApprovalWorkflow, description="Approval workflow for drafts"
    )
    escalation_manager: EscalationManager = Field(
        default_factory=EscalationManager, description="Escalation management"
    )
    info_extractor: InformationExtractor = Field(
        default_factory=InformationExtractor, description="Information extraction"
    )

    # Email storage
    emails: Dict[str, Email] = Field(default_factory=dict, description="Stored emails")
    drafts: Dict[str, DraftMessage] = Field(default_factory=dict, description="Draft responses")

    # User preferences
    email_preferences: Dict = Field(
        default_factory=lambda: {
            "auto_categorize": True,
            "auto_prioritize": True,
            "draft_mode": "auto_send_routine",  # auto_send_routine, all_need_approval, review_important
            "work_hours_start": 9,
            "work_hours_end": 17,
        },
        description="Email handling preferences",
    )

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    class Config:
        arbitrary_types_allowed = True

    async def step(self) -> str:
        """Execute a single step in email management workflow."""
        try:
            # Check for pending escalations first
            pending_escalations = self.escalation_manager.get_pending_escalations()
            if pending_escalations:
                return await self._handle_escalations(pending_escalations)

            # Check for pending approvals
            pending_approvals = self.approval_workflow.get_pending_approvals()
            if pending_approvals:
                return await self._handle_pending_approvals(pending_approvals)

            # Process new emails
            if self.emails:
                return await self._process_next_email()

            # No more work
            return "All emails processed"

        except Exception as e:
            logger.error(f"Error in email agent step: {e}")
            self.update_memory("assistant", f"Error occurred: {str(e)}")
            return f"Error: {str(e)}"

    async def _process_next_email(self) -> str:
        """Process the next unprocessed email."""
        # Find first unread email
        unread_email = None
        for email in self.emails.values():
            if not email.is_read:
                unread_email = email
                break

        if not unread_email:
            return "No unread emails to process"

        # Analyze email
        analysis = self._analyze_email(unread_email)

        # Update email metadata
        unread_email.category = analysis["category"]
        unread_email.priority = analysis["priority"]
        unread_email.is_read = True

        # Add to context
        thread_id = self.context_manager.add_email_to_thread(unread_email)

        # Extract action items and decisions
        action_items = self.info_extractor.extract_action_items(
            unread_email.body, unread_email.id
        )
        for action in action_items:
            self.context_manager.add_action_item(thread_id, action.description)

        decisions = self.info_extractor.extract_decisions(unread_email.body)
        for decision in decisions:
            self.context_manager.add_decision(thread_id, decision)

        # Check if response is needed
        needs_response = self._should_respond_to_email(unread_email)

        if needs_response:
            # Draft response
            draft = await self._draft_response(unread_email)
            self.drafts[draft.id] = draft

            # Assess draft for approval
            assessment = self.approval_workflow.assess_draft(draft, self.email_preferences)
            if assessment["requires_approval"]:
                self.approval_workflow.submit_for_approval(draft)
                return f"Email from {unread_email.from_email} requires response. Draft submitted for approval."

        # Log to audit
        self.approval_workflow.audit_log.append(
            self._create_audit_log(
                email_id=unread_email.id,
                action="read_and_analyze",
                category=unread_email.category,
                priority=unread_email.priority,
            )
        )

        summary = f"""Processed email from {unread_email.from_email}:
- Category: {unread_email.category.value}
- Priority: {unread_email.priority.value}
- Subject: {unread_email.subject}
- Action Items: {len(action_items)}"""

        self.update_memory("assistant", summary)
        return summary

    def _analyze_email(self, email: Email) -> Dict:
        """Analyze email for categorization and priority."""
        # Check if email should be escalated
        should_escalate, reason, priority = self.escalation_manager.should_escalate_email(
            email
        )

        if should_escalate:
            self.escalation_manager.escalate(
                item_id=email.id,
                item_type="email",
                reason=reason,
                priority=priority,
                data=email.model_dump(),
            )

        # Categorize email
        category = self._categorize_email(email)

        # Determine priority if not escalated
        if not should_escalate:
            priority = self._prioritize_email(email)

        return {"category": category, "priority": priority}

    def _categorize_email(self, email: Email) -> EmailCategory:
        """Categorize email into category."""
        full_text = f"{email.subject} {email.body}".lower()

        # Check for spam indicators
        spam_keywords = ["viagra", "click here", "verify account", "limited time"]
        if any(keyword in full_text for keyword in spam_keywords):
            return EmailCategory.SPAM

        # Check for promotional
        promo_keywords = ["deal", "offer", "discount", "sale", "limited", "promotion"]
        if any(keyword in full_text for keyword in promo_keywords):
            return EmailCategory.PROMOTIONAL

        # Check for work-related
        work_keywords = ["project", "meeting", "review", "deadline", "sprint", "task", "bug"]
        if any(keyword in full_text for keyword in work_keywords):
            return EmailCategory.WORK

        # Default to personal
        return EmailCategory.PERSONAL

    def _prioritize_email(self, email: Email) -> PriorityLevel:
        """Determine priority of email."""
        full_text = f"{email.subject} {email.body}".lower()

        # Check for critical indicators
        if any(word in full_text for word in ["emergency", "critical", "outage"]):
            return PriorityLevel.CRITICAL

        # Check for urgent
        if any(word in full_text for word in ["urgent", "asap", "immediately", "now"]):
            return PriorityLevel.URGENT

        # Check for important
        if any(word in full_text for word in ["important", "must", "required"]):
            return PriorityLevel.HIGH

        # Check for low priority
        if email.category == EmailCategory.PROMOTIONAL:
            return PriorityLevel.LOW

        return PriorityLevel.NORMAL

    def _should_respond_to_email(self, email: Email) -> bool:
        """Determine if email needs a response."""
        # Questions need responses
        if email.body.endswith("?"):
            return True

        # Action items need responses
        full_text = email.body.lower()
        if any(keyword in full_text for keyword in ["please let me know", "can you", "could you"]):
            return True

        # Spam and promotional don't need responses
        if email.category in [EmailCategory.SPAM, EmailCategory.PROMOTIONAL]:
            return False

        return False

    async def _draft_response(self, email: Email) -> DraftMessage:
        """Draft a response to an email."""
        # Prepare draft context
        context = f"""Original email from {email.from_email}:
Subject: {email.subject}

{email.body}

---

Draft a professional response that:
1. Maintains the user's communication style
2. Addresses the sender's questions or requests
3. Is concise and clear
4. Includes any necessary next steps"""

        # Get LLM to draft response
        self.update_memory("user", context)

        try:
            response = await self.llm.ask(
                messages=self.messages,
                system_msgs=[Message.system_message(SYSTEM_PROMPT)],
                max_tokens=500,
            )
        except Exception as e:
            logger.error(f"Error drafting response: {e}")
            response = f"Thank you for your email. I'll get back to you shortly."

        # Create draft
        draft = DraftMessage(
            id=f"draft_{email.id}",
            communication_type="email",
            recipient=email.from_email,
            subject=f"Re: {email.subject}",
            body=response,
            confidence_score=0.8,
        )

        return draft

    async def _handle_pending_approvals(self, pending_drafts: List[DraftMessage]) -> str:
        """Handle pending drafts awaiting approval."""
        if not pending_drafts:
            return "No pending approvals"

        draft = pending_drafts[0]
        summary = f"""Draft awaiting approval:
To: {draft.recipient}
Subject: {draft.subject}

{draft.body}

Status: {draft.status.value}"""

        self.update_memory("assistant", summary)
        return summary

    async def _handle_escalations(self, escalations: List[Dict]) -> str:
        """Handle escalated items."""
        if not escalations:
            return "No escalations"

        escalation = escalations[0]
        summary = f"""Escalation requiring attention:
Type: {escalation['type']}
Reason: {escalation['reason']}
Priority: {escalation['priority'].value}
Time: {escalation['timestamp']}"""

        self.update_memory("assistant", summary)
        return summary

    def _create_audit_log(self, email_id: str, action: str, **kwargs):
        """Create audit log entry."""
        from app.agent.models.communication import CommunicationAuditLog

        return CommunicationAuditLog(
            id=f"log_{email_id}_{action}",
            action=action,
            communication_type="email",
            recipient=self.emails[email_id].from_email if email_id in self.emails else "unknown",
            content_preview=self.emails[email_id].subject if email_id in self.emails else "",
            status="success",
            reason=" | ".join(f"{k}={v}" for k, v in kwargs.items()),
        )

    def get_email_summary(self) -> str:
        """Get summary of email processing."""
        total_emails = len(self.emails)
        unread_count = sum(1 for e in self.emails.values() if not e.is_read)

        category_counts = {}
        priority_counts = {}

        for email in self.emails.values():
            category_counts[email.category.value] = category_counts.get(email.category.value, 0) + 1
            priority_counts[email.priority.value] = priority_counts.get(email.priority.value, 0) + 1

        summary = f"""Email Summary:
- Total: {total_emails}
- Unread: {unread_count}
- Categories: {category_counts}
- Priorities: {priority_counts}
- Drafts pending: {len(self.approval_workflow.get_pending_approvals())}
- Escalations: {len(self.escalation_manager.get_pending_escalations())}"""

        return summary
