from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.planning import PlanningTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch

# Optional tools that may not be available due to missing dependencies
_optional_tools = []

try:
    from app.tool.browser_use_tool import BrowserUseTool
    _optional_tools.append("BrowserUseTool")
except ImportError:
    BrowserUseTool = None

try:
    from app.tool.crawl4ai import Crawl4aiTool
    _optional_tools.append("Crawl4aiTool")
except ImportError:
    Crawl4aiTool = None

__all__ = [
    "BaseTool",
    "Bash",
    "Terminate",
    "StrReplaceEditor",
    "WebSearch",
    "ToolCollection",
    "CreateChatCompletion",
    "PlanningTool",
] + _optional_tools
