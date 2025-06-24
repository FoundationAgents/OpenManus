from app.agent.base import BaseAgent
from app.agent.browser import BrowserAgent # Restaurado
from app.agent.mcp import MCPAgent # Restaurado
from app.agent.react import ReActAgent
from app.agent.swe import SWEAgent
from app.agent.toolcall import ToolCallAgent
from app.agent.critic_agent import CriticAgent


__all__ = [
    "BaseAgent",
    "BrowserAgent", # Restaurado
    "ReActAgent",
    "SWEAgent",
    "ToolCallAgent",
    "MCPAgent", # Restaurado
    "CriticAgent",
]
