from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class McpTool:
    """
    Represents an MCP tool with complete information.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    server: str
    tool: str

    def get_name(self) -> str:
        """Return the tool name."""
        return self.name

    def get_server(self) -> str:
        """Return the server name that provides this tool."""
        return self.server 