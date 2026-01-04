"""
Enhanced planning methods for PlanningFlow.

This file contains the advanced planning methods that integrate:
- Tree-of-Thoughts reasoning
- Reflection-based plan improvement
- Advanced prompt engineering

These methods can be integrated into the PlanningFlow class.
"""

import json

from app.llm_router import llm_router
from app.logger import logger
from app.prompt.advanced_planning import (
    ADVANCED_PLANNING_SYSTEM_PROMPT,
    REFLECTION_ENHANCED_PLANNING_PROMPT,
    TOT_EVALUATION_PROMPT,
    TREE_OF_THOUGHTS_PLANNING_PROMPT,
    format_reflections,
)
from app.reasoning import TreeOfThoughts
from app.schema import Message, ToolChoice


async def create_plan_with_tot(self, request: str, num_alternatives: int = 3) -> None:
    """
    Create a plan using Tree-of-Thoughts reasoning.

    This method:
    1. Generates multiple alternative approaches
    2. Evaluates each approach
    3. Selects the best one
    4. Creates the final plan

    Args:
        request: The task description
        num_alternatives: Number of alternative approaches to explore
    """
    logger.info(
        f"Creating plan with Tree-of-Thoughts (alternatives={num_alternatives})"
    )

    # Initialize ToT if not already done
    if self.tree_of_thoughts is None:
        self.tree_of_thoughts = TreeOfThoughts(
            max_depth=2, max_branches=num_alternatives  # Root + alternatives
        )

    planning_llm = llm_router.select_model("planning")

    # Step 1: Generate alternative approaches
    tot_prompt = TREE_OF_THOUGHTS_PLANNING_PROMPT.format(
        task_description=request, num_alternatives=num_alternatives
    )

    user_message = Message.user_message(tot_prompt)

    try:
        response = await planning_llm.ask(messages=[user_message])

        # Add root thought
        root = self.tree_of_thoughts.add_thought(
            content=f"Task: {request}", metadata={"type": "root", "task": request}
        )

        # Parse alternatives from response and add as children
        # Simple parsing - look for "## Approach" markers
        approaches = response.split("## Approach")[1:]  # Skip before first approach

        for i, approach_text in enumerate(approaches[:num_alternatives], 1):
            self.tree_of_thoughts.add_thought(
                content=f"Approach {i}:\n{approach_text.strip()}",
                parent_id=root.id if root else None,
                metadata={"type": "alternative", "index": i},
            )

        # Step 2: Evaluate all alternatives
        await self.tree_of_thoughts.evaluate_all_thoughts(
            llm=planning_llm, evaluation_prompt=TOT_EVALUATION_PROMPT
        )

        # Step 3: Get best path
        best_path = self.tree_of_thoughts.get_best_path()

        if len(best_path) < 2:
            logger.warning(
                "ToT did not produce valid alternatives, falling back to standard planning"
            )
            await self._create_initial_plan_standard(request)
            return

        # The best alternative is the second node in the path (after root)
        best_alternative = best_path[1]

        logger.info(
            f"Selected best alternative (score={best_alternative.score:.2f}): "
            f"{best_alternative.content[:100]}..."
        )

        # Step 4: Convert best alternative to structured plan
        await self._convert_tot_to_plan(best_alternative.content, request)

    except Exception as e:
        logger.error(f"Error in ToT planning: {e}")
        # Fallback to standard planning
        await self._create_initial_plan_standard(request)


async def create_plan_with_reflection(self, request: str) -> None:
    """
    Create a plan enhanced by past reflections.

    This method:
    1. Retrieves relevant reflections from past executions
    2. Incorporates lessons learned into the planning prompt
    3. Creates an improved plan

    Args:
        request: The task description
    """
    logger.info("Creating plan with reflection-based improvement")

    planning_llm = llm_router.select_model("planning")

    # Get relevant reflections
    relevant_reflections = self.reflection_engine._select_relevant_reflections(
        task_description=request, max_count=5
    )

    if not relevant_reflections:
        logger.info("No relevant reflections found, using standard planning")
        await self._create_initial_plan_standard(request)
        return

    # Format reflections for prompt
    reflections_text = format_reflections(relevant_reflections)

    # Create reflection-enhanced prompt
    reflection_prompt = REFLECTION_ENHANCED_PLANNING_PROMPT.format(
        task_description=request, reflections=reflections_text
    )

    # Add agent information
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
        reflection_prompt += (
            f"\n\n**Available Agents:**\n"
            f"{json.dumps(agents_description, indent=2)}\n"
            "Specify agent assignments using '[agent_name]' format."
        )

    user_message = Message.user_message(reflection_prompt)

    try:
        # Get LLM response with planning tool
        response = await planning_llm.ask_tool(
            messages=[user_message],
            system_msgs=[Message.system_message(ADVANCED_PLANNING_SYSTEM_PROMPT)],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.AUTO,
        )

        # Process tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        args = json.loads(args)

                    args["plan_id"] = self.active_plan_id
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"Reflection-enhanced plan created: {str(result)}")
                    return

        # Fallback
        logger.warning("No tool call in reflection-enhanced planning, using standard")
        await self._create_initial_plan_standard(request)

    except Exception as e:
        logger.error(f"Error in reflection-enhanced planning: {e}")
        await self._create_initial_plan_standard(request)


