"""Approval workflow for communications before sending."""

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.agent.models.communication import (
    ApprovalStatus,
    CommunicationAuditLog,
    CommunicationType,
    DraftMessage,
)
from app.logger import logger


class ApprovalWorkflow(BaseModel):
    """Manages approval workflow for communications."""

    pending_drafts: Dict[str, DraftMessage] = Field(
        default_factory=dict, description="Drafts awaiting approval"
    )
    audit_log: List[CommunicationAuditLog] = Field(
        default_factory=list, description="Audit trail of all communications"
    )

    class Config:
        arbitrary_types_allowed = True

    def should_require_approval(
        self, draft: DraftMessage, user_preferences: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """Determine if draft requires approval before sending.

        Args:
            draft: Draft message to assess
            user_preferences: Optional user preferences

        Returns:
            Tuple of (requires_approval, reason)
        """
        reasons = []

        # Always require approval for important/sensitive communications
        if draft.communication_type in [
            CommunicationType.EMAIL,
            CommunicationType.LINKEDIN,
        ]:
            # Check for commitments
            commitment_phrases = [
                "i'll",
                "i will",
                "we'll",
                "we will",
                "can do",
                "will complete",
                "will provide",
                "promise",
                "guarantee",
            ]
            if any(phrase in draft.body.lower() for phrase in commitment_phrases):
                reasons.append("Contains commitment/promise")

            # Check for apologies or bad news
            sensitive_phrases = [
                "apologize",
                "sorry",
                "unfortunately",
                "regret",
                "decline",
                "unable",
                "can't",
                "cannot",
            ]
            if any(phrase in draft.body.lower() for phrase in sensitive_phrases):
                reasons.append("Contains sensitive content (apology/bad news)")

        # Check confidence score
        if draft.confidence_score < 0.7:
            reasons.append(f"Low confidence score ({draft.confidence_score:.0%})")

        # Check for uncertain tone
        uncertain_phrases = ["maybe", "perhaps", "possibly", "might", "could", "?"]
        uncertain_count = sum(1 for phrase in uncertain_phrases if phrase in draft.body.lower())
        if uncertain_count > 2:
            reasons.append("Uncertain tone detected")

        # Check custom preferences
        if user_preferences and user_preferences.get("always_approve_important"):
            if draft.communication_type in user_preferences.get("important_types", []):
                reasons.append("Important communication type (per preferences)")

        requires_approval = len(reasons) > 0 or draft.requires_approval
        reason = "; ".join(reasons) if reasons else "Standard workflow"

        return requires_approval, reason

    def categorize_for_workflow(self, draft: DraftMessage) -> str:
        """Categorize draft into workflow category.

        Args:
            draft: Draft to categorize

        Returns:
            Workflow category (important, routine, uncertain, escalate)
        """
        lower_body = draft.body.lower()

        # Check for escalation triggers
        escalation_triggers = [
            "emergency",
            "critical",
            "urgent",
            "immediate",
            "legal",
            "sensitive",
        ]
        if any(trigger in lower_body for trigger in escalation_triggers):
            return "escalate"

        # Check for commitments (important)
        commitment_phrases = [
            "i'll",
            "i will",
            "we'll",
            "we will",
            "can do",
            "will complete",
        ]
        if any(phrase in lower_body for phrase in commitment_phrases):
            return "important"

        # Check for uncertain tone
        uncertain_phrases = ["maybe", "perhaps", "possibly", "might", "could"]
        uncertain_count = sum(1 for phrase in uncertain_phrases if phrase in lower_body)
        if uncertain_count > 1:
            return "uncertain"

        # Default to routine
        return "routine"

    def assess_draft(
        self, draft: DraftMessage, user_preferences: Optional[Dict] = None
    ) -> Dict:
        """Comprehensively assess a draft message.

        Args:
            draft: Draft to assess
            user_preferences: Optional user preferences

        Returns:
            Assessment with recommendations
        """
        requires_approval, reason = self.should_require_approval(draft, user_preferences)
        category = self.categorize_for_workflow(draft)

        # Generate recommendation
        recommendations = []
        if draft.confidence_score < 0.5:
            recommendations.append("Consider rewriting - low confidence")
        if len(draft.body) > 500:
            recommendations.append("Consider shortening message")
        if "???" in draft.body or "!!!" in draft.body:
            recommendations.append("Consider reducing punctuation emphasis")

        assessment = {
            "draft_id": draft.id,
            "requires_approval": requires_approval,
            "reason": reason,
            "category": category,
            "confidence_score": draft.confidence_score,
            "recommendations": recommendations,
            "suggested_action": "approve" if not requires_approval else "review",
        }

        logger.info(f"✓ Assessed draft {draft.id}: {category} - {reason}")
        return assessment

    def submit_for_approval(self, draft: DraftMessage) -> None:
        """Submit draft for user approval.

        Args:
            draft: Draft to submit
        """
        draft.status = ApprovalStatus.PENDING_APPROVAL
        self.pending_drafts[draft.id] = draft
        logger.info(f"✓ Submitted draft {draft.id} for approval")

    def approve_draft(self, draft_id: str, approved_by: str = "user") -> bool:
        """Approve a draft for sending.

        Args:
            draft_id: ID of draft to approve
            approved_by: Who approved it

        Returns:
            Success status
        """
        if draft_id not in self.pending_drafts:
            logger.warning(f"Draft {draft_id} not found in pending")
            return False

        draft = self.pending_drafts[draft_id]
        draft.status = ApprovalStatus.APPROVED

        # Log to audit trail
        self.audit_log.append(
            CommunicationAuditLog(
                id=f"log_{draft_id}_approve",
                action="approve",
                communication_type=draft.communication_type,
                recipient=draft.recipient,
                content_preview=draft.body[:200],
                status="approved",
                approved_by=approved_by,
            )
        )

        logger.info(f"✓ Draft {draft_id} approved by {approved_by}")
        return True

    def reject_draft(self, draft_id: str, reason: str = "", rejected_by: str = "user") -> bool:
        """Reject a draft from sending.

        Args:
            draft_id: ID of draft to reject
            reason: Reason for rejection
            rejected_by: Who rejected it

        Returns:
            Success status
        """
        if draft_id not in self.pending_drafts:
            logger.warning(f"Draft {draft_id} not found in pending")
            return False

        draft = self.pending_drafts[draft_id]
        draft.status = ApprovalStatus.REJECTED

        # Log to audit trail
        self.audit_log.append(
            CommunicationAuditLog(
                id=f"log_{draft_id}_reject",
                action="reject",
                communication_type=draft.communication_type,
                recipient=draft.recipient,
                content_preview=draft.body[:200],
                status="rejected",
                reason=reason,
                approved_by=rejected_by,
            )
        )

        logger.info(f"✓ Draft {draft_id} rejected by {rejected_by}. Reason: {reason}")
        return True

    def mark_sent(self, draft_id: str) -> bool:
        """Mark draft as sent.

        Args:
            draft_id: ID of draft to mark as sent

        Returns:
            Success status
        """
        if draft_id not in self.pending_drafts:
            logger.warning(f"Draft {draft_id} not found in pending")
            return False

        draft = self.pending_drafts[draft_id]
        draft.status = ApprovalStatus.SENT

        # Log to audit trail
        self.audit_log.append(
            CommunicationAuditLog(
                id=f"log_{draft_id}_sent",
                action="send",
                communication_type=draft.communication_type,
                recipient=draft.recipient,
                content_preview=draft.body[:200],
                status="sent",
            )
        )

        logger.info(f"✓ Draft {draft_id} marked as sent")
        return True

    def get_pending_approvals(self) -> List[DraftMessage]:
        """Get all drafts pending approval.

        Returns:
            List of pending drafts
        """
        return [
            draft
            for draft in self.pending_drafts.values()
            if draft.status == ApprovalStatus.PENDING_APPROVAL
        ]

    def get_audit_trail(self, draft_id: str = "", limit: int = 10) -> List[CommunicationAuditLog]:
        """Get audit trail for communications.

        Args:
            draft_id: Optional draft ID to filter by
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        if draft_id:
            logs = [log for log in self.audit_log if draft_id in log.id]
        else:
            logs = self.audit_log

        return sorted(
            logs, key=lambda log: log.timestamp, reverse=True
        )[:limit]

    def get_auto_send_candidates(self) -> List[DraftMessage]:
        """Get drafts that can be auto-sent (routine responses).

        Returns:
            List of drafts safe to auto-send
        """
        candidates = []
        for draft in self.pending_drafts.values():
            # Routine messages with high confidence can be auto-sent
            if (
                draft.status == ApprovalStatus.DRAFT
                and self.categorize_for_workflow(draft) == "routine"
                and draft.confidence_score >= 0.8
            ):
                candidates.append(draft)

        return candidates
