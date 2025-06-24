from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str # Identificador do componente que originou o evento (e.g., "ManusAgent", "WorkflowOrchestrator")
    version: str = "1.0"


class TaskInfo(BaseModel):
    task_id: str
    parent_task_id: Optional[str] = None
    # Outros metadados relevantes da tarefa podem ser adicionados aqui


# Eventos de Gerenciamento de Tarefas e Fluxo de Trabalho
class TaskCreatedEvent(BaseEvent):
    task_info: TaskInfo
    user_prompt: str
    initial_plan: Optional[Dict[str, Any]] = None # Pode ser o DAG inicial ou uma descrição


class TaskStateChangeEvent(BaseEvent):
    task_id: str
    old_state: str
    new_state: str # e.g., "PENDING", "RUNNING", "WAITING_HUMAN", "COMPLETED", "FAILED"
    details: Optional[Dict[str, Any]] = None


class SubtaskCompletedEvent(BaseEvent):
    task_id: str # ID da tarefa principal
    subtask_id: str
    result: Optional[Any] = None
    next_subtasks_ready: List[str] = Field(default_factory=list)


class SubtaskFailedEvent(BaseEvent):
    task_id: str # ID da tarefa principal
    subtask_id: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class WorkflowCheckpointEvent(BaseEvent):
    task_id: str
    checkpoint_id: str # ID do checkpoint salvo no armazenamento durável
    reason: str # e.g., "periodic", "before_human_input", "subtask_completed"
    state_snapshot_summary: Optional[Dict[str, Any]] = None # Um resumo do que foi salvo


class ParallelExecutionPossibleEvent(BaseEvent):
    task_id: str
    subtasks_available_for_parallel_run: List[str]


# Eventos de Ação do Agente e Ferramentas
class AgentActionScheduledEvent(BaseEvent): # Publicado pelo orquestrador para um agente
    task_id: str
    subtask_id: str
    agent_name: str
    action_details: Dict[str, Any] # e.g., prompt para o agente, estado para carregar


class ToolCallInitiatedEvent(BaseEvent): # Publicado por um agente antes de chamar uma ferramenta
    task_id: str
    subtask_id: str
    agent_name: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: str # ID da chamada da ferramenta para rastreamento


class ToolCallResultEvent(BaseEvent): # Publicado por um agente após uma ferramenta retornar
    task_id: str
    subtask_id: str
    agent_name: str
    tool_name: str
    tool_call_id: str
    result: Any # Pode ser o ToolResult completo ou uma representação
    error: Optional[str] = None
    is_success: bool


# Eventos de Intervenção Humana
class HumanInputRequiredEvent(BaseEvent): # Publicado por um agente ou ferramenta
    task_id: str
    subtask_id: str
    requesting_component: str # e.g., "ManusAgent:AskHumanTool"
    question_or_prompt: str
    context: Optional[Dict[str, Any]] = None # Contexto para o usuário entender o pedido
    relevant_checkpoint_id: Optional[str] = None # Checkpoint para retomar após o input


class HumanInputProvidedEvent(BaseEvent): # Publicado pelo componente de UI/Notificação
    task_id: str
    subtask_id: str
    response_to_event_id: UUID # ID do HumanInputRequiredEvent original
    user_response: Any
    responder_info: Optional[Dict[str, str]] = None # e.g., user_id, if available


# Exemplo de como usar:
#
# async def example_usage(event_bus):
#     task_created = TaskCreatedEvent(
#         source="WebApp",
#         task_info=TaskInfo(task_id="task_123"),
#         user_prompt="Please summarize the provided document."
#     )
#     await event_bus.publish("task_events", task_created.model_dump(mode='json'))
#
#     human_input_needed = HumanInputRequiredEvent(
#         source="ManusAgent",
#         task_id="task_123",
#         subtask_id="subtask_abc",
#         requesting_component="AskHumanTool",
#         question_or_prompt="The document mentions 'Project X'. Do you want more details on this?",
#         relevant_checkpoint_id="chkpt_xyz"
#     )
#     await event_bus.publish("human_interaction_events", human_input_needed.model_dump(mode='json'))
