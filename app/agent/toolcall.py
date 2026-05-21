import asyncio
import difflib
import json
import re
from typing import Any, List, Optional, Union

from pydantic import Field

from app.agent.base import Task, TaskInterrupted
from app.agent.react import ReActAgent
from app.config import config
from app.exceptions import TokenLimitExceeded
from app.llm import MULTIMODAL_MODELS
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.task_context import (
    current_tool_call,
    get_current_auto_context_compress,
    get_current_requested_context_window,
)
from app.tool import CreateChatCompletion, Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from context.engine import ContextEngine


TOOL_CALL_REQUIRED = "Tool calls required but none provided"
# Patterns that suggest the model is in the middle of executing a plan (not finished).
_INCOMPLETE_RE = re.compile(
    r"\b(let me|i(?:'| a)m going to|next i(?:'| a)ll|i(?:'| a)ll now|continuing|to debug|to inspect|to verify)\b",
    re.IGNORECASE,
)

# Strong explicit finish markers — a single match is enough to consider the turn final.
_STRONG_FINAL_RE = re.compile(
    r"\b(task (?:is )?(?:complete|done|finished)|all (?:steps|requirements) (?:are )?(?:done|complete|met)|here(?:'s| is) (?:the )?(?:final|complete|full)|remaining limitations|implementation (?:is )?(?:complete|done))\b",
    re.IGNORECASE,
)

# Weak finish words — need 2+ of these (or 1 + no tool intent) to avoid false positives.
_WEAK_FINAL_RE = re.compile(
    r"\b(done|completed|finished|implemented|created|verified|summary|blocked|successfully)\b",
    re.IGNORECASE,
)

# Kept for external import compatibility.
FINAL_RESPONSE_RE = _STRONG_FINAL_RE

