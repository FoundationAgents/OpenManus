import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.logger import logger


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    # Event system integration
    enable_events: bool = Field(
        default=True, description="Whether to publish tool execution events"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Current conversation ID for event tracking"
    )

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters and publish events."""

        # Publish tool execution start event
        start_time = time.time()
        if self.enable_events:
            await self._publish_tool_start_event(kwargs)

        try:
            result = await self.execute(**kwargs)
            execution_time = time.time() - start_time

            # Publish tool execution success event
            if self.enable_events:
                await self._publish_tool_complete_event(
                    kwargs, result, True, execution_time
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # Publish tool execution failure event
            if self.enable_events:
                await self._publish_tool_complete_event(
                    kwargs, str(e), False, execution_time
                )

            raise

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    # Event system integration methods

    def set_conversation_id(self, conversation_id: str) -> None:
        """Set the conversation ID for event tracking."""
        self.conversation_id = conversation_id

    def enable_event_publishing(self, enabled: bool = True) -> None:
        """Enable or disable event publishing."""
        self.enable_events = enabled

    async def _publish_tool_start_event(self, parameters: Dict[str, Any]) -> bool:
        """Publish tool execution start event."""
        try:
            from app.event import bus, create_tool_execution_event

            event = create_tool_execution_event(
                tool_name=self.name,
                tool_type=self.__class__.__name__,
                status="started",
                parameters=parameters,
                conversation_id=self.conversation_id,
            )
            return await bus.publish(event)
        except Exception as e:
            logger.warning(f"Failed to publish tool start event: {e}")
            return False

    async def _publish_tool_complete_event(
        self,
        parameters: Dict[str, Any],
        result: Any,
        success: bool,
        execution_time: float,
    ) -> bool:
        """Publish tool execution complete event."""
        try:
            from app.event import BaseEvent, bus

            event = BaseEvent(
                event_type="tool.execution.complete",
                data={
                    "tool_name": self.name,
                    "tool_type": self.__class__.__name__,
                    "parameters": parameters,
                    "result": str(result) if result is not None else None,
                    "success": success,
                    "execution_time": execution_time,
                    "conversation_id": self.conversation_id,
                },
                source=self.name,
            )
            return await bus.publish(event)
        except Exception as e:
            logger.warning(f"Failed to publish tool complete event: {e}")
            return False

    async def publish_custom_tool_event(self, event_type: str, data: dict) -> bool:
        """Publish a custom tool event.

        Args:
            event_type: Type of the event (e.g., "tool.custom.progress")
            data: Event data dictionary

        Returns:
            bool: True if event was published successfully
        """
        if not self.enable_events:
            return False

        try:
            from app.event import BaseEvent, bus

            event = BaseEvent(
                event_type=event_type,
                data={
                    "tool_name": self.name,
                    "tool_type": self.__class__.__name__,
                    "conversation_id": self.conversation_id,
                    **data,
                },
                source=self.name,
            )
            return await bus.publish(event)
        except Exception as e:
            logger.warning(f"Failed to publish custom tool event {event_type}: {e}")
            return False


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
