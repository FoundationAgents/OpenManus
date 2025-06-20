import asyncio
import json
from typing import Any, List, Optional, Union
from uuid import UUID # Adicionado para current_workflow_id

from pydantic import Field

from app.config import config
from app.agent.base import BaseAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
# Removido SANDBOX_CLIENT, pois a execução da ferramenta agora é gerenciada pelas próprias ferramentas
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice, Function, Role
# CriticAgent removido daqui, sua lógica será gerenciada pelo Orchestrator ou um agente supervisor
# from app.agent.critic_agent import CriticAgent

from app.tool import CreateChatCompletion, Terminate, ToolCollection # Terminate é uma ferramenta especial
from app.tool.base import ToolResult
# Outras importações de ferramentas específicas não são necessárias aqui, pois available_tools as gerencia.

# Importações para o novo paradigma orientado a eventos
from app.event_bus.redis_bus import RedisEventBus
from app.event_bus.events import (
    ToolCallInitiatedEvent, # Este evento não será publicado se a execução da ferramenta for direta
    SubtaskCompletedEvent,
    SubtaskFailedEvent,
    HumanInputRequiredEvent # AskHuman agora publica isso
)
# from app.checkpointing.postgresql_checkpointer import PostgreSQLCheckpointer


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(BaseAgent):
    name: str = "toolcall"
    description: str = "an agent that can execute tool calls based on events."
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: Optional[str] = NEXT_STEP_PROMPT

    available_tools: ToolCollection = Field(default_factory=ToolCollection) # Será preenchido por subclasses como Manus
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name.lower()]) # Normalizado para lower

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    event_bus: RedisEventBus # Injetado no construtor
    # checkpointer: Optional[PostgreSQLCheckpointer] = None # Injetado se necessário

    current_workflow_id: Optional[UUID] = None
    current_subtask_id: Optional[str] = None
    current_subtask_prompt: Optional[str] = None

    max_steps_per_subtask: int = 10 # Número de ciclos de think/act por subtarefa
    max_observe: Optional[Union[int, bool]] = 10000 # Limite para observação de ferramenta

    # Contador para tentativas de auto-correção dentro de handle_tool_result
    _max_self_correction_attempts_per_tool_error: int = 1


    def __init__(self, event_bus: RedisEventBus, **data: Any):
        super().__init__(**data)
        self.event_bus = event_bus
        # Se available_tools não for definido pela subclasse, inicializar vazio
        if not isinstance(self.available_tools, ToolCollection):
            self.available_tools = ToolCollection()
        # Adicionar Terminate se não estiver lá, pois é fundamental
        if not self.available_tools.get_tool(Terminate().name):
            self.available_tools.add_tool(Terminate())


    async def process_action(
        self,
        workflow_id: UUID,
        subtask_id: str,
        action_prompt: Optional[str] = None,
        human_response: Optional[str] = None,
        resuming_from_checkpoint_id: Optional[str] = None,
        **action_details
    ) -> None:
        self.current_workflow_id = workflow_id
        self.current_subtask_id = subtask_id
        self.current_subtask_prompt = action_prompt or f"Process subtask {subtask_id}"
        self.current_step = 0

        async with self.state_context(AgentState.RUNNING):
            logger.info(f"Agent {self.name}: Starting subtask '{self.current_subtask_id}' for workflow '{self.current_workflow_id}'. Prompt: '{self.current_subtask_prompt[:100]}...'")

            if resuming_from_checkpoint_id:
                logger.info(f"Agent {self.name} resuming from checkpoint {resuming_from_checkpoint_id} for subtask {self.current_subtask_id}.")
                # Lógica de restauração de checkpoint (memória, current_step, etc.)
                # checkpoint_data = await self.checkpointer.load_checkpoint_data(UUID(resuming_from_checkpoint_id))
                # if checkpoint_data:
                #     await self.checkpointer.deserialize_agent_state(self, ...) # Passar os snapshots corretos
                # else:
                #     await self._publish_subtask_failed(f"Could not load checkpoint {resuming_from_checkpoint_id}.")
                #     return
                pass # Placeholder

            if human_response:
                self.update_memory(Role.USER, f"Human input received: {human_response}")
            
            self.update_memory(Role.USER, self.current_subtask_prompt)

            # Iniciar o ciclo de processamento da subtarefa
            await self._process_current_subtask_iteration()

    async def _process_current_subtask_iteration(self):
        """Executa um ciclo de think e depois lida com as tool_calls planejadas."""
        self.current_step += 1
        if self.current_step > self.max_steps_per_subtask:
            logger.warning(f"Agent {self.name} reached max_steps_per_subtask ({self.max_steps_per_subtask}) for subtask {self.current_subtask_id}.")
            await self._publish_subtask_failed("Max steps reached for subtask.")
            return

        if await self.think(): # Pensa e define self.tool_calls
            await self.act_and_handle_results() # Executa ferramentas e lida com resultados
        else:
            # Think não produziu ferramentas. A subtarefa pode estar concluída.
            last_message_content = "Subtask completed without new tool actions."
            if self.memory.messages and self.memory.messages[-1].role == Role.ASSISTANT and self.memory.messages[-1].content:
                last_message_content = self.memory.messages[-1].content

            logger.info(f"Agent {self.name}: No tools planned by think() for subtask '{self.current_subtask_id}'. Assuming completion.")
            await self._publish_subtask_completed(result={"response": last_message_content})


    async def think(self) -> bool:
        current_system_prompt = self.system_prompt.format(directory=str(config.workspace_root)) if self.system_prompt else None
        try:
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=[Message.system_message(current_system_prompt)] if current_system_prompt else None,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except TokenLimitExceeded as tle:
            logger.error(f"Token limit exceeded for subtask {self.current_subtask_id}: {tle}")
            await self._publish_subtask_failed(f"Token limit exceeded: {tle}")
            return False
        except Exception as e:
            logger.error(f"LLM API error for subtask {self.current_subtask_id}: {e}", exc_info=True)
            await self._publish_subtask_failed(f"LLM API error: {e}")
            return False

        if response is None:
            logger.error(f"LLM returned None for subtask {self.current_subtask_id}.")
            await self._publish_subtask_failed("LLM returned no response.")
            return False

        raw_calls = response.tool_calls or []
        self.tool_calls = [
            ToolCall(id=tc.id, type=tc.type or "function", function=Function(name=tc.function.name, arguments=tc.function.arguments))
            for tc in raw_calls if tc.function
        ]
        content = response.content or ""
        logger.info(f"✨ Agent {self.name} (subtask {self.current_subtask_id}, step {self.current_step}) thoughts: {content}")
        logger.info(f"🛠️ Planned {len(self.tool_calls)} tool(s): {[tc.function.name for tc in self.tool_calls]}")

        assistant_msg_content = content
        # Se houver chamadas de ferramentas, o LLM pode ter omitido o conteúdo textual.
        # Adicionar um conteúdo padrão se as chamadas de ferramentas existirem mas o conteúdo estiver vazio.
        if self.tool_calls and not assistant_msg_content:
            assistant_msg_content = f"Planning to use tool(s): {[tc.function.name for tc in self.tool_calls]}."

        assistant_msg = Message(role=Role.ASSISTANT, content=assistant_msg_content, tool_calls=self.tool_calls if self.tool_calls else None)
        self.memory.add_message(assistant_msg)
        return bool(self.tool_calls)

    async def act_and_handle_results(self) -> None:
        """Executa as tool_calls planejadas UMA DE CADA VEZ e lida com seus resultados."""
        if not self.tool_calls:
            # Chamado por _process_current_subtask_iteration, mas think() não produziu ferramentas.
            # Isso significa que a subtarefa pode ser uma resposta direta ou já concluída.
            logger.info(f"Agent {self.name}: No tools to execute for subtask {self.current_subtask_id} in act_and_handle_results.")
            # A decisão de concluir a subtarefa é melhor tomada após o `think`.
            # Se `think` retornou False, `_process_current_subtask_iteration` já lidou com isso.
            # Se `think` retornou True mas `tool_calls` está vazio aqui, é um estado inesperado.
            # Vamos assumir que a subtarefa está concluída se não houver mais ferramentas para executar.
            last_message_content = "Subtask processing completed without further tool actions."
            if self.memory.messages and self.memory.messages[-1].role == Role.ASSISTANT and self.memory.messages[-1].content:
                last_message_content = self.memory.messages[-1].content
            await self._publish_subtask_completed(result={"response": last_message_content})
            return

        # Processar uma ferramenta de cada vez, como no loop original de `act`
        # A lista self.tool_calls é consumida aqui.
        command_to_execute = self.tool_calls.pop(0) # Pega a primeira e remove da lista

        # Adiciona mensagem ANTES da execução da ferramenta, indicando a intenção.
        # Isso já é feito em think() quando a mensagem do assistente com tool_calls é adicionada.
        # logger.info(f"Agent {self.name}: Preparing to execute tool '{command_to_execute.function.name}' for subtask {self.current_subtask_id}")

        observation = await self.execute_tool(command_to_execute) # Executa a ferramenta

        # Passar os IDs corretos para handle_tool_result
        await self.handle_tool_result(
            tool_name=command_to_execute.function.name,
            tool_call_id=command_to_execute.id,
            tool_observation=observation,
            subtask_id=self.current_subtask_id,
            workflow_id=str(self.current_workflow_id) # Garante que é string
        )

    async def handle_tool_result(self, tool_name: str, tool_call_id: str, tool_observation: str, subtask_id: str, workflow_id: str) -> None:
        if str(self.current_workflow_id) != workflow_id or self.current_subtask_id != subtask_id:
            logger.warning(f"Agent {self.name} ignoring tool result for mismatched task/subtask. Current: {self.current_workflow_id}/{self.current_subtask_id}, Received: {workflow_id}/{subtask_id}.")
            return

        logger.info(f"Agent {self.name}: Handling tool result for '{tool_name}' (ID: {tool_call_id}) for subtask '{subtask_id}'. Observation: {tool_observation[:200]}...")
        self.update_memory(role=Role.TOOL, content=tool_observation, name=tool_name, tool_call_id=tool_call_id)

        is_error = tool_observation.startswith("Error:")

        # Resetar contador de autocorreção se a ferramenta foi bem-sucedida ou se é uma nova ferramenta
        # Esta lógica precisa ser refinada. Por enquanto, resetamos se não há erro.
        if not is_error:
            self._current_self_correction_attempts = 0

        if is_error:
            if self._can_self_reflect_on_failure() and self._current_self_correction_attempts < self._max_self_correction_attempts_per_tool_error:
                self._current_self_correction_attempts += 1
                logger.info(f"Attempting self-reflection for tool error ({self._current_self_correction_attempts}/{self._max_self_correction_attempts_per_tool_error}).")

                # Encontrar a ToolCall original que falhou
                original_failed_command = None
                last_assistant_msg = next((m for m in reversed(self.memory.messages) if m.role == Role.ASSISTANT and m.tool_calls), None)
                if last_assistant_msg:
                    original_failed_command = next((tc for tc in last_assistant_msg.tool_calls if tc.id == tool_call_id), None)

                if original_failed_command:
                    corrected_tool_call = await self._self_reflection_on_tool_failure(
                        original_command=original_failed_command,
                        failure_observation=tool_observation,
                        task_context=self.current_subtask_prompt or "N/A"
                    )
                    if corrected_tool_call:
                        self.tool_calls = [corrected_tool_call] # Planejar a ação corrigida
                        await self.act_and_handle_results() # Tentar a ação corrigida
                        return
                else:
                    logger.warning(f"Could not find original ToolCall for failed ID {tool_call_id} to perform self-reflection.")

            logger.error(f"Subtask {subtask_id} failed after tool error in '{tool_name}' (self-correction exhausted or not applicable). Error: {tool_observation}")
            await self._publish_subtask_failed(f"Tool '{tool_name}' failed. Observation: {tool_observation}")
        else: # Sem erro na ferramenta
            self._current_self_correction_attempts = 0 # Resetar contador em sucesso
            # Se ainda houver ferramentas planejadas na lista self.tool_calls (após pop(0) em act_and_handle_results), processá-las.
            if self.tool_calls:
                logger.info(f"Agent {self.name}: More tools planned for subtask {self.current_subtask_id}. Continuing...")
                await self.act_and_handle_results() # Processa a próxima ferramenta da lista
            else: # Não há mais ferramentas na lista self.tool_calls desta iteração de `think`
                  # Então, precisamos chamar `think()` novamente para ver se são necessários mais passos para a subtarefa.
                logger.info(f"Agent {self.name}: All planned tools for this cycle executed for subtask {self.current_subtask_id}. Thinking about next step...")
                await self._process_current_subtask_iteration() # Chama o ciclo de novo

    # Os métodos _publish_subtask_completed e _publish_subtask_failed são mantidos como estão.
    async def _publish_subtask_completed(self, result: Any):
        if not self.event_bus:
            logger.error(f"Agent {self.name}: Event bus not available to publish SubtaskCompletedEvent.")
            return
        logger.info(f"Agent {self.name}: Publishing SubtaskCompletedEvent for subtask {self.current_subtask_id}.")
        completion_event = SubtaskCompletedEvent(
            source=self.name,
            task_id=str(self.current_workflow_id),
            subtask_id=self.current_subtask_id,
            result=result
        )
        await self.event_bus.publish("subtask_completion_events", completion_event.model_dump(mode='json'))

    async def _publish_subtask_failed(self, error_message: str, details: Optional[Dict] = None):
        if not self.event_bus:
            logger.error(f"Agent {self.name}: Event bus not available to publish SubtaskFailedEvent.")
            return
        logger.info(f"Agent {self.name}: Publishing SubtaskFailedEvent for subtask {self.current_subtask_id}.")
        failure_event = SubtaskFailedEvent(
            source=self.name,
            task_id=str(self.current_workflow_id),
            subtask_id=self.current_subtask_id,
            error_message=error_message,
            details=details
        )
        await self.event_bus.publish("subtask_failure_events", failure_event.model_dump(mode='json'))

    # `step()` e `should_request_feedback()` de BaseAgent são abstratos
    # e precisam ser implementados aqui ou em Manus.
    async def step(self) -> str:
        # Esta implementação de `step` é para o antigo loop `run` de BaseAgent.
        # No novo modelo, `_process_current_subtask_iteration` é o loop principal por subtarefa.
        # Manter uma implementação simples para compatibilidade se BaseAgent.run fosse chamado.
        logger.warning(f"Agent {self.name}: Legacy step() called. This should ideally be driven by process_action now.")
        await self._process_current_subtask_iteration()
        return f"Step executed for subtask {self.current_subtask_id}. Check logs/events for outcome."

    async def should_request_feedback(self) -> bool:
        # A lógica de solicitar feedback humano agora é uma decisão do `think()` que resulta
        # em uma chamada para a ferramenta `AskHuman`.
        # Este método, no contexto do antigo `BaseAgent.run` loop, não é mais o principal driver.
        return False

    # --- Métodos de Auto-Reflexão ---
    def _can_self_reflect_on_failure(self) -> bool:
        return False # Subclasses como Manus devem sobrescrever

    async def _self_reflection_on_tool_failure(
        self, original_command: ToolCall, failure_observation: str, task_context: str
    ) -> Optional[ToolCall]:
        logger.warning(f"Agent {self.name} _self_reflection_on_tool_failure not implemented. Escalating failure.")
        return None

    async def execute_tool(self, command: ToolCall) -> str:
        from app.tool.sandbox_python_executor import SandboxPythonExecutor

        if not command or not isinstance(command, ToolCall) or not command.function:
            logger.error(f"Invalid command object passed to execute_tool: {command}")
            return "Error: Invalid command object provided to execute_tool."
        name = command.function.name
        if not name: return "Error: Command function name is missing."
        if name not in self.available_tools.tool_map: return f"Error: Unknown tool '{name}'"

        try:
            args = json.loads(command.function.arguments or "{}")
            logger.info(f"[TOOL_EXEC_START] Agent {self.name}: Executing tool '{name}' (ID: {command.id}) for subtask {self.current_subtask_id} with args: {args}")
            tool_output_obj = await self.available_tools.execute(name=name, tool_input=args)
            logger.info(f"[TOOL_EXEC_END] Agent {self.name}: Tool '{name}' (ID: {command.id}) for subtask {self.current_subtask_id} finished.")

            observation = ""
            self._current_base64_image = None
            if isinstance(tool_output_obj, ToolResult):
                if tool_output_obj.base64_image: self._current_base64_image = tool_output_obj.base64_image
                if tool_output_obj.error: observation = f"Error: {tool_output_obj.error}"
                elif tool_output_obj.output is not None: observation = str(tool_output_obj.output)
                if tool_output_obj.system: self.memory.add_message(Message.system_message(tool_output_obj.system))
            elif isinstance(tool_output_obj, str): observation = tool_output_obj
            else:
                observation = f"Error: Tool '{name}' returned unexpected type: {type(tool_output_obj)}. Value: {str(tool_output_obj)[:200]}"
                logger.warning(observation)

            formatted_observation = f"Observed output of tool `{name}` (ID: {command.id}):\n{observation}"
            if observation.startswith("Error:"): formatted_observation = observation # Evitar "Error: Error: ..."

            # Se a ferramenta for Terminate, o evento de conclusão/falha da subtarefa já foi publicado dentro de _publish_...
            # Portanto, não precisamos de lógica especial aqui, apenas retornar a observação.
            # A terminação do workflow/agente será tratada pelo Orchestrator.
            if name.lower() == Terminate().name.lower():
                 logger.info(f"Agent {self.name}: Terminate tool called for subtask {self.current_subtask_id}. Observation: {formatted_observation}")
                 # O evento de conclusão/falha já foi publicado por _handle_special_tool (que não existe mais com essa forma)
                 # ou será publicado por handle_tool_result após esta chamada.
                 # Se Terminate for chamado, significa que o agente decidiu finalizar a subtarefa.
                 # O status (success/failure) é determinado pelos args da ferramenta Terminate.
                 terminate_args = json.loads(command.function.arguments or '{}')
                 term_status = terminate_args.get("status", "success")
                 term_message = terminate_args.get("message", "Task terminated by agent.")
                 if term_status == "failure":
                     # A chamada para _publish_subtask_failed será feita em handle_tool_result se for um erro
                     # ou se o agente explicitamente falhou a tarefa.
                     # Aqui, apenas retornamos a observação. O handle_tool_result fará o resto.
                     pass # Deixar handle_tool_result publicar o evento de falha.
                 else:
                     # Da mesma forma, handle_tool_result publicará o evento de sucesso.
                     pass
            return formatted_observation
        except json.JSONDecodeError:
            err_msg = f"Error parsing arguments for tool {name}: Invalid JSON. Arguments: {command.function.arguments}"
            logger.error(err_msg)
            return f"Error: {err_msg}"
        except Exception as e:
            err_msg = f"Error executing tool '{name}': {str(e)}"
            logger.error(err_msg, exc_info=True)
            return f"Error: {err_msg}"

    async def cleanup(self):
        logger.info(f"ToolCallAgent {self.name} cleanup starting.")
        if self.available_tools:
            for tool_name, tool_instance in self.available_tools.tool_map.items():
                if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                    getattr(tool_instance, "cleanup")
                ):
                    try:
                        logger.debug(f"Cleaning up tool: {tool_name} in agent {self.name}")
                        await tool_instance.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up tool '{tool_name}' in agent {self.name}: {str(e)}")
        await super().cleanup()
        logger.info(f"ToolCallAgent {self.name} cleanup complete.")

# O método _handle_special_tool foi integrado/removido pois Terminate agora é tratado via eventos de conclusão/falha.
# _is_special_tool e _should_finish_execution também são menos relevantes no novo paradigma.
# A decisão de terminar uma subtarefa (e, por extensão, o workflow) é baseada nos eventos.