OBSERVE_ONLY_TOOLS = {"codebase_overview", "glob", "grep", "read_files"}


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
    _last_assistant_content: str = ""
    _consecutive_no_tool_nonfinal: int = 0
    _consecutive_observe_only_steps: int = 0

    max_steps: int = config.agent.max_steps
    max_tools_per_step: int = config.agent.max_tools_per_step
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
            self._maybe_compress_context(task, system_msgs)

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
        if tool_calls and self._is_observe_only_batch(tool_calls):
            self._consecutive_observe_only_steps += 1
            if self._consecutive_observe_only_steps >= 5:
                task.emit(
                    "warning",
                    {
                        "message": "Repeated observe-only steps detected. Agent must now execute implementation/verification actions or terminate with a concrete status summary."
                    },
                )
                self.memory.add_message(
                    Message.user_message(
                        "Do not run more inspection-only steps now. "
                        "Execute the next implementation action(s), then verify. "
                        "If blocked, call terminate with exact blocker, completed steps, and remaining work."
                    )
                )
        elif tool_calls:
            self._consecutive_observe_only_steps = 0
        if len(tool_calls) > self.max_tools_per_step:
            tool_calls = tool_calls[: self.max_tools_per_step]
            self.tool_calls = tool_calls
            task.emit(
                "warning",
                {
                    "message": (
                        f"Tool call batch trimmed to {self.max_tools_per_step} calls "
                        "to protect runtime stability."
                    )
                },
            )
        content = response.content if response and response.content else ""
        self._last_assistant_content = content.strip()

        task.emit(
            "thought",
            {
                "agent": self.name,
                "content": content,
                "tool_count": len(tool_calls) if tool_calls else 0,
                "tools": [call.function.name for call in tool_calls]
                if tool_calls
                else [],
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ]
                if tool_calls
                else [],
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
                if content.strip():
                    if "[TEMPLATE_FALLBACK_FINAL]" in content:
                        clean_content = content.replace(
                            "[TEMPLATE_FALLBACK_FINAL]", ""
                        ).strip()
                        task.emit(
                            "final_response",
                            {
                                "message": clean_content,
                                "reason": "Template fallback forced graceful final summary.",
                            },
                        )
                        self.state = AgentState.FINISHED
                        return True
                    if not self._looks_final_response(content):
                        self._consecutive_no_tool_nonfinal += 1
                        # The model produced a continuation sentence without tool calls.
                        # Keep the run alive and ask for an actionable next step.
                        task.emit(
                            "warning",
                            {
                                "message": "Model returned a non-final continuation without tool calls; requesting explicit completion or next action."
                            },
                        )
                        self.memory.add_message(
                            Message.user_message(
                                "Continue autonomously and follow the existing plan strictly. "
                                "Either call the next tool(s) now, or if all plan steps are truly done, "
                                "provide a final summary with what was completed, verification performed, "
                                "artifact/file paths, and any remaining limitations."
                            )
                        )
                        if self._consecutive_no_tool_nonfinal >= 3:
                            task.emit(
                                "warning",
                                {
                                    "message": "Repeated no-tool non-final responses detected; requiring actionable next step."
                                },
                            )
                        return True
                    self._consecutive_no_tool_nonfinal = 0
                    task.emit(
                        "final_response",
                        {
                            "message": content.strip(),
                            "reason": "Model provided a final answer without requesting another tool.",
                        },
                    )
                    self.state = AgentState.FINISHED
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

    @staticmethod
    def _looks_incomplete_response(content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return False
        if "?" in text:
            return True
        return bool(_INCOMPLETE_RE.search(text))

    @staticmethod
    def _looks_final_response(content: str) -> bool:
        """Heuristic: is this turn a genuine task completion or mid-task commentary?

        Rules (applied in order):
        1. Empty / whitespace → never final.
        2. Looks incomplete (has in-progress signal words) → not final.
        3. Strong explicit finish marker (e.g. 'task is complete') → final.
        4. Two or more weak finish words present → final.
        5. One weak finish word AND the message ends without a colon (not leading into next step) → final.
        6. Otherwise → not final.
        """
        text = (content or "").strip()
        if not text:
            return False
        if ToolCallAgent._looks_incomplete_response(text):
            return False
        # Rule 3: strong explicit signal is sufficient on its own
        if _STRONG_FINAL_RE.search(text):
            return True
        weak_matches = _WEAK_FINAL_RE.findall(text)
        # Rule 4: two or more weak signals
        if len(weak_matches) >= 2:
            return not text.endswith(":")
        # Rule 5: one weak signal + not trailing into a next-step list
        if len(weak_matches) == 1:
            return not text.endswith(":")
        return False

    @staticmethod
    def _is_observe_only_batch(tool_calls: List[ToolCall]) -> bool:
        names = [call.function.name for call in tool_calls]
        if not names:
            return False
        return all(name in OBSERVE_ONLY_TOOLS for name in names)

    def _maybe_compress_context(self, task: Task, system_msgs: List[Message]) -> None:
        if not get_current_auto_context_compress():
            return
        requested_window = get_current_requested_context_window()
        if requested_window is None or requested_window <= 0:
            requested_window = self.llm.max_input_tokens
        if requested_window is None or requested_window <= 0:
            return
        if len(self.messages) < 30:
            return
        try:
            supports_images = self.llm.active_model in MULTIMODAL_MODELS
            formatted_system = self.llm.format_messages(system_msgs, supports_images)
            formatted_messages = self.llm.format_messages(
                self.messages, supports_images
            )
            total_tokens = self.llm.count_message_tokens(
                formatted_system + formatted_messages
            )
        except Exception:
            return

        ratio = total_tokens / max(1, requested_window)
        if ratio < 0.9:
            return

        keep_recent = 24
        older = self.messages[:-keep_recent]
        recent = self.messages[-keep_recent:]
        if not older:
            return

        lines: list[str] = []
        for msg in older[-80:]:
            role = str(msg.role)
            text = (msg.content or "").replace("\n", " ").strip()
            if not text:
                continue
            if len(text) > 220:
                text = text[:220] + "..."
            lines.append(f"- {role}: {text}")

        summary = (
            "Compressed conversation memory to preserve context window. "
            "Use this as persistent prior state:\n" + "\n".join(lines[-60:])
        )
        self.memory.messages = [Message.system_message(summary), *recent]
        task.emit(
            "context_compressed",
            {
                "before_tokens": total_tokens,
                "requested_window": requested_window,
                "usage_ratio": round(ratio, 4),
                "kept_recent_messages": keep_recent,
                "compressed_messages": max(0, len(older)),
            },
        )

    async def act(self, task: Task) -> str:
        """Execute tool calls and handle their results."""
        if task.is_interrupted():
            raise TaskInterrupted()

        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            return self.messages[-1].content or "No content or commands to execute"

        results = []
        index = 0
        # Dedup set: skip tool calls with an identical name+args signature seen in this step.
        seen_sigs: set[str] = set()
        while index < len(self.tool_calls):
            if task.is_interrupted():
                raise TaskInterrupted()

            command = self.tool_calls[index]
            # --- Intra-step deduplication ---
            sig = f"{command.function.name}:{command.function.arguments}"
            if sig in seen_sigs:
                index += 1
                task.emit(
                    "warning",
                    {
                        "message": f"Duplicate tool call skipped: '{command.function.name}' with identical args.",
                        "tool": command.function.name,
                    },
                )
                # Still need a tool message to keep the message chain intact
                self.memory.add_message(
                    Message.tool_message(
                        content="[skipped: identical call already executed in this step]",
                        tool_call_id=command.id,
                        name=command.function.name,
                    )
                )
                results.append("[skipped: duplicate]")
                continue
            seen_sigs.add(sig)

            command = self.tool_calls[index]
            if self._is_parallel_safe(command):
                batch = [command]
                next_index = index + 1
                while next_index < len(self.tool_calls) and self._is_parallel_safe(
                    self.tool_calls[next_index]
                ):
                    batch.append(self.tool_calls[next_index])
                    next_index += 1

                batch_results = await asyncio.gather(
                    *(self.execute_tool(item, task) for item in batch)
                )
                for item, result in zip(batch, batch_results):
                    if self.max_observe:
                        result = result[: self.max_observe]
                    task.emit(
                        "tool_result",
                        {
                            "tool": item.function.name,
                            "result": result,
                            "tool_call_id": item.id,
                        },
                    )
                    self.memory.add_message(
                        Message.tool_message(
                            content=result,
                            tool_call_id=item.id,
                            name=item.function.name,
                            base64_image=self._current_base64_image,
                        )
                    )
                    results.append(result)
                index = next_index
                continue

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
            self.memory.add_message(
                Message.tool_message(
                    content=result,
                    tool_call_id=command.id,
                    name=command.function.name,
                    base64_image=self._current_base64_image,
                )
            )
            results.append(result)
            index += 1

        return "\n\n".join(results)

    def _is_parallel_safe(self, command: ToolCall) -> bool:
        """Return True if the tool can run concurrently with others.

        Prefers the tool instance's ``parallel_safe`` capability flag when
        available; falls back to checking a hard-coded allowlist so that older
        tools without the flag still batch correctly.
        """
        name = (command.function.name or "").lower()
        tool_instance = self.available_tools.tool_map.get(name)
        if tool_instance is not None and hasattr(tool_instance, "parallel_safe"):
            return bool(tool_instance.parallel_safe)
        # Fallback: a conservative allowlist of known-safe tool names.
        _SAFE_FALLBACK = {"skill_playbook", "codebase_overview", "glob", "grep", "read_files", "web_search"}
        return name in _SAFE_FALLBACK

    async def execute_tool(self, command: ToolCall, task: Task) -> str:
        """Execute a single tool call with robust error handling.

        For tools that declare ``can_retry=True`` (the default), a failed first
        attempt is retried once with the error injected into the arguments so
        the model's implementation gets a second chance with corrective context.
        """
        if task.is_interrupted():
            raise TaskInterrupted()

        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        tool_instance = self.available_tools.tool_map.get(name)
        tool_can_retry = getattr(tool_instance, "can_retry", True)

        try:
            args = json.loads(command.function.arguments or "{}")
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            task.emit(
                "error",
                {
                    "message": f"Invalid JSON arguments for tool '{name}'",
                    "detail": command.function.arguments,
                    "fatal": False,
                },
            )
            return f"Error: {error_msg}"

        async def _run_once(run_args: dict) -> str:
            """Execute the tool once and return the observation string."""
            token = current_tool_call.set({"id": command.id, "name": name})
            try:
                result = await self.available_tools.execute(name=name, tool_input=run_args)
            finally:
                current_tool_call.reset(token)

            if name == BrowserUseTool().name:
                browser_screenshot = await self._emit_browser_screenshot(task)
                if browser_screenshot:
                    self._current_base64_image = browser_screenshot

            await self._handle_special_tool(task=task, name=name, result=result)

            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image

            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )
            return observation, result

        try:
            observation, result = await _run_once(args)

            # --- Retry with error feedback (one attempt only) ---
            result_is_error = (
                isinstance(result, str) and result.lower().startswith("error")
            ) or (hasattr(result, "is_error") and result.is_error)

            if result_is_error and tool_can_retry:
                error_hint = str(result)
                task.emit(
                    "warning",
                    {
                        "message": f"Tool '{name}' failed on first attempt; retrying with error context.",
                        "detail": error_hint,
                    },
                )
                retry_args = {**args, "_error_context": error_hint}
                try:
                    observation, result = await _run_once(retry_args)
                except Exception:
                    pass  # Keep the first error observation on retry failure

            return observation

        except Exception as e:
            error_msg = f"Tool '{name}' encountered a problem: {str(e)}"
            task.emit(
                "error",
                {
                    "message": "Tool execution failed",
                    "tool": name,
                    "detail": str(e),
                    "fatal": False,
                },
            )
            return f"Error: {error_msg}"

    @staticmethod
    def _build_str_replace_diff_preview(args: dict) -> dict:
        command = str(args.get("command") or "")
        old_str = str(args.get("old_str") or "")
        new_str = str(args.get("new_str") or "")
        file_text = str(args.get("file_text") or "")

        def _clip(
            lines: list[str], max_lines: int = 120, max_len: int = 240
        ) -> list[str]:
            trimmed = [line[:max_len] for line in lines[:max_lines]]
            if len(lines) > max_lines:
                trimmed.append("... (diff truncated)")
            return trimmed

        payload: dict[str, Any] = {"command": command, "lines": []}

        if command == "str_replace":
            old_lines = old_str.splitlines()
            new_lines = new_str.splitlines()
            raw = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile="before",
                    tofile="after",
                    n=2,
                    lineterm="",
                )
            )
            payload["lines"] = _clip(raw)
            payload["added_lines"] = sum(
                1 for line in raw if line.startswith("+") and not line.startswith("+++")
            )
            payload["deleted_lines"] = sum(
                1 for line in raw if line.startswith("-") and not line.startswith("---")
            )
            return payload

        if command == "insert":
            payload["lines"] = _clip([f"+{line}" for line in new_str.splitlines()])
            payload["added_lines"] = len(new_str.splitlines())
            payload["deleted_lines"] = 0
            return payload

        if command == "create":
            payload["lines"] = _clip([f"+{line}" for line in file_text.splitlines()])
            payload["added_lines"] = len(file_text.splitlines())
            payload["deleted_lines"] = 0
            return payload

        payload["added_lines"] = 0
        payload["deleted_lines"] = 0
        return payload

    async def _emit_browser_screenshot(self, task: Task) -> Optional[str]:
        browser_tool = self.available_tools.get_tool(BrowserUseTool().name)
        if browser_tool is None or not hasattr(browser_tool, "get_current_state"):
            return None

        state_result = await browser_tool.get_current_state()
        screenshot = getattr(state_result, "base64_image", None)
        if not screenshot:
            return None

        url = ""
        title = ""
        try:
            state = json.loads(state_result.output or "{}")
            url = state.get("url", "")
            title = state.get("title", "")
        except Exception:
            pass

        task.emit(
            "browser_screenshot",
            {"screenshot": screenshot, "url": url, "title": title},
        )
        return screenshot

    async def _handle_special_tool(self, task: Task, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes."""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            summary = self._last_assistant_content or str(result)
            task.emit(
                "finish_signal",
                {
                    "tool": name,
                    "message": summary,
                    "reason": "Finish tool signaled completion.",
                },
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
