"""User voice and tone model for maintaining communication style."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.agent.models.communication import ToneStyle, UserVoiceProfile
from app.logger import logger


class VoiceModel(BaseModel):
    """Learns and maintains user's communication voice and style."""

    profile: UserVoiceProfile = Field(
        default_factory=UserVoiceProfile, description="User's voice profile"
    )
    storage_path: Optional[Path] = Field(
        default=None, description="Path to store voice profile"
    )

    class Config:
        arbitrary_types_allowed = True

    def load_profile(self, path: Optional[Path] = None) -> None:
        """Load user voice profile from storage.

        Args:
            path: Path to voice profile JSON file
        """
        try:
            profile_path = path or self.storage_path
            if profile_path and profile_path.exists():
                with open(profile_path) as f:
                    data = json.load(f)
                    self.profile = UserVoiceProfile(**data)
                logger.info(f"✓ Loaded voice profile from {profile_path}")
            else:
                logger.info("No voice profile found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load voice profile: {e}")

    def save_profile(self, path: Optional[Path] = None) -> None:
        """Save user voice profile to storage.

        Args:
            path: Path to save voice profile JSON file
        """
        try:
            profile_path = path or self.storage_path
            if profile_path:
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(profile_path, "w") as f:
                    json.dump(self.profile.model_dump(), f, indent=2)
                logger.info(f"✓ Saved voice profile to {profile_path}")
        except Exception as e:
            logger.error(f"Failed to save voice profile: {e}")

    def update_from_sample(
        self,
        text: str,
        tone: ToneStyle = ToneStyle.PROFESSIONAL,
        recipient_type: str = "general",
    ) -> None:
        """Update voice profile from a sample message.

        Args:
            text: Sample message text
            tone: Tone of the message
            recipient_type: Type of recipient (team, manager, external, user)
        """
        try:
            # Analyze text for characteristics
            emoji_count = sum(
                1 for char in text if ord(char) > 0x1F300 and ord(char) < 0x1F6FF
            )
            word_count = len(text.split())
            emoji_freq = emoji_count / max(word_count, 1)

            # Update profile based on sample
            if emoji_freq > 0.05:
                self.profile.emoji_usage = min(0.9, self.profile.emoji_usage + 0.1)
            elif emoji_freq == 0:
                self.profile.emoji_usage = max(0.1, self.profile.emoji_usage - 0.05)

            # Update tone by recipient
            self.profile.tone_by_recipient[recipient_type] = tone

            logger.info(f"✓ Updated voice profile from sample (recipient: {recipient_type})")
        except Exception as e:
            logger.error(f"Failed to update voice profile: {e}")

    def adapt_to_recipient(self, recipient_type: str) -> ToneStyle:
        """Get appropriate tone for recipient type.

        Args:
            recipient_type: Type of recipient (team, manager, external, user)

        Returns:
            Appropriate tone style
        """
        # Default mappings if not in profile
        default_tones = {
            "manager": ToneStyle.PROFESSIONAL,
            "team": ToneStyle.FRIENDLY,
            "external": ToneStyle.FORMAL,
            "user": ToneStyle.CASUAL,
        }

        return self.profile.tone_by_recipient.get(
            recipient_type, default_tones.get(recipient_type, ToneStyle.PROFESSIONAL)
        )

    def get_greeting(self, recipient_type: str = "general") -> str:
        """Get appropriate greeting for recipient type.

        Args:
            recipient_type: Type of recipient

        Returns:
            Greeting string
        """
        if recipient_type == "formal" or recipient_type == "external":
            return "Hello"
        elif recipient_type == "team":
            return self.profile.greeting_style or "Hi"
        elif recipient_type == "manager":
            return "Hi"
        else:
            return self.profile.greeting_style or "Hi"

    def get_closing(self, recipient_type: str = "general") -> str:
        """Get appropriate closing for recipient type.

        Args:
            recipient_type: Type of recipient

        Returns:
            Closing string
        """
        if recipient_type == "formal" or recipient_type == "external":
            return "Best regards"
        elif recipient_type == "team":
            return self.profile.closing_style or "Thanks"
        elif recipient_type == "manager":
            return "Thanks"
        else:
            return self.profile.closing_style or "Thanks"

    def should_use_emoji(self, recipient_type: str = "general") -> bool:
        """Determine if emoji should be used.

        Args:
            recipient_type: Type of recipient

        Returns:
            Whether emoji should be used
        """
        if recipient_type == "formal" or recipient_type == "external":
            return False
        return self.profile.emoji_usage > 0.5

    def get_formality_level(self) -> str:
        """Get formality level descriptor.

        Returns:
            Formality level (very_formal, formal, neutral, casual, very_casual)
        """
        level = self.profile.formal_level
        if level > 0.8:
            return "very_formal"
        elif level > 0.6:
            return "formal"
        elif level > 0.4:
            return "neutral"
        elif level > 0.2:
            return "casual"
        else:
            return "very_casual"

    def get_voice_summary(self) -> str:
        """Get a summary of the user's communication voice.

        Returns:
            Formatted summary of voice profile
        """
        summary = f"""User Communication Voice Profile:
- Formality: {self.get_formality_level()} ({self.profile.formal_level:.1%})
- Directness: {self.profile.directness:.1%}
- Emoji Usage: {self.profile.emoji_usage:.1%}
- Detail Level: {self.profile.detail_level:.1%}
- Greeting: "{self.profile.greeting_style}"
- Closing: "{self.profile.closing_style}"
- Common Phrases: {', '.join(self.profile.preferred_phrases[:3]) if self.profile.preferred_phrases else 'None'}
"""
        if self.profile.tone_by_recipient:
            summary += "- Tone by Recipient:\n"
            for recipient, tone in self.profile.tone_by_recipient.items():
                summary += f"  • {recipient}: {tone.value}\n"

        return summary

    def generate_styled_response(
        self, base_response: str, recipient_type: str = "general"
    ) -> str:
        """Apply user voice to a base response.

        Args:
            base_response: The response text to style
            recipient_type: Type of recipient

        Returns:
            Styled response matching user's voice
        """
        # Get greeting and closing
        greeting = self.get_greeting(recipient_type)
        closing = self.get_closing(recipient_type)

        # Determine if emoji should be used
        use_emoji = self.should_use_emoji(recipient_type)

        # Build styled response
        lines = base_response.split("\n")
        if not lines[0].startswith(greeting):
            lines.insert(0, greeting + ",")

        if not any(closing.lower() in line.lower() for line in lines[-2:]):
            lines.append("")
            lines.append(closing + ",")

        styled = "\n".join(lines)

        # Add emoji if appropriate
        if use_emoji and self.profile.emoji_usage > 0.3:
            # Add subtle emoji (not overdone)
            if "thanks" in styled.lower():
                styled = styled.replace("thanks", "thanks 👍", 1)

        return styled
