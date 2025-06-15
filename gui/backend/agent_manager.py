import asyncio
import uuid
import re # Added for plan parsing
from typing import Any, Dict, List, Optional

from app.agent.manus import Manus
from app.flow.flow_factory import FlowFactory, FlowType
from app.logger import logger # Main application logger
from app.config import config as app_config # Main app config
from app.schema import AgentState
from app.tool import ToolCollection # For listing tools
from app.tool.base import BaseTool # Added
from app.tool.ask_human import AskHuman # Added

# Global state for the agent manager (simplification for now)
# In a production scenario, you might want a class or a more robust state management.
active_execution_id: Optional[str] = None
current_agent_instance: Optional[Any] = None # Can be Manus or PlanningFlow
current_agent_task: Optional[asyncio.Task] = None

# For handling user input for AskHuman tool
# This is a simplified mechanism. A more robust solution might involve events or callbacks.
_user_input_queue = asyncio.Queue()
_agent_waiting_for_input = False

# --- GUIAskHumanWrapper Definition ---
class GUIAskHumanWrapper(BaseTool):
    name: str = AskHuman().name # Inherit name from original
    description: str = AskHuman().description # Inherit description
    parameters: dict = AskHuman().parameters # Inherit parameters

    async def execute(self, inquire: str, **kwargs) -> str:
        # This now calls the function within agent_manager.py
        logger.info(f"GUIAskHumanWrapper: Relaying inquiry to GUI: {inquire}")
        return await request_human_input_from_gui(inquire)
# --- End GUIAskHumanWrapper Definition ---


async def start_new_agent_session(prompt: str, agent_type: str = "manus") -> str:
    global active_execution_id, current_agent_instance, current_agent_task, _agent_waiting_for_input

    if current_agent_task and not current_agent_task.done():
        # For simplicity, prevent starting a new session if one is running.
        # Production systems might queue requests or manage multiple agents.
        raise RuntimeError("An agent session is already running.")

    active_execution_id = str(uuid.uuid4())
    _agent_waiting_for_input = False # Reset input flag

    # Bind execution_id to the logger for all subsequent logs in this session
    # This specific logger instance will carry the bound ID.
    # Note: this only affects logs emitted through *this specific* `bound_logger`.
    # If other parts of the app import `app.logger.logger` directly, they won't have this binding.
    # The `gui_sink` in `app/logger.py` handles `record.extra.get("execution_id")`,
    # so we need to ensure the agent's internal logger calls are bound.
    # This can be done by passing the bound logger or by rebinding within agent methods.
    # A simpler way for now: the main agent run call will be wrapped with logger.bind.
    
    bound_logger = logger.bind(execution_id=active_execution_id)
    bound_logger.info(f"Starting new agent session (type: {agent_type}) with prompt: {prompt}")

    try:
        if agent_type == "manus":
            # Manus.create() is async
            agent = await Manus.create() 
            # Make sure Manus agent uses the bound logger or its logs get the execution_id
            # This is a bit tricky as Manus might use its own logger instance internally.
            # For now, we rely on the fact that `gui_sink` will be active for all loggers.
            # And we will use logger.patch to add execution_id to records if not present.
            current_agent_instance = agent
            
            # Replace AskHuman with the GUI wrapper
            logger.info("Replacing AskHuman tool with GUIAskHumanWrapper for GUI interaction.")
            gui_ask_human_wrapper = GUIAskHumanWrapper()
            agent.available_tools.add_tool(gui_ask_human_wrapper, replace=True)

            # Wrap the agent's run method with the logger binding
            async def run_with_bound_log():
                # This patch adds execution_id to all log records generated within this context
                # if they don't already have one from a more specific binding.
                with logger.contextualize(execution_id=active_execution_id):
                    await current_agent_instance.run(prompt)
            
            current_agent_task = asyncio.create_task(run_with_bound_log())

        elif agent_type == "planning_flow":
            # Assuming PlanningFlow needs a Manus agent as an executor
            manus_agent = await Manus.create()

            # Replace AskHuman in the manus_agent used by the flow
            logger.info("Replacing AskHuman tool with GUIAskHumanWrapper for planning_flow's Manus agent.")
            gui_ask_human_wrapper = GUIAskHumanWrapper()
            manus_agent.available_tools.add_tool(gui_ask_human_wrapper, replace=True)

            # The PlanningFlow itself doesn't have an async create method in the provided snippets
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents={"manus": manus_agent}, # or other configured agents
                # Pass execution_id to PlanningFlow if it can accept it for internal logging
            )
            current_agent_instance = flow
            async def run_flow_with_bound_log():
                 with logger.contextualize(execution_id=active_execution_id):
                    await current_agent_instance.execute(prompt)

            current_agent_task = asyncio.create_task(run_flow_with_bound_log())
        else:
            bound_logger.error(f"Unknown agent type: {agent_type}")
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return active_execution_id
    except Exception as e:
        bound_logger.exception(f"Failed to start agent session: {e}")
        # Reset global state on failure
        active_execution_id = None
        current_agent_instance = None
        current_agent_task = None
        raise

def get_agent_status() -> dict:
    status = {
        "execution_id": active_execution_id,
        "is_running": current_agent_task is not None and not current_agent_task.done(),
        "agent_state": None,
        "is_waiting_for_input": _agent_waiting_for_input,
        "current_step": None, # For planning flow
        "max_steps": None,    # For planning flow
    }
    if current_agent_instance:
        if hasattr(current_agent_instance, 'state'):
            status["agent_state"] = current_agent_instance.state.value if isinstance(current_agent_instance.state, AgentState) else current_agent_instance.state
        
        if hasattr(current_agent_instance, 'current_step_index') and current_agent_instance.current_step_index is not None: # For PlanningFlow
             status["current_step"] = current_agent_instance.current_step_index
        elif hasattr(current_agent_instance, 'current_step'): # For BaseAgent
             status["current_step"] = current_agent_instance.current_step
        
        if hasattr(current_agent_instance, 'max_steps'):
             status["max_steps"] = current_agent_instance.max_steps

    return status

