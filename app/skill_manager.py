import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError

from app.logger import logger
from app.schema_skill import Skill, SkillContext


class SkillManager:
    """Manages loading, discovery, and execution of agent skills"""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_paths: List[Path] = []
        self._initialized = False

    async def initialize(self, skills_paths: Optional[List[str]] = None) -> None:
        """Initialize skill manager and load all skills"""
        if self._initialized:
            return

        if skills_paths:
            self.skill_paths = [Path(p) for p in skills_paths]

        await self._discover_and_load_skills()
        self._initialized = True

        logger.info(
            f"🎯 SkillManager initialized with {len(self.skills)} skills loaded"
        )

    async def _discover_and_load_skills(self) -> None:
        """Discover and load skills from configured paths"""
        all_paths = self._get_all_skill_paths()

        for skill_path in all_paths:
            try:
                await self._load_skill_from_path(skill_path)
            except Exception as e:
                logger.warning(f"⚠️ Failed to load skill from {skill_path}: {e}")

    def _get_all_skill_paths(self) -> List[Path]:
        """Get all skill directories from configured paths"""
        all_paths = []

        for base_path in self.skill_paths:
            if not base_path.exists():
                logger.debug(f"Skill path does not exist: {base_path}")
                continue

            if base_path.is_file():
                skill_dir = base_path.parent
            else:
                skill_dir = base_path

            if (skill_dir / "SKILL.md").exists():
                all_paths.append(skill_dir)
            elif skill_dir.is_dir():
                for subpath in skill_dir.iterdir():
                    if subpath.is_dir() and (subpath / "SKILL.md").exists():
                        all_paths.append(subpath)

        return all_paths

    async def _load_skill_from_path(self, skill_path: Path) -> None:
        """Load a single skill from its directory"""
        skill_file = skill_path / "SKILL.md"

        if not skill_file.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        content = skill_file.read_text(encoding="utf-8")

        metadata = self._parse_yaml_frontmatter(content)
        if not metadata:
            raise ValueError("No valid YAML frontmatter found in SKILL.md")

        skill_name = metadata.get("name")
        if not skill_name:
            raise ValueError("Skill name is required in metadata")

        skill_description = metadata.get("description", "")
        if not skill_description:
            raise ValueError("Skill description is required in metadata")

        skill = Skill(
            name=skill_name,
            description=skill_description,
            path=skill_path,
            content=content,
            keywords=metadata.get("keywords"),
            allowed_tools=metadata.get("allowed-tools"),
            model=metadata.get("model"),
            context=SkillContext(metadata.get("context", "inline")),
            agent=metadata.get("agent"),
            hooks=metadata.get("hooks"),
            user_invocable=metadata.get("user-invocable", True),
            disable_model_invocation=metadata.get("disable-model-invocation", False),
        )

        await self._load_supporting_files(skill)

        self.skills[skill_name] = skill
        logger.info(f"✅ Loaded skill: {skill_name}")

    async def _load_supporting_files(self, skill: Skill) -> None:
        """Load supporting files referenced in skill content"""
        skill_dir = skill.path

        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.findall(pattern, skill.content)

        for link_text, file_path in matches:
            file_full_path = skill_dir / file_path

            if file_full_path.exists():
                try:
                    content = file_full_path.read_text(encoding="utf-8")
                    skill.supporting_files[file_path] = content
                    logger.debug(f"📄 Loaded supporting file: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load {file_path}: {e}")

    def _parse_yaml_frontmatter(self, content: str) -> Optional[Dict]:
        """Parse YAML frontmatter from markdown content"""
        if not content.startswith("---"):
            return None

        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None

        yaml_content = content[3:end_idx]
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return None

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name"""
        return self.skills.get(name)

    def get_all_skills(self) -> Dict[str, Skill]:
        """Get all loaded skills"""
        return self.skills.copy()

    def get_relevant_skills(
        self, user_request: str, threshold: float = 0.0
    ) -> List[Skill]:
        """Get skills that are relevant to the user request"""
        relevant = []
        request_lower = user_request.lower()

        for skill in self.skills.values():
            if skill.disable_model_invocation:
                continue

            if skill.should_trigger(user_request):
                relevance_score = self._calculate_relevance(
                    skill, user_request, request_lower
                )
                if relevance_score >= threshold:
                    relevant.append((skill, relevance_score))

        relevant.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in relevant]

    def _calculate_relevance(
        self, skill: Skill, user_request: str, request_lower: str
    ) -> float:
        """Calculate relevance score for a skill"""
        score = 0.0
        request_words = request_lower.split()

        # Score based on keyword matches (more weight for direct matches)
        for keyword in skill.keywords:
            keyword_lower = keyword.lower()

            # Direct match - high weight
            if keyword_lower in request_lower:
                score += 0.4

            # Check word stems/variations - if request word is prefix of keyword
            # This handles: debug -> debugs, fix -> fixes, etc.
            for word in request_words:
                if len(keyword_lower) > 4 and word.startswith(keyword_lower[:4]):
                    score += 0.3
                # Also check reverse: keyword is prefix of request word
                elif len(word) > 4 and keyword_lower.startswith(word[:4]):
                    score += 0.3

        # Small bonus for description word matches (capped to avoid high scores)
        description_lower = skill.description.lower()
        description_words = [w.strip('.,;:"()[]{}') for w in description_lower.split()]
        desc_match_count = 0
        for word in description_words:
            if word in request_lower and len(word) > 4:
                desc_match_count += 1
                if desc_match_count <= 2:  # Only count first 2 matches
                    score += 0.1

        return min(score, 1.0)

    def get_skill_prompt(self, skill_name: str) -> Optional[str]:
        """Get the full prompt for a specific skill"""
        skill = self.skills.get(skill_name)
        if not skill:
            return None

        return skill.get_full_prompt()

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills with basic info"""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
                "context": skill.context,
                "user_invocable": skill.user_invocable,
            }
            for skill in self.skills.values()
        ]

    async def reload_skills(self) -> None:
        """Reload all skills from disk"""
        logger.info("🔄 Reloading skills...")
        self.skills.clear()
        await self._discover_and_load_skills()
        logger.info(f"✅ Reloaded {len(self.skills)} skills")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.skills.clear()
        self.skill_paths.clear()
        self._initialized = False


skill_manager = SkillManager()
