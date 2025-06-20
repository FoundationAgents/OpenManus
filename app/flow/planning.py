import json
import time # Mantido para gerar plan_id padrão
from typing import Dict, List, Optional, Union, Any # Adicionado Any
from uuid import UUID, uuid4 # Adicionado UUID

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
# Removido AgentState, pois o fluxo não gerencia mais o estado do agente diretamente
# from app.schema import AgentState, Message, ToolChoice
from app.schema import Message, ToolChoice # Manter Message e ToolChoice para _create_initial_plan
from app.tool.planning import PlanningTool, Plan as PlanModel, Subtask as SubtaskModel # PlanningTool refatorada
from app.event_bus.redis_bus import RedisEventBus # Adicionado
from app.event_bus.events import TaskCreatedEvent, TaskInfo # Adicionado

# PlanStepStatus não é mais usado diretamente por PlanningFlow
# class PlanStepStatus(str, Enum): ...


class PlanningFlow(BaseFlow):
    """
    Um fluxo que inicia o planejamento de tarefas.
    Ele cria um plano inicial (DAG de subtarefas) e publica um TaskCreatedEvent
    para o WorkflowOrchestrator processar.
    """

    llm: LLM = Field(default_factory=LLM)
    planning_tool: PlanningTool = Field(default_factory=PlanningTool) # PlanningTool refatorada
    event_bus: RedisEventBus # Deve ser injetado

    # executor_keys e active_plan_id podem não ser mais necessários aqui,
    # pois o plano é gerenciado pela PlanningTool e executado pelo Orchestrator.
    # O active_plan_id será gerado e usado para o TaskCreatedEvent.

    def __init__(
        self,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        event_bus: RedisEventBus, # Injetar event_bus
        **data
    ):
        # PlanningTool é default_factory, então será criada se não fornecida em data.
        super().__init__(agents, **data) # Passar agents e data para BaseFlow
        self.event_bus = event_bus
        if not self.event_bus.redis_client or not self.event_bus.redis_client.is_connected:
            logger.warning("PlanningFlow: RedisEventBus não parece estar conectado. Tentará conectar ao publicar.")


    # get_executor não é mais relevante para PlanningFlow, pois ele não executa passos.
    # async def get_executor(self, step_type: Optional[str] = None) -> BaseAgent: ...

    async def execute(self, input_text: str) -> str:
        """
        Inicia o fluxo de planejamento: cria um plano DAG e publica um TaskCreatedEvent.
        Retorna uma mensagem indicando que a tarefa foi iniciada.
        """
        if not self.primary_agent: # primary_agent é definido em BaseFlow
            # Embora o primary_agent não seja usado para executar passos aqui,
            # ele pode ser usado por _create_initial_plan se o LLM for chamado diretamente do agente.
            # No entanto, _create_initial_plan usa self.llm diretamente.
            logger.warning("Nenhum agente primário definido para PlanningFlow, mas _create_initial_plan usa self.llm.")
            # raise ValueError("Nenhum agente primário disponível")

        # Gerar um ID único para este workflow/tarefa
        workflow_id = uuid4()
        plan_id_for_tool = f"plan_{workflow_id.hex}" # Usar o ID do workflow para o plan_id da PlanningTool

        try:
            # 1. Criar o plano inicial (DAG de subtarefas)
            # _create_initial_plan agora deve retornar o objeto PlanModel ou um dict representando o DAG
            initial_plan_dag_dict: Optional[Dict[str, Any]] = await self._create_initial_plan(
                request=input_text,
                plan_id_for_tool=plan_id_for_tool
            )

            if not initial_plan_dag_dict:
                error_msg = f"Falha ao criar plano inicial para a solicitação: {input_text}"
                logger.error(error_msg)
                # Poderia publicar um TaskCreationFailedEvent aqui
                return error_msg

            # 2. Publicar TaskCreatedEvent
            task_info = TaskInfo(task_id=str(workflow_id))
            task_created_event = TaskCreatedEvent(
                source="PlanningFlow",
                task_info=task_info,
                user_prompt=input_text,
                initial_plan=initial_plan_dag_dict # O DAG das subtarefas
            )

            if not self.event_bus.redis_client or not self.event_bus.redis_client.is_connected:
                logger.info("PlanningFlow: Conectando ao event_bus antes de publicar.")
                await self.event_bus.connect()

            await self.event_bus.publish("task_creation_events", task_created_event.model_dump(mode='json'))

            success_msg = f"Tarefa '{initial_plan_dag_dict.get('title', 'N/A')}' iniciada com Workflow ID: {workflow_id}. O progresso será gerenciado de forma assíncrona."
            logger.info(success_msg)
            return success_msg

        except Exception as e:
            logger.error(f"Erro em PlanningFlow.execute para '{input_text}': {str(e)}", exc_info=True)
            # Publicar um evento de falha na criação da tarefa, se apropriado
            return f"Execução do fluxo de planejamento falhou: {str(e)}"

    async def _create_initial_plan(self, request: str, plan_id_for_tool: str) -> Optional[Dict[str, Any]]:
        """
        Cria um plano inicial (DAG) usando o LLM e a PlanningTool.
        Retorna um dicionário representando o PlanModel ou None em caso de falha.
        """
        logger.info(f"PlanningFlow: Criando plano DAG inicial com ID da ferramenta: {plan_id_for_tool} para request: '{request[:100]}...'")

        system_message = Message.system_message(
            "Você é um assistente de planejamento especialista. Dada uma tarefa do usuário, "
            "decomponha-a em um conjunto de subtarefas. Para cada subtarefa, forneça um ID único, "
            "um nome descritivo, e uma lista dos IDs das subtarefas das quais ela depende diretamente. "
            "Se uma subtarefa não tiver dependências, sua lista `depends_on` deve ser vazia. "
            "O objetivo é criar um plano que possa ser executado com paralelismo onde possível. "
            "Responda usando a ferramenta 'planning' com o comando 'create_plan'."
        )
        user_message = Message.user_message(
            f"Crie um plano detalhado com subtarefas e suas dependências para a seguinte solicitação: {request}"
        )

        try:
            response = await self.llm.ask_tool(
                messages=[user_message],
                system_msgs=[system_message],
                tools=[self.planning_tool.to_param()], # Passa o schema da PlanningTool
                tool_choice=ToolChoice.REQUIRED, # Forçar o uso da PlanningTool
            )

            if response and response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call.function.name == self.planning_tool.name: # "planning"
                        args_str = tool_call.function.arguments
                        try:
                            args = json.loads(args_str)
                        except json.JSONDecodeError:
                            logger.error(f"Falha ao decodificar argumentos JSON da PlanningTool: {args_str}")
                            return None

                        # Garantir que o comando correto seja usado e o plan_id seja passado
                        if args.get("command") == "create_plan":
                            args["plan_id"] = plan_id_for_tool # Sobrescrever ou definir o plan_id

                            # A PlanningTool.execute agora deve retornar um ToolResult
                            # e o plano criado (objeto Plan) estará em self.planning_tool.plans[plan_id_for_tool]
                            tool_result: ToolResult = await self.planning_tool.execute(**args)

                            if tool_result.error:
                                logger.error(f"Erro ao criar plano via PlanningTool: {tool_result.error}")
                                return None

                            # Obter o objeto Plan recém-criado da ferramenta
                            created_plan_obj: Optional[PlanModel] = self.planning_tool.plans.get(plan_id_for_tool)
                            if created_plan_obj:
                                logger.info(f"Plano DAG criado com sucesso pela PlanningTool: {plan_id_for_tool}")
                                return created_plan_obj.model_dump(mode='json')
                            else:
                                logger.error(f"PlanningTool executou create_plan mas o plano {plan_id_for_tool} não foi encontrado em seu armazenamento.")
                                return None
                        else:
                            logger.error(f"LLM tentou usar a PlanningTool com comando inesperado '{args.get('command')}' em vez de 'create_plan'.")
                            return None

            logger.error("LLM não usou a PlanningTool como esperado para criar o plano.")
            return None

        except Exception as e:
            logger.error(f"Erro durante a chamada ao LLM para criação do plano: {e}", exc_info=True)
            return None

    # Métodos _get_current_step_info, _execute_step, _mark_step_completed,
    # _get_plan_text, _generate_plan_text_from_storage, _finalize_plan
    # não são mais responsabilidade direta do PlanningFlow.
    # O WorkflowOrchestrator e a PlanningTool (com seus comandos get_plan_details, etc.)
    # agora lidam com o estado e a visualização do plano.

    async def cleanup(self): # Adicionado para consistência, embora PlanningFlow não tenha muito estado para limpar
        logger.info(f"PlanningFlow ({self.primary_agent.name if self.primary_agent else 'N/A'}) cleanup.")
        # O event_bus é gerenciado externamente.
        # A planning_tool pode ter estado (self.plans), mas é limpo com a instância.
        await super().cleanup() # Chama cleanup de BaseFlow, que chama cleanup dos agentes
