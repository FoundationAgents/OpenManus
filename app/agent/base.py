import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional, Any # Adicionado Any

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import ROLE_TYPE, AgentState, Memory, Message, Role # Adicionado Role


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination") # Será reavaliado no contexto de subtarefas
    current_step: int = Field(default=0, description="Current step in execution for a given action")
    user_pause_requested_event: asyncio.Event = Field(default_factory=asyncio.Event, description="Event to signal a user-initiated pause.")

    tool_calls: Optional[List[dict]] = Field(default=None, description="Tool calls planned by think()") # Mudou para List[dict] para ser compatível com Pydantic

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        # Event bus e checkpointer seriam injetados aqui se fossem atributos diretos do BaseAgent
        # self.event_bus = kwargs.get("event_bus")
        # self.checkpointer = kwargs.get("checkpointer")
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            raise e
        finally:
            if self.state not in [
                AgentState.FINISHED, AgentState.ERROR, AgentState.USER_HALTED,
                AgentState.AWAITING_USER_FEEDBACK, AgentState.USER_PAUSED,
            ]:
                self.state = previous_state

    def update_memory(
        self,
        role: ROLE_TYPE,
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }
        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # kwargs para tool_message já inclui name e tool_call_id
        # Para outras mensagens, apenas base64_image é relevante aqui.
        msg_kwargs = {"base64_image": base64_image}
        if role == "tool":
            msg_kwargs.update(kwargs)
            
        self.memory.add_message(message_map[role](content, **msg_kwargs))

    # O método run() original foi removido. A lógica de execução será orientada por eventos.
    # Os agentes reagirão a AgentActionScheduledEvent.

    async def process_action(
        self,
        action_prompt: Optional[str] = None,
        human_response: Optional[str] = None,
        resuming_from_checkpoint_id: Optional[str] = None,
        # Outros detalhes da ação do AgentActionScheduledEvent.action_details
        **action_details
    ) -> None:
        """
        Processa uma ação agendada (geralmente uma subtarefa),
        potencialmente continuando de um checkpoint ou com input humano.
        Esta é uma única iteração: carrega estado (se aplicável), pensa, age (publica ToolCallInitiatedEvents).
        O resultado da ação (conclusão da subtarefa, falha, etc.) será comunicado via eventos pelo agente.
        """
        async with self.state_context(AgentState.RUNNING): # Define o estado como RUNNING para este processamento
            self.current_step = 0 # Resetar current_step para cada nova ação/subtarefa processada
            logger.info(f"Agent {self.name}: Processing action/subtask. Details: {action_details}")

            if resuming_from_checkpoint_id:
                # TODO: Implementar lógica para carregar estado do checkpoint.
                # Isso envolveria chamar o PostgreSQLCheckpointer.load_checkpoint_data
                # e depois aplicar o estado ao self (ex: self.memory, self.current_step, etc.)
                # checkpointer = self.dependencies.get('checkpointer') # Exemplo de como obter dependência
                # if checkpointer:
                #     checkpoint_data = await checkpointer.load_checkpoint_data(UUID(resuming_from_checkpoint_id))
                #     if checkpoint_data:
                #         await checkpointer.deserialize_agent_state(
                #             self,
                #             checkpoint_data.get('agent_memory_snapshot'),
                #             checkpoint_data.get('agent_internal_state_snapshot')
                #         )
                #         logger.info(f"Agent {self.name} state restored from checkpoint {resuming_from_checkpoint_id}.")
                # else:
                #     logger.error(f"Checkpointer not available to agent {self.name} for restoring from checkpoint.")
                logger.info(f"Agent {self.name} would resume from checkpoint {resuming_from_checkpoint_id} if fully implemented.")
                pass

            # Adicionar prompt da ação e resposta humana (se houver) à memória
            if action_prompt:
                self.update_memory(Role.USER, action_prompt)
            
            if human_response:
                self.update_memory(Role.USER, f"Human input received: {human_response}")

            # O loop de `think` e `act` (publicação de ToolCallInitiatedEvent)
            # e o processamento de `ToolCallResultEvent` acontecerão aqui.
            # Este é um ciclo único de think-act para a EDA.

            # Primeiro `think` para planejar as ferramentas para a ação/subtarefa atual
            if await self.think(): # think() define self.tool_calls (List[ToolCall])
                await self.act()   # act() publica ToolCallInitiatedEvent para cada tool_call
            else:
                # Se think() não planejou ferramentas, pode ser que a subtarefa possa ser resolvida
                # com uma resposta direta ou já está concluída com base no prompt/input.
                logger.info(f"Agent {self.name} did not plan any tool calls for the current action. Subtask might be simple or require direct response.")
                # O agente precisaria de lógica para determinar se deve publicar SubtaskCompletedEvent aqui.
                # Ex: Se self.memory.messages[-1].role == ASSISTANT e não tem tool_calls, pode ser uma resposta final.
                # Esta lógica será mais refinada.
                # Por enquanto, se não houver ferramentas, a ação é considerada "concluída" do ponto de vista deste ciclo.
                # O agente deve então publicar um evento de conclusão de subtarefa.
                # Exemplo:
                # await self.publish_subtask_completed_event(action_details.get("subtask_id"), action_details.get("task_id"), {"response": self.memory.messages[-1].content})
                pass

            # Após act() publicar os eventos de ferramenta, este método `process_action` termina.
            # O agente agora espera por `ToolCallResultEvent`s, que serão tratados por `handle_tool_result`.
            logger.info(f"Agent {self.name}: Finished initial processing of action. Waiting for tool results or next action.")
            # O estado do agente (RUNNING) é mantido. O Orchestrator gerencia o estado da subtarefa.

    @abstractmethod
    async def think(self) -> bool:
        """
        Analisa o estado atual (memória, prompt da ação) e planeja as próximas `tool_calls`.
        Define `self.tool_calls` com uma lista de objetos `ToolCall` (de app.schema).
        Retorna True se alguma `ToolCall` foi planejada, False caso contrário.
        """
        pass

    @abstractmethod
    async def act(self) -> None:
        """
        Itera sobre `self.tool_calls` (preenchido por `think()`) e, para cada uma,
        publica um `ToolCallInitiatedEvent` no barramento de eventos.
        """
        pass

    @abstractmethod
    async def handle_tool_result(self, tool_name: str, tool_call_id: str, tool_observation: str, subtask_id: str, workflow_id: str) -> None:
        """
        Processa o resultado de uma execução de ferramenta (recebido via ToolCallResultEvent).
        Adiciona a observação à memória.
        Decide o próximo passo:
        - Chamar `think()` novamente para planejar mais ferramentas para a subtarefa atual.
        - Publicar `SubtaskCompletedEvent` se a subtarefa estiver concluída.
        - Publicar `SubtaskFailedEvent` se a subtarefa falhou (após tentativas de auto-correção).
        - Chamar `AskHuman` (que publicará `HumanInputRequiredEvent`) se necessário.
        """
        pass

    # O método step() original, que continha um loop, não é mais o principal ponto de entrada para a execução.
    # Pode ser mantido como um helper interno se uma única iteração think-act for útil,
    # ou sua lógica pode ser incorporada em process_action e handle_tool_result.
    # Por enquanto, vamos comentá-lo para evitar confusão.
    # @abstractmethod
    # async def step(self) -> str:
    #     """Execute a single step in the agent's workflow."""

    @abstractmethod
    async def should_request_feedback(self) -> bool: # Ainda pode ser útil para auto-reflexão
        """Determines if the agent should pause and request user feedback."""
        pass

    def handle_stuck_state(self):
        stuck_prompt = ("Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted.")
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}" # next_step_prompt pode ser obsoleto

    def is_stuck(self) -> bool: # Ainda útil para auto-reflexão
        if len(self.memory.messages) < 2 * (self.duplicate_threshold +1) : # Precisa de mais histórico para detectar stuck
            return False

        # Considera as últimas N respostas do assistente
        assistant_responses = [msg.content for msg in self.memory.messages[- (2 * self.duplicate_threshold + 2):] if msg.role == Role.ASSISTANT and msg.tool_calls is None and msg.content]
        if not assistant_responses or len(assistant_responses) < self.duplicate_threshold +1:
            return False

        # Verifica se a última resposta se repetiu N vezes
        last_response = assistant_responses[-1]
        return assistant_responses.count(last_response) > self.duplicate_threshold


    @property
    def messages(self) -> List[Message]:
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        self.memory.messages = value

    async def cleanup(self): # Adicionado para garantir que todos os agentes tenham cleanup
        logger.info(f"Cleaning up agent {self.name}...")
        # Adicionar lógica de limpeza específica do agente aqui, se necessário
        if hasattr(SANDBOX_CLIENT, 'cleanup') and callable(SANDBOX_CLIENT.cleanup):
            try:
                await SANDBOX_CLIENT.cleanup() # Limpeza do sandbox global
            except Exception as e:
                logger.error(f"Error during SANDBOX_CLIENT.cleanup in BaseAgent {self.name}: {e}")
        logger.info(f"Agent {self.name} cleanup complete.")
