"""
Context window management for LLM interactions.

Handles:
- Keeping last N messages in context
- Compressing old messages (summarization)
- Prioritizing messages (recent > important > oldest)
- Monitoring token usage
- Automatic context cleanup
"""

import time
from collections import deque
from typing import Dict, List, Optional, Tuple

from app.logger import logger


class Message:
    """Represents a message in the context."""

    def __init__(self, role: str, content: str, timestamp: Optional[float] = None, importance: float = 0.5):
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
        self.importance = importance  # 0.0 to 1.0
        self.token_count = self._estimate_tokens()

    def _estimate_tokens(self) -> int:
        """Estimate token count for this message."""
        # Simple heuristic: ~4 chars per token
        return len(self.content) // 4 + 4  # +4 for role and metadata

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for API."""
        return {"role": self.role, "content": self.content}

    def __repr__(self):
        return f"Message({self.role}: {self.content[:50]}...)"


class ContextManager:
    """
    Manages the LLM context window with smart message handling.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        max_messages: Optional[int] = None,
        warning_threshold: float = 0.8,
        compression_threshold: float = 0.9,
    ):
        """
        Initialize context manager.

        Args:
            max_tokens: Maximum tokens to keep in context (default: 8000)
            max_messages: Maximum number of messages to keep (None = unlimited)
            warning_threshold: Warn when token usage exceeds this ratio (0-1)
            compression_threshold: Compress context when exceeding this ratio (0-1)
        """
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.warning_threshold = warning_threshold
        self.compression_threshold = compression_threshold

        self.messages: deque = deque()
        self.current_tokens = 0
        self.system_message: Optional[Message] = None
        self.compression_history: List[str] = []

    def add_message(self, role: str, content: str, importance: float = 0.5):
        """
        Add a message to the context.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            importance: Importance score (0.0-1.0) for prioritization

        Raises:
            ValueError: If role is invalid
        """
        if role not in ("user", "assistant", "system"):
            raise ValueError(f"Invalid role: {role}")

        message = Message(role, content, importance=importance)

        # Handle system message separately
        if role == "system":
            self.system_message = message
            return

        self.messages.append(message)
        self.current_tokens += message.token_count

        # Check if we need to cleanup
        self._check_and_cleanup()

        logger.debug(
            f"Added message from {role}. Total tokens: {self.current_tokens}/{self.max_tokens} "
            f"({100 * self.current_tokens / self.max_tokens:.1f}%)"
        )

    def _check_and_cleanup(self):
        """Check if cleanup is needed and perform it."""
        usage_ratio = self.current_tokens / self.max_tokens

        if usage_ratio >= self.compression_threshold:
            logger.warning(
                f"Context usage at {100 * usage_ratio:.1f}%, compressing context..."
            )
            self._compress_context()
        elif usage_ratio >= self.warning_threshold:
            logger.warning(
                f"Context usage approaching limit: {100 * usage_ratio:.1f}%"
            )

        # Enforce max messages limit
        if self.max_messages and len(self.messages) > self.max_messages:
            self._trim_old_messages()

    def _compress_context(self):
        """
        Compress context by removing low-importance old messages.

        Keeps: recent messages and high-importance messages.
        Removes: oldest low-importance messages.
        """
        if not self.messages:
            return

        # Sort by importance and recency
        sorted_messages = sorted(
            self.messages,
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )

        # Keep messages until we're under threshold
        target_tokens = int(self.max_tokens * 0.6)  # Compress to 60% of max
        kept_messages = []
        total_tokens = 0

        for msg in sorted_messages:
            if total_tokens + msg.token_count <= target_tokens:
                kept_messages.append(msg)
                total_tokens += msg.token_count

        # Restore original order
        kept_messages.sort(key=lambda m: m.timestamp)

        removed_count = len(self.messages) - len(kept_messages)
        self.messages = deque(kept_messages)
        self.current_tokens = total_tokens

        logger.info(
            f"Compressed context: removed {removed_count} messages, "
            f"new total: {self.current_tokens} tokens"
        )

    def _trim_old_messages(self):
        """Remove oldest messages when exceeding max_messages limit."""
        while len(self.messages) > self.max_messages:
            removed = self.messages.popleft()
            self.current_tokens -= removed.token_count
            logger.debug(f"Removed old message, new total: {self.current_tokens} tokens")

    def get_context(self) -> List[Dict[str, str]]:
        """
        Get formatted context for API call.

        Returns:
            List of message dictionaries ready for API

        Raises:
            ValueError: If no messages in context
        """
        if not self.messages and not self.system_message:
            raise ValueError("No messages in context")

        context = []

        # Add system message if present
        if self.system_message:
            context.append(self.system_message.to_dict())

        # Add regular messages
        context.extend([msg.to_dict() for msg in self.messages])

        return context

    def get_status(self) -> Dict:
        """Get context status information."""
        usage_ratio = self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0

        return {
            "total_messages": len(self.messages),
            "total_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "usage_ratio": usage_ratio,
            "usage_percent": 100 * usage_ratio,
            "remaining_tokens": max(0, self.max_tokens - self.current_tokens),
            "has_system_message": self.system_message is not None,
            "compressions_performed": len(self.compression_history),
        }

    def clear(self):
        """Clear all messages from context."""
        self.messages.clear()
        self.system_message = None
        self.current_tokens = 0
        logger.info("Cleared context")

    def set_system_message(self, content: str):
        """Set or update the system message."""
        self.system_message = Message("system", content)
        logger.debug("System message updated")

    def get_messages(self) -> List[Tuple[str, str]]:
        """
        Get messages as tuples of (role, content).

        Returns:
            List of (role, content) tuples
        """
        return [(msg.role, msg.content) for msg in self.messages]

    def estimate_tokens_for_message(self, content: str) -> int:
        """Estimate token count for a message."""
        return len(content) // 4 + 4

    def can_add_message(self, content: str) -> bool:
        """Check if a new message would fit in context."""
        message_tokens = self.estimate_tokens_for_message(content)
        return (self.current_tokens + message_tokens) <= self.max_tokens

    def get_available_tokens(self) -> int:
        """Get remaining available tokens."""
        return max(0, self.max_tokens - self.current_tokens)
