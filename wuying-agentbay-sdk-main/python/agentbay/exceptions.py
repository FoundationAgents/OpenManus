class AgentBayError(Exception):
    """Base exception for all AgentBay SDK errors."""

    def __init__(self, message=None, *args, **kwargs):
        if message is None:
            message = self.__class__.__name__
        super().__init__(message, *args)
        self.extra = kwargs


class AuthenticationError(AgentBayError):
    """Raised when there is an authentication error."""

    def __init__(self, message="Authentication failed", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class APIError(AgentBayError):
    """Raised when there is an error with the API."""

    def __init__(self, message="API error", status_code=None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.status_code = status_code


class FileError(AgentBayError):
    """Raised for errors related to file operations."""

    def __init__(self, message="File operation error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class CommandError(AgentBayError):
    """Raised for errors related to command execution."""

    def __init__(self, message="Command execution error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class SessionError(AgentBayError):
    """Raised for errors related to session operations."""

    def __init__(self, message="Session error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class OssError(AgentBayError):
    """Raised for errors related to OSS operations."""

    def __init__(self, message="OSS operation error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class ApplicationError(AgentBayError):
    """Raised for errors related to application operations."""

    def __init__(self, message="Application operation error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class UIError(AgentBayError):
    """Raised for errors related to UI operations."""

    def __init__(self, message="UI operation error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class BrowserError(AgentBayError):
    """Raised when there is an error with the browser."""

    def __init__(self, message="Browser error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class AgentError(AgentBayError):
    """Raised for errors related to Agent actions."""

    def __init__(self, message="Agent action error", *args, **kwargs):
        super().__init__(message, *args, **kwargs)
