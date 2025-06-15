from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role options"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """Tool choice options"""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
    USER_HALTED = "user_halted" # Added for periodic user interaction
    AWAITING_USER_FEEDBACK = "awaiting_user_feedback" # New state for explicit feedback points
    USER_PAUSED = "user_paused" # New state for user-initiated pause


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: ROLE_TYPE = Field(...)  # type: ignore
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        if self.base64_image is not None:
            message["base64_image"] = self.base64_image
        return message

    @classmethod
    def user_message(
        cls, content: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER, content=content, base64_image=base64_image)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(
        cls, content: Optional[str] = None, base64_image: Optional[str] = None
    ) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content, base64_image=base64_image)

    @classmethod
    def tool_message(
        cls, content: str, name, tool_call_id: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            base64_image=base64_image,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: List[Any],
        content: Union[str, List[str]] = "",
        base64_image: Optional[str] = None,
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            base64_image: Optional base64 encoded image
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=formatted_calls,
            base64_image=base64_image,
            **kwargs,
        )


class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """
        Add a message to memory. If the memory exceeds max_messages,
        it truncates older messages, ensuring that no 'tool' message becomes
        the first message if its corresponding 'assistant' message (that called it)
        is truncated.
        """
        self.messages.append(message)

        if len(self.messages) > self.max_messages:
            # Step 1: Calculate the initial cut-off point.
            # Messages before this index would be truncated by a simple trim.
            cut_off_index = len(self.messages) - self.max_messages
            
            # Step 2: Select the messages that would be kept by simple truncation.
            # This is our working list that we might shrink from the left.
            potential_kept_messages = self.messages[cut_off_index:]

            # Step 3-6: Iteratively check and remove orphan tool messages from the beginning
            # of potential_kept_messages.
            while potential_kept_messages:
                first_kept_message = potential_kept_messages[0]

                # Step 3: Check if the first message in our potential list is a tool message.
                if first_kept_message.role == Role.TOOL and first_kept_message.tool_call_id:
                    # Step 4: It's a tool message. Identify its tool_call_id.
                    tool_call_id_to_find = first_kept_message.tool_call_id
                    
                    # Assume it's an orphan until proven otherwise.
                    is_orphan = True
                    
                    # Step 5: Check if the assistant message that generated this tool call
                    # is present *within the currently visible potential_kept_messages*.
                    for msg_in_kept_list in potential_kept_messages:
                        if msg_in_kept_list.role == Role.ASSISTANT and msg_in_kept_list.tool_calls:
                            for tool_call in msg_in_kept_list.tool_calls:
                                if tool_call.id == tool_call_id_to_find:
                                    # Found the originating assistant message within the kept messages.
                                    # Therefore, the first_kept_message (tool message) is NOT an orphan.
                                    is_orphan = False
                                    break  # Exit inner loop (tool_calls)
                        if not is_orphan:
                            break  # Exit outer loop (potential_kept_messages iteration)
                    
                    if is_orphan:
                        # Step 6: The originating assistant message was not found in potential_kept_messages
                        # (meaning it was in the truncated part: self.messages[:cut_off_index]).
                        # So, this first_kept_message (tool message) is an orphan. Remove it.
                        potential_kept_messages.pop(0)
                        # Continue the 'while potential_kept_messages' loop to check the new first message.
                    else:
                        # The first_kept_message (tool message) is not an orphan.
                        # We can stop checking and keep the current potential_kept_messages.
                        break 
                else:
                    # The first message is not a tool message (or has no tool_call_id),
                    # so the orphan check logic doesn't apply to it. Stop checking.
                    break
            
            # Step 7: Finally, assign the potentially modified list of messages back.
            self.messages = potential_kept_messages

    def add_messages(self, messages: List[Message]) -> None:
        """
        Add multiple messages to memory.
        This method calls add_message for each message to ensure the
        orphan prevention logic is applied consistently upon each addition
        that might trigger truncation.
        """
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]
