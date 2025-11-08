"""Orchestrator for managing all communication agents."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent.calendar_agent import CalendarAgent
from app.agent.email_agent import EmailAgent
from app.agent.message_agent import MessageAgent
from app.agent.models.communication import (
    CommunicationAuditLog,
    DraftMessage,
    Email,
    Message,
    SocialPost,
)
from app.agent.report_agent import ReportAgent
from app.agent.social_media_agent import SocialMediaAgent
from app.agent.voice_model import VoiceModel
from app.logger import logger


class CommunicationOrchestrator(BaseModel):
    """Orchestrates all communication management agents."""

    email_agent: EmailAgent = Field(
        default_factory=EmailAgent, description="Email management agent"
    )
    message_agent: MessageAgent = Field(
        default_factory=MessageAgent, description="Message management agent"
    )
    social_media_agent: SocialMediaAgent = Field(
        default_factory=SocialMediaAgent, description="Social media management agent"
    )
    calendar_agent: CalendarAgent = Field(
        default_factory=CalendarAgent, description="Calendar management agent"
    )
    report_agent: ReportAgent = Field(
        default_factory=ReportAgent, description="Report generation agent"
    )

    voice_model: VoiceModel = Field(
        default_factory=VoiceModel, description="Shared voice profile"
    )

    # Configuration
    enabled_agents: List[str] = Field(
        default_factory=lambda: [
            "email",
            "message",
            "social_media",
            "calendar",
            "report",
        ],
        description="Enabled agents",
    )

    class Config:
        arbitrary_types_allowed = True

    async def process_communications(self) -> str:
        """Process all pending communications."""
        results = []

        try:
            # Process emails
            if "email" in self.enabled_agents:
                logger.info("📧 Processing emails...")
                email_result = await self.email_agent.run()
                results.append(f"Emails: {email_result}")

            # Process messages
            if "message" in self.enabled_agents:
                logger.info("💬 Processing messages...")
                message_result = await self.message_agent.run()
                results.append(f"Messages: {message_result}")

            # Process social media
            if "social_media" in self.enabled_agents:
                logger.info("📱 Processing social media...")
                social_result = await self.social_media_agent.run()
                results.append(f"Social Media: {social_result}")

            # Process calendar
            if "calendar" in self.enabled_agents:
                logger.info("📅 Processing calendar...")
                calendar_result = await self.calendar_agent.run()
                results.append(f"Calendar: {calendar_result}")

            # Generate reports
            if "report" in self.enabled_agents:
                logger.info("📊 Generating reports...")
                report_result = await self.report_agent.run()
                results.append(f"Reports: {report_result}")

        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            results.append(f"Error: {str(e)}")

        return "\n".join(results)

    def add_email(self, email: Email) -> None:
        """Add email to email agent."""
        self.email_agent.emails[email.id] = email
        logger.info(f"✓ Added email to orchestrator: {email.subject}")

    def add_message(self, message: Message) -> None:
        """Add message to message agent."""
        self.message_agent.stored_messages[message.id] = message
        logger.info(f"✓ Added message to orchestrator: {message.content[:50]}")

    def add_social_post(self, post: SocialPost) -> None:
        """Add social post to social media agent."""
        self.social_media_agent.posts[post.id] = post
        logger.info(f"✓ Added social post to orchestrator: {post.platform.value}")

    def enable_agent(self, agent_name: str) -> None:
        """Enable a communication agent."""
        if agent_name not in self.enabled_agents:
            self.enabled_agents.append(agent_name)
            logger.info(f"✓ Enabled agent: {agent_name}")

    def disable_agent(self, agent_name: str) -> None:
        """Disable a communication agent."""
        if agent_name in self.enabled_agents:
            self.enabled_agents.remove(agent_name)
            logger.info(f"✓ Disabled agent: {agent_name}")

    def get_pending_approvals(self) -> Dict[str, List[DraftMessage]]:
        """Get all pending approvals across agents."""
        approvals = {}

        if "email" in self.enabled_agents:
            email_pending = self.email_agent.approval_workflow.get_pending_approvals()
            if email_pending:
                approvals["email"] = email_pending

        if "message" in self.enabled_agents:
            msg_pending = self.message_agent.approval_workflow.get_pending_approvals()
            if msg_pending:
                approvals["message"] = msg_pending

        if "social_media" in self.enabled_agents:
            social_pending = self.social_media_agent.approval_workflow.get_pending_approvals()
            if social_pending:
                approvals["social_media"] = social_pending

        return approvals

    def get_pending_escalations(self) -> Dict[str, List[Dict]]:
        """Get all pending escalations across agents."""
        escalations = {}

        if "email" in self.enabled_agents:
            email_escalations = self.email_agent.escalation_manager.get_pending_escalations()
            if email_escalations:
                escalations["email"] = email_escalations

        if "message" in self.enabled_agents:
            msg_escalations = self.message_agent.escalation_manager.get_pending_escalations()
            if msg_escalations:
                escalations["message"] = msg_escalations

        if "social_media" in self.enabled_agents:
            social_escalations = self.social_media_agent.escalation_manager.get_pending_escalations()
            if social_escalations:
                escalations["social_media"] = social_escalations

        return escalations

    def approve_draft(self, draft_id: str, approved_by: str = "user") -> bool:
        """Approve a draft across any agent."""
        # Try each agent
        agents_to_check = [
            self.email_agent,
            self.message_agent,
            self.social_media_agent,
        ]

        for agent in agents_to_check:
            if draft_id in agent.drafts:
                return agent.approval_workflow.approve_draft(draft_id, approved_by)

        logger.warning(f"Draft {draft_id} not found in any agent")
        return False

    def reject_draft(self, draft_id: str, reason: str = "", rejected_by: str = "user") -> bool:
        """Reject a draft across any agent."""
        agents_to_check = [
            self.email_agent,
            self.message_agent,
            self.social_media_agent,
        ]

        for agent in agents_to_check:
            if draft_id in agent.drafts:
                return agent.approval_workflow.reject_draft(draft_id, reason, rejected_by)

        logger.warning(f"Draft {draft_id} not found in any agent")
        return False

    def get_audit_trail(self, limit: int = 50) -> List[CommunicationAuditLog]:
        """Get combined audit trail from all agents."""
        all_logs: List[CommunicationAuditLog] = []

        if "email" in self.enabled_agents:
            all_logs.extend(self.email_agent.approval_workflow.audit_log)

        if "message" in self.enabled_agents:
            all_logs.extend(self.message_agent.approval_workflow.audit_log)

        if "social_media" in self.enabled_agents:
            all_logs.extend(self.social_media_agent.approval_workflow.audit_log)

        # Sort by timestamp and return latest
        return sorted(all_logs, key=lambda log: log.timestamp, reverse=True)[:limit]

    def get_communication_summary(self) -> str:
        """Get overall communication summary."""
        summary = "=== Communication System Summary ===\n\n"

        if "email" in self.enabled_agents:
            summary += self.email_agent.get_email_summary() + "\n\n"

        if "message" in self.enabled_agents:
            summary += self.message_agent.get_message_summary() + "\n\n"

        if "social_media" in self.enabled_agents:
            summary += self.social_media_agent.get_social_summary() + "\n\n"

        if "calendar" in self.enabled_agents:
            summary += self.calendar_agent.get_calendar_summary() + "\n\n"

        if "report" in self.enabled_agents:
            summary += self.report_agent.get_report_summary() + "\n\n"

        # Add escalations and approvals
        pending_approvals = self.get_pending_approvals()
        pending_escalations = self.get_pending_escalations()

        summary += f"Pending Approvals: {sum(len(v) for v in pending_approvals.values())}\n"
        summary += f"Pending Escalations: {sum(len(v) for v in pending_escalations.values())}\n"

        # Voice model summary
        summary += "\n" + self.voice_model.get_voice_summary()

        return summary

    def set_voice_profile_path(self, path: str) -> None:
        """Set path for saving voice profile."""
        from pathlib import Path

        self.voice_model.storage_path = Path(path)
        # Load if exists
        self.voice_model.load_profile()
        logger.info(f"✓ Set voice profile path: {path}")

    def export_all_contexts(self) -> Dict:
        """Export all conversation contexts."""
        contexts = {}

        if "email" in self.enabled_agents:
            contexts["email"] = self.email_agent.context_manager.export_contexts()

        if "message" in self.enabled_agents:
            contexts["message"] = self.message_agent.context_manager.export_contexts()

        return contexts

    def get_action_items(self) -> Dict[str, List[str]]:
        """Get all pending action items."""
        all_actions = {}

        if "email" in self.enabled_agents:
            email_actions = self.email_agent.context_manager.get_pending_actions()
            if email_actions:
                all_actions["email"] = sum(email_actions.values(), [])

        if "message" in self.enabled_agents:
            msg_actions = self.message_agent.context_manager.get_pending_actions()
            if msg_actions:
                all_actions["message"] = sum(msg_actions.values(), [])

        return all_actions
