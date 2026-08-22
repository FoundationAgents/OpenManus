import json
import time
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message, ToolChoice
from app.tool import PlanningTool


class PlanStepStatus(str, Enum):
    """Enum class defining possible statuses of a plan step"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """Return a list of all possible step status values"""
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """Return a list of values representing active statuses (not started or in progress)"""
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """Return a mapping of statuses to their marker symbols"""
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }


class PlanningFlow(BaseFlow):
    """A flow that manages planning and execution of tasks using agents."""

    llm: LLM = Field(default_factory=lambda: LLM())
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)
    executor_keys: List[str] = Field(default_factory=list)
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None
    max_retry_per_step: int = Field(default=2)  # Max retries before replanning
    max_replan_count: int = Field(default=3)  # Max replanning attempts to prevent infinite loop
    replan_counts: Dict[int, int] = Field(default_factory=dict)  # Track replans per step
    step_retry_counts: Dict[int, int] = Field(default_factory=dict)  # Track retries per step

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Set executor keys before super().__init__
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # Set plan ID if provided
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")

        # Initialize the planning tool if not provided
        if "planning_tool" not in data:
            planning_tool = PlanningTool()
            data["planning_tool"] = planning_tool

        # Call parent's init with the processed data
        super().__init__(agents, **data)

        # Set executor_keys to all agent keys if not specified
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """
        Get an appropriate executor agent for the current step.
        Can be extended to select agents based on step type/requirements.
        """
        # If step type is provided and matches an agent key, use that agent
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # Otherwise use the first available executor or fall back to primary agent
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # Fallback to primary agent
        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """Execute the planning flow with agents."""
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            # Create initial plan if input provided
            if input_text:
                await self._create_initial_plan(input_text)

                # Verify plan was created successfully
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(
                        f"Plan creation failed. Plan ID {self.active_plan_id} not found in planning tool."
                    )
                    return f"Failed to create plan for: {input_text}"

            result = ""
            while True:
                # Get current step to execute
                self.current_step_index, step_info = await self._get_current_step_info()

                # Exit if no more steps or plan completed
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # Execute current step with appropriate agent
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)
                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # Check if step is blocked (failed after max retries), trigger replanning
                # Keep completed steps, replan the blocked step and subsequent steps
                # Also check max replan count to prevent infinite loop
                retry_count = self.step_retry_counts.get(self.current_step_index, 0)
                replan_count = self.replan_counts.get(self.current_step_index, 0)
                if retry_count >= self.max_retry_per_step:
                    if replan_count >= self.max_replan_count:
                        logger.warning(f"Step {self.current_step_index} exceeded max replan attempts, marking as failed...")
                        result += f"\n--- Task Failed ---\nStep {self.current_step_index} failed after {replan_count} replanning attempts.\nOriginal error: {step_result}\n--- End ---\n"
                        break
                    logger.info(f"Step {self.current_step_index} is blocked, triggering replanning...")
                    self.replan_counts[self.current_step_index] = replan_count + 1
                    replan_result = await self._replan(step_result)
                    result += f"\n--- Replanning ---\n{replan_result}\n--- End Replanning ---\n"

                # Check if agent wants to terminate
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return result
        except Exception as e:
            logger.error(f"Error in PlanningFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    async def _create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request using the flow's LLM and PlanningTool."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        system_message_content = (
            "You are a planning assistant. Create a concise, actionable plan with clear steps. "
            "Focus on key milestones rather than detailed sub-steps. "
            "Optimize for clarity and efficiency."
        )
        agents_description = []
        for key in self.executor_keys:
            if key in self.agents:
                agents_description.append(
                    {
                        "name": key.upper(),
                        "description": self.agents[key].description,
                    }
                )
        if len(agents_description) > 1:
            # Add description of agents to select
            system_message_content += (
                f"\nNow we have {agents_description} agents. "
                f"The infomation of them are below: {json.dumps(agents_description)}\n"
                "When creating steps in the planning tool, please specify the agent names using the format '[agent_name]'."
            )

        # Create a system message for plan creation
        system_message = Message.system_message(system_message_content)

        # Create a user message with the request
        user_message = Message.user_message(
            f"Create a reasonable plan with clear steps to accomplish the task: {request}"
        )

        # Call LLM with PlanningTool
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.AUTO,
        )

        # Process tool calls if present
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # Parse the arguments
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments: {args}")
                            continue

                    # Ensure plan_id is set correctly and execute the tool
                    args["plan_id"] = self.active_plan_id

                    # Execute the tool via ToolCollection instead of directly
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"Plan creation result: {str(result)}")
                    return

        # If execution reached here, create a default plan
        logger.warning("Creating default plan")

        # Create default plan using the ToolCollection
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["Analyze request", "Execute task", "Verify results"],
            }
        )

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Parse the current plan to identify the first non-completed step's index and info.
        Returns (None, None) if no active step is found.
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"Plan with ID {self.active_plan_id} not found")
            return None, None

        try:
            # Direct access to plan data from planning tool storage
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Find first non-completed step
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = PlanStepStatus.NOT_STARTED.value
                else:
                    status = step_statuses[i]

                if status in PlanStepStatus.get_active_statuses():
                    # Extract step type/category if available
                    step_info = {"text": step}

                    # Try to extract step type from the text (e.g., [SEARCH] or [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Mark current step as in_progress
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status=PlanStepStatus.IN_PROGRESS.value,
                        )
                    except Exception as e:
                        logger.warning(f"Error marking step as in_progress: {e}")
                        # Update step status directly if needed
                        if i < len(step_statuses):
                            step_statuses[i] = PlanStepStatus.IN_PROGRESS.value
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
                            step_statuses.append(PlanStepStatus.IN_PROGRESS.value)

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # No active step found

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None, None

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """Execute the current step with the specified agent using agent.run()."""
        # Prepare context for the agent with current plan status
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"Step {self.current_step_index}")

        # Create a prompt for the agent to execute the current step
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_status}

        YOUR CURRENT TASK:
        You are now working on step {self.current_step_index}: "{step_text}"

        Please only execute this current step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """

        # Use agent.run() to execute the step
        try:
            step_result = await executor.run(step_prompt)

            # Check if the step execution indicates a failure (Error: prefix)
            result_lower = step_result.strip().lower()
            has_failure = result_lower.startswith("error:")

            if has_failure:
                # Increment retry count
                retry_count = self.step_retry_counts.get(self.current_step_index, 0) + 1
                self.step_retry_counts[self.current_step_index] = retry_count

                # Only mark as blocked after max retries reached
                if retry_count >= self.max_retry_per_step:
                    await self._mark_step_blocked(step_result, f"Failed after {retry_count} retries")
                else:
                    # Still in progress, will retry
                    logger.info(f"Step {self.current_step_index} failed, retry {retry_count}/{self.max_retry_per_step}")
            else:
                # Mark the step as completed after successful execution
                await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"Error executing step {self.current_step_index}: {e}")
            # Increment retry count
            retry_count = self.step_retry_counts.get(self.current_step_index, 0) + 1
            self.step_retry_counts[self.current_step_index] = retry_count

            # Only mark as blocked after max retries reached
            if retry_count >= self.max_retry_per_step:
                await self._mark_step_blocked(str(e), f"Exception after {retry_count} retries")

            return f"Error executing step {self.current_step_index}: {str(e)}"

    async def _mark_step_blocked(self, reason: str = "", notes: str = "") -> None:
        """Mark the current step as blocked with optional reason."""
        if self.current_step_index is None:
            return

        try:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.BLOCKED.value,
                step_notes=notes if notes else reason
            )
        except Exception as e:
            logger.warning(f"Failed to mark step as blocked: {e}")

    async def _mark_step_completed(self) -> None:
        """Mark the current step as completed."""
        if self.current_step_index is None:
            return

        # Clean up retry counts for completed step
        self.step_retry_counts.pop(self.current_step_index, None)
        self.replan_counts.pop(self.current_step_index, None)

        try:
            # Mark the step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.COMPLETED.value,
            )
            logger.info(
                f"Marked step {self.current_step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")
            # Update step status directly in planning tool storage
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # Ensure the step_statuses list is long enough
                while len(step_statuses) <= self.current_step_index:
                    step_statuses.append(PlanStepStatus.NOT_STARTED.value)

                # Update the status
                step_statuses[self.current_step_index] = PlanStepStatus.COMPLETED.value
                plan_data["step_statuses"] = step_statuses

    async def _replan(self, step_result: str) -> str:
        """
        Replan by analyzing failure reason with LLM, then directly update the plan.
        Keeps completed steps, replans the blocked step and subsequent steps.
        Flow calls LLM to get analysis, then updates plan using PlanningTool (not via LLM tool call).
        """
        # Get current plan info
        plan_text = await self._get_plan_text()
        plan_data = self.planning_tool.plans.get(self.active_plan_id)

        # Find completed steps (keep them in the new plan)
        completed_steps = []
        current_step_text = ""
        subsequent_steps = []

        if plan_data and self.current_step_index is not None:
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            for i, step in enumerate(steps):
                if i < self.current_step_index:
                    # Steps before current one - keep if completed
                    if i < len(step_statuses) and step_statuses[i] == PlanStepStatus.COMPLETED.value:
                        completed_steps.append(step)
                elif i == self.current_step_index:
                    # Current step (blocked) - get text for analysis
                    current_step_text = step
                else:
                    # Subsequent steps
                    subsequent_steps.append(step)

        # Call LLM to analyze failure and get new plan (only for blocked and subsequent steps)
        system_msg = Message.system_message(
            "You are a planning assistant. Analyze the failure and provide a new plan. "
            "Respond with JSON only: {\"title\": \"new title\", \"steps\": [\"step1\", \"step2\", ...]}"
        )

        # Build user message with context about completed steps
        completed_context = ""
        if completed_steps:
            completed_context = f"\n\nCOMPLETED STEPS (keep these, do not repeat):\n" + "\n".join(f"- {s}" for s in completed_steps)

        user_msg = Message.user_message(
            f"Current plan:\n{plan_text}\n"
            f"{completed_context}\n\n"
            f"BLOCKED STEP (needs to be replanned): {current_step_text}\n\n"
            f"Failure result:\n{step_result}\n\n"
            f"Please analyze why this step failed and provide an updated plan. "
            f"IMPORTANT: Do NOT include already completed steps in your response. "
            f"Only provide new steps to replace the blocked step and handle any remaining work."
        )

        response = await self.llm.ask(messages=[user_msg], system_msgs=[system_msg])

        # Parse LLM response to get new plan
        try:
            # Try to extract and parse JSON from response with improved robustness
            import re
            # Try to find JSON block (supports nested objects)
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            if json_match:
                new_plan = json.loads(json_match.group())
            else:
                new_plan = json.loads(response)

            # Validate required fields
            if not isinstance(new_plan.get("steps"), list):
                raise ValueError("LLM response missing 'steps' field")

            # Combine completed steps with new steps from LLM
            new_steps_from_llm = new_plan.get("steps", [])
            final_steps = completed_steps + new_steps_from_llm

            # Update step statuses: keep COMPLETED for old steps, reset others to NOT_STARTED
            new_step_statuses = []
            for i, step in enumerate(final_steps):
                if i < len(completed_steps):
                    new_step_statuses.append(PlanStepStatus.COMPLETED.value)
                else:
                    new_step_statuses.append(PlanStepStatus.NOT_STARTED.value)

            # Directly update the plan using PlanningTool
            await self.planning_tool.execute(
                command="update",
                plan_id=self.active_plan_id,
                title=new_plan.get("title"),
                steps=final_steps
            )

            # Update step statuses
            if self.active_plan_id in self.planning_tool.plans:
                self.planning_tool.plans[self.active_plan_id]["step_statuses"] = new_step_statuses

            # Reset retry and replan counts after successful replanning
            self.step_retry_counts[self.current_step_index] = 0
            self.replan_counts[self.current_step_index] = 0

            return f"Plan updated successfully. Completed: {len(completed_steps)}, New steps: {new_steps_from_llm}"
        except Exception as e:
            logger.error(f"Failed to parse LLM response or update plan: {e}")
            # Fallback: keep completed steps, mark current as blocked, add retry step
            # Include original error info for debugging
            original_error = step_result.strip() if step_result else "Unknown error"
            if plan_data:
                new_steps = completed_steps + [
                    f"[BLOCKED] {current_step_text}",
                    f"[RETRY] Alternative approach for: {current_step_text}"
                ]
                await self.planning_tool.execute(
                    command="update",
                    plan_id=self.active_plan_id,
                    steps=new_steps
                )
            return f"Plan updated with fallback strategy. Original error: {original_error}. Parse error: {str(e)}"

    async def _get_plan_text(self) -> str:
        """Get the current plan as formatted text."""
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Generate plan text directly from storage if the planning tool fails."""
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "Untitled Plan")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # Ensure step_statuses and step_notes match the number of steps
            while len(step_statuses) < len(steps):
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            while len(step_notes) < len(steps):
                step_notes.append("")

            # Count steps by status
            status_counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts[PlanStepStatus.COMPLETED.value]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"Progress: {completed}/{total} steps completed ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} completed, {status_counts[PlanStepStatus.IN_PROGRESS.value]} in progress, "
            plan_text += f"{status_counts[PlanStepStatus.BLOCKED.value]} blocked, {status_counts[PlanStepStatus.NOT_STARTED.value]} not started\n\n"
            plan_text += "Steps:\n"

            status_marks = PlanStepStatus.get_status_marks()

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                # Use status marks to indicate step status
                status_mark = status_marks.get(
                    status, status_marks[PlanStepStatus.NOT_STARTED.value]
                )

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   Notes: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Error generating plan text from storage: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    async def _finalize_plan(self) -> str:
        """Finalize the plan and provide a summary using the flow's LLM directly."""
        plan_text = await self._get_plan_text()

        # Create a summary using the flow's LLM directly
        try:
            system_message = Message.system_message(
                "You are a planning assistant. Your task is to summarize the completed plan."
            )

            user_message = Message.user_message(
                f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\nPlease provide a summary of what was accomplished and any final thoughts."
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"Plan completed:\n\n{response}"
        except Exception as e:
            logger.error(f"Error finalizing plan with LLM: {e}")

            # Fallback to using an agent for the summary
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                The plan has been completed. Here is the final plan status:

                {plan_text}

                Please provide a summary of what was accomplished and any final thoughts.
                """
                summary = await agent.run(summary_prompt)
                return f"Plan completed:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Error finalizing plan with agent: {e2}")
                return "Plan completed. Error generating summary."
