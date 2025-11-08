"""Context awareness for communication threads and conversations."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent.models.communication import ConversationContext, Email, Message
from app.logger import logger


class ConversationThreadManager(BaseModel):
    """Manages context for conversations and email threads.
    
    Note: Renamed from ContextManager to avoid conflict with LLM's ContextManager
    in app.llm.context_manager (which manages token/context windows).
    
    For backward compatibility, ContextManager is aliased to this class.
    """

    contexts: Dict[str, ConversationContext] = Field(
        default_factory=dict, description="Active conversation contexts"
    )
    email_threads: Dict[str, List[Email]] = Field(
        default_factory=dict, description="Email threads by thread ID"
    )
    message_conversations: Dict[str, List[Message]] = Field(
        default_factory=dict, description="Message conversations by thread ID"
    )

    class Config:
        arbitrary_types_allowed = True

    def add_email_to_thread(self, email: Email) -> str:
        """Add email to conversation thread.

        Args:
            email: Email to add

        Returns:
            Thread ID
        """
        thread_id = email.thread_id or f"email_thread_{email.id[:8]}"

        if thread_id not in self.email_threads:
            self.email_threads[thread_id] = []

        self.email_threads[thread_id].append(email)

        # Update or create context
        if thread_id not in self.contexts:
            self.contexts[thread_id] = ConversationContext(
                thread_id=thread_id,
                subject=email.subject,
                participants=[email.from_email] + email.to_emails,
                messages=[email.id],
            )
        else:
            if email.id not in self.contexts[thread_id].messages:
                self.contexts[thread_id].messages.append(email.id)
            # Update participants
            for recipient in email.to_emails:
                if recipient not in self.contexts[thread_id].participants:
                    self.contexts[thread_id].participants.append(recipient)

        logger.info(f"✓ Added email {email.id} to thread {thread_id}")
        return thread_id

    def add_message_to_conversation(self, message: Message) -> str:
        """Add message to conversation thread.

        Args:
            message: Message to add

        Returns:
            Thread ID
        """
        thread_id = message.thread_id or f"msg_thread_{message.id[:8]}"

        if thread_id not in self.message_conversations:
            self.message_conversations[thread_id] = []

        self.message_conversations[thread_id].append(message)

        # Update or create context
        if thread_id not in self.contexts:
            self.contexts[thread_id] = ConversationContext(
                thread_id=thread_id,
                subject=f"{message.platform} - {message.channel}",
                participants=[message.sender],
                messages=[message.id],
            )
        else:
            if message.id not in self.contexts[thread_id].messages:
                self.contexts[thread_id].messages.append(message.id)
            if message.sender not in self.contexts[thread_id].participants:
                self.contexts[thread_id].participants.append(message.sender)

        logger.info(f"✓ Added message {message.id} to thread {thread_id}")
        return thread_id

    def get_thread_context(self, thread_id: str) -> Optional[ConversationContext]:
        """Get context for a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Thread context or None
        """
        return self.contexts.get(thread_id)

    def get_email_thread(self, thread_id: str) -> List[Email]:
        """Get all emails in a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            List of emails in thread (chronological order)
        """
        emails = self.email_threads.get(thread_id, [])
        return sorted(emails, key=lambda e: e.timestamp)

    def get_message_conversation(self, thread_id: str) -> List[Message]:
        """Get all messages in a conversation.

        Args:
            thread_id: Thread identifier

        Returns:
            List of messages in conversation (chronological order)
        """
        messages = self.message_conversations.get(thread_id, [])
        return sorted(messages, key=lambda m: m.timestamp)

    def get_thread_summary(self, thread_id: str) -> str:
        """Get summary of thread context.

        Args:
            thread_id: Thread identifier

        Returns:
            Formatted summary of thread
        """
        context = self.get_thread_context(thread_id)
        if not context:
            return f"No context found for thread {thread_id}"

        summary = f"""Thread Context: {context.subject}
- Participants: {', '.join(context.participants)}
- Status: {context.status}
- Messages: {len(context.messages)}
"""

        if context.action_items:
            summary += f"- Action Items: {len(context.action_items)}\n"
            for action in context.action_items[:3]:
                summary += f"  • {action}\n"

        if context.decisions_made:
            summary += f"- Decisions Made: {len(context.decisions_made)}\n"
            for decision in context.decisions_made[:2]:
                summary += f"  • {decision}\n"

        if context.important_dates:
            summary += "- Important Dates:\n"
            for date in context.important_dates[:3]:
                summary += f"  • {date.strftime('%Y-%m-%d')}\n"

        return summary

    def add_action_item(self, thread_id: str, action: str) -> None:
        """Add action item to thread context.

        Args:
            thread_id: Thread identifier
            action: Action item description
        """
        if thread_id in self.contexts:
            if action not in self.contexts[thread_id].action_items:
                self.contexts[thread_id].action_items.append(action)
                logger.info(f"✓ Added action item to thread {thread_id}")

    def add_decision(self, thread_id: str, decision: str) -> None:
        """Add decision made to thread context.

        Args:
            thread_id: Thread identifier
            decision: Decision description
        """
        if thread_id in self.contexts:
            if decision not in self.contexts[thread_id].decisions_made:
                self.contexts[thread_id].decisions_made.append(decision)
                logger.info(f"✓ Added decision to thread {thread_id}")

    def resolve_thread(self, thread_id: str, reason: str = "") -> None:
        """Mark thread as resolved.

        Args:
            thread_id: Thread identifier
            reason: Reason for resolution
        """
        if thread_id in self.contexts:
            self.contexts[thread_id].status = "resolved"
            logger.info(f"✓ Marked thread {thread_id} as resolved. Reason: {reason}")

    def get_unresolved_threads(self) -> List[ConversationContext]:
        """Get all unresolved conversation threads.

        Returns:
            List of unresolved contexts
        """
        return [
            context
            for context in self.contexts.values()
            if context.status == "active"
        ]

    def get_pending_actions(self) -> Dict[str, List[str]]:
        """Get all pending action items by thread.

        Returns:
            Dictionary of thread_id -> action items
        """
        pending = {}
        for thread_id, context in self.contexts.items():
            if context.action_items and context.status == "active":
                pending[thread_id] = context.action_items

        return pending

    def get_related_threads(self, thread_id: str, topic: str = "") -> List[str]:
        """Get threads related to the given thread.

        Args:
            thread_id: Thread identifier
            topic: Optional topic to match

        Returns:
            List of related thread IDs
        """
        related = []
        source_context = self.get_thread_context(thread_id)

        if not source_context:
            return related

        # Find threads with common participants
        for other_id, context in self.contexts.items():
            if other_id == thread_id:
                continue

            # Check for common participants
            common = set(source_context.participants) & set(context.participants)
            if common:
                related.append(other_id)

        return related[:5]  # Return top 5 related threads

    def export_contexts(self) -> Dict:
        """Export all contexts for analysis/reporting.

        Returns:
            Dictionary of all contexts
        """
        return {
            tid: {
                "subject": ctx.subject,
                "participants": ctx.participants,
                "status": ctx.status,
                "action_items": ctx.action_items,
                "decisions": ctx.decisions_made,
                "message_count": len(ctx.messages),
            }
            for tid, ctx in self.contexts.items()
        }


# Backward compatibility alias
ContextManager = ConversationThreadManager