async def _create_initial_plan_standard(self, request: str) -> None:
    """
    Standard plan creation (original method, kept as fallback).

    This is the original _create_initial_plan method, renamed for clarity.
    """
    logger.info(f"Creating standard plan with ID: {self.active_plan_id}")

    system_message_content = ADVANCED_PLANNING_SYSTEM_PROMPT

    agents_description = []
    for key in self.executor_keys:
        if key in self.agents:
            agents_description.append(
                {
                    "name": key.UPPER(),
                    "description": self.agents[key].description,
                }
            )

    if len(agents_description) > 1:
        system_message_content += (
            f"\n\n**Available Agents:**\n"
            f"{json.dumps(agents_description, indent=2)}\n"
            "Specify agent assignments using '[agent_name]' format."
        )

    system_message = Message.system_message(system_message_content)
    user_message = Message.user_message(
        f"Create a comprehensive plan to accomplish: {request}"
    )

    planning_llm = llm_router.select_model("planning")
    response = await planning_llm.ask_tool(
        messages=[user_message],
        system_msgs=[system_message],
        tools=[self.planning_tool.to_param()],
        tool_choice=ToolChoice.AUTO,
    )

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                args = tool_call.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)

                args["plan_id"] = self.active_plan_id
                result = await self.planning_tool.execute(**args)

                logger.info(f"Standard plan created: {str(result)}")
                return

    # Default plan fallback
    logger.warning("Creating minimal default plan")
    await self.planning_tool.execute(
        command="create",
        plan_id=self.active_plan_id,
        title=f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
        steps=["Analyze request", "Execute task", "Verify results"],
    )


async def _convert_tot_to_plan(self, alternative_text: str, request: str) -> None:
    """
    Convert a ToT alternative into a structured plan.

    Args:
        alternative_text: The text of the selected alternative approach
        request: Original task description
    """
    logger.info("Converting ToT alternative to structured plan")

    planning_llm = llm_router.select_model("planning")

    conversion_prompt = f"""Convert this high-level approach into a detailed, structured plan.

Task: {request}

Selected Approach:
{alternative_text}

Create a plan with specific, actionable steps using the planning tool.
Each step should be clear and executable."""

    user_message = Message.user_message(conversion_prompt)
    system_message = Message.system_message(ADVANCED_PLANNING_SYSTEM_PROMPT)

    try:
        response = await planning_llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.AUTO,
        )

        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        args = json.loads(args)

                    args["plan_id"] = self.active_plan_id
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"ToT plan conversion successful: {str(result)}")
                    return

        # Fallback
        await self._create_initial_plan_standard(request)

    except Exception as e:
        logger.error(f"Error converting ToT to plan: {e}")
        await self._create_initial_plan_standard(request)


async def _create_initial_plan(self, request: str) -> None:
    """
    Main entry point for plan creation with advanced reasoning.

    This method decides which planning strategy to use based on configuration.
    """
    if not self.use_advanced_planning:
        await self._create_initial_plan_standard(request)
        return

    # Check if we have enough execution history for reflection
    has_history = len(self.reflection_engine.execution_history) >= 3

    # Decision logic for planning strategy
    if has_history:
        # Use reflection-enhanced planning if we have learnings
        logger.info("Using reflection-enhanced planning")
        await self.create_plan_with_reflection(request)
    else:
        # Use ToT for complex tasks when no history available
        logger.info("Using Tree-of-Thoughts planning")
        await self.create_plan_with_tot(request, num_alternatives=3)
