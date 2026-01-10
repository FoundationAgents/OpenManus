from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillContext(str, Enum):
    """Execution context for skills"""

    INLINE = "inline"
    FORK = "fork"


class SkillTrigger(BaseModel):
    """Trigger conditions for skill activation"""

    keywords: List[str] = Field(default_factory=list)
    description_match: bool = True
    user_invocable: bool = True


class SkillHook(BaseModel):
    """Hook definition for skill lifecycle events"""

    PreToolUse: Optional[Dict] = None
    PostToolUse: Optional[Dict] = None
    Stop: Optional[Dict] = None


class Skill(BaseModel):
    """Represents an agent skill with metadata and content"""

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    path: Path
    content: str = ""

    keywords: List[str] = Field(default_factory=list)
    allowed_tools: Optional[List[str]] = None
    model: Optional[str] = None
    context: SkillContext = SkillContext.INLINE
    agent: Optional[str] = None
    hooks: Optional[Dict[str, List[Dict]]] = None
    user_invocable: bool = True
    disable_model_invocation: bool = False

    supporting_files: Dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name format"""
        import re

        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Skill name must only contain lowercase letters, numbers, and hyphens"
            )
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Validate skill path exists"""
        if not v.exists():
            raise ValueError(f"Skill path does not exist: {v}")
        return v

    @model_validator(mode="after")
    def extract_keywords_from_description(self) -> "Skill":
        """Extract keywords from description if not provided"""
        if not self.keywords or len(self.keywords) == 0:
            # Extract meaningful words from description
            words = self.description.lower().split()
            # Filter out common words and keep meaningful ones
            common_words = {
                "use",
                "when",
                "for",
                "to",
                "a",
                "an",
                "the",
                "and",
                "or",
                "with",
                "this",
                "that",
                "your",
                "from",
            }
            self.keywords = []
            for word in words:
                # Clean word: remove punctuation and quotes
                clean_word = word.strip(".,;:'\"()[]{}")
                if (
                    len(clean_word) > 3
                    and clean_word not in common_words
                    and clean_word not in self.keywords
                ):
                    self.keywords.append(clean_word)
        return self

    def get_full_prompt(self) -> str:
        """Get full prompt including any supporting file references"""
        return self.content

    def should_trigger(self, user_request: str) -> bool:
        """Determine if skill should trigger based on request"""
        if self.disable_model_invocation:
            return False

        request_lower = user_request.lower()
        request_words = request_lower.split()

        # Check if any keyword or its root is in the request
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            # Direct match
            if keyword_lower in request_lower:
                return True
            # Check for word stems (simple approach)
            keyword_stem = (
                keyword_lower[:-1] if len(keyword_lower) > 4 else keyword_lower
            )
            for word in request_words:
                if keyword_lower.startswith(word[:3]) and word.startswith(
                    keyword_lower[:3]
                ):
                    return True

        return False
