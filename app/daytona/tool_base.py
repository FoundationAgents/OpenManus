from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from daytona import Daytona, DaytonaConfig, Sandbox, SandboxState
from pydantic import Field

from app.config import config
from app.daytona.sandbox import create_sandbox, start_supervisord_session
from app.tool.base import BaseTool
from app.utils.files_utils import clean_path
from app.utils.logger import logger


# load_dotenv()
daytona_settings = config.daytona
daytona_config = DaytonaConfig(
    api_key=daytona_settings.daytona_api_key,
    server_url=daytona_settings.daytona_server_url,
    target=daytona_settings.daytona_target,
)
daytona = Daytona(daytona_config)


@dataclass
class ThreadMessage:
    """
    Represents a message to be added to a thread.
    """

    type: str
    content: Dict[str, Any]
    is_llm_message: bool = False
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = field(
        default_factory=lambda: datetime.now().timestamp()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary for API calls"""
        return {
            "type": self.type,
            "content": self.content,
            "is_llm_message": self.is_llm_message,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp,
        }


class SandboxToolsBase(BaseTool):
    """Base class for all sandbox tools that provides project-based sandbox access."""

    # Class variable to track if sandbox URLs have been printed
    _urls_printed: ClassVar[bool] = False

    # Required fields
    project_id: Optional[str] = None
    # thread_manager: Optional[ThreadManager] = None

    # Private fields (not part of the model schema)
    _sandbox: Optional[Sandbox] = None
    _sandbox_id: Optional[str] = None
    _sandbox_pass: Optional[str] = None
    workspace_path: str = Field(default="/workspace", exclude=True)
    _sessions: dict[str, str] = {}

    class Config:
        arbitrary_types_allowed = True  # Allow non-pydantic types like ThreadManager
        underscore_attrs_are_private = True

    async def _ensure_sandbox(self) -> Sandbox:
        """Ensure we have a valid sandbox instance, retrieving it from the project if needed."""
        if self._sandbox is None:
            # Get or start the sandbox
            try:
                self._sandbox = create_sandbox(password=config.daytona.VNC_password)
                # Log URLs if not already printed
                if not SandboxToolsBase._urls_printed:
                    vnc_link = self._sandbox.get_preview_link(6080)
                    website_link = self._sandbox.get_preview_link(8080)

                    vnc_url = (
                        vnc_link.url if hasattr(vnc_link, "url") else str(vnc_link)
                    )
                    website_url = (
                        website_link.url
                        if hasattr(website_link, "url")
                        else str(website_link)
                    )

                    print("\033[95m***")
                    print(f"VNC URL: {vnc_url}")
                    print(f"Website URL: {website_url}")
                    print("***\033[0m")
                    SandboxToolsBase._urls_printed = True
            except Exception as e:
                logger.error(f"Error retrieving or starting sandbox: {str(e)}")
                raise e
        else:
            if (
                self._sandbox.state == SandboxState.ARCHIVED
                or self._sandbox.state == SandboxState.STOPPED
            ):
                logger.info(f"Sandbox is in {self._sandbox.state} state. Starting...")
                try:
                    daytona.start(self._sandbox)
                    # Wait a moment for the sandbox to initialize
                    # sleep(5)
                    # Refresh sandbox state after starting

                    # Start supervisord in a session when restarting
                    start_supervisord_session(self._sandbox)
                except Exception as e:
                    logger.error(f"Error starting sandbox: {e}")
                    raise e
        return self._sandbox

    @property
    def sandbox(self) -> Sandbox:
        """Get the sandbox instance, ensuring it exists."""
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized. Call _ensure_sandbox() first.")
        return self._sandbox

    @property
    def sandbox_id(self) -> str:
        """Get the sandbox ID, ensuring it exists."""
        if self._sandbox_id is None:
            raise RuntimeError(
                "Sandbox ID not initialized. Call _ensure_sandbox() first."
            )
        return self._sandbox_id

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to /workspace."""
        cleaned_path = clean_path(path, self.workspace_path)
        logger.debug(f"Cleaned path: {path} -> {cleaned_path}")
        return cleaned_path
