"""
Startup Detection
Detect user intent and determine which components to load.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.config import config
from app.logger import logger


@dataclass
class UserIntent:
    """Detected user intent for startup."""
    intent_type: str
    confidence: float
    required_components: List[str]
    optional_components: List[str]
    description: str


class StartupDetection:
    """
    Detect user intent at startup to determine which components to load.
    """
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.workspace_dir = Path(config.local_service.workspace_directory)
    
    def detect_intent(self) -> UserIntent:
        """
        Detect user intent based on environment and history.
        
        Returns:
            UserIntent with detected intent and component requirements
        """
        intents = []
        
        # Check for existing project
        project_intent = self._check_existing_project()
        if project_intent:
            intents.append(project_intent)
        
        # Check for code editing
        code_intent = self._check_code_editing()
        if code_intent:
            intents.append(code_intent)
        
        # Check for web research
        web_intent = self._check_web_research()
        if web_intent:
            intents.append(web_intent)
        
        # Check for collaboration
        collab_intent = self._check_collaboration()
        if collab_intent:
            intents.append(collab_intent)
        
        # Default intent if no specific intent detected
        if not intents:
            return UserIntent(
                intent_type="general",
                confidence=0.5,
                required_components=[
                    "config", "logger", "database", "code_editor",
                    "command_log", "agent_control", "agent_monitor", "guardian"
                ],
                optional_components=[],
                description="General usage - load essential components only"
            )
        
        # Return highest confidence intent
        return max(intents, key=lambda i: i.confidence)
    
    def _check_existing_project(self) -> Optional[UserIntent]:
        """Check if user is continuing work on existing project."""
        # Check for project markers
        has_git = (self.workspace_dir / ".git").exists()
        has_project_files = any(
            (self.workspace_dir / name).exists()
            for name in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod"]
        )
        has_recent_files = self._has_recent_files()
        
        if has_git or has_project_files or has_recent_files:
            confidence = 0.8 if has_git else 0.6
            
            return UserIntent(
                intent_type="existing_project",
                confidence=confidence,
                required_components=[
                    "config", "logger", "database", "code_editor",
                    "command_log", "agent_control", "agent_monitor", "guardian"
                ],
                optional_components=["versioning", "backup", "knowledge_graph"],
                description="Continuing work on existing project"
            )
        
        return None
    
    def _check_code_editing(self) -> Optional[UserIntent]:
        """Check if user intends to do code editing."""
        # Check for code files in workspace
        code_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c"}
        code_files = []
        
        try:
            for item in self.workspace_dir.iterdir():
                if item.is_file() and item.suffix in code_extensions:
                    code_files.append(item)
                    if len(code_files) >= 5:  # Don't need to count all
                        break
        except Exception as e:
            logger.debug(f"Error checking code files: {e}")
        
        if code_files:
            return UserIntent(
                intent_type="code_editing",
                confidence=0.7,
                required_components=[
                    "config", "logger", "database", "code_editor",
                    "command_log", "agent_control", "guardian"
                ],
                optional_components=["sandbox", "agent_monitor"],
                description="Code editing and execution"
            )
        
        return None
    
    def _check_web_research(self) -> Optional[UserIntent]:
        """Check if user intends to do web research."""
        # This is harder to detect automatically, so we use heuristics
        # Check for research-related files or history
        research_keywords = ["research", "search", "web", "scrape", "crawl"]
        
        try:
            workspace_files = list(self.workspace_dir.glob("*"))
            research_files = [
                f for f in workspace_files
                if any(kw in f.name.lower() for kw in research_keywords)
            ]
            
            if research_files:
                return UserIntent(
                    intent_type="web_research",
                    confidence=0.6,
                    required_components=[
                        "config", "logger", "database", "agent_control",
                        "guardian", "network", "command_log"
                    ],
                    optional_components=["web_search", "browser", "knowledge_graph"],
                    description="Web research and data gathering"
                )
        except Exception as e:
            logger.debug(f"Error checking research files: {e}")
        
        return None
    
    def _check_collaboration(self) -> Optional[UserIntent]:
        """Check if user intends to collaborate."""
        # Check for collaboration indicators
        has_remote = self._has_git_remote()
        
        if has_remote:
            return UserIntent(
                intent_type="collaboration",
                confidence=0.7,
                required_components=[
                    "config", "logger", "database", "code_editor",
                    "command_log", "agent_control", "guardian", "versioning"
                ],
                optional_components=["backup", "resource_catalog"],
                description="Collaborative development"
            )
        
        return None
    
    def _has_recent_files(self) -> bool:
        """Check if workspace has recently modified files."""
        try:
            import time
            current_time = time.time()
            day_in_seconds = 24 * 60 * 60
            
            for item in self.workspace_dir.rglob("*"):
                if item.is_file():
                    mtime = item.stat().st_mtime
                    if current_time - mtime < day_in_seconds:
                        return True
        except Exception as e:
            logger.debug(f"Error checking recent files: {e}")
        
        return False
    
    def _has_git_remote(self) -> bool:
        """Check if workspace has git remote configured."""
        try:
            git_config = self.workspace_dir / ".git" / "config"
            if git_config.exists():
                content = git_config.read_text()
                return "remote" in content.lower()
        except Exception as e:
            logger.debug(f"Error checking git remote: {e}")
        
        return False
    
    def get_recommended_components(self) -> List[str]:
        """
        Get list of recommended components to load based on detected intent.
        
        Returns:
            List of component names
        """
        intent = self.detect_intent()
        
        # Combine required and optional (for now, load all recommended)
        components = intent.required_components + intent.optional_components
        
        # Remove duplicates while preserving order
        seen = set()
        unique_components = []
        for comp in components:
            if comp not in seen:
                seen.add(comp)
                unique_components.append(comp)
        
        return unique_components
    
    def get_essential_components(self) -> List[str]:
        """
        Get list of essential components that should always be loaded.
        
        Returns:
            List of component names
        """
        return [
            "config",
            "logger",
            "database",
            "guardian",
            "code_editor",
            "command_log",
            "agent_control",
            "agent_monitor"
        ]
    
    def should_load_component(self, component_name: str) -> bool:
        """
        Check if a component should be loaded based on detected intent.
        
        Args:
            component_name: Name of the component
        
        Returns:
            True if component should be loaded
        """
        intent = self.detect_intent()
        return (
            component_name in intent.required_components or
            component_name in intent.optional_components
        )
    
    def format_intent(self) -> str:
        """Format detected intent as human-readable string."""
        intent = self.detect_intent()
        
        lines = [
            f"Detected Intent: {intent.intent_type}",
            f"Confidence: {intent.confidence * 100:.0f}%",
            f"Description: {intent.description}",
            "",
            "Required components:",
        ]
        
        for comp in intent.required_components:
            lines.append(f"  ✓ {comp}")
        
        if intent.optional_components:
            lines.append("")
            lines.append("Optional components:")
            for comp in intent.optional_components:
                lines.append(f"  • {comp}")
        
        return "\n".join(lines)


# Global singleton
_startup_detection = None


def get_startup_detection() -> StartupDetection:
    """Get the global startup detection singleton."""
    global _startup_detection
    if _startup_detection is None:
        _startup_detection = StartupDetection()
    return _startup_detection
