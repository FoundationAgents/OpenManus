"""
UI panels package for IDE layout components.
Contains reusable panel widgets for different IDE functions.
"""

from app.ui.panels.code_editor import CodeEditorPanel
from app.ui.panels.agent_control import AgentControlPanel
from app.ui.panels.workflow_visualizer import WorkflowVisualizerPanel
from app.ui.panels.command_log import CommandLogPanel
from app.ui.panels.console import ConsolePanel
from app.ui.panels.agent_monitor import AgentMonitorPanel
from app.ui.panels.retrieval_insights import RetrievalInsightsPanel
from app.ui.panels.backup_panel import BackupPanel

__all__ = [
    "CodeEditorPanel",
    "AgentControlPanel",
    "WorkflowVisualizerPanel",
    "CommandLogPanel",
    "ConsolePanel",
    "AgentMonitorPanel",
    "RetrievalInsightsPanel",
    "BackupPanel",
]
