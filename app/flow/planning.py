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
    """Classe Enum que define os status possíveis de um passo do plano"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """Retorna uma lista de todos os valores de status de passo possíveis"""
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """Retorna uma lista de valores que representam status ativos (não iniciado ou em progresso)"""
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """Retorna um mapeamento de status para seus símbolos marcadores"""
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }


class PlanningFlow(BaseFlow):
    """Um fluxo que gerencia o planejamento e a execução de tarefas usando agentes."""

    llm: LLM = Field(default_factory=lambda: LLM())
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)
    executor_keys: List[str] = Field(default_factory=list)
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Define as chaves do executor antes de super().__init__
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # Define o ID do plano se fornecido
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")

        # Inicializa a ferramenta de planejamento se não fornecida
        if "planning_tool" not in data:
            planning_tool = PlanningTool()
            data["planning_tool"] = planning_tool

        # Chama o init do pai com os dados processados
        super().__init__(agents, **data)

        # Define executor_keys para todas as chaves de agente se não especificado
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """
        Obtém um agente executor apropriado para o passo atual.
        Pode ser estendido para selecionar agentes com base no tipo/requisitos do passo.
        """
        # Se o tipo de passo for fornecido e corresponder a uma chave de agente, use esse agente
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # Caso contrário, use o primeiro executor disponível ou recorra ao agente primário
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # Recorrer ao agente primário
        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """Executa o fluxo de planejamento com agentes."""
        try:
            if not self.primary_agent:
                raise ValueError("Nenhum agente primário disponível")

            # Cria plano inicial se a entrada for fornecida
            if input_text:
                await self._create_initial_plan(input_text)

                # Verifica se o plano foi criado com sucesso
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(
                        f"Criação do plano falhou. ID do plano {self.active_plan_id} não encontrado na ferramenta de planejamento."
                    )
                    return f"Falha ao criar plano para: {input_text}"

            result = ""
            while True:
                # Obtém o passo atual para executar
                self.current_step_index, step_info = await self._get_current_step_info()

                # Sai se não houver mais passos ou se o plano estiver concluído
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # Executa o passo atual com o agente apropriado
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)
                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # Verifica se o agente quer encerrar
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return result
        except Exception as e:
            logger.error(f"Erro em PlanningFlow: {str(e)}")
            return f"Execução falhou: {str(e)}"

    async def _create_initial_plan(self, request: str) -> None:
        """Cria um plano inicial com base na solicitação usando o LLM e PlanningTool do fluxo."""
        logger.info(f"Criando plano inicial com ID: {self.active_plan_id}")

        # Cria uma mensagem de sistema para criação do plano
        system_message = Message.system_message(
            "Você é um assistente de planejamento. Crie um plano conciso e acionável com passos claros. "
            "Concentre-se em marcos chave em vez de sub-passos detalhados. "
            "Otimize para clareza e eficiência."
        )

        # Cria uma mensagem de usuário com a solicitação
        user_message = Message.user_message(
            f"Crie um plano razoável com passos claros para realizar a tarefa: {request}"
        )

        # Chama LLM com PlanningTool
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.AUTO,
        )

        # Processa chamadas de ferramenta se presentes
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # Analisa os argumentos
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"Falha ao analisar argumentos da ferramenta: {args}")
                            continue

                    # Garante que plan_id esteja definido corretamente e executa a ferramenta
                    args["plan_id"] = self.active_plan_id

                    # Executa a ferramenta via ToolCollection em vez de diretamente
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"Resultado da criação do plano: {str(result)}")
                    return

        # Se a execução chegou aqui, cria um plano padrão
        logger.warning("Criando plano padrão")

        # Cria plano padrão usando ToolCollection
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"Plano para: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["Analisar solicitação", "Executar tarefa", "Verificar resultados"],
            }
        )

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Analisa o plano atual para identificar o índice e as informações do primeiro passo não concluído.
        Retorna (None, None) se nenhum passo ativo for encontrado.
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"Plano com ID {self.active_plan_id} não encontrado")
            return None, None

        try:
            # Acesso direto aos dados do plano do armazenamento da ferramenta de planejamento
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Encontra o primeiro passo não concluído
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = PlanStepStatus.NOT_STARTED.value
                else:
                    status = step_statuses[i]

                if status in PlanStepStatus.get_active_statuses():
                    # Extrai o tipo/categoria do passo se disponível
                    step_info = {"text": step}

                    # Tenta extrair o tipo de passo do texto (ex: [SEARCH] ou [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Marca o passo atual como em_progresso
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status=PlanStepStatus.IN_PROGRESS.value,
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao marcar passo como em_progresso: {e}")
                        # Atualiza o status do passo diretamente se necessário
                        if i < len(step_statuses):
                            step_statuses[i] = PlanStepStatus.IN_PROGRESS.value
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
                            step_statuses.append(PlanStepStatus.IN_PROGRESS.value)

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # Nenhum passo ativo encontrado

        except Exception as e:
            logger.warning(f"Erro ao encontrar índice do passo atual: {e}")
            return None, None

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """Executa o passo atual com o agente especificado usando agent.run()."""
        # Prepara o contexto para o agente com o status atual do plano
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"Passo {self.current_step_index}")

        # Cria um prompt para o agente executar o passo atual
        step_prompt = f"""
        STATUS ATUAL DO PLANO:
        {plan_status}

        SUA TAREFA ATUAL:
        Você está trabalhando no passo {self.current_step_index}: "{step_text}"

        Por favor, execute este passo usando as ferramentas apropriadas. Quando terminar, forneça um resumo do que você realizou.
        """

        # Usa agent.run() para executar o passo
        try:
            step_result = await executor.run(step_prompt)

            # Marca o passo como concluído após execução bem-sucedida
            await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"Erro ao executar passo {self.current_step_index}: {e}")
            return f"Erro ao executar passo {self.current_step_index}: {str(e)}"

    async def _mark_step_completed(self) -> None:
        """Marca o passo atual como concluído."""
        if self.current_step_index is None:
            return

        try:
            # Marca o passo como concluído
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.COMPLETED.value,
            )
            logger.info(
                f"Marcado passo {self.current_step_index} como concluído no plano {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Falha ao atualizar status do plano: {e}")
            # Atualiza o status do passo diretamente no armazenamento da ferramenta de planejamento
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # Garante que a lista step_statuses seja longa o suficiente
                while len(step_statuses) <= self.current_step_index:
                    step_statuses.append(PlanStepStatus.NOT_STARTED.value)

                # Atualiza o status
                step_statuses[self.current_step_index] = PlanStepStatus.COMPLETED.value
                plan_data["step_statuses"] = step_statuses

    async def _get_plan_text(self) -> str:
        """Obtém o plano atual como texto formatado."""
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Erro ao obter plano: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Gera texto do plano diretamente do armazenamento se a ferramenta de planejamento falhar."""
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Erro: Plano com ID {self.active_plan_id} não encontrado"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "Plano sem título")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # Garante que step_statuses e step_notes correspondam ao número de passos
            while len(step_statuses) < len(steps):
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            while len(step_notes) < len(steps):
                step_notes.append("")

            # Conta passos por status
            status_counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts[PlanStepStatus.COMPLETED.value]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plano: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"Progresso: {completed}/{total} passos concluídos ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} concluídos, {status_counts[PlanStepStatus.IN_PROGRESS.value]} em progresso, "
            plan_text += f"{status_counts[PlanStepStatus.BLOCKED.value]} bloqueados, {status_counts[PlanStepStatus.NOT_STARTED.value]} não iniciados\n\n"
            plan_text += "Passos:\n"

            status_marks = PlanStepStatus.get_status_marks()

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                # Usa marcas de status para indicar o status do passo
                status_mark = status_marks.get(
                    status, status_marks[PlanStepStatus.NOT_STARTED.value]
                )

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   Notas: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Erro ao gerar texto do plano do armazenamento: {e}")
            return f"Erro: Não foi possível recuperar o plano com ID {self.active_plan_id}"

    async def _finalize_plan(self) -> str:
        """Finaliza o plano e fornece um resumo usando o LLM do fluxo diretamente."""
        plan_text = await self._get_plan_text()

        # Cria um resumo usando o LLM do fluxo diretamente
        try:
            system_message = Message.system_message(
                "Você é um assistente de planejamento. Sua tarefa é resumir o plano concluído."
            )

            user_message = Message.user_message(
                f"O plano foi concluído. Aqui está o status final do plano:\n\n{plan_text}\n\nPor favor, forneça um resumo do que foi realizado e quaisquer considerações finais."
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"Plano concluído:\n\n{response}"
        except Exception as e:
            logger.error(f"Erro ao finalizar plano com LLM: {e}")

            # Recorrer ao uso de um agente para o resumo
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                O plano foi concluído. Aqui está o status final do plano:

                {plan_text}

                Por favor, forneça um resumo do que foi realizado e quaisquer considerações finais.
                """
                summary = await agent.run(summary_prompt)
                return f"Plano concluído:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Erro ao finalizar plano com agente: {e2}")
                return "Plano concluído. Erro ao gerar resumo."
