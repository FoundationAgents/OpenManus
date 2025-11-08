"""Social media agent for managing LinkedIn, Twitter, GitHub, and other social platforms."""

from typing import Dict, List, Optional

from pydantic import Field

from app.agent.approval_workflow import ApprovalWorkflow
from app.agent.communication_context import ContextManager
from app.agent.communication_escalation import EscalationManager
from app.agent.info_extraction import InformationExtractor
from app.agent.models.communication import CommunicationType, DraftMessage, SocialPost
from app.agent.toolcall import ToolCallAgent
from app.agent.voice_model import VoiceModel
from app.config import config
from app.logger import logger
from app.prompt.communication import SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection


class SocialMediaAgent(ToolCallAgent):
    """Agent for managing social media interactions and engagement."""

    name: str = "SocialMediaAgent"
    description: str = (
        "An intelligent social media agent that monitors mentions, responds to engagement, "
        "and manages posts across LinkedIn, Twitter, GitHub, and other social platforms"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "Process the next social media interaction or engagement."

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

    # Social posts and engagement
    posts: Dict[str, SocialPost] = Field(default_factory=dict, description="Social posts")
    drafts: Dict[str, DraftMessage] = Field(default_factory=dict, description="Draft posts/responses")

    # Platform settings
    platform_settings: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "linkedin": {
                "tone": "professional",
                "auto_engage": True,
                "response_threshold": 50,
            },
            "twitter": {
                "tone": "casual",
                "auto_engage": False,
                "response_threshold": 100,
            },
            "github": {
                "tone": "technical",
                "auto_engage": True,
                "response_threshold": 10,
            },
        },
        description="Settings per social platform",
    )

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    class Config:
        arbitrary_types_allowed = True

    async def step(self) -> str:
        """Execute a single step in social media management workflow."""
        try:
            # Check for pending escalations
            pending_escalations = self.escalation_manager.get_pending_escalations()
            if pending_escalations:
                return await self._handle_escalations(pending_escalations)

            # Check for pending approvals
            pending_approvals = self.approval_workflow.get_pending_approvals()
            if pending_approvals:
                return await self._handle_pending_approvals(pending_approvals)

            # Process new posts/mentions
            if self.posts:
                return await self._process_next_post()

            return "All social media interactions processed"

        except Exception as e:
            logger.error(f"Error in social media agent step: {e}")
            self.update_memory("assistant", f"Error occurred: {str(e)}")
            return f"Error: {str(e)}"

    async def _process_next_post(self) -> str:
        """Process the next post or mention."""
        # Find post requiring engagement
        target_post = None
        for post in self.posts.values():
            if post.engagement_count > 0:  # Has engagement
                target_post = post
                break

        if not target_post:
            return "No posts with engagement to process"

        # Analyze post
        analysis = self._analyze_post(target_post)

        # Extract relevant info
        action_items = self.info_extractor.extract_action_items(
            target_post.content, target_post.id
        )

        # Determine engagement strategy
        strategy = self._determine_engagement_strategy(target_post, analysis)

        if strategy == "respond":
            # Draft response
            draft = await self._draft_engagement(target_post)
            self.drafts[draft.id] = draft

            # Assess for approval
            assessment = self.approval_workflow.assess_draft(draft)
            if assessment["requires_approval"]:
                self.approval_workflow.submit_for_approval(draft)
                return f"Post engagement drafted and submitted for approval: {target_post.platform.value}"

        elif strategy == "escalate":
            self.escalation_manager.escalate(
                item_id=target_post.id,
                item_type="social_post",
                reason=analysis.get("escalation_reason", "Requires user attention"),
                priority=analysis.get("priority"),
            )

        summary = f"""Processed social media engagement:
- Platform: {target_post.platform.value}
- Author: {target_post.author}
- Engagement: {target_post.engagement_count}
- Strategy: {strategy}
- Action Items: {len(action_items)}"""

        self.update_memory("assistant", summary)
        return summary

    def _analyze_post(self, post: SocialPost) -> Dict:
        """Analyze social post for engagement type."""
        # Determine if it's positive/negative/neutral sentiment
        sentiment = self.info_extractor.detect_sentiment(post.content)

        # Check if urgent
        is_urgent = self.info_extractor.detect_urgency(post.content)

        # Check for escalation triggers
        should_escalate, reason, priority = self.escalation_manager.should_escalate_message(
            # Convert to Message for escalation check
            __class__.PostAdapter(post)  # type: ignore
        )

        analysis = {
            "sentiment": sentiment,
            "is_urgent": is_urgent,
            "should_escalate": should_escalate,
            "platform_tone": self._get_platform_tone(post.platform),
        }

        if should_escalate:
            analysis["escalation_reason"] = reason
            analysis["priority"] = priority

        return analysis

    def _determine_engagement_strategy(self, post: SocialPost, analysis: Dict) -> str:
        """Determine how to engage with post.

        Returns:
            Strategy: 'respond', 'like', 'escalate', 'ignore'
        """
        # Always escalate if needed
        if analysis.get("should_escalate"):
            return "escalate"

        # Check platform settings
        platform = post.platform.value
        settings = self.platform_settings.get(platform, {})

        if not settings.get("auto_engage", True):
            return "like"  # Just engage with like

        # Respond if engagement is significant
        threshold = settings.get("response_threshold", 50)
        if post.engagement_count >= threshold:
            return "respond"

        # Respond if sentiment is negative (need to address concerns)
        if analysis.get("sentiment") == "negative":
            return "respond"

        # Positive sentiment or low engagement
        return "like"

    async def _draft_engagement(self, post: SocialPost) -> DraftMessage:
        """Draft engagement response to social post."""
        platform = post.platform.value
        tone = self.platform_settings.get(platform, {}).get("tone", "professional")

        context = f"""Social media post on {platform}:
Author: {post.author}
Content: {post.content}

---

Draft a brief, engaging response that:
1. Is appropriate for {platform}
2. Maintains {tone} tone
3. Adds value to the conversation
4. Is concise (1-3 sentences)"""

        self.update_memory("user", context)

        try:
            response = await self.llm.ask(
                messages=self.messages,
                system_msgs=[Message.system_message(SYSTEM_PROMPT)],
                max_tokens=150,
            )
        except Exception as e:
            logger.error(f"Error drafting social engagement: {e}")
            response = "Great post! Appreciate you sharing this."

        draft = DraftMessage(
            id=f"draft_{post.id}",
            communication_type=post.platform,
            recipient=post.author,
            body=response,
            confidence_score=0.85,
        )

        return draft

    def _get_platform_tone(self, platform: CommunicationType) -> str:
        """Get appropriate tone for platform."""
        tones = {
            CommunicationType.LINKEDIN: "professional",
            CommunicationType.TWITTER: "casual",
            CommunicationType.GITHUB: "technical",
        }
        return tones.get(platform, "professional")

    async def _handle_pending_approvals(self, pending_drafts: List[DraftMessage]) -> str:
        """Handle pending engagement drafts."""
        if not pending_drafts:
            return "No pending approvals"

        draft = pending_drafts[0]
        summary = f"""Draft engagement awaiting approval:
Platform: {draft.communication_type.value}
Recipient: {draft.recipient}

{draft.body}"""

        self.update_memory("assistant", summary)
        return summary

    async def _handle_escalations(self, escalations: List[Dict]) -> str:
        """Handle escalated social media items."""
        if not escalations:
            return "No escalations"

        escalation = escalations[0]
        summary = f"""Social media engagement requires attention:
Type: {escalation['type']}
Reason: {escalation['reason']}
Priority: {escalation['priority'].value}"""

        self.update_memory("assistant", summary)
        return summary

    def get_social_summary(self) -> str:
        """Get summary of social media engagement."""
        total_posts = len(self.posts)

        # Count by platform
        platform_counts = {}
        engagement_total = 0

        for post in self.posts.values():
            platform = post.platform.value
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            engagement_total += post.engagement_count

        summary = f"""Social Media Summary:
- Total Posts: {total_posts}
- Platforms: {platform_counts}
- Total Engagement: {engagement_total}
- Pending drafts: {len(self.approval_workflow.get_pending_approvals())}
- Escalations: {len(self.escalation_manager.get_pending_escalations())}"""

        return summary

    class PostAdapter:
        """Adapter to use SocialPost with escalation manager."""

        def __init__(self, post: SocialPost):
            self.content = post.content
            self.platform = post.platform
            self.sender = post.author
            self.channel = post.platform.value
