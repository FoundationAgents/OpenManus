class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class IXlinxAgentError(Exception):
    """Base exception for all iXlinx Agent errors"""


class TokenLimitExceeded(IXlinxAgentError):
    """Exception raised when the token limit is exceeded"""
