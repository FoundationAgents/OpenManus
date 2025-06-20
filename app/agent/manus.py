import os
import uuid
from typing import Dict, List, Optional, Any
from uuid import UUID as UUID_TYPE # Para type hinting do workflow_id

from pydantic import Field, model_validator, PrivateAttr

import json
import re
import ast
from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent, ToolCall
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, Role, Function as FunctionCall
from app.tool import Terminate, ToolCollection
from app.exceptions import ToolError
from app.tool.ask_human import AskHuman
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.file_operators import LocalFileOperator
from app.tool.read_file_content import ReadFileContentTool
from app.tool.checklist_tools import ViewChecklistTool, AddChecklistTaskTool, UpdateChecklistTaskTool, ResetCurrentTaskChecklistTool
from app.tool.file_system_tools import CheckFileExistenceTool, ListFilesTool
from app.agent.checklist_manager import ChecklistManager
from .regex_patterns import re_subprocess
from app.tool.background_process_tools import ExecuteBackgroundProcessTool, CheckProcessStatusTool, GetProcessOutputTool

from app.event_bus.redis_bus import RedisEventBus


INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE = """... (template como antes) ..."""
TOOL_CORRECTION_PROMPT_TEMPLATE = """... (template como antes) ..."""


class Manus(ToolCallAgent):
    name: str = "Manus"
    description: str = "Um agente versátil que pode resolver várias tarefas usando múltiplas ferramentas, incluindo ferramentas baseadas em MCP"
    system_prompt: str = SYSTEM_PROMPT

    _mcp_clients: Optional[MCPClients] = PrivateAttr(default=None)
    _checklist_manager: ChecklistManager = PrivateAttr(default_factory=ChecklistManager)
    _monitoring_background_task: bool = PrivateAttr(default=False)
    _background_task_log_file: Optional[str] = PrivateAttr(default=None)
    _background_task_expected_artifact: Optional[str] = PrivateAttr(default=None)
    _background_task_artifact_path: Optional[str] = PrivateAttr(default=None)
    _background_task_description: Optional[str] = PrivateAttr(default=None)
    _background_task_last_log_size: int = PrivateAttr(default=0)
    _background_task_no_change_count: int = PrivateAttr(default=0)
    _MAX_LOG_NO_CHANGE_TURNS: int = PrivateAttr(default=3)

    _just_resumed_from_feedback_internal: bool = PrivateAttr(default=False) # Para lógica interna do Manus
    _trigger_failure_check_in_internal: bool = PrivateAttr(default=False)

    _pending_script_after_dependency: Optional[str] = PrivateAttr(default=None)
    _original_tool_call_for_pending_script: Optional[ToolCall] = PrivateAttr(default=None)
    _workspace_script_analysis_cache: Optional[Dict[str, Dict[str, Any]]] = PrivateAttr(default=None)
    _current_sandbox_pid: Optional[int] = PrivateAttr(default=None)
    _current_sandbox_pid_file: Optional[str] = PrivateAttr(default=None)
    _current_script_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _fallback_attempted_for_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _pending_fallback_tool_call: Optional[ToolCall] = PrivateAttr(default=None)
    _last_ask_human_for_fallback_id: Optional[str] = PrivateAttr(default=None)
    _autonomous_mode: bool = PrivateAttr(default=False)
    _reset_initiated_by_new_directive: bool = PrivateAttr(default=False)

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name.lower(), AskHuman().name.lower()])
    browser_context_helper: Optional[BrowserContextHelper] = None

    # _MAX_SELF_CORRECTION_ATTEMPTS_PER_STEP e _current_self_correction_attempts são herdados de ToolCallAgent

    def __init__(self, event_bus: RedisEventBus, **data):
        super().__init__(event_bus=event_bus, **data)
        self._mcp_clients = MCPClients()
        self._checklist_manager = ChecklistManager(checklist_filename=f"manus_internal_checklist_{self.current_subtask_id or 'default'}.md")

        self.available_tools = ToolCollection() # Começar com coleção vazia e adicionar
        self.available_tools.add_tools(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            AskHuman(),
            Terminate(), # Adicionar Terminate explicitamente aqui também
            Bash(),
            SandboxPythonExecutor(),
            ReadFileContentTool(),
            ViewChecklistTool(),
            AddChecklistTaskTool(),
            UpdateChecklistTaskTool(),
            ResetCurrentTaskChecklistTool(),
            CheckFileExistenceTool(),
            ListFilesTool(),
            ExecuteBackgroundProcessTool(),
            CheckProcessStatusTool(),
            GetProcessOutputTool(),
            # Adicionar ferramentas de edição de código que estavam em ToolCallAgent
            FormatPythonCode(), ReplaceCodeBlock(), ApplyDiffPatch(), ASTRefactorTool()
        )
        self._initialized = False

    def __getstate__(self):
        state = super().__getstate__()
        state.pop('_mcp_clients', None)
        state.pop('_checklist_manager', None)
        state.pop('browser_context_helper', None)
        # available_tools é recriado em __setstate__
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        self._mcp_clients = MCPClients()
        # O nome do arquivo do checklist pode precisar ser ajustado com base no current_subtask_id,
        # que pode não estar disponível diretamente ao desserializar.
        # Uma solução seria o Orchestrator passar o subtask_id ao restaurar.
        self._checklist_manager = ChecklistManager(checklist_filename=f"manus_internal_checklist_{self.current_subtask_id or 'default_restored'}.md")
        self.browser_context_helper = BrowserContextHelper(self)
        
        self.available_tools = ToolCollection(
            PythonExecute(), BrowserUseTool(), StrReplaceEditor(), AskHuman(), Terminate(),
            Bash(), SandboxPythonExecutor(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(), ResetCurrentTaskChecklistTool(),
            CheckFileExistenceTool(), ListFilesTool(),
            ExecuteBackgroundProcessTool(), CheckProcessStatusTool(), GetProcessOutputTool(),
            FormatPythonCode(), ReplaceCodeBlock(), ApplyDiffPatch(), ASTRefactorTool()
        )
        self._initialized = False
        # self.connected_servers é restaurado por super()

    @model_validator(mode="after")
    def initialize_manus_specific_helpers(self) -> "Manus":
        if not self.browser_context_helper:
            self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, event_bus: RedisEventBus, **kwargs) -> "Manus":
        initial_messages = kwargs.pop('memory_messages', None)
        instance = cls(event_bus=event_bus, **kwargs)
        if initial_messages:
            instance.memory.add_messages(initial_messages)
        logger.info(f"Agente Manus criado. System prompt (primeiros 200 chars): {instance.system_prompt[:200]}")
        # ... (lógica de recuperação de tarefas em background como antes, se mantida) ...
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None: # Implementação como antes
        pass
    async def connect_mcp_server(self, server_url: str, server_id: str = "", use_stdio: bool = False, stdio_args: List[str] = None) -> None:
        pass
    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        pass

    def _can_self_reflect_on_failure(self) -> bool:
        return True

    async def _self_reflection_on_tool_failure(
        self, original_command: ToolCall, failure_observation: str, task_context: str
    ) -> Optional[ToolCall]:
        # ... (implementação como definida anteriormente, usando TOOL_CORRECTION_PROMPT_TEMPLATE) ...
        logger.info(f"Manus: Iniciando auto-reflexão para falha da ferramenta '{original_command.function.name}'.")
        recent_messages_str = "\n".join(
            [f"  - {msg.role}: {msg.content[:150]}..." for msg in self.memory.messages[-3:] if msg.content]
        )
        tool_args_str = original_command.function.arguments
        try:
            parsed_args = json.loads(tool_args_str)
            tool_args_str_for_prompt = json.dumps(parsed_args, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            tool_args_str_for_prompt = tool_args_str
        prompt_for_correction = TOOL_CORRECTION_PROMPT_TEMPLATE.format(
            task_context=task_context, tool_name=original_command.function.name,
            tool_args=tool_args_str_for_prompt, failure_observation=failure_observation,
            recent_messages=recent_messages_str
        )
        try:
            correction_system_prompt = ("Você é um assistente de IA especialista em depurar e corrigir falhas na execução de ferramentas. "
                                        "Analise a falha e forneça uma sugestão de correção no formato JSON especificado.")
            llm_response_str = await self.llm.ask(
                messages=[Message.user_message(content=prompt_for_correction)],
                system_msgs=[Message.system_message(content=correction_system_prompt)],
                temperature=0.1
            )
            suggestion_json_str = self._extract_json_from_response(llm_response_str)
            if suggestion_json_str:
                # ... (lógica de parse do JSON e retorno de ToolCall ou None como antes) ...
                pass # Implementação completa omitida para brevidade, mas segue o já definido
        except Exception as e:
            logger.error(f"Erro durante o ciclo de auto-reflexão do LLM: {e}", exc_info=True)
        return None # Fallback

    async def think(self) -> bool:
        # Adicionar estado do checklist interno ao contexto, se houver
        await self._checklist_manager._load_checklist() # Garante que o checklist interno está carregado
        internal_checklist_tasks = self._checklist_manager.get_tasks()
        if internal_checklist_tasks:
            formatted_checklist = ["Checklist Interno da Subtarefa Atual:"]
            for task in internal_checklist_tasks:
                agent_display = f" [Agente: {task.get('agent')}]" if task.get("agent") else ""
                formatted_checklist.append(f"- [{task.get('status', 'N/A')}]" + agent_display + f" {task.get('description', 'Sem descrição')}")
            self.memory.add_message(Message.system_message("\n".join(formatted_checklist)))

        # Lógica para lidar com _new_task_directive_received para o checklist *interno*
        if self._reset_initiated_by_new_directive: # Esta flag agora seria para o checklist interno
            logger.info(f"Manus: Resetando checklist interno para subtarefa {self.current_subtask_id} devido a nova diretiva.")
            await self._checklist_manager.add_task("Decompor nova diretiva da subtarefa e popular checklist interno.") # Tarefa inicial
            self._reset_initiated_by_new_directive = False
            # O `think` de ToolCallAgent será chamado e provavelmente usará `ViewChecklistTool` ou `AddChecklistTaskTool`
            # para o checklist interno.

        # Lógica do BrowserContextHelper (se este Manus for um agente de navegador)
        # if self.browser_context_helper and "browser" in self.name.lower(): # Melhorar esta verificação
        #    browser_state_prompt = await self.browser_context_helper.format_next_step_prompt()
        #    self.memory.add_message(Message.system_message(f"Contexto do Navegador Atual:\n{browser_state_prompt}"))

        return await super().think() # Chama o think de ToolCallAgent

    async def handle_tool_result(self, tool_name: str, tool_call_id: str, tool_observation: str, subtask_id: str, workflow_id: str) -> None:
        await super().handle_tool_result(tool_name, tool_call_id, tool_observation, subtask_id, workflow_id)

        # Se super().handle_tool_result já decidiu falhar a subtarefa (e.g., após auto-correção falhar), não fazer mais nada.
        # Precisamos de uma forma de verificar isso. Por enquanto, se tool_calls não foi preenchido por uma correção:
        if not self.tool_calls and not tool_observation.startswith("Error:"): # Se não houve erro ou foi corrigido

            is_manus_checklist_complete = await self._is_internal_checklist_complete_for_subtask()
            ask_human_planned_tool_call: Optional[ToolCall] = None

            if is_manus_checklist_complete:
                logger.info(f"Manus: Checklist interno para subtarefa {self.current_subtask_id} completo.")
                if not self._autonomous_mode:
                    ask_human_planned_tool_call = await self.periodic_user_check_in(is_final_check=True)
                else:
                    logger.info(f"Manus: Modo autônomo. Marcando subtarefa {self.current_subtask_id} como concluída.")
                    await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída autonomamente."})
                    return

            elif not self._autonomous_mode and self.current_step > 0 and \
                 self.max_steps_per_subtask > 0 and \
                 self.current_step % (self.max_steps_per_subtask // 2) == 0 and \
                 self.current_step < self.max_steps_per_subtask: # Check-in no meio da subtarefa
                ask_human_planned_tool_call = await self.periodic_user_check_in(is_final_check=False, is_failure_scenario=False)

            if ask_human_planned_tool_call:
                self.tool_calls = [ask_human_planned_tool_call]
                await self.act()
                return

            if not is_manus_checklist_complete:
                logger.info(f"Manus: Subtarefa {self.current_subtask_id} não concluída e sem input humano pendente. Novo ciclo de think.")
                await self._process_current_subtask_iteration() # Continua a subtarefa
            elif self._autonomous_mode and is_manus_checklist_complete:
                 await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída autonomamente."})
            else: # Checklist completo, não autônomo, mas sem AskHuman (talvez periodic_user_check_in retornou None)
                logger.warning(f"Manus: Checklist interno completo para {self.current_subtask_id}, mas sem AskHuman final. Concluindo subtarefa.")
                await self._publish_subtask_completed(result={"response": f"Subtarefa {self.current_subtask_id} concluída."})


    async def _is_internal_checklist_complete_for_subtask(self) -> bool:
        await self._checklist_manager._load_checklist()
        if not self._checklist_manager.get_tasks():
            # Se o prompt da subtarefa for muito simples, pode não precisar de checklist interno.
            # Considerar o prompt da subtarefa atual (self.current_subtask_prompt) para decidir.
            # Por agora, se não há checklist interno, consideramos "não aplicável" ou "completo" para não bloquear.
            # Isso precisa de uma heurística melhor. Se o SYSTEM_PROMPT sempre instrui a criar, então
            # um checklist vazio após o primeiro `think` pode significar que a subtarefa é trivial.
            # Vamos assumir que se o checklist está vazio, a parte gerenciada pelo Manus está "completa".
            if self.current_step > 1: # Se já passou do primeiro passo de think
                 logger.info(f"Manus: Checklist interno para subtarefa {self.current_subtask_id} está vazio após o passo inicial. Considerando completo.")
                 return True
            return False # No primeiro passo, um checklist vazio significa que precisa ser populado.
        return self._checklist_manager.are_all_tasks_complete()

    async def periodic_user_check_in(self, is_final_check: bool = False, is_failure_scenario: bool = False) -> Optional[ToolCall]:
        # ... (lógica adaptada como antes para construir a pergunta) ...
        # Esta lógica precisa ser robusta. Usar o INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE
        # para gerar o `relatorio_autoanalise` como antes.
        # Por enquanto, uma pergunta placeholder:
        question_for_human = "Este é um check-in. Como devo proceder com a subtarefa?"
        if is_final_check:
            question_for_human = f"O checklist interno para a subtarefa '{self.current_subtask_id}' parece completo. Deseja marcar esta subtarefa como concluída?"
        if is_failure_scenario:
            # Aqui, o `relatorio_autoanalise` seria sobre a falha da subtarefa do Manus.
            question_for_human = f"Encontrei um problema com a subtarefa '{self.current_subtask_id}'. [Relatório de Análise da Falha da Subtarefa aqui]. Como devo proceder?"

        logger.info(f"Manus: Planejando AskHuman para check-in na subtarefa {self.current_subtask_id}: {question_for_human[:100]}")

        # Obter o ID do último checkpoint relevante. O Orchestrator pode precisar passar isso para o agente.
        # Ou o agente pode precisar de acesso ao checkpointer para encontrar o último checkpoint para este workflow/subtarefa.
        # Por agora, deixaremos como None.
        relevant_checkpoint_id = None
        # Se o agente tivesse acesso ao checkpointer:
        # if self.checkpointer and self.current_workflow_id:
        #    latest_chkpt_data = await self.checkpointer.load_latest_checkpoint_data(self.current_workflow_id)
        #    if latest_chkpt_data: relevant_checkpoint_id = str(latest_chkpt_data["checkpoint_id"])

        ask_human_args = {
            "inquire": question_for_human,
            "workflow_id": str(self.current_workflow_id) if self.current_workflow_id else "unknown_workflow",
            "subtask_id": self.current_subtask_id or "unknown_subtask",
            "relevant_checkpoint_id": relevant_checkpoint_id
        }
        return ToolCall(
            id=f"ask_human_manus_{uuid.uuid4().hex[:4]}",
            function=FunctionCall(name=AskHuman().name, arguments=json.dumps(ask_human_args))
        )

    async def cleanup(self): # Sobrescreve cleanup de ToolCallAgent
        logger.info(f"Manus ({self.name}) cleanup starting.")
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._mcp_clients and self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False
        await super().cleanup() # Chama ToolCallAgent.cleanup() que chama BaseAgent.cleanup()
        logger.info(f"Manus ({self.name}) cleanup complete.")

    # Métodos auxiliares mantidos
    def _sanitize_text_for_file(self, text_content: str) -> str: # ... (como antes) ...
        if not isinstance(text_content, str): return text_content
        return text_content.replace('\u0000', '')
    def _extract_python_code(self, text: str) -> str: # ... (como antes) ...
        if "```python" in text: return text.split("```python")[1].split("```")[0].strip()
        if "```" in text: return text.split("```")[1].split("```")[0].strip()
        return text.strip()
    async def _execute_self_coding_cycle(self, task_prompt_for_llm: str, max_attempts: int = 3) -> Dict[str, Any]: # ... (como antes, mas usando self.available_tools.get_tool) ...
        logger.info(f"Iniciando ciclo de auto-codificação para tarefa: {task_prompt_for_llm}")
        # ... (implementação completa omitida para brevidade, mas deve usar self.available_tools.get_tool)
        return {"success": False, "message": "Self-coding cycle not fully implemented in this refactor."}
    def _extract_json_from_response(self, llm_response: str) -> Optional[str]: # ... (como antes) ...
        logger.debug(f"Tentando extrair JSON da resposta do LLM: '{llm_response[:500]}...'")
        match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response)
        if match: return match.group(1).strip()
        response_stripped = llm_response.strip()
        if response_stripped.startswith("{") and response_stripped.endswith("}"): return response_stripped
        logger.warning("Nenhum bloco de código JSON encontrado na resposta do LLM para extração.")
        return None
    def _build_targeted_analysis_prompt(self, script_content: str, stdout: str, stderr: str, original_task: str) -> str: # ... (como antes) ...
        return f"Analysis prompt for {original_task}..." # Placeholder
    async def _analyze_python_script(self, script_path: str, script_content: Optional[str] = None) -> Dict[str, Any]: # ... (como antes) ...
        return {"inputs": [], "outputs": [], "libraries": []}
    async def _analyze_workspace(self) -> Dict[str, Dict[str, Any]]: # ... (como antes) ...
        return {}
    async def _initiate_sandbox_script_cancellation(self): # ... (como antes) ...
        pass
    async def _cleanup_sandbox_file(self, file_path_in_sandbox: str): # ... (como antes) ...
        pass

# Remover a lógica de `think` de Manus que foi movida para ToolCallAgent ou não é mais necessária.
# O `think` de Manus agora pode focar em preparar contexto para `super().think()` e
# em decidir se um `AskHuman` é necessário após as ferramentas planejadas por `super().think()`.
# A lógica de fallback do sandbox e outras lógicas específicas do Manus podem ser
# re-integradas como ferramentas ou como parte do `think` do Manus se ele decidir
# não chamar `super().think()` em certos casos.
# Por agora, a sobrescrita de `think` e `handle_tool_result` acima é o foco.
