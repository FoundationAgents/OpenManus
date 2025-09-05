# tool/planning.py
# tool/planning.py
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator
import uuid

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult
from app.logger import logger

# Enum para status da subtarefa (similar ao PlanStepStatus de app.flow.planning)
SubtaskStatus = Literal["PENDING", "READY", "RUNNING", "COMPLETED", "FAILED", "WAITING_HUMAN"]

class Subtask(BaseModel):
    id: str = Field(default_factory=lambda: f"subtask_{uuid.uuid4().hex[:8]}")
    name: str
    status: SubtaskStatus = "PENDING"
    depends_on: List[str] = Field(default_factory=list)
    agent_name: Optional[str] = None
    tool_calls_spec: Optional[List[Dict[str, Any]]] = None # Especificação das chamadas de ferramenta
    result: Optional[Any] = None
    error: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('status')
    def validate_status(cls, value):
        allowed_statuses = ["PENDING", "READY", "RUNNING", "COMPLETED", "FAILED", "WAITING_HUMAN"]
        if value not in allowed_statuses:
            raise ValueError(f"Invalid status: {value}. Allowed statuses are: {allowed_statuses}")
        return value

class Plan(BaseModel):
    plan_id: str
    title: str
    subtasks: Dict[str, Subtask] = Field(default_factory=dict) # Subtasks por ID
    # Adicionar outros metadados do plano se necessário, como created_at, updated_at

    def get_subtask(self, subtask_id: str) -> Optional[Subtask]:
        return self.subtasks.get(subtask_id)

    def add_subtask_object(self, subtask: Subtask) -> bool:
        if subtask.id in self.subtasks:
            logger.warning(f"Subtask with ID '{subtask.id}' already exists in plan '{self.plan_id}'.")
            return False
        # Validar dependências
        for dep_id in subtask.depends_on:
            if dep_id not in self.subtasks:
                logger.error(f"Dependency '{dep_id}' for subtask '{subtask.id}' not found in plan '{self.plan_id}'.")
                # Poderia levantar um erro aqui ou retornar False
                raise ToolError(f"Dependency '{dep_id}' not found when adding subtask '{subtask.id}'.")
        self.subtasks[subtask.id] = subtask
        return True

    def update_subtask_status(self, subtask_id: str, new_status: SubtaskStatus) -> bool:
        subtask = self.get_subtask(subtask_id)
        if subtask:
            subtask.status = new_status
            # Se uma tarefa for concluída, atualizar o status das dependentes para READY
            if new_status == "COMPLETED":
                for st_id, st_obj in self.subtasks.items():
                    if st_obj.status == "PENDING" and subtask_id in st_obj.depends_on:
                        if all(self.subtasks[dep].status == "COMPLETED" for dep in st_obj.depends_on):
                            st_obj.status = "READY"
            return True
        return False

    def get_ready_subtasks(self) -> List[Subtask]:
        ready = []
        for subtask in self.subtasks.values():
            if subtask.status == "PENDING": # Verificar se todas as dependências estão concluídas
                if all(self.subtasks[dep_id].status == "COMPLETED" for dep_id in subtask.depends_on):
                    subtask.status = "READY" # Mudar status para READY
                    ready.append(subtask)
            elif subtask.status == "READY":
                ready.append(subtask)
        return ready

    def are_all_subtasks_completed(self) -> bool:
        if not self.subtasks:
            return False # Um plano vazio não está "concluído" no sentido de ter realizado trabalho
        return all(st.status == "COMPLETED" for st in self.subtasks.values())


