class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class OpenManusError(Exception):
    """Base exception for all OpenManus errors"""


class TokenLimitExceeded(OpenManusError):
    """Exception raised when the token limit is exceeded"""


class AgentLoopError(OpenManusError):
    """Raised when the agent loop encounters a structural problem.

    Examples: model refuses to call tools, repeated no-tool responses,
    or the loop reaches an invalid state transition.
    """


class VerificationFailed(OpenManusError):
    """Raised when a verification step rejects the agent's claimed completion.

    Contains the reason so it can be fed back into the loop for another attempt.
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)
