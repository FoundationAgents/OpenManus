# Try to import base agents, but gracefully handle failures
# This allows team management modules to be used independently
try:
    from app.agent.base import BaseAgent
    from app.agent.browser import BrowserAgent
    from app.agent.calendar_agent import CalendarAgent
    from app.agent.communication_orchestrator import CommunicationOrchestrator
    from app.agent.email_agent import EmailAgent
    from app.agent.mcp import MCPAgent
    from app.agent.message_agent import MessageAgent
    from app.agent.react import ReActAgent
    from app.agent.report_agent import ReportAgent
    from app.agent.social_media_agent import SocialMediaAgent
    from app.agent.swe import SWEAgent
    from app.agent.toolcall import ToolCallAgent
    _base_agents_available = True
except ImportError:
    # Base agents unavailable, but team management can still work
    _base_agents_available = False


__all__ = []

if _base_agents_available:
    __all__.extend([
        "BaseAgent",
        "BrowserAgent",
        "ReActAgent",
        "SWEAgent",
        "ToolCallAgent",
        "MCPAgent",
        "EmailAgent",
        "MessageAgent",
        "SocialMediaAgent",
        "CalendarAgent",
        "ReportAgent",
        "CommunicationOrchestrator",
    ])
