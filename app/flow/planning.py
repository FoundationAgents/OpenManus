import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Tuple

from pydantic import BaseModel, Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, PlanStepStatus
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message
from app.tool import PlanningTool


@dataclass
class StepInfo:
    """Represents information about a plan step."""
    text: str
    type: Optional[str] = None
    status: str = PlanStepStatus.NOT_STARTED.value
    notes: str = ""


class PlanData(BaseModel):
    """Represents the data structure of a plan."""
    title: str
    steps: List[str]
    step_statuses: List[str] = Field(default_factory=list)
    step_notes: List[str] = Field(default_factory=list)


class PlanManager:
    """Manages plan creation, updates and status tracking."""
    
    def __init__(self, planning_tool: PlanningTool):
        self.planning_tool = planning_tool
        self.active_plan_id: Optional[str] = None
        self.current_step_index: Optional[int] = None

    async def create_plan(self, request: str, llm: LLM) -> str:
        """Creates a new plan based on the request."""
        plan_id = f"plan_{int(time.time())}"
        self.active_plan_id = plan_id
        
        system_message = Message.system_message(
            "You are a planning assistant. Create a concise, actionable plan with clear steps. "
            "Focus on key milestones rather than detailed sub-steps. "
            "Optimize for clarity and efficiency."
        )
        
        user_message = Message.user_message(
            f"Create a reasonable plan with clear steps to accomplish the task: {request}"
        )
        
        response = await llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice="required",
        )
        
        if response.tool_calls:
            await self._process_tool_calls(response.tool_calls, request)
        else:
            await self._create_default_plan(request)
            
        return plan_id

    async def _process_tool_calls(self, tool_calls: List[dict], request: str) -> None:
        """Process tool calls from LLM response."""
        for tool_call in tool_calls:
            if tool_call.function.name == "planning":
                try:
                    args = json.loads(tool_call.function.arguments)
                    args["plan_id"] = self.active_plan_id
                    await self.planning_tool.execute(**args)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    await self._create_default_plan(request)

    async def _create_default_plan(self, request: str) -> None:
        """Creates a default plan when LLM response fails."""
        await self.planning_tool.execute(
            command="create",
            plan_id=self.active_plan_id,
            title=f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
            steps=["Analyze request", "Execute task", "Verify results"],
        )

    async def get_current_step(self) -> Tuple[Optional[int], Optional[StepInfo]]:
        """Gets the current step information."""
        if not self.active_plan_id or self.active_plan_id not in self.planning_tool.plans:
            return None, None

        try:
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            for i, step in enumerate(steps):
                status = step_statuses[i] if i < len(step_statuses) else PlanStepStatus.NOT_STARTED.value
                
                if status in PlanStepStatus.get_active_statuses():
                    step_info = self._create_step_info(step, i)
                    await self._mark_step_in_progress(i)
                    return i, step_info

            return None, None
        except Exception as e:
            logger.error(f"Error getting current step: {e}")
            return None, None

    def _create_step_info(self, step: str, index: int) -> StepInfo:
        """Creates a StepInfo object from step text."""
        import re
        type_match = re.search(r"\[([A-Z_]+)\]", step)
        step_type = type_match.group(1).lower() if type_match else None
        return StepInfo(text=step, type=step_type)

    async def _mark_step_in_progress(self, step_index: int) -> None:
        """Marks a step as in progress."""
        try:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=step_index,
                step_status=PlanStepStatus.IN_PROGRESS.value,
            )
        except Exception as e:
            logger.warning(f"Error marking step as in_progress: {e}")
            self._update_step_status_directly(step_index, PlanStepStatus.IN_PROGRESS.value)

    def _update_step_status_directly(self, step_index: int, status: str) -> None:
        """Updates step status directly in planning tool storage."""
        if self.active_plan_id in self.planning_tool.plans:
            plan_data = self.planning_tool.plans[self.active_plan_id]
            step_statuses = plan_data.get("step_statuses", [])
            
            while len(step_statuses) <= step_index:
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            
            step_statuses[step_index] = status
            plan_data["step_statuses"] = step_statuses

    async def mark_step_completed(self, step_index: int) -> None:
        """Marks a step as completed."""
        try:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=step_index,
                step_status=PlanStepStatus.COMPLETED.value,
            )
        except Exception as e:
            logger.warning(f"Failed to mark step as completed: {e}")
            self._update_step_status_directly(step_index, PlanStepStatus.COMPLETED.value)

    async def get_plan_text(self) -> str:
        """Gets the current plan as formatted text."""
        try:
            result = await self.planning_tool.execute(
                command="get",
                plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Generates plan text from storage."""
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            return self._format_plan_text(plan_data)
        except Exception as e:
            logger.error(f"Error generating plan text: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    def _format_plan_text(self, plan_data: Dict) -> str:
        """Formats plan data into readable text."""
        title = plan_data.get("title", "Untitled Plan")
        steps = plan_data.get("steps", [])
        step_statuses = plan_data.get("step_statuses", [])
        step_notes = plan_data.get("step_notes", [])

        # Ensure lists are properly sized
        while len(step_statuses) < len(steps):
            step_statuses.append(PlanStepStatus.NOT_STARTED.value)
        while len(step_notes) < len(steps):
            step_notes.append("")

        # Calculate progress
        status_counts = self._count_step_statuses(step_statuses)
        completed = status_counts[PlanStepStatus.COMPLETED.value]
        total = len(steps)
        progress = (completed / total) * 100 if total > 0 else 0

        # Build plan text
        plan_text = [
            f"Plan: {title} (ID: {self.active_plan_id})",
            "=" * (len(title) + 20),
            f"\nProgress: {completed}/{total} steps completed ({progress:.1f}%)",
            f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} completed, "
            f"{status_counts[PlanStepStatus.IN_PROGRESS.value]} in progress, "
            f"{status_counts[PlanStepStatus.BLOCKED.value]} blocked, "
            f"{status_counts[PlanStepStatus.NOT_STARTED.value]} not started\n",
            "Steps:"
        ]

        # Add steps with status marks
        status_marks = PlanStepStatus.get_status_marks()
        for i, (step, status, notes) in enumerate(zip(steps, step_statuses, step_notes)):
            status_mark = status_marks.get(status, status_marks[PlanStepStatus.NOT_STARTED.value])
            plan_text.append(f"{i}. {status_mark} {step}")
            if notes:
                plan_text.append(f"   Notes: {notes}")

        return "\n".join(plan_text)

    def _count_step_statuses(self, step_statuses: List[str]) -> Dict[str, int]:
        """Counts the number of steps in each status."""
        counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}
        for status in step_statuses:
            if status in counts:
                counts[status] += 1
        return counts


class PlanningFlow(BaseFlow):
    """A flow that manages planning and execution of tasks using agents."""

    def __init__(
        self,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **data
    ):
        # Initialize base components
        self.llm = data.pop("llm", LLM())
        self.planning_tool = data.pop("planning_tool", PlanningTool())
        
        # Initialize plan manager
        self.plan_manager = PlanManager(self.planning_tool)
        
        # Set executor keys
        self.executor_keys = data.pop("executors", [])
        
        # Initialize base flow
        super().__init__(agents, **data)
        
        # Set default executor keys if not specified
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """Gets an appropriate executor agent for the current step."""
        if step_type and step_type in self.agents:
            return self.agents[step_type]
        
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]
        
        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """Executes the planning flow with agents."""
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            # Create initial plan if input provided
            if input_text:
                await self.plan_manager.create_plan(input_text, self.llm)

            result = []
            while True:
                # Get and execute current step
                step_index, step_info = await self.plan_manager.get_current_step()
                
                if step_index is None:
                    result.append(await self._finalize_plan())
                    break

                # Execute step with appropriate agent
                step_result = await self._execute_step(step_index, step_info)
                result.append(step_result)

                # Check if agent wants to terminate
                executor = self.get_executor(step_info.type)
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error in PlanningFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    async def _execute_step(self, step_index: int, step_info: StepInfo) -> str:
        """Executes a single step with the appropriate agent."""
        executor = self.get_executor(step_info.type)
        plan_status = await self.plan_manager.get_plan_text()
        
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_status}

        YOUR CURRENT TASK:
        You are now working on step {step_index}: "{step_info.text}"

        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """

        try:
            step_result = await executor.run(step_prompt)
            await self.plan_manager.mark_step_completed(step_index)
            return step_result
        except Exception as e:
            logger.error(f"Error executing step {step_index}: {e}")
            return f"Error executing step {step_index}: {str(e)}"

    async def _finalize_plan(self) -> str:
        """Finalizes the plan and provides a summary."""
        plan_text = await self.plan_manager.get_plan_text()

        try:
            # Try to get summary from LLM
            system_message = Message.system_message(
                "You are a planning assistant. Your task is to summarize the completed plan."
            )
            user_message = Message.user_message(
                f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\n"
                "Please provide a summary of what was accomplished and any final thoughts."
            )
            response = await self.llm.ask(
                messages=[user_message],
                system_msgs=[system_message]
            )
            return f"Plan completed:\n\n{response}"
        except Exception as e:
            logger.error(f"Error finalizing plan with LLM: {e}")
            
            # Fallback to agent summary
            try:
                summary = await self.primary_agent.run(
                    f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\n"
                    "Please provide a summary of what was accomplished and any final thoughts."
                )
                return f"Plan completed:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Error finalizing plan with agent: {e2}")
                return "Plan completed. Error generating summary."
