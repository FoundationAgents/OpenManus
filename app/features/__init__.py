"""FreEco.AI Features Module

Provides Tasks, Settings, and Knowledge Base functionality.
"""

from .knowledge_base import KnowledgeBaseManager
from .settings import SettingsManager
from .tasks import TaskManager


__all__ = ["TaskManager", "SettingsManager", "KnowledgeBaseManager"]