async def get_agent_plan() -> Optional[dict]: # Return type changed
    if current_agent_instance and hasattr(current_agent_instance, "_get_plan_text"): # Check for PlanningFlow
        try:
            plan_text = await current_agent_instance._get_plan_text()
            # This returns a string. For the GUI, a structured dict would be better.
            # For now, we'll return the text and parse/display on frontend.
            # A more advanced implementation would have _get_plan_data() returning structured info.
            
            # Basic parsing of the plan_text (example, might need adjustment)
            title_match = re.search(r"Plan: (.*?) \(ID: (.*?)\)", plan_text)
            title = title_match.group(1) if title_match else "Plan"
            plan_id = title_match.group(2) if title_match else active_execution_id

            steps_raw = re.findall(r"(\d+)\. \[\([✓→! ]\)\] (.*?)(?:\n   Notes: (.*?))?(?=\n\d+\. \[|\n\n|$)", plan_text, re.DOTALL)
            steps = []
            for step_data in steps_raw:
                status_map = {"✓": "completed", "→": "in_progress", "!": "blocked", " ": "not_started"}
                steps.append({
                    "index": int(step_data[0]),
                    "status_icon": step_data[1],
                    "status": status_map.get(step_data[1], "unknown"),
                    "text": step_data[2].strip(),
                    "notes": step_data[3].strip() if step_data[3] else ""
                })
            
            progress_match = re.search(r"Progress: (\d+)/(\d+) steps completed \((.*?%)\)", plan_text)
            completed_steps = int(progress_match.group(1)) if progress_match else 0
            total_steps = int(progress_match.group(2)) if progress_match else len(steps)
            progress_percent = progress_match.group(3) if progress_match else "0.0%"

            return {
                "id": plan_id,
                "title": title,
                "raw_text": plan_text, # Keep raw text for now
                "steps": steps,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "progress_percent": progress_percent
            }

        except Exception as e:
            logger.error(f"Error getting/parsing agent plan: {e}")
            return {"error": str(e), "raw_text": "Could not retrieve or parse plan."}
    return None


async def provide_input_to_agent(user_input: str) -> bool:
    global _agent_waiting_for_input
    if _agent_waiting_for_input and not _user_input_queue.full():
        await _user_input_queue.put(user_input)
        _agent_waiting_for_input = False # Input provided, agent no longer waiting for manager
        logger.info(f"User input '{user_input}' provided to agent via queue.")
        return True
    logger.warning(f"Agent not waiting for input or queue full. Input '{user_input}' ignored.")
    return False

# This function will be called by a modified AskHuman tool
async def request_human_input_from_gui(prompt_to_user: str) -> str:
    global _agent_waiting_for_input
    logger.info(f"Agent is requesting human input via GUI: {prompt_to_user}")
    _agent_waiting_for_input = True
    # The agent's AskHuman tool will await this queue.
    # The message from AskHuman (prompt_to_user) could also be sent via SSE to GUI if needed.
    # For now, the GUI polls /api/agent/status which shows _agent_waiting_for_input.
    # The GUI would then show the prompt (which it might get from the log stream if AskHuman logs it)
    # and use POST /api/agent/input.
    
    # This is a placeholder for the actual prompt to be displayed in the GUI.
    # Ideally, this prompt (`prompt_to_user`) should also be sent to the GUI
    # perhaps via a special SSE event or stored for GET /api/agent/status to return.
    # For now, the frontend might need to infer the prompt from the logs.
    
    user_response = await _user_input_queue.get()
    logger.info(f"Human input received from GUI queue: {user_response}")
    return user_response


def get_available_tools() -> List[dict]:
    # Create a temporary Manus instance just to list its tools.
    # This is not ideal if Manus.create() has heavy side effects or is slow.
    # A better way would be to have tools registered centrally or Manus having a static method.
    try:
        # Manus.create() is async, but this function is sync.
        # This is problematic. For now, let's assume we have a default Manus instance
        # or can list tools by inspecting the ToolCollection class or a default instance.
        # Let's try to instantiate Manus synchronously for tool listing if possible,
        # or make this function async.
        # Given the plan, this function is called from a sync FastAPI route handler,
        # so it should remain sync or the route handler needs to be async.
        # For now, let's just use the default tools from Manus class definition.
        
        temp_agent = Manus() # This uses the default_factory for available_tools
        tools_list = []
        for tool_name, tool_instance in temp_agent.available_tools.tool_map.items():
            tools_list.append({
                "name": tool_name,
                "description": tool_instance.description,
                "parameters": tool_instance.parameters if hasattr(tool_instance, 'parameters') else "N/A"
            })
        return tools_list
    except Exception as e:
        logger.error(f"Error listing available tools: {e}")
        return [{"name": "Error", "description": "Could not retrieve tools.", "parameters": {}}]


def get_agent_config() -> dict:
    # Return non-sensitive parts of the app_config
    # Be careful about exposing sensitive data like API keys.
    cfg = {
        "llm_default_model": app_config.llm.get("default", {}).get("model"),
        "sandbox_enabled": app_config.sandbox.use_sandbox if app_config.sandbox else False,
        "workspace_root": str(app_config.workspace_root),
        "max_steps_default": Manus.model_fields["max_steps"].default, # Get default from Pydantic model
    }
    return cfg
