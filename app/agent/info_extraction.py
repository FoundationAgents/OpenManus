"""Information extraction from communications."""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.agent.models.communication import ActionItem, PriorityLevel
from app.logger import logger


class InformationExtractor:
    """Extract important information from communications."""

    ACTION_KEYWORDS = [
        "can you",
        "could you",
        "please",
        "i need",
        "we need",
        "required",
        "must",
        "should",
        "todo",
        "fix",
        "review",
        "check",
        "complete",
        "finish",
        "submit",
    ]

    DECISION_KEYWORDS = [
        "decided",
        "agreed",
        "approve",
        "will",
        "won't",
        "don't",
        "do not",
        "approved",
        "rejected",
        "selected",
        "chosen",
    ]

    DATE_PATTERNS = [
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        r"(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+\d{1,2}",
        r"(today|tomorrow|next\s+\w+|this\s+\w+)",
        r"(\d{1,2}:\d{2}\s*(am|pm|AM|PM))",
    ]

    def __init__(self):
        """Initialize the information extractor."""
        pass

    def extract_action_items(self, text: str, source_id: str) -> List[ActionItem]:
        """Extract action items from text.

        Args:
            text: The text to extract from
            source_id: ID of the source communication

        Returns:
            List of extracted action items
        """
        action_items: List[ActionItem] = []

        # Look for sentences starting with action keywords
        sentences = re.split(r"[.!?]+", text)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains action keywords
            lower_sentence = sentence.lower()
            has_action = any(
                keyword in lower_sentence for keyword in self.ACTION_KEYWORDS
            )

            if has_action:
                # Determine priority
                priority = PriorityLevel.NORMAL
                if any(
                    word in lower_sentence
                    for word in ["urgent", "asap", "critical", "emergency", "immediately"]
                ):
                    priority = PriorityLevel.URGENT
                elif any(word in lower_sentence for word in ["important", "high priority"]):
                    priority = PriorityLevel.HIGH

                # Try to extract due date
                due_date = self._extract_date(sentence)

                action_item = ActionItem(
                    id=f"action_{source_id}_{i}",
                    description=sentence[:200],
                    source=source_id,
                    priority=priority,
                    due_date=due_date,
                )
                action_items.append(action_item)

        logger.info(f"✓ Extracted {len(action_items)} action items from {source_id}")
        return action_items

    def extract_decisions(self, text: str) -> List[str]:
        """Extract decisions made from text.

        Args:
            text: The text to extract from

        Returns:
            List of extracted decisions
        """
        decisions: List[str] = []
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            lower_sentence = sentence.lower()
            if any(keyword in lower_sentence for keyword in self.DECISION_KEYWORDS):
                # Look for specific decision patterns
                if "agreed" in lower_sentence or "decided" in lower_sentence:
                    # Extract what was decided
                    if "to" in lower_sentence:
                        decision_part = sentence[sentence.lower().find("to") :]
                        decisions.append(decision_part[:150])
                elif "will" in lower_sentence or "won't" in lower_sentence:
                    decisions.append(sentence[:150])

        logger.info(f"✓ Extracted {len(decisions)} decisions")
        return decisions

    def extract_dates(self, text: str) -> List[Tuple[str, Optional[datetime]]]:
        """Extract dates and deadlines from text.

        Args:
            text: The text to extract from

        Returns:
            List of tuples (date_string, parsed_datetime)
        """
        dates: List[Tuple[str, Optional[datetime]]] = []

        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(0)
                parsed_date = self._parse_date_string(date_str)
                dates.append((date_str, parsed_date))

        logger.info(f"✓ Extracted {len(dates)} dates from text")
        return dates

    def extract_relationships(self, text: str) -> List[Tuple[str, str]]:
        """Extract relationships mentioned in text.

        Args:
            text: The text to extract from

        Returns:
            List of tuples (person, relationship_type)
        """
        relationships: List[Tuple[str, str]] = []

        # Look for patterns like "John said", "Mary agreed", etc.
        patterns = [
            r"(\w+)\s+(said|told|mentioned|agreed|disagreed|thinks)",
            r"from\s+(\w+)",
            r"with\s+(\w+)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                person = match.group(1)
                relationship_type = match.group(2) if len(match.groups()) > 1 else "mentioned"
                relationships.append((person, relationship_type))

        return relationships

    def detect_sentiment(self, text: str) -> str:
        """Detect overall sentiment of text.

        Args:
            text: The text to analyze

        Returns:
            Sentiment (positive, negative, neutral)
        """
        lower_text = text.lower()

        positive_indicators = [
            "great",
            "excellent",
            "amazing",
            "perfect",
            "wonderful",
            "thank",
            "appreciate",
            "good",
            "love",
        ]
        negative_indicators = [
            "bad",
            "terrible",
            "awful",
            "hate",
            "problem",
            "issue",
            "broken",
            "fail",
            "error",
            "sorry",
        ]

        positive_count = sum(
            1 for word in positive_indicators if word in lower_text
        )
        negative_count = sum(
            1 for word in negative_indicators if word in lower_text
        )

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def detect_urgency(self, text: str) -> bool:
        """Detect if text indicates urgency.

        Args:
            text: The text to analyze

        Returns:
            Whether text indicates urgency
        """
        urgency_indicators = [
            "urgent",
            "asap",
            "immediately",
            "critical",
            "emergency",
            "now",
            "today",
            "right away",
            "quickly",
        ]

        lower_text = text.lower()
        return any(indicator in lower_text for indicator in urgency_indicators)

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract a single date from text.

        Args:
            text: Text containing date

        Returns:
            Parsed datetime or None
        """
        try:
            dates = self.extract_dates(text)
            if dates and dates[0][1]:
                return dates[0][1]
        except Exception as e:
            logger.debug(f"Failed to extract date: {e}")

        return None

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse a date string into datetime.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime or None
        """
        try:
            # Handle relative dates
            lower_str = date_str.lower()

            today = datetime.now()

            if lower_str == "today":
                return today
            elif lower_str == "tomorrow":
                return today + timedelta(days=1)
            elif "next" in lower_str:
                # Simple next week parsing
                if "week" in lower_str:
                    return today + timedelta(weeks=1)
                elif "month" in lower_str:
                    return today + timedelta(days=30)

            # Try to parse standard formats
            formats = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d-%m-%Y"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"Failed to parse date string '{date_str}': {e}")

        return None
