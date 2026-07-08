import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import logger


# class BaseTool(ABC, BaseModel):
#     name: str
#     description: str
#     parameters: Optional[dict] = None

#     class Config:
#         arbitrary_types_allowed = True

#     async def __call__(self, **kwargs) -> Any:
#         """Execute the tool with given parameters."""
#         return await self.execute(**kwargs)

#     @abstractmethod
#     async def execute(self, **kwargs) -> Any:
#         """Execute the tool with given parameters."""

#     def to_param(self) -> Dict:
#         """Convert tool to function call format."""
#         return {
#             "type": "function",
#             "function": {
#                 "name": self.name,
#                 "description": self.description,
#                 "parameters": self.parameters,
#             },
#         }


class ToolResult(BaseModel):
    """Represents the result of a tool execution.

    Fields
    ------
    output      : Primary text output from the tool.
    error       : Error message when the tool failed, or None on success.
    base64_image: Optional screenshot / image attached to the result.
    system      : Optional system-level note (e.g. sandbox info).
    exit_code   : Numeric exit status (0 = success, non-zero = failure).
    metadata    : Arbitrary key-value context (e.g. path, lines_changed, url).
    """

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)
    exit_code: int = Field(default=0, description="Exit status; 0 = success")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured context attached to the result (path, diff, url, …)",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_error(self) -> bool:
        """True when the tool reported a failure."""
        return bool(self.error) or self.exit_code != 0

    def __bool__(self):
        if hasattr(self, "model_fields") and self.model_fields:
            fields = self.model_fields
        else:
            fields = getattr(self, "__fields__", {})
        return any(getattr(self, field) for field in fields)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        combined_meta = {**self.metadata, **other.metadata}
        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
            exit_code=other.exit_code if other.exit_code != 0 else self.exit_code,
            metadata=combined_meta,
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else str(self.output or "")

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        return type(self)(**{**self.model_dump(), **kwargs})


class BaseTool(ABC, BaseModel):
    """Consolidated base class for all tools combining BaseModel and Tool functionality.

    Provides:
    - Pydantic model validation
    - Schema registration
    - Standardized result handling
    - Abstract execution interface

    Capability flags
    ----------------
    parallel_safe  : Tool can run concurrently with other tools in the same step
                     (no shared mutable state, no exclusive resource locks).
    can_retry      : A failed call may be retried once with the error injected as
                     context. Set to False for destructive / non-idempotent tools.
    emits_progress : Tool streams intermediate progress events during execution.
    """

    name: str
    description: str
    parameters: Optional[dict] = None

    # --- Capability flags (read by ToolCallAgent) ---
    parallel_safe: bool = Field(
        default=False,
        description="Safe to run in parallel with other tool calls in the same step.",
    )
    can_retry: bool = Field(
        default=True,
        description="Whether a single retry-with-error-feedback is allowed on failure.",
    )
    emits_progress: bool = Field(
        default=False,
        description="Tool streams intermediate progress events (e.g. long bash commands).",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    # def __init__(self, **data):
    #     """Initialize tool with model validation and schema registration."""
    #     super().__init__(**data)
    #     logger.debug(f"Initializing tool class: {self.__class__.__name__}")
    #     self._register_schemas()

    # def _register_schemas(self):
    #     """Register schemas from all decorated methods."""
    #     for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
    #         if hasattr(method, 'tool_schemas'):
    #             self._schemas[name] = method.tool_schemas
    #             logger.debug(f"Registered schemas for method '{name}' in {self.__class__.__name__}")

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format.

        Returns:
            Dictionary with tool metadata in OpenAI function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    # def get_schemas(self) -> Dict[str, List[ToolSchema]]:
    #     """Get all registered tool schemas.

    #     Returns:
    #         Dict mapping method names to their schema definitions
    #     """
    #     return self._schemas

    def success_response(self, data: Union[Dict[str, Any], str]) -> ToolResult:
        """Create a successful tool result.

        Args:
            data: Result data (dictionary or string)

        Returns:
            ToolResult with success=True and formatted output
        """
        if isinstance(data, str):
            text = data
        else:
            text = json.dumps(data, indent=2)
        logger.debug(f"Created success response for {self.__class__.__name__}")
        return ToolResult(output=text)

    def fail_response(self, msg: str) -> ToolResult:
        """Create a failed tool result.

        Args:
            msg: Error message describing the failure

        Returns:
            ToolResult with success=False and error message
        """
        logger.debug(f"Tool {self.__class__.__name__} returned failed result: {msg}")
        return ToolResult(error=msg)


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
