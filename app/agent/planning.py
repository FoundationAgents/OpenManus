import time
import json, re, ast

from typing import Any, Dict, List, Optional
from pydantic import Field, model_validator

from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.agent.browser import BrowserAgent
from app.agent.manus import Manus
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT, NEXT_STEP_AGENT_PROMPT, NEXT_STEP_TOOL_PROMPT
from app.schema import TOOL_CHOICE_TYPE, Message, ToolCall, ToolChoice, AgentState, ExecutorChoice
from app.tool import PlanningTool, Terminate, ToolCollection, BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.config import config
from app.exceptions import TokenLimitExceeded

class PlanningAgent(ToolCallAgent):
    """
    An agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and tracks progress through individual steps until task completion.
    """

    name: str = "planning"
    description: str = "An agent that creates and manages plans to solve tasks"

    system_prompt: str = PLANNING_SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), PythonExecute(), StrReplaceEditor(), Terminate())
    )
    # available_agents: List[BaseAgent] = Field(default_factory=lambda: [Manus()])
    available_agents: List[BaseAgent] = Field(default_factory=lambda: [Manus(available_tools=ToolCollection(BrowserUseTool(), Terminate()))])
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    agent_calls: List[BaseAgent] = Field(default_factory=list)

    select_agent_or_tool: ExecutorChoice = ExecutorChoice.NONE

    active_plan_id: Optional[str] = Field(default=None)

    # Add a dictionary to track the step status for each tool call
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)
    current_step_index: Optional[int] = None

    max_steps: int = 20

    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "PlanningAgent":
        """Initialize the agent with a default plan ID and validate required tools."""
        self.active_plan_id = f"plan_{int(time.time())}"

        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        return self

    async def get_cuffent_plan_status(self) -> str:
        current_plan_status = ''
        if self.active_plan_id:
            current_plan_status = f"CURRENT PLAN STATUS:\n{await self.get_plan()}"
        return current_plan_status

    async def get_available_agent_info(self) -> List[Dict[str, Any]]:
        available_agent_info = [{
            "type": "agent",
            "property": {"name": agent.name, "description": agent.description}}
            for agent in self.available_agents
        ] if self.available_agents else []
        return available_agent_info

    async def parse_selected_agent_response(self, select_agent_res) -> object:
        pattern = r'```json\n(.*?)\n```'
        match = re.search(pattern, select_agent_res, re.DOTALL)

        if not match:
            logger.error("No JSON content found.")
            return None

        json_str = match.group(1).strip()

        try:
            select_agent_info = json.loads(json_str)
        except json.JSONDecodeError:
            try:
                select_agent_info = ast.literal_eval(json_str)
            except (SyntaxError, ValueError) as e:
                logger.error("fInvalid JSON: {e}")
                return None
        return select_agent_info

    async def get_selected_agent(self, select_agent_info) -> BaseAgent | None:
        selected_agent = None
        if isinstance(select_agent_info['agent_name'], str) and len(select_agent_info['agent_name']) > 0:
            agent_name = select_agent_info['agent_name']
            for agent in self.available_agents:
                if agent_name == agent.name:
                    selected_agent = agent

        return selected_agent

    async def get_selected_agent_task_desc(self, select_agent_info) -> str | None:
        select_agent_task_desc = None
        if isinstance(select_agent_info['agent_task_desc'], str) and len(select_agent_info['agent_task_desc']) > 0:
            select_agent_task_desc = select_agent_info['agent_task_desc']
        return select_agent_task_desc

    async def generate_message_for_select_agent(self):
        select_agent_messages :List[Message] = []

        # inster user request into select_agent_messages
        select_agent_messages.append(Message.user_message(f"The original request is: {self.request}"))

        # get current plan status, and insert it into select_agent_messages
        current_plan_status = await self.get_cuffent_plan_status()
        if current_plan_status and len(current_plan_status) > 0:
            select_agent_messages.append(Message.user_message(current_plan_status))

        # add current step index into select_agent_messages
        select_agent_messages.append(Message.user_message(f"The current plan step index is {self.current_step_index}"))

        # generate next_step_agent_prompt with avaliable agents info, and insert it into select_agent_messages
        available_agents = await self.get_available_agent_info()
        selected_agents_format = """{"agent_name":${agent name}, "agent_task_desc":${plan step content for the agent need to execute}}"""
        next_step_agent_prompt = NEXT_STEP_AGENT_PROMPT.format(
            avaliable_agents=json.dumps(available_agents), selected_agents_format=selected_agents_format)
        select_agent_messages.append(Message.user_message(next_step_agent_prompt))

        return select_agent_messages

    async def select_agent_for_current_plan_step(self) -> Dict | None:
        # init messages for select agent
        select_agent_message = await self.generate_message_for_select_agent()
        # ask llm to select agent for current plan
        try:
            # Get response with tool options
            select_agent_response = await self.llm.ask(
                messages=select_agent_message,
                system_msgs=[Message.system_message("Please select an appropriate agent to execute the current plan step.")],
                stream=False,
                temperature=0.0
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return None
            raise

        # if agent is selected, insert selected agent to self.agent_calls, update self.step_execution_tracker, then return
        logger.info(f'select agent response: {select_agent_response}')
        if (select_agent_response):
            select_agent_info = await self.parse_selected_agent_response(select_agent_response)
            if select_agent_info:
                selected_agent = await self.get_selected_agent(select_agent_info)
                selected_agent_task_desc = await self.get_selected_agent_task_desc(select_agent_info)
                if selected_agent and selected_agent_task_desc:
                    return {"agent": selected_agent, "agent_task_desc": selected_agent_task_desc, "content": None}
        return {"agent": None, "agent_task_desc": None, "content": "No agent are selected"}

    async def generate_messages_for_select_tool(self):
        select_tool_messages :List[Message] = []

        # add request message
        select_tool_messages.append(Message.user_message(f"The original request is: {self.request}"))

        # get current plan status and next step prompt, insert them into messages
        current_plan_status = await self.get_cuffent_plan_status()
        if current_plan_status and len(current_plan_status) > 0:
            select_tool_messages.append(Message.user_message(current_plan_status))

         # add current step index into select_agent_messages
        select_tool_messages.append(Message.user_message(f"The current plan step index is {self.current_step_index}"))

        # insert select tool prompt
        select_tool_messages.append(Message.user_message(NEXT_STEP_TOOL_PROMPT))

        return select_tool_messages

    async def select_tool_for_current_plan_step(self) -> Dict | None:
        # init message for select tool
        select_tool_messages = await self.generate_messages_for_select_tool()

        try:
            # Get response with tool options
            select_tool_response = await self.llm.ask_tool(
                messages=select_tool_messages,
                system_msgs=([Message.system_message("Please select an appropriate tool to execute the current plan step.")]),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        tool_calls = (
            select_tool_response.tool_calls if select_tool_response and select_tool_response.tool_calls else []
        )
        content = select_tool_response.content if select_tool_response and select_tool_response.content else ""

        return {"tool_calls": tool_calls, "content": content}

    async def think(self) -> bool:
        # get the current step index before thinking, if all steps are completed, set planning agent status to FINISH
        self.current_step_index = await self._get_current_step_index()
        if self.current_step_index == None:
            self.state = AgentState.FINISHED
            return False

        # add current plan status to slef.messages
        current_plan_status = await self.get_cuffent_plan_status()
        if current_plan_status and len(current_plan_status) > 0:
            self.update_memory("user", current_plan_status)

        # before think, init self.select_agent_or_tool value
        self.select_agent_or_tool = ExecutorChoice.NONE

        # ask llm to select agent for current plan step
        agent_info = await self.select_agent_for_current_plan_step()
        if agent_info:
            selected_agent :BaseAgent = agent_info["agent"]
            selected_agent_task_desc :str = agent_info["agent_task_desc"]
            # flag agent is selected to execute the current plan step
            self.select_agent_or_tool = ExecutorChoice.AGENT
            # insert selected agent into agent_calls for self.act to run
            self.agent_calls = [selected_agent]
            # insert agent name and agent task desc into self.messages
            self.messages.append(Message.user_message(f"Agent {selected_agent.name} is selected to execute the current plan step"))
            self.messages.append(Message.user_message(f"The task of agent is: {selected_agent_task_desc}"))
            if self.current_step_index is not None:
                self.step_execution_tracker[selected_agent.name] = {
                    "step_index": self.current_step_index,
                    "agent_name": selected_agent.name,
                    "status": "pending",  # Will be updated after execution
                }
            return True

        tool_info = await self.select_tool_for_current_plan_step()
        # After thinking, if we decided to execute a tool and it's not a planning tool or special tool,
        # associate it with the current step for tracking
        if tool_info:
            if tool_info["tool_calls"] and len(tool_info["tool_calls"]) > 0:
                # set self.tool_calls
                self.tool_calls = tool_info["tool_calls"]
                self.select_agent_or_tool = ExecutorChoice.TOOL
                self.memory.add_message(Message.from_tool_calls(content=tool_info["content"], tool_calls=tool_info["tool_calls"]))
                tool_call = self.tool_calls[0]  # Get the most recent tool call
                if (tool_call.function.name != "planning"
                    and tool_call.function.name not in self.special_tool_names
                    and self.current_step_index is not None):
                    self.step_execution_tracker[tool_call.id] = {
                        "step_index": self.current_step_index,
                        "tool_name": tool_call.function.name,
                        "status": "pending",  # Will be updated after execution
                    }
        # if both agent an tool are not selected, do not exectue following steps
        self.state = AgentState.FINISHED
        self.messages.append(Message.user_message(f"No agent or tools are selected to execute the current plan step"))
        return False

    async def run_selected_agent_for_current_plan_step(self) -> str:
        # get selected agent
        selected_agent_call = self.agent_calls[0]
        # get agent task desc
        selected_agent_task_desc = self.messages[len(self.messages) - 1]
        # cleanup selected agent
        await selected_agent_call.cleanup()
        # insert planning agent's request and plan steps to selected agent memory, let selected agent to know the contenxt info
        selected_agent_call.update_memory("user", f"The original request is: {self.request}")
        current_plan_status = await self.get_cuffent_plan_status()
        if current_plan_status and len(current_plan_status) > 0:
            selected_agent_call.update_memory("user", current_plan_status)
        selected_agent_call.update_memory("user", f"The current plan step index is {self.current_step_index}")

        # run agent
        agent_call_result = await selected_agent_call.run(f"Your task is to accomplish the current step of the plan: {selected_agent_task_desc.content}")
        return agent_call_result

    async def run_selected_tool_for_current_plan_step(self) -> str:
        tool_call_result = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            tool_call_result.append(result)

        return "\n\n".join(tool_call_result)

    async def act(self) -> str:
        # if in self.think, an agent is selected, run the selected agent
        if self.select_agent_or_tool == ExecutorChoice.AGENT and self.agent_calls and len(self.agent_calls) > 0:
            # get selected agent
            selected_agent_call = self.agent_calls[0]
            # run agent
            agent_call_result = await self.run_selected_agent_for_current_plan_step()
            self.update_memory("user", f"The execute process of the plan step {self.current_step_index} is: {agent_call_result}")
            # update run agent status
            if selected_agent_call.name in self.step_execution_tracker:
                self.step_execution_tracker[selected_agent_call.name]["status"] = "completed"
                self.step_execution_tracker[selected_agent_call.name]["result"] = agent_call_result
                await self.update_plan_status(selected_agent_call.name)
            return agent_call_result

        # if in self.think, a tool is selected, invoke ToolAgent act to run selected tool
        if self.select_agent_or_tool == ExecutorChoice.TOOL and self.tool_calls and len(self.tool_calls) > 0:
            # The tool call result has been added to self.messages in super().act(), do not add it here
            tool_call_result = await self.run_selected_tool_for_current_plan_step()
            self.update_memory("user", f"The execute process of the plan step {self.current_step_index} is: {tool_call_result}")
            latest_tool_call = self.tool_calls[0]
            # Update the execution status to completed
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = tool_call_result
                # Update the plan status if this was a non-planning, non-special tool
                if (latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names):
                    await self.update_plan_status(latest_tool_call.id)
            return tool_call_result
        return ''

    async def get_plan(self) -> str:
        """Retrieve the current plan status."""
        if not self.active_plan_id:
            return "No active plan. Please create a plan first."

        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    async def update_plan_status(self, call_id: str) -> None:
        """
        Update the current plan progress based on completed tool execution.
        Only marks a step as completed if the associated tool has been successfully executed.
        """
        if not self.active_plan_id:
            return

        if call_id not in self.step_execution_tracker:
            logger.warning(f"No step tracking found for tool call {call_id}")
            return

        tracker = self.step_execution_tracker[call_id]
        if tracker["status"] != "completed":
            logger.warning(f"Tool call {call_id} has not completed successfully")
            return

        step_index = tracker["step_index"]

        try:
            # Mark the step as completed
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "step_status": "completed",
                },
            )
            logger.info(
                f"Marked step {step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")

    async def _get_current_step_index(self) -> Optional[int]:
        """
        Parse the current plan to identify the first non-completed step's index.
        Returns None if no active step is found.
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

            # Find the first non-completed step
            for i, line in enumerate(plan_lines[steps_index + 1 :], start=0):
                if "[ ]" in line or "[→]" in line:  # not_started or in_progress
                    # Mark current step as in_progress
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": i,
                            "step_status": "in_progress",
                        },
                    )
                    return i

            return None  # No active step found
        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None

    async def create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        messages = [
            Message.user_message(
                f"Analyze the request and create a plan with ID {self.active_plan_id}: {request}"
            )
        ]
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
                break

        if not plan_created:
            logger.warning("No plan created from initial request")
            tool_msg = Message.assistant_message(
                "Error: Parameter `plan_id` is required for command: create"
            )
            self.memory.add_message(tool_msg)

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            await self.create_initial_plan(request)
        return await super().run(request)
