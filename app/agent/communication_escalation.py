"""Escalation and human-in-loop management for communications."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.agent.models.communication import (
    CommunicationType,
    DraftMessage,
    Email,
    Message,
    PriorityLevel,
)
from app.logger import logger


class EscalationRule(BaseModel):
    """Rule for escalating communications."""

    name: str = Field(..., description="Rule name")
    trigger_keywords: List[str] = Field(..., description="Keywords that trigger escalation")
    priority: PriorityLevel = Field(default=PriorityLevel.HIGH, description="Escalation priority")
    reason: str = Field(..., description="Reason for escalation")
    requires_immediate_review: bool = Field(
        default=True, description="Requires immediate user review"
    )


class EscalationManager(BaseModel):
    """Manages escalation of communications."""

    escalation_rules: Dict[str, EscalationRule] = Field(
        default_factory=dict, description="Defined escalation rules"
    )
    escalated_items: Dict[str, Dict] = Field(
        default_factory=dict, description="Escalated communications"
    )
    resolution_queue: List[str] = Field(
        default_factory=list, description="Queue of unresolved escalations"
    )

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Initialize escalation manager with default rules."""
        super().__init__(**data)
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Set up default escalation rules."""
        default_rules = [
            EscalationRule(
                name="urgent_request",
                trigger_keywords=["urgent", "asap", "emergency", "immediately"],
                priority=PriorityLevel.URGENT,
                reason="Urgent request requires immediate attention",
                requires_immediate_review=True,
            ),
            EscalationRule(
                name="commitment",
                trigger_keywords=["i'll", "i will", "we will", "can do", "will complete", "promise"],
                priority=PriorityLevel.HIGH,
                reason="Contains commitment - requires approval before sending",
                requires_immediate_review=True,
            ),
            EscalationRule(
                name="sensitive_topic",
                trigger_keywords=["apology", "sorry", "unfortunately", "regret", "decline"],
                priority=PriorityLevel.HIGH,
                reason="Sensitive topic requires review",
                requires_immediate_review=True,
            ),
            EscalationRule(
                name="financial",
                trigger_keywords=["payment", "invoice", "budget", "expense", "cost", "price"],
                priority=PriorityLevel.HIGH,
                reason="Financial communication requires review",
                requires_immediate_review=False,
            ),
            EscalationRule(
                name="legal",
                trigger_keywords=["legal", "contract", "agreement", "liability", "lawsuit"],
                priority=PriorityLevel.CRITICAL,
                reason="Legal matter - critical escalation",
                requires_immediate_review=True,
            ),
        ]

        for rule in default_rules:
            self.escalation_rules[rule.name] = rule

    def add_escalation_rule(self, rule: EscalationRule) -> None:
        """Add custom escalation rule.

        Args:
            rule: Escalation rule to add
        """
        self.escalation_rules[rule.name] = rule
        logger.info(f"✓ Added escalation rule: {rule.name}")

    def should_escalate_email(self, email: Email) -> Tuple[bool, str, PriorityLevel]:
        """Determine if email should be escalated.

        Args:
            email: Email to assess

        Returns:
            Tuple of (should_escalate, reason, priority)
        """
        full_text = f"{email.subject} {email.body}".lower()

        for rule in self.escalation_rules.values():
            if any(keyword in full_text for keyword in rule.trigger_keywords):
                return True, rule.reason, rule.priority

        # Check for suspicious patterns
        if self._is_suspicious_content(full_text):
            return True, "Suspicious content patterns detected", PriorityLevel.HIGH

        # Check sender reputation
        if self._is_suspicious_sender(email.from_email):
            return True, "Suspicious sender address", PriorityLevel.URGENT

        return False, "", email.priority

    def should_escalate_message(self, message: Message) -> Tuple[bool, str, PriorityLevel]:
        """Determine if message should be escalated.

        Args:
            message: Message to assess

        Returns:
            Tuple of (should_escalate, reason, priority)
        """
        full_text = f"{message.content}".lower()

        for rule in self.escalation_rules.values():
            if any(keyword in full_text for keyword in rule.trigger_keywords):
                return True, rule.reason, rule.priority

        # Check if user is being attacked or harassed
        if self._is_harassment_content(full_text):
            return True, "Potential harassment detected", PriorityLevel.CRITICAL

        # Check for misinformation
        if self._is_misinformation(full_text):
            return True, "Potential misinformation requires review", PriorityLevel.HIGH

        return False, "", message.priority

    def should_escalate_draft(self, draft: DraftMessage) -> Tuple[bool, str]:
        """Determine if draft should be escalated.

        Args:
            draft: Draft to assess

        Returns:
            Tuple of (should_escalate, reason)
        """
        full_text = f"{draft.subject or ''} {draft.body}".lower()

        # Check against rules
        for rule in self.escalation_rules.values():
            if any(keyword in full_text for keyword in rule.trigger_keywords):
                if rule.requires_immediate_review:
                    return True, rule.reason

        # Check for tone issues
        if self._has_harsh_tone(draft.body):
            return True, "Tone might be too harsh - review before sending"

        # Check for unclear meaning
        if self._has_unclear_meaning(draft.body):
            return True, "Meaning is unclear - review for clarity"

        return False, ""

    def escalate(
        self,
        item_id: str,
        item_type: str,
        reason: str,
        priority: PriorityLevel = PriorityLevel.HIGH,
        data: Optional[Dict] = None,
    ) -> None:
        """Escalate an item for user review.

        Args:
            item_id: ID of item to escalate
            item_type: Type of item (email, message, draft, etc.)
            reason: Reason for escalation
            priority: Priority level
            data: Optional additional data
        """
        self.escalated_items[item_id] = {
            "id": item_id,
            "type": item_type,
            "reason": reason,
            "priority": priority,
            "timestamp": datetime.now(),
            "data": data or {},
            "resolved": False,
        }
        self.resolution_queue.append(item_id)
        logger.warning(f"⚠️  Escalated {item_type} {item_id}: {reason} (Priority: {priority.value})")

    def resolve_escalation(self, item_id: str, action: str = "reviewed") -> bool:
        """Mark escalation as resolved.

        Args:
            item_id: ID of escalated item
            action: Action taken (reviewed, approved, rejected, etc.)

        Returns:
            Success status
        """
        if item_id not in self.escalated_items:
            logger.warning(f"Escalation {item_id} not found")
            return False

        self.escalated_items[item_id]["resolved"] = True
        self.escalated_items[item_id]["action"] = action
        self.escalated_items[item_id]["resolved_at"] = datetime.now()

        if item_id in self.resolution_queue:
            self.resolution_queue.remove(item_id)

        logger.info(f"✓ Resolved escalation {item_id} with action: {action}")
        return True

    def get_pending_escalations(self) -> List[Dict]:
        """Get all pending escalations.

        Returns:
            List of unresolved escalations, sorted by priority
        """
        pending = [
            item
            for item in self.escalated_items.values()
            if not item.get("resolved", False)
        ]

        # Sort by priority
        priority_order = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.URGENT: 1,
            PriorityLevel.HIGH: 2,
            PriorityLevel.NORMAL: 3,
            PriorityLevel.LOW: 4,
        }

        return sorted(
            pending,
            key=lambda x: priority_order.get(x["priority"], 5),
        )

    def _is_suspicious_content(self, text: str) -> bool:
        """Check for suspicious content patterns."""
        suspicious_patterns = [
            "click here",
            "verify account",
            "confirm password",
            "urgent action required",
            "limited time",
            "act now",
        ]
        return any(pattern in text for pattern in suspicious_patterns)

    def _is_suspicious_sender(self, sender: str) -> bool:
        """Check if sender address is suspicious."""
        # Check for spoofed addresses
        if "@" not in sender:
            return True

        domain = sender.split("@")[1]

        # Check for suspicious domains
        suspicious_domains = [
            "mail.com",
            "email.com",
            "verify",
            "support-verify",
            "account-verify",
        ]
        return any(sus_domain in domain for sus_domain in suspicious_domains)

    def _is_harassment_content(self, text: str) -> bool:
        """Check for harassment or abuse content."""
        harassment_indicators = [
            "i'll hurt",
            "you're stupid",
            "you suck",
            "go kill yourself",
            "you deserve",
        ]
        return any(indicator in text for indicator in harassment_indicators)

    def _is_misinformation(self, text: str) -> bool:
        """Check for potential misinformation."""
        # Simple heuristic - claims without evidence
        if text.count("?") > 3 and text.count("!") > 2:
            return True
        return False

    def _has_harsh_tone(self, text: str) -> bool:
        """Check if text has harsh tone."""
        harsh_phrases = [
            "you're wrong",
            "that's stupid",
            "obviously",
            "clearly",
            "pathetic",
            "disgusting",
        ]
        return any(phrase in text.lower() for phrase in harsh_phrases)

    def _has_unclear_meaning(self, text: str) -> bool:
        """Check if text meaning is unclear."""
        # Too many pronouns without clear antecedents, cryptic language
        if text.count("it") > 5 or text.count("that") > 5:
            if len(text.split()) < 20:  # Short text with many pronouns
                return True

        return False

    def get_escalation_summary(self) -> Dict:
        """Get summary of escalations.

        Returns:
            Summary of escalation status
        """
        pending = self.get_pending_escalations()

        priority_counts = {priority.value: 0 for priority in PriorityLevel}
        type_counts: Dict[str, int] = {}

        for item in pending:
            priority_counts[item["priority"].value] += 1
            item_type = item["type"]
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

        return {
            "total_pending": len(pending),
            "by_priority": priority_counts,
            "by_type": type_counts,
            "oldest_escalation": (
                pending[-1].get("timestamp") if pending else None
            ),
        }
