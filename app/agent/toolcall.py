import asyncio
import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.agent.react import ReActAgent
from app.agent.base import Task, TaskInterrupted
from context.engine import ContextEngine
from app.exceptions import TokenLimitExceeded
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction."""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self, task: Task) -> bool:
        """Process current state and decide next actions using tools."""
        if task.is_interrupted():
            raise TaskInterrupted()

        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            context = ContextEngine.build(task, agent_role=self.name)
            context_msg = Message.system_message(
                json.dumps(context, ensure_ascii=False)
            )
            if task.is_interrupted():
                raise TaskInterrupted()

            system_msgs = (
                [Message.system_message(self.system_prompt), context_msg]
                if self.system_prompt
                else [context_msg]
            )

            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=system_msgs,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                task.emit(
                    "error",
                    {
                        "message": "Token limit reached during tool thinking",
                        "detail": str(token_limit_error),
                    },
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        task.emit(
            "thought",
            {
                "agent": self.name,
                "content": content,
                "tool_count": len(tool_calls) if tool_calls else 0,
                "tools": [call.function.name for call in tool_calls] if tool_calls else [],
                "arguments": tool_calls[0].function.arguments if tool_calls else None,
            },
        )

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    task.emit(
                        "warning",
                        {
                            "message": f"{self.name} tried to use tools when none were available"
                        },
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            task.emit(
                "error",
                {
                    "message": f"The {self.name}'s thinking process hit a snag",
                    "detail": str(e),
                },
            )
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self, task: Task) -> str:
        """Execute tool calls and handle their results."""
        if task.is_interrupted():
            raise TaskInterrupted()

        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            if task.is_interrupted():
                raise TaskInterrupted()

            self._current_base64_image = None

            result = await self.execute_tool(command, task)

            if self.max_observe:
                result = result[: self.max_observe]

            task.emit(
                "tool_result",
                {
                    "tool": command.function.name,
                    "result": result,
                    "tool_call_id": command.id,
                },
            )

            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall, task: Task) -> str:
        """Execute a single tool call with robust error handling."""
        if task.is_interrupted():
            raise TaskInterrupted()

        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            args = json.loads(command.function.arguments or "{}")

            result = await self.available_tools.execute(name=name, tool_input=args)

            await self._handle_special_tool(task=task, name=name, result=result)

            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image

            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            task.emit(
                "error",
                {
                    "message": f"Invalid JSON arguments for tool '{name}'",
                    "detail": command.function.arguments,
                },
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Tool '{name}' encountered a problem: {str(e)}"
            task.emit(
                "error",
                {"message": "Tool execution failed", "tool": name, "detail": str(e)},
            )
            return f"Error: {error_msg}"

    async def _handle_special_tool(
        self, task: Task, name: str, result: Any, **kwargs
    ):
        """Handle special tool execution and state changes."""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            task.emit(
                "finish_signal",
                {"tool": name, "message": "Special tool signaled completion."},
            )
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent."""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list."""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        for tool_instance in self.available_tools.tool_map.values():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    await tool_instance.cleanup()
                except Exception:
                    # Ignore cleanup errors to avoid masking main flow
                    pass

    async def run(self, task: Task, input: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(task, input)
        finally:
            await self.cleanup()
