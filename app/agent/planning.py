import time
from typing import Dict, List, Optional, Set, Tuple, Union
import json

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, Message, ToolCall, ToolChoice
from app.tool import PlanningTool, Terminate, ToolCollection
from app.tool.code_act import CodeAct


class PlanningAgent(ToolCallAgent):
    """
    An agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and tracks progress through individual steps until task completion.

    Enhanced features:
    - Step dependencies tracking
    - Integration with CodeAct for Python-based actions
    - Support for nested subplans
    - Improved error handling and recovery
    - Time and resource estimation
    """

    name: str = "planning"
    description: str = "An agent that creates and manages plans to solve tasks"

    system_prompt: str = PLANNING_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), Terminate(), CodeAct())
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    active_plan_id: Optional[str] = Field(default=None)

    # Расширенное отслеживание шагов и зависимостей
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)
    current_step_index: Optional[int] = None

    # Новые атрибуты для расширенного планирования
    step_dependencies: Dict[int, Set[int]] = Field(
        default_factory=dict, description="Maps step index to set of prerequisite step indexes"
    )
    step_durations: Dict[int, float] = Field(
        default_factory=dict, description="Estimated duration of each step in minutes"
    )
    step_errors: Dict[int, List[Dict]] = Field(
        default_factory=dict, description="Error history for each step"
    )
    subplans: Dict[int, str] = Field(
        default_factory=dict, description="Maps step index to subplan ID if step has a subplan"
    )

    # Настройки планирования
    max_steps: int = 30
    max_retries_per_step: int = 3
    should_adapt_plan: bool = True

    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "PlanningAgent":
        """Initialize the agent with a default plan ID and validate required tools."""
        self.active_plan_id = f"plan_{int(time.time())}"

        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        # Ensure we have CodeAct tool available
        if "code_act" not in self.available_tools.tool_map:
            self.available_tools.add_tool(CodeAct())

        return self

    async def think(self) -> bool:
        """Decide the next action based on plan status."""
        prompt = (
            f"CURRENT PLAN STATUS:\n{await self.get_plan()}\n\n{self.next_step_prompt}"
            if self.active_plan_id
            else self.next_step_prompt
        )
        self.messages.append(Message.user_message(prompt))

        # Get the current step index before thinking
        self.current_step_index = await self._get_current_step_index()

        result = await super().think()

        # After thinking, if we decided to execute a tool and it's not a planning tool or special tool,
        # associate it with the current step for tracking
        if result and self.tool_calls:
            latest_tool_call = self.tool_calls[0]  # Get the most recent tool call
            if (
                latest_tool_call.function.name != "planning"
                and latest_tool_call.function.name not in self.special_tool_names
                and self.current_step_index is not None
            ):
                self.step_execution_tracker[latest_tool_call.id] = {
                    "step_index": self.current_step_index,
                    "tool_name": latest_tool_call.function.name,
                    "status": "pending",  # Will be updated after execution
                }

        return result

    async def act(self) -> str:
        """Execute a step and track its completion status."""
        # Before acting, check if we should use code_act for the current step
        if (
            self.current_step_index is not None
            and self.tool_calls
            and self.tool_calls[0].function.name != "planning"
            and self.tool_calls[0].function.name not in self.special_tool_names
        ):
            # Check if we can use code for this action
            can_use_code = await self._check_code_act_compatibility(self.current_step_index)

            if can_use_code:
                # Convert the tool call to CodeAct
                code_action = await self._create_code_action_for_tool(self.tool_calls[0])
                if code_action:
                    logger.info(f"Converting tool call to CodeAct for step {self.current_step_index}")
                    # Replace the first tool call with our CodeAct tool call
                    self.tool_calls[0] = code_action

        # Continue with standard act behavior
        result = await super().act()

        # After executing the tool, update the plan status
        if self.tool_calls:
            latest_tool_call = self.tool_calls[0]

            # Update the execution status to completed
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = result

                # Update the plan status if this was a non-planning, non-special tool
                if (
                    latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names
                ):
                    await self.update_plan_status(latest_tool_call.id)

        return result

    async def get_plan(self) -> str:
        """Retrieve the current plan status."""
        if not self.active_plan_id:
            return "No active plan. Please create a plan first."

        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            await self.create_initial_plan(request)
        return await super().run()

    async def update_plan_status(self, tool_call_id: str) -> None:
        """
        Update the current plan progress based on completed tool execution.
        Only marks a step as completed if the associated tool has been successfully executed.
        Also updates any steps that may have become executable because their dependencies
        have been satisfied.
        """
        if not self.active_plan_id:
            return

        if tool_call_id not in self.step_execution_tracker:
            logger.warning(f"No step tracking found for tool call {tool_call_id}")
            return

        tracker = self.step_execution_tracker[tool_call_id]
        if tracker["status"] != "completed":
            logger.warning(f"Tool call {tool_call_id} has not completed successfully")
            return

        step_index = tracker["step_index"]
        is_successful = "error" not in tracker["result"].lower()

        try:
            # If the step failed, record the error and mark as blocked
            if not is_successful:
                # Record error
                if step_index not in self.step_errors:
                    self.step_errors[step_index] = []

                self.step_errors[step_index].append({
                    "tool_call_id": tool_call_id,
                    "error_message": tracker["result"],
                    "attempt": len(self.step_errors[step_index]) + 1
                })

                # If we've exceeded retry limit, mark as blocked
                if len(self.step_errors[step_index]) >= self.max_retries_per_step:
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": step_index,
                            "step_status": "blocked",
                            "step_notes": f"Failed after {self.max_retries_per_step} attempts. Last error: {tracker['result']}"
                        },
                    )
                    logger.warning(f"Step {step_index} marked as blocked after {self.max_retries_per_step} failed attempts")

                    # If plan should adapt, we need to propose alternative steps
                    if self.should_adapt_plan:
                        await self._adapt_plan_for_blocked_step(step_index)
                else:
                    # Reset status to not started to retry later
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": step_index,
                            "step_status": "not_started",
                            "step_notes": f"Retry #{len(self.step_errors[step_index])} pending. Previous error: {tracker['result']}"
                        },
                    )
                    logger.info(f"Step {step_index} reset for retry attempt #{len(self.step_errors[step_index])}")
            else:
                # Mark the step as completed on success
                await self.available_tools.execute(
                    name="planning",
                    tool_input={
                        "command": "mark_step",
                        "plan_id": self.active_plan_id,
                        "step_index": step_index,
                        "step_status": "completed",
                    },
                )
                logger.info(f"Marked step {step_index} as completed in plan {self.active_plan_id}")

                # Also check if this step has a subplan, and if so, create or activate it
                if step_index in self.subplans:
                    subplan_id = self.subplans[step_index]
                    logger.info(f"Step {step_index} has subplan {subplan_id}, activating...")
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "set_active",
                            "plan_id": subplan_id,
                        },
                    )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")

    async def _adapt_plan_for_blocked_step(self, blocked_step_index: int) -> None:
        """
        Adapts the plan when a step is blocked by proposing alternative approaches.

        This method is called when a step has failed after max_retries_per_step attempts.
        It asks the LLM to suggest alternative steps or approaches to work around the blocked step.
        """
        if not self.active_plan_id:
            return

        plan = await self.get_plan()
        error_history = self.step_errors.get(blocked_step_index, [])
        error_messages = [entry["error_message"] for entry in error_history]

        # Ask LLM to suggest alternatives
        adaptation_prompt = f"""
The following step in our plan is blocked after {len(error_history)} failed attempts:

{plan}

Failed step index: {blocked_step_index}
Error history:
{error_messages}

Please suggest ONE of the following:
1. Alternative steps to replace the blocked step
2. A way to fix the blocked step
3. A way to continue without this step if it's not critical

Your recommendation should include concrete steps or code to implement the solution.
"""

        messages = [Message.user_message(adaptation_prompt)]
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.AUTO,
        )

        # Process the response and update the plan
        if response and response.content:
            logger.info(f"Plan adaptation suggestion received: {response.content[:100]}...")

            # Add adaptation note to the blocked step
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": blocked_step_index,
                    "step_status": "blocked",
                    "step_notes": f"ADAPTATION SUGGESTED: {response.content[:200]}..."
                },
            )

            # If there are tool calls, execute them to update the plan
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    result = await self.execute_tool(tool_call)
                    logger.info(f"Executed adaptation tool {tool_call.function.name}: {result[:100]}...")

    async def _get_current_step_index(self) -> Optional[int]:
        """
        Parse the current plan to identify the next executable step based on dependencies.
        Returns the index of the highest-priority step that has all dependencies satisfied.
        Returns None if no eligible step is found.
        """
        if not self.active_plan_id:
            return None

        plan = await self.get_plan()

        try:
            plan_lines = plan.splitlines()
            steps_index = -1

            # Find the index of the "Steps:" line
            for i, line in enumerate(plan_lines):
                if line.strip() == "Steps:":
                    steps_index = i
                    break

            if steps_index == -1:
                return None

            # First, find all available (not completed) steps
            available_steps = []
            for i, line in enumerate(plan_lines[steps_index + 1:], start=0):
                if "[ ]" in line or "[→]" in line:  # not_started or in_progress
                    available_steps.append(i)

            # From available steps, find first step with all dependencies satisfied
            for step_index in available_steps:
                if await self._check_dependencies(step_index):
                    # Mark current step as in_progress
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": step_index,
                            "step_status": "in_progress",
                        },
                    )
                    return step_index

            # No steps with satisfied dependencies found
            logger.info("No executable steps found - either all completed or dependencies not met")
            return None

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None

    async def _check_dependencies(self, step_index: int) -> bool:
        """
        Check if all dependencies for a step are satisfied.

        Args:
            step_index: The index of the step to check dependencies for

        Returns:
            True if all dependencies are satisfied or no dependencies exist,
            False otherwise
        """
        # If no dependencies defined for this step, it's executable
        if step_index not in self.step_dependencies or not self.step_dependencies[step_index]:
            return True

        # Get the current plan to check dependency statuses
        plan = await self.get_plan()
        plan_lines = plan.splitlines()
        steps_index = -1

        # Find the "Steps:" line
        for i, line in enumerate(plan_lines):
            if line.strip() == "Steps:":
                steps_index = i
                break

        if steps_index == -1:
            logger.warning("Failed to find Steps section in plan")
            return False

        # Check each dependency
        for dep_index in self.step_dependencies[step_index]:
            if dep_index >= len(plan_lines) - steps_index - 1:
                logger.warning(f"Invalid dependency index {dep_index} for step {step_index}")
                return False

            dep_line = plan_lines[steps_index + 1 + dep_index]
            # Check if dependency is completed (contains [x] marker)
            if "[x]" not in dep_line:
                logger.info(f"Dependency {dep_index} not completed for step {step_index}")
                return False

        return True

    async def _check_code_act_compatibility(self, step_index: int) -> bool:
        """
        Check if the current step can be executed using CodeAct instead of a direct tool call.

        Args:
            step_index: The index of the step to check

        Returns:
            True if the step can use CodeAct, False otherwise
        """
        # Get the plan to examine the step
        plan = await self.get_plan()
        plan_lines = plan.splitlines()
        steps_index = -1

        # Find the "Steps:" line
        for i, line in enumerate(plan_lines):
            if line.strip() == "Steps:":
                steps_index = i
                break

        if steps_index == -1 or step_index >= len(plan_lines) - steps_index - 1:
            return False

        step_line = plan_lines[steps_index + 1 + step_index]

        # Simple heuristic: if step description mentions code, data processing, calculation, etc.
        code_keywords = [
            "code", "script", "program", "calculate", "compute", "process",
            "transform", "analyze", "algorithm", "function", "data", "python"
        ]

        for keyword in code_keywords:
            if keyword.lower() in step_line.lower():
                return True

        # If we've had errors with this step before, try CodeAct approach
        return step_index in self.step_errors

    async def _create_code_action_for_tool(self, tool_call: ToolCall) -> Optional[ToolCall]:
        """
        Convert a regular tool call to a code_act tool call that accomplishes the same goal.

        Args:
            tool_call: The original tool call to convert

        Returns:
            A new ToolCall using code_act, or None if conversion is not possible
        """
        if not tool_call or not tool_call.function or not tool_call.function.name:
            return None

        # Get information about the original tool and its parameters
        tool_name = tool_call.function.name
        tool_args = tool_call.function.arguments

        # Create a prompt asking how to accomplish this task with code
        code_act_prompt = f"""
Task: Convert the following tool call to Python code using the CodeAct pattern.

Original tool: {tool_name}
Tool arguments: {tool_args}
Current plan step: {self.current_step_index}

Write Python code that accomplishes the same task as the tool would.
The code should handle errors gracefully and print results clearly.
If appropriate, update the plan status upon completion.

Example code structure:
```python
# Import necessary libraries
import ...

try:
    # Main logic to accomplish the task
    ...

    # Print results
    print(f"Successfully completed task: ...")

    # Update plan status
    if success:
        context.plan_status['{self.current_step_index}'] = 'completed'
except Exception as e:
    print(f"Error: {str(e)}")
```
"""

        messages = [Message.user_message(code_act_prompt)]
        response = await self.llm.ask(messages=messages)

        if not response or not response.content:
            logger.warning("Failed to get code_act conversion")
            return None

        # Extract code from the response
        code = self._extract_code_from_text(response.content)
        if not code:
            logger.warning("No valid code found in response")
            return None

        # Create a ToolCall for code_act
        from app.schema import Function

        code_act_function = Function(
            name="code_act",
            arguments=f'{{"code": {json.dumps(code)}, "plan_step": "{self.current_step_index}"}}',
        )

        import uuid

        return ToolCall(
            id=f"code_act_{uuid.uuid4()}",
            type="function",
            function=code_act_function,
        )

    def _extract_code_from_text(self, text: str) -> Optional[str]:
        """
        Extract Python code from a text that may contain Markdown code blocks.

        Args:
            text: Text potentially containing code blocks

        Returns:
            Extracted code or None if no code found
        """
        import re

        # Try to extract code between python code blocks
        python_block_pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(python_block_pattern, text)

        if matches:
            return matches[0].strip()

        # If no code blocks found, look for code-like indented blocks
        lines = text.split("\n")
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                in_code_block = True
                code_lines.append(line)
            elif in_code_block and line.strip() and not line.startswith("#"):
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines)

        return None

    async def create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # Add guidance for creating plans with dependencies and time estimates
        planning_guidance = f"""
Analyze the following request and create a comprehensive plan with ID {self.active_plan_id}.

When creating the plan:
1. Break down the task into logical steps
2. Include time estimates for each step (in minutes)
3. Note dependencies between steps where applicable
4. Consider whether any steps would benefit from using Python code
5. Identify any steps that might require special handling or error recovery

Request: {request}
"""

        messages = [Message.user_message(planning_guidance)]
        self.memory.add_messages(messages)
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.AUTO,
        )
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )

        self.memory.add_message(assistant_msg)

        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"Executed tool {tool_call.function.name} with result: {result}"
                )

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True

                # Parse the plan to extract dependencies and time estimates
                await self._extract_plan_metadata()
                break

        if not plan_created:
            logger.warning("No plan created from initial request")
            tool_msg = Message.assistant_message(
                "Error: Parameter `plan_id` is required for command: create"
            )
            self.memory.add_message(tool_msg)

    async def _extract_plan_metadata(self) -> None:
        """
        Extract metadata from the plan, such as dependencies, time estimates, and subplans.
        This is called after a plan is created or updated.
        """
        if not self.active_plan_id:
            return

        plan = await self.get_plan()
        plan_lines = plan.splitlines()
        steps_index = -1

        # Find the "Steps:" line
        for i, line in enumerate(plan_lines):
            if line.strip() == "Steps:":
                steps_index = i
                break

        if steps_index == -1:
            logger.warning("Failed to find Steps section in plan")
            return

        # Process each step to extract metadata
        for i, line in enumerate(plan_lines[steps_index + 1:], start=0):
            if not line.strip():
                continue

            # Extract time estimate if present (e.g., "(~30m)" or "(30 min)")
            import re
            time_pattern = r"\(~?(\d+)(?:\s*(?:m|min|mins|minutes))\)"
            time_match = re.search(time_pattern, line)
            if time_match:
                try:
                    minutes = float(time_match.group(1))
                    self.step_durations[i] = minutes
                    logger.info(f"Found time estimate for step {i}: {minutes} minutes")
                except ValueError:
                    pass

            # Extract dependencies if present (e.g., "depends on: 1, 2" or "depends on step 1")
            dep_pattern = r"depends? on:?\s*((?:\d+(?:,\s*)?)+)"
            dep_match = re.search(dep_pattern, line, re.IGNORECASE)
            if dep_match:
                dep_str = dep_match.group(1)
                deps = [int(d.strip()) for d in dep_str.split(",") if d.strip().isdigit()]
                self.step_dependencies[i] = set(deps)
                logger.info(f"Found dependencies for step {i}: {deps}")

            # Check for subplan references
            subplan_pattern = r"subplan:?\s*(\w+)"
            subplan_match = re.search(subplan_pattern, line, re.IGNORECASE)
            if subplan_match:
                subplan_id = subplan_match.group(1)
                self.subplans[i] = subplan_id
                logger.info(f"Found subplan for step {i}: {subplan_id}")


async def main():
    # Configure and run the agent
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), Terminate(), CodeAct()))
    result = await agent.run("Help me plan a trip to the moon")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
