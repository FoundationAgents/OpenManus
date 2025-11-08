"""Message agent for handling Slack, Discord, Teams, and other messaging platforms."""

from typing import Dict, List, Optional

from pydantic import Field

from app.agent.approval_workflow import ApprovalWorkflow
from app.agent.communication_context import ContextManager
from app.agent.communication_escalation import EscalationManager
from app.agent.info_extraction import InformationExtractor
from app.agent.models.communication import (
    CommunicationType,
    DraftMessage,
    Message,
    MessageType,
    PriorityLevel,
)
from app.agent.toolcall import ToolCallAgent
from app.agent.voice_model import VoiceModel
from app.config import config
from app.logger import logger
from app.prompt.communication import SYSTEM_PROMPT
from app.schema import Message as SchemaMessage
from app.tool import Terminate, ToolCollection


class MessageAgent(ToolCallAgent):
    """Agent for managing messages across platforms (Slack, Discord, Teams, etc.)."""

    name: str = "MessageAgent"
    description: str = (
        "An intelligent message management agent that monitors mentions, responds to questions, "
        "and manages messages across Slack, Discord, Teams, and other platforms"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "Process the next message or message task."

    max_steps: int = 20
    max_observe: int = 10000

    # Core components
    voice_model: VoiceModel = Field(
        default_factory=VoiceModel, description="User's communication voice"
    )
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

    # Message storage (Note: 'messages' here is for communication Message, not schema Message)
    stored_messages: Dict[str, Message] = Field(default_factory=dict, description="Stored messages")
    drafts: Dict[str, DraftMessage] = Field(default_factory=dict, description="Draft responses")

    # Platform configuration
    platform_settings: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "slack": {"auto_respond": True, "escalate_mentions": True},
            "discord": {"auto_respond": False, "escalate_mentions": True},
            "teams": {"auto_respond": True, "escalate_mentions": True},
        },
        description="Settings per platform",
    )

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    class Config:
        arbitrary_types_allowed = True

    async def step(self) -> str:
        """Execute a single step in message management workflow."""
        try:
            # Check for pending escalations
            pending_escalations = self.escalation_manager.get_pending_escalations()
            if pending_escalations:
                return await self._handle_escalations(pending_escalations)

            # Check for pending approvals
            pending_approvals = self.approval_workflow.get_pending_approvals()
            if pending_approvals:
                return await self._handle_pending_approvals(pending_approvals)

            # Process new messages
            if self.stored_messages:
                return await self._process_next_message()

            return "All messages processed"

        except Exception as e:
            logger.error(f"Error in message agent step: {e}")
            self.update_memory("assistant", f"Error occurred: {str(e)}")
            return f"Error: {str(e)}"

    async def _process_next_message(self) -> str:
        """Process the next unprocessed message."""
        # Find message requiring response
        target_message = None
        for msg in self.stored_messages.values():
            if msg.is_mentioned or msg.requires_action:
                target_message = msg
                break

        if not target_message:
            return "No messages requiring response"

        # Analyze message
        analysis = self._analyze_message(target_message)

        # Update message metadata
        target_message.message_type = analysis["type"]
        target_message.priority = analysis["priority"]

        # Add to context
        thread_id = self.context_manager.add_message_to_conversation(target_message)

        # Extract action items
        action_items = self.info_extractor.extract_action_items(
            target_message.content, target_message.id
        )
        for action in action_items:
            self.context_manager.add_action_item(thread_id, action.description)

        # Determine response strategy
        response_strategy = self._determine_response_strategy(target_message)

        if response_strategy == "respond":
            draft = await self._draft_response(target_message)
            self.drafts[draft.id] = draft

            # Check if approval is needed
            assessment = self.approval_workflow.assess_draft(draft)
            if assessment["requires_approval"]:
                self.approval_workflow.submit_for_approval(draft)

        elif response_strategy == "escalate":
            reason = analysis.get("escalation_reason", "Requires user attention")
            self.escalation_manager.escalate(
                item_id=target_message.id,
                item_type="message",
                reason=reason,
                priority=target_message.priority,
            )

        summary = f"""Processed message from {target_message.sender}:
- Platform: {target_message.platform.value}
- Channel: {target_message.channel}
- Type: {target_message.message_type.value}
- Priority: {target_message.priority.value}
- Strategy: {response_strategy}"""

        self.update_memory("assistant", summary)
        return summary

    def _analyze_message(self, message: Message) -> Dict:
        """Analyze message for type and priority."""
        # Check if should escalate
        should_escalate, reason, priority = self.escalation_manager.should_escalate_message(
            message
        )

        # Determine message type
        msg_type = self._determine_message_type(message)

        # Determine priority
        if not should_escalate:
            priority = self._prioritize_message(message)

        analysis = {
            "type": msg_type,
            "priority": priority,
            "should_escalate": should_escalate,
        }

        if should_escalate:
            analysis["escalation_reason"] = reason

        return analysis

    def _determine_message_type(self, message: Message) -> MessageType:
        """Determine type of message."""
        content_lower = message.content.lower()

        # Check for question
        if content_lower.endswith("?") or any(
            q in content_lower for q in ["what", "why", "how", "when", "where", "who"]
        ):
            return MessageType.QUESTION

        # Check for announcement
        if any(word in content_lower for word in ["announcement", "attention all", "fyi"]):
            return MessageType.ANNOUNCEMENT

        # Check for urgent
        if any(
            word in content_lower
            for word in ["urgent", "asap", "emergency", "critical", "immediately"]
        ):
            return MessageType.URGENT

        # Check for action required
        if any(
            phrase in content_lower
            for phrase in ["please", "can you", "could you", "need your help", "action required"]
        ):
            return MessageType.ACTION_REQUIRED

        # Default to social
        return MessageType.SOCIAL

    def _prioritize_message(self, message: Message) -> PriorityLevel:
        """Determine priority of message."""
        content_lower = message.content.lower()

        # Urgent takes highest priority
        if any(word in content_lower for word in ["emergency", "critical", "outage"]):
            return PriorityLevel.URGENT

        # Check for important markers
        if any(word in content_lower for word in ["important", "must", "required", "asap"]):
            return PriorityLevel.HIGH

        # Mentions are always important
        if message.is_mentioned:
            return PriorityLevel.HIGH

        return PriorityLevel.NORMAL

    def _determine_response_strategy(self, message: Message) -> str:
        """Determine how to respond to message.

        Returns:
            Strategy: 'respond', 'escalate', 'archive', 'flag'
        """
        # Don't respond to announcements or FYI
        if message.message_type == MessageType.ANNOUNCEMENT:
            return "archive"

        # Always escalate urgent messages
        if message.priority == PriorityLevel.URGENT:
            return "escalate"

        # Check platform settings
        platform = message.platform.value
        if platform in self.platform_settings:
            if not self.platform_settings[platform].get("auto_respond", True):
                if message.requires_action:
                    return "escalate"
                return "archive"

        # Respond to questions and action items
        if message.message_type in [
            MessageType.QUESTION,
            MessageType.ACTION_REQUIRED,
        ] or message.requires_action:
            return "respond"

        # Flag for review
        if message.priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]:
            return "escalate"

        return "archive"

    async def _draft_response(self, message: Message) -> DraftMessage:
        """Draft a response to a message."""
        # Prepare context
        context = f"""Message from {message.sender} in {message.channel}:
{message.content}

---

Draft a concise response that:
1. Directly addresses the question or request
2. Maintains professional yet friendly tone
3. Is brief (1-2 sentences)
4. Includes any necessary information"""

        self.update_memory("user", context)

        try:
            response = await self.llm.ask(
                messages=self.messages,  # This uses self.messages from ToolCallAgent
                system_msgs=[SchemaMessage.system_message(SYSTEM_PROMPT)],
                max_tokens=200,
            )
        except Exception as e:
            logger.error(f"Error drafting message response: {e}")
            response = "Thanks for reaching out, I'll get back to you!"

        draft = DraftMessage(
            id=f"draft_{message.id}",
            communication_type=message.platform,
            recipient=message.sender,
            body=response,
            confidence_score=0.8,
        )

        return draft

    async def _handle_pending_approvals(self, pending_drafts: List[DraftMessage]) -> str:
        """Handle pending drafts awaiting approval."""
        if not pending_drafts:
            return "No pending approvals"

        draft = pending_drafts[0]
        summary = f"""Draft message awaiting approval:
To: {draft.recipient}
Platform: {draft.communication_type.value}

{draft.body}"""

        self.update_memory("assistant", summary)
        return summary

    async def _handle_escalations(self, escalations: List[Dict]) -> str:
        """Handle escalated messages."""
        if not escalations:
            return "No escalations"

        escalation = escalations[0]
        summary = f"""Message requires attention:
From: {escalation['data'].get('sender', 'unknown')}
Reason: {escalation['reason']}
Priority: {escalation['priority'].value}"""

        self.update_memory("assistant", summary)
        return summary

    def get_message_summary(self) -> str:
        """Get summary of message processing."""
        total_messages = len(self.stored_messages)

        # Count by platform
        platform_counts = {}
        type_counts = {}
        priority_counts = {}

        for msg in self.stored_messages.values():
            platform = msg.platform.value
            msg_type = msg.message_type.value
            priority = msg.priority.value

            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        summary = f"""Message Summary:
- Total: {total_messages}
- Platforms: {platform_counts}
- Types: {type_counts}
- Priorities: {priority_counts}
- Pending drafts: {len(self.approval_workflow.get_pending_approvals())}
- Escalations: {len(self.escalation_manager.get_pending_escalations())}"""

        return summary