_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans with dependent subtasks for solving complex tasks.
The tool provides functionality for creating plans, adding subtasks with dependencies, updating subtask statuses, and tracking overall progress.
"""

class PlanningTool(BaseTool):
    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create_plan, add_subtask, update_subtask_status, get_plan_details, list_plans, set_active_plan, get_ready_subtasks, delete_plan.",
                "enum": [
                    "create_plan",
                    "add_subtask",
                    "update_subtask_status",
                    "get_plan_details",
                    "list_plans",
                    "set_active_plan",
                    "get_ready_subtasks",
                    "delete_plan"
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for most commands. If not provided for 'create_plan', a new ID will be generated.",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for 'create_plan' command.",
                "type": "string",
            },
            "subtasks_definition": {
                "description": "List of subtask definitions for 'create_plan'. Each definition is an object with 'id', 'name', and 'depends_on' (list of IDs).",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique ID for the subtask within the plan."},
                        "name": {"type": "string", "description": "Description of the subtask."},
                        "depends_on": {"type": "array", "items": {"type": "string"}, "description": "List of subtask IDs this subtask depends on."}
                    },
                    "required": ["id", "name"]
                }
            },
            "subtask_id": {"type": "string", "description": "ID of the subtask for 'add_subtask' or 'update_subtask_status'."},
            "subtask_name": {"type": "string", "description": "Name/description of the subtask for 'add_subtask'."},
            "depends_on": {"type": "array", "items": {"type": "string"}, "description": "List of subtask IDs for 'add_subtask'."},
            "new_status": {
                "description": "New status for 'update_subtask_status'.",
                "enum": ["PENDING", "READY", "RUNNING", "COMPLETED", "FAILED", "WAITING_HUMAN"],
                "type": "string",
            },
            "agent_name": {"type": "string", "description": "Agent name for 'add_subtask' (optional)."},
            "notes": {"type": "string", "description": "Notes for 'update_subtask_status' (optional)."},
            "result": {"type": "object", "description": "Result for 'update_subtask_status' when COMPLETED (optional)."},
            "error_message": {"type": "string", "description": "Error message for 'update_subtask_status' when FAILED (optional)."},
        },
        "required": ["command"],
    }

    plans: Dict[str, Plan] = {}
    _current_plan_id: Optional[str] = None

    async def execute(self, command: str, **kwargs: Any) -> ToolResult:
        logger.debug(f"PlanningTool executing command: {command} with args: {kwargs}")
        plan_id = kwargs.get("plan_id")

        if command == "create_plan":
            title = kwargs.get("title")
            subtasks_def = kwargs.get("subtasks_definition")
            if not title: raise ToolError("Title is required for create_plan.")
            plan_id_to_use = plan_id or f"plan_{uuid.uuid4().hex[:8]}"
            return self._create_plan(plan_id_to_use, title, subtasks_def or [])

        # For other commands, ensure plan_id or _current_plan_id is available
        if not plan_id and command not in ["list_plans", "set_active_plan"]: # set_active_plan needs plan_id from kwargs
            plan_id = self._current_plan_id
            if not plan_id:
                raise ToolError("No active plan set and plan_id not provided for command.")

        if command == "add_subtask":
            subtask_id = kwargs.get("subtask_id", f"subtask_{uuid.uuid4().hex[:8]}")
            name = kwargs.get("subtask_name")
            depends_on = kwargs.get("depends_on", [])
            agent_name = kwargs.get("agent_name")
            if not name: raise ToolError("Subtask name is required for add_subtask.")
            return self._add_subtask(plan_id, subtask_id, name, depends_on, agent_name)

        elif command == "update_subtask_status":
            subtask_id = kwargs.get("subtask_id")
            new_status = kwargs.get("new_status")
            if not subtask_id or not new_status: raise ToolError("subtask_id and new_status are required.")
            return self._update_subtask_status(plan_id, subtask_id, new_status,
                                               kwargs.get("notes"), kwargs.get("result"), kwargs.get("error_message"))

        elif command == "get_plan_details":
            return self._get_plan_details(plan_id)

        elif command == "list_plans":
            return self._list_plans()

        elif command == "set_active_plan":
            target_plan_id = kwargs.get("plan_id")
            if not target_plan_id: raise ToolError("plan_id is required for set_active_plan.")
            return self._set_active_plan(target_plan_id)

        elif command == "get_ready_subtasks":
            return self._get_ready_subtasks(plan_id)

        elif command == "delete_plan":
            target_plan_id = kwargs.get("plan_id")
            if not target_plan_id: raise ToolError("plan_id is required for delete_plan.")
            return self._delete_plan(target_plan_id)

        else:
            raise ToolError(f"Unrecognized command: {command}")

    def _create_plan(self, plan_id: str, title: str, subtasks_definition: List[Dict]) -> ToolResult:
        if plan_id in self.plans:
            raise ToolError(f"Plan with ID '{plan_id}' already exists.")

        new_plan = Plan(plan_id=plan_id, title=title)

        # Add subtasks with dependency validation
        # Need to add all subtasks first, then validate dependencies, or add in order if possible
        temp_subtasks_dict = {}
        for st_def in subtasks_definition:
            st_id = st_def.get("id")
            st_name = st_def.get("name")
            st_deps = st_def.get("depends_on", [])
            if not st_id or not st_name:
                raise ToolError(f"Subtask definition missing 'id' or 'name': {st_def}")
            if st_id in temp_subtasks_dict:
                 raise ToolError(f"Duplicate subtask ID '{st_id}' in subtasks_definition.")
            temp_subtasks_dict[st_id] = Subtask(id=st_id, name=st_name, depends_on=st_deps, agent_name=st_def.get("agent_name"))

        # Now add to plan, which will validate dependencies against existing tasks in the plan
        for st_id in temp_subtasks_dict: # Iterate in a defined order if possible, e.g., sorted IDs or by dependency level
            try:
                new_plan.add_subtask_object(temp_subtasks_dict[st_id])
            except ToolError as e_dep: # Catch dependency errors from add_subtask_object
                # This happens if a dependency is listed but the depended-on task isn't in subtasks_definition
                raise ToolError(f"Error adding subtask '{st_id}': {str(e_dep)}. Ensure all dependencies are defined in 'subtasks_definition'.")


        self.plans[plan_id] = new_plan
        self._current_plan_id = plan_id
        return ToolResult(output=f"Plan '{title}' (ID: {plan_id}) created successfully.\n{self._format_plan(new_plan)}")

    def _add_subtask(self, plan_id: str, subtask_id: str, name: str, depends_on: List[str], agent_name: Optional[str]) -> ToolResult:
        plan = self.plans.get(plan_id)
        if not plan: raise ToolError(f"Plan with ID '{plan_id}' not found.")

        subtask = Subtask(id=subtask_id, name=name, depends_on=depends_on, agent_name=agent_name)
        if not plan.add_subtask_object(subtask):
            return ToolResult(error=f"Failed to add subtask '{name}' (ID: {subtask_id}) to plan '{plan_id}'. It might already exist or have invalid dependencies.")
        return ToolResult(output=f"Subtask '{name}' (ID: {subtask_id}) added to plan '{plan_id}'.\n{self._format_plan(plan)}")

    def _update_subtask_status(self, plan_id: str, subtask_id: str, new_status: SubtaskStatus,
                               notes: Optional[str], result: Optional[Any], error_message: Optional[str]) -> ToolResult:
        plan = self.plans.get(plan_id)
        if not plan: raise ToolError(f"Plan with ID '{plan_id}' not found.")
        subtask = plan.get_subtask(subtask_id)
        if not subtask: raise ToolError(f"Subtask with ID '{subtask_id}' not found in plan '{plan_id}'.")

        subtask.status = new_status
        if notes is not None: subtask.notes = notes
        if result is not None and new_status == "COMPLETED": subtask.result = result
        if error_message is not None and new_status == "FAILED": subtask.error = error_message

        # Trigger dependency update
        if new_status == "COMPLETED":
            for st_id, st_obj in plan.subtasks.items():
                if st_obj.status == "PENDING" and subtask_id in st_obj.depends_on:
                    if all(plan.subtasks[dep].status == "COMPLETED" for dep in st_obj.depends_on):
                        st_obj.status = "READY"
                        logger.info(f"Subtask {st_id} is now READY as its dependencies are met.")

        return ToolResult(output=f"Status of subtask '{subtask.name}' (ID: {subtask_id}) in plan '{plan_id}' updated to {new_status}.\n{self._format_plan(plan)}")

    def _get_plan_details(self, plan_id: str) -> ToolResult:
        plan = self.plans.get(plan_id)
        if not plan: raise ToolError(f"Plan with ID '{plan_id}' not found.")
        return ToolResult(output=self._format_plan(plan))

    def _list_plans(self) -> ToolResult:
        if not self.plans:
            return ToolResult(output="No plans available.")
        output = "Available plans:\n"
        for plan_id, plan_obj in self.plans.items():
            active_marker = " (active)" if plan_id == self._current_plan_id else ""
            completed_count = sum(1 for st in plan_obj.subtasks.values() if st.status == "COMPLETED")
            total_count = len(plan_obj.subtasks)
            output += f"  - {plan_obj.title} (ID: {plan_id}{active_marker}) - {completed_count}/{total_count} subtasks completed.\n"
        return ToolResult(output=output)

    def _set_active_plan(self, plan_id: str) -> ToolResult:
        if plan_id not in self.plans:
            raise ToolError(f"Plan with ID '{plan_id}' not found.")
        self._current_plan_id = plan_id
        return ToolResult(output=f"Plan '{self.plans[plan_id].title}' (ID: {plan_id}) is now active.")

    def _get_ready_subtasks(self, plan_id: str) -> ToolResult:
        plan = self.plans.get(plan_id)
        if not plan: raise ToolError(f"Plan with ID '{plan_id}' not found.")

        ready_subtasks = plan.get_ready_subtasks() # This method now updates status to READY internally

        if not ready_subtasks:
            if plan.are_all_subtasks_completed():
                 return ToolResult(output=f"All subtasks in plan '{plan.title}' (ID: {plan_id}) are completed.")
            return ToolResult(output=f"No subtasks are currently ready to run in plan '{plan.title}' (ID: {plan_id}).")

        output_str = f"Ready subtasks for plan '{plan.title}' (ID: {plan_id}):\n"
        for st in ready_subtasks:
            output_str += f"  - ID: {st.id}, Name: {st.name}, Dependencies: {st.depends_on or 'None'}\n"
        return ToolResult(output=output_str)

    def _delete_plan(self, plan_id: str) -> ToolResult:
        if plan_id not in self.plans:
            raise ToolError(f"Plan with ID '{plan_id}' not found.")
        del self.plans[plan_id]
        if self._current_plan_id == plan_id:
            self._current_plan_id = None
        return ToolResult(output=f"Plan '{plan_id}' deleted.")

    def _format_plan(self, plan: Plan) -> str:
        output = f"Plan: {plan.title} (ID: {plan.plan_id})\n"
        output += "=" * (len(plan.title) + len(plan.plan_id) + 10) + "\n"

        total_subtasks = len(plan.subtasks)
        status_counts: Dict[SubtaskStatus, int] = {
            "PENDING": 0, "READY": 0, "RUNNING": 0,
            "COMPLETED": 0, "FAILED": 0, "WAITING_HUMAN": 0
        }
        for st in plan.subtasks.values():
            status_counts[st.status] = status_counts.get(st.status, 0) + 1

        completed_count = status_counts["COMPLETED"]
        progress_percent = (completed_count / total_subtasks) * 100 if total_subtasks > 0 else 0

        output += f"Progress: {completed_count}/{total_subtasks} subtasks completed ({progress_percent:.1f}%)\n"
        output += f"Status Breakdown: P: {status_counts['PENDING']}, R: {status_counts['READY']}, X: {status_counts['RUNNING']}, C: {status_counts['COMPLETED']}, F: {status_counts['FAILED']}, H: {status_counts['WAITING_HUMAN']}\n\n"
        output += "Subtasks:\n"

        # Simple topological sort for display, or just sort by ID for now
        # For a more complex DAG display, libraries might be needed.
        # Sorting by ID for consistent display order.
        sorted_subtask_ids = sorted(plan.subtasks.keys())

        for subtask_id in sorted_subtask_ids:
            st = plan.subtasks[subtask_id]
            status_symbol = {
                "PENDING": "[P]", "READY": "[R]", "RUNNING": "[X]",
                "COMPLETED": "[✓]", "FAILED": "[!]", "WAITING_HUMAN": "[H]"
            }.get(st.status, "[?]")

            deps_str = f"(depends on: {', '.join(st.depends_on)})" if st.depends_on else ""
            agent_str = f" (Agent: {st.agent_name})" if st.agent_name else ""
            output += f"  {status_symbol} ID: {st.id} - {st.name} {deps_str}{agent_str}\n"
            if st.notes:
                output += f"      Notes: {st.notes}\n"
            if st.result and st.status == "COMPLETED":
                 # Truncate long results for display
                result_str = str(st.result)
                if len(result_str) > 100: result_str = result_str[:100] + "..."
                output += f"      Result: {result_str}\n"
            if st.error and st.status == "FAILED":
                output += f"      Error: {st.error}\n"
        return output
